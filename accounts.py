# accounts.py
# NEW: Multi-Account Manager System using Telethon userbots
# Automates first-contact private messages to new group members,
# tracks conversation replies to automatically halt re-engagement,
# and runs a scheduled background checker to deliver Day 1, 3, 5 follow-ups.

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
                chat_id_str = str(chat.id)
                
                # Check if this group matches the managed groups (by username, ID, or link)
                monitored_groups = [g.lower() for g in mgr_cfg.get("groups", [])]
                is_monitored = False
                
                if chat_username and chat_username.lower() in monitored_groups:
                    is_monitored = True
                elif chat_id_str in monitored_groups:
                    is_monitored = True
                    
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
    @client.on(events.NewMessage(incoming=True, private=True))
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
            
            # Check user authorization non-blockingly
            if not await client.is_user_authorized():
                logger.warning(
                    f"⚠️ Telethon session '{session_name}' is not authorized!\n"
                    f"To authorize this session, please run a separate interactive script or "
                    f"execute: client.start(phone='{mgr.get('phone')}') in a console environment."
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
