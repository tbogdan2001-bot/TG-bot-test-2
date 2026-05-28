# accounts.py
# NEW: Multi-Account Manager System using Telethon userbots
# Automates first-contact private messages to new group members,
# tracks conversation replies to automatically halt re-engagement,
# and runs a scheduled background checker to deliver Day 1, 3, 5 follow-ups.
# - Extended to support Multi-Group Manager Rotation (Feature 3) using SQLite-backed round-robin rotation.
# FIXED: Replaced deprecated NewMessage(private=True) with NewMessage(func=lambda e: e.is_private)

import asyncio
import logging
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.tl.types import ChannelParticipantsRecent

import config
import database
from scheduler import scheduler  # Shared APScheduler instance

logger = logging.getLogger(__name__)

# Registry for authorized running Telethon clients (session_name -> TelegramClient)
active_clients = {}

async def is_group_assigned_to_manager(session_name: str, chat_id: int, chat_username: str = None) -> bool:
    """Helper to check if a group is assigned to a manager session in database."""
    assigned_groups = await database.get_assigned_groups_for_manager(session_name)
    chat_id_str = str(chat_id)
    alt_chat_id_str = chat_id_str
    if chat_id_str.startswith("-100"):
        alt_chat_id_str = chat_id_str[4:]
    elif not chat_id_str.startswith("-"):
        alt_chat_id_str = f"-100{chat_id_str}"
        
    for g_id in assigned_groups:
        g_id_str = str(g_id)
        if g_id_str == chat_id_str or g_id_str == alt_chat_id_str:
            return True
        if chat_username and g_id_str.lower() == chat_username.lower():
            return True
    return False

async def assign_groups_to_managers():
    """
    Ensures all groups in config.MANAGER_GROUPS are assigned to a manager session.
    Implements round-robin assignment targeting session with fewest assignments (max 3).
    """
    db = database.get_db()
    
    # 1. Fetch current assignments
    async with db.execute("SELECT session_name, group_id FROM manager_assignments") as cursor:
        rows = await cursor.fetchall()
        existing_assignments = {row[1]: row[0] for row in rows} # group_id -> session_name
        
    # 2. Identify sessions from config
    sessions = [mgr["session"] for mgr in config.MANAGER_ACCOUNTS]
    if not sessions:
        logger.warning("No manager accounts configured in config.MANAGER_ACCOUNTS.")
        return
        
    # 3. For each group in config.MANAGER_GROUPS
    for group in config.MANAGER_GROUPS:
        group_id = str(group["group_id"])
        
        # Check if already assigned
        if group_id in existing_assignments:
            # Check if the assigned session is still in config
            if existing_assignments[group_id] in sessions:
                continue
            else:
                # Assigned manager no longer exists in config, delete assignment so it can be reassigned
                await db.execute("DELETE FROM manager_assignments WHERE group_id = ?", (group_id,))
                await db.commit()
                
        # Needs assignment! Find session with fewest assignments (max 3)
        session_counts = {}
        for s in sessions:
            # Count current assignments in database
            async with db.execute("SELECT COUNT(*) FROM manager_assignments WHERE session_name = ?", (s,)) as c:
                count = (await c.fetchone())[0] or 0
                session_counts[s] = count
                
        # Filter sessions with < 3 assignments
        eligible_sessions = {s: count for s, count in session_counts.items() if count < 3}
        if not eligible_sessions:
            logger.error(f"Cannot assign group {group_id} ({group['name']}): all managers have reached the max of 3 assignments.")
            continue
            
        # Pick the one with the fewest assignments
        assigned_session = min(eligible_sessions, key=eligible_sessions.get)
        
        # Insert assignment
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        await db.execute("""
            INSERT OR REPLACE INTO manager_assignments (session_name, group_id, assigned_at)
            VALUES (?, ?, ?)
        """, (assigned_session, group_id, now_str))
        await db.commit()
        logger.info(f"Assigned group {group_id} ({group['name']}) to manager session '{assigned_session}' (assignments count: {eligible_sessions[assigned_session] + 1})")

async def register_chat_event_listeners(session_name: str, client: TelegramClient, mgr_cfg: dict):
    """Registers real-time join events and incoming reply listeners for a userbot client."""
    persona_id = mgr_cfg["persona_id"]
    persona = config.PERSONAS.get(persona_id)
    if not persona:
        logger.error(f"Persona '{persona_id}' not found for userbot '{session_name}'. Skipping listener setup.")
        return

    # 1. Listen for new members joining target groups
    @client.on(events.ChatAction)
    async def handle_new_member(event):
        # We check if a user joined or was added to the group
        if event.user_joined or event.user_added:
            try:
                # Retrieve chat entity to resolve group name
                chat = await event.get_chat()
                chat_username = f"@{chat.username}" if getattr(chat, "username", None) else None
                
                # Check if this group is assigned to this manager session in SQLite (Feature 2 Rotation)
                is_monitored = await is_group_assigned_to_manager(session_name, chat.id, chat_username)
                if not is_monitored:
                    return
                
                user_id = event.user_id
                logger.info(f"Userbot '{session_name}' detected new member {user_id} in group '{chat.title}'.")
                
                # Formulate first contact message
                group_name = chat.title or "нашу группу"
                text = config.FIRST_MESSAGE_SCRIPT.format(
                    group_name=group_name,
                    persona_name=persona["name"],
                    niche=persona["niche"]
                )
                
                # Send first contact PM
                await client.send_message(user_id, text)
                logger.info(f"Userbot '{session_name}' sent first contact to {user_id}.")
                
                # Log step 0 to database
                await database.log_manager_message(session_name, user_id, 0)
                
            except Exception as e:
                logger.error(f"Userbot '{session_name}' failed to process join event: {e}", exc_info=True)

    # 2. Listen for incoming private messages to detect user replies
    # FIXED: private=True is deprecated in newer Telethon versions, use func=lambda instead
    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def handle_reply(event):
        try:
            sender_id = event.sender_id
            logger.info(f"Userbot '{session_name}' received incoming message from user {sender_id}. Marking as replied.")
            
            # Automatically mark as replied to halt all future automated follow-up steps
            await database.mark_replied(session_name, sender_id)
            
        except Exception as e:
            logger.error(f"Userbot '{session_name}' failed to handle reply marking: {e}", exc_info=True)

    logger.info(f"Event listeners successfully registered for userbot session '{session_name}'.")

async def send_as_manager(session_name: str, chat_id: int, text: str) -> bool:
    """Sends a private message to a specific user using the active Telethon client session."""
    client = active_clients.get(session_name)
    if not client:
        logger.error(f"Manager session '{session_name}' is not running or active.")
        return False
        
    try:
        await client.send_message(chat_id, text)
        logger.info(f"Sent message to user {chat_id} from manager session '{session_name}'.")
        return True
    except Exception as e:
        logger.error(f"Failed to send message from manager session '{session_name}' to user {chat_id}: {e}")
        return False

async def check_manager_followups(session_name: str):
    """
    Periodic check to trigger Day 1, 3, 5 userbot follow-ups.
    If a user has replied (replied=1), followups are naturally bypassed.
    """
    client = active_clients.get(session_name)
    if not client:
        return
        
    mgr_cfg = next((m for m in config.MANAGER_ACCOUNTS if m["session"] == session_name), None)
    if not mgr_cfg:
        return
        
    persona = config.PERSONAS.get(mgr_cfg["persona_id"])
    if not persona:
        return
        
    logger.info(f"Running periodic follow-up checks for userbot '{session_name}'...")
    
    # Day 1 Followup: 24h since Step 0 -> Send Step 1
    pending_step1 = await database.get_pending_followups(session_name, step=0, hours_since=24.0)
    for user_id in pending_step1:
        text = config.FOLLOWUP_SCRIPTS[0].format(
            persona_name=persona["name"],
            niche=persona["niche"]
        )
        if await send_as_manager(session_name, user_id, text):
            await database.log_manager_message(session_name, user_id, 1)
            
    # Day 3 Followup: 48h since Step 1 (72h since Step 0) -> Send Step 2
    pending_step2 = await database.get_pending_followups(session_name, step=1, hours_since=48.0)
    for user_id in pending_step2:
        text = config.FOLLOWUP_SCRIPTS[1].format(
            persona_name=persona["name"],
            niche=persona["niche"]
        )
        if await send_as_manager(session_name, user_id, text):
            await database.log_manager_message(session_name, user_id, 2)
            
    # Day 5 Followup: 48h since Step 2 (120h since Step 0) -> Send Step 3
    pending_step3 = await database.get_pending_followups(session_name, step=2, hours_since=48.0)
    for user_id in pending_step3:
        # Resolve target channel link dynamically
        text = config.FOLLOWUP_SCRIPTS[2].format(
            persona_name=persona["name"],
            niche=persona["niche"],
            channel_link=config.CHANNEL_LINK
        )
        if await send_as_manager(session_name, user_id, text):
            await database.log_manager_message(session_name, user_id, 3)

async def start_manager_accounts():
    """
    Initializes and starts all configured Telethon manager userbots.
    Grades auth checks non-blockingly so the main bot runs smoothly.
    """
    if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
        logger.warning("TELEGRAM_API_ID or TELEGRAM_API_HASH is not set. Skipping Multi-Account userbots.")
        return
        
    # Ensure Multi-Group Manager Assignments are populated (Feature 2 Rotation)
    await assign_groups_to_managers()
    
    logger.info("Initializing multi-account manager userbots...")
    
    for mgr in config.MANAGER_ACCOUNTS:
        session_name = mgr["session"]
        try:
            logger.info(f"Connecting to Telethon session '{session_name}'...")
            
            # Create a TelegramClient instance
            client = TelegramClient(
                session_name,
                config.TELEGRAM_API_ID,
                config.TELEGRAM_API_HASH
            )
            
            await client.connect()
            
            # Check user authorization
            if not await client.is_user_authorized():
                import sys
                is_interactive = sys.stdin and sys.stdin.isatty()
                
                if is_interactive:
                    logger.info(f"🔑 Сессия Telethon '{session_name}' не авторизована.")
                    phone_num = mgr.get("phone") or (config.MANAGER_1_PHONE if hasattr(config, "MANAGER_1_PHONE") else "")
                    if not phone_num:
                        phone_num = input(f"📱 Введите номер телефона для менеджера '{session_name}' (например +380991234567): ").strip()
                    
                    print(f"\n=========================================================")
                    print(f"   🔐 ВХОД В АККАУНТ ТЕЛЕГРАМ ДЛЯ ЮЗЕРБОТА '{session_name}'")
                    print(f"   Телефон: {phone_num}")
                    print(f"   (Код подтверждения придет в ваш Telegram-клиент)")
                    print(f"=========================================================")
                    try:
                        await client.start(
                            phone=phone_num,
                            password=lambda: input("🔒 Введите пароль двухфакторной аутентификации (2FA, если есть): ").strip(),
                            code_callback=lambda: input("📨 Введите код подтверждения Telegram: ").strip()
                        )
                        logger.info(f"✅ Сессия Telethon '{session_name}' успешно авторизована!")
                    except Exception as auth_err:
                        logger.error(f"❌ Не удалось авторизовать сессию '{session_name}': {auth_err}")
                        await client.disconnect()
                        continue
                else:
                    logger.warning(
                        f"⚠️ Telethon session '{session_name}' is not authorized!\n"
                        f"To authorize this session, please run the bot in an interactive console."
                    )
                    await client.disconnect()
                    continue
                
            # Logged in successfully! Cache client in running registry
            active_clients[session_name] = client
            
            # Setup real-time event listeners
            await register_chat_event_listeners(session_name, client, mgr)
            
            logger.info(f"Successfully started and authorized Telethon session '{session_name}'.")
            
        except Exception as e:
            logger.error(f"Failed to start manager session '{session_name}': {e}", exc_info=True)

def schedule_manager_loops():
    """Schedules periodic follow-up checking tasks for active Telethon clients."""
    logger.info("Setting up manager follow-up re-engagement schedulers...")
    
    for mgr in config.MANAGER_ACCOUNTS:
        session_name = mgr["session"]
        
        # We only add a scheduler job if the client was successfully started and cached
        if session_name in active_clients:
            job_id = f"manager_followups_{session_name}"
            
            scheduler.add_job(
                check_manager_followups,
                trigger="interval",
                minutes=30,  # runs checks every 30 minutes
                args=[session_name],
                id=job_id,
                replace_existing=True
            )
            logger.info(f"Scheduled periodic re-engagement checker for session '{session_name}' every 30 mins (ID: {job_id})")
