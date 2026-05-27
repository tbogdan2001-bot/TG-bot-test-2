# scheduler.py
# CHANGED: Upgraded transition and checks to support visual quiz funnel flow:
# - Updated send_warmup_message() to execute for both stage 4 and stage 5 active users
# - Upgraded notify_closer_hub() to fetch and format Q1, Q2, and Q3 quiz answers for CRM logs
# - Rewrote transition_to_step_4() to auto-resolve personalized bonuses, deliver them with image_4,
#   advance stage to 5, and immediately send the final dark-themed CTA card with image_5
# - Updated restore_scheduled_jobs() startup recovery to handle both stage 4 and stage 5
# - Added functions for ERR analytics (messages_sent tracking, unsubscription on bot block)
# - Added Feature 1: Pressure Lead Funnel ("Дожим") triggers, APscheduler jobs, and recovery

from datetime import datetime, timedelta
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
import pytz

import config
import database
import keyboards

logger = logging.getLogger(__name__)

# Initialize the scheduler with UTC timezone
scheduler = AsyncIOScheduler(timezone=pytz.utc)

async def safe_send(bot: Bot, user_id: int, text: str, photo: str = None, kb = None) -> bool:
    """
    Safely sends a text or photo message to a user.
    If photo sending fails, automatically falls back to sending text.
    If the user has blocked the bot, marks the user as blocked and unsubscribed in the database and returns False.
    Returns True if successfully sent.
    """
    try:
        if photo:
            try:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=text,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
                return True
            except TelegramForbiddenError:
                logger.warning(f"User {user_id} blocked the bot on sending photo. Marking as blocked & unsubscribed.")
                await database.set_user_blocked(user_id, True)
                await database.set_user_subscription(user_id, False)
                return False
            except Exception as photo_err:
                logger.error(f"Failed to send photo to {user_id}: {photo_err}, falling back to text only.")
                # Fallback to text message
        
        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
        return True
    except TelegramForbiddenError:
        logger.warning(f"User {user_id} blocked the bot on sending message. Marking as blocked & unsubscribed.")
        await database.set_user_blocked(user_id, True)
        await database.set_user_subscription(user_id, False)
        return False
    except Exception as e:
        logger.error(f"Failed to send message to user {user_id}: {e}", exc_info=True)
        return False

# -------------------------------------------------------------
# BACKGROUND TASK ACTIONS
# -------------------------------------------------------------

async def check_member_status(bot: Bot, channel_id: str, user_id: int) -> bool:
    """Helper to check if a user is subscribed to the channel."""
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        # Member statuses that count as subscribed
        return member.status in ["member", "creator", "administrator"]
    except Exception as e:
        logger.error(f"Error checking sub status for user {user_id}: {e}")
        return False

async def send_subscription_nudge(bot: Bot, user_id: int):
    """
    Executes after FOLLOW_UP_DELAYS[0] minutes.
    Checks subscription status. If not subscribed, sends the nudge message.
    If subscribed, automatically transitions the user to Step 4 (bonus selection).
    """
    # Check if user is blocked or doesn't exist
    user = await database.get_user(user_id)
    if not user or user.get("is_blocked"):
        logger.info(f"Skipping nudge for user {user_id} (blocked or not found)")
        return

    logger.info(f"Running scheduled subscription nudge check for user {user_id}")
    
    # 1. Dynamically resolve correct target verification ID based on user source channel
    target_channel_id = config.get_channel_id_for_user(user)
    
    # 2. Check current subscription via API
    is_subscribed = await check_member_status(bot, target_channel_id, user_id)
    
    # 3. Update status in Database
    await database.set_user_subscription(user_id, is_subscribed)
    
    # Refresh user reference
    user = await database.get_user(user_id)
    if not user:
        return

    # If the user is subscribed but hasn't reached stage 4 yet, let's advance them!
    if is_subscribed:
        if user["этап_воронки"] < 4:
            await transition_to_step_4(bot, user_id)
        return

    # If not subscribed, send nudge (Step 2b)
    # Dynamically resolves specific referral channel link for the nudge buttons
    channel_link = None
    source_channel_id = user.get("source_channel")
    if source_channel_id:
        for ch in config.CHANNELS:
            if ch["id"] == source_channel_id:
                channel_link = ch["link"]
                break
                
    kb = keyboards.get_nudge_keyboard(channel_link)
    
    # Resolve assigned persona profile to pull customized nudge graphics (image_2)
    persona = config.get_persona_for_user(user)
    nudge_photo = persona["images"].get("image_2", config.IMAGE_2)
    
    await safe_send(bot, user_id, config.NUDGE_TEXT, photo=nudge_photo, kb=kb)
    logger.info(f"Nudge task executed for user {user_id}")

async def send_warmup_message(bot: Bot, user_id: int, sequence_index: int):
    """
    Sends the scheduled progressive warm-up message to the user.
    Only executes if the user is in stage 4 or stage 5 (active subscribed user receiving warm-ups).
    """
    user = await database.get_user(user_id)
    # CHANGED: Allow stage 4 or stage 5
    if not user or user.get("is_blocked") or user["этап_воронки"] not in [4, 5]:
        logger.info(f"Skipping warm-up {sequence_index} for user {user_id} (blocked or not in stage 4/5)")
        return
        
    # Get the sequence data
    if sequence_index >= len(config.CONTENT_PLAN):
        return
        
    seq = config.CONTENT_PLAN[sequence_index]
    
    # Dynamically resolve correct marketing persona configurations
    persona = config.get_persona_for_user(user)
    
    # Format placeholders using assigned expert properties
    text = seq["text"].format(
        persona_name=persona["name"],
        persona_description=persona["description"],
        niche=persona["niche"],
        channel_name=config.CHANNEL_NAME
    )
    
    # Custom keyboard if specified, otherwise None
    kb = None
    if "keyboard" in seq:
        kb = keyboards.get_custom_keyboard(seq["keyboard"])
        
    image_url = seq.get("image")
    
    # Using safe_send() utility function to send warm-up sequences safely
    sent = await safe_send(bot, user_id, text, photo=image_url, kb=kb)
    if sent:
        # Increment ERR messages sent counter
        await database.increment_user_messages_sent(user_id)
    logger.info(f"Warmup task executed for user {user_id}, index {sequence_index} ({seq['type']})")

async def send_retention_message(bot: Bot, user_id: int, retention_index: int):
    """
    Sends the long-term re-engagement retention messages.
    If the user completes Day 30 without further interaction, marks their status as 'cold' and triggers pressure.
    """
    user = await database.get_user(user_id)
    if not user or user.get("is_blocked") or user.get("status") != "active":
        logger.info(f"Skipping retention #{retention_index} for user {user_id} (blocked, not active or not found)")
        return
        
    if retention_index >= len(config.RETENTION_PLAN):
        return
        
    ret = config.RETENTION_PLAN[retention_index]
    
    # Resolve dynamic persona parameters
    persona = config.get_persona_for_user(user)
    text = ret["text"].format(
        persona_name=persona["name"],
        niche=persona["niche"]
    )
    
    kb = None
    if "keyboard" in ret:
        kb = keyboards.get_custom_keyboard(ret["keyboard"])
        
    image_url = ret.get("image")
    
    # Send re-engagement messages safely
    sent = await safe_send(bot, user_id, text, photo=image_url, kb=kb)
    
    if sent:
        # Increment ERR messages sent counter
        await database.increment_user_messages_sent(user_id)
        
        # Increment user retention stage in SQLite
        stage_num = ret["stage"]
        await database.set_user_retention_stage(user_id, stage_num)
        
        # If this is the final retention check (Day 30), mark the user as 'cold' and start the pressure lead funnel
        if retention_index == len(config.RETENTION_PLAN) - 1:
            await database.set_user_status(user_id, "cold")
            logger.info(f"User {user_id} reached final retention step. Marked as cold. Starting pressure lead funnel.")
            await start_pressure_funnel(bot, user_id)

async def notify_closer_hub(bot: Bot, user_id: int):
    """
    Pushes lead details, source channel, traffic parameter, quiz answers (Q1/Q2/Q3),
    and a direct conversation deep-link to the CLOSER_NOTIFY_CHAT_ID Telegram CRM group chat.
    """
    if not config.CLOSER_NOTIFY_CHAT_ID:
        logger.warning("CLOSER_NOTIFY_CHAT_ID is not configured. Skipping Closer notification.")
        return
        
    user = await database.get_user(user_id)
    if not user or user.get("closer_notified", 0) == 1:
        return
        
    # Gather statistics
    username = user["username"]
    username_str = f"@{username}" if username and username != "unknown" else "Отсутствует"
    chosen_bonus = user.get("bonus_variant") or "Не выбран"
    traffic_source = user.get("traffic_source") or "Прямой переход"
    source_channel_id = user.get("source_channel") or "Не указан"
    join_date = user.get("дата_входа")
    
    # CHANGED: Added Q1, Q2, Q3 quiz answers
    q1 = user.get("quiz_q1") or "Не указан"
    q2 = user.get("quiz_q2") or "Не указан"
    q3 = user.get("quiz_q3") or "Не указан"
    
    # Build direct dialog deep links
    chat_link = f"tg://user?id={user_id}"
    if username and username != "unknown":
        chat_link = f"https://t.me/{username}"
        
    # Resolve human readable source channel name
    source_channel_name = source_channel_id
    for ch in config.CHANNELS:
        if ch["id"] == source_channel_id:
            source_channel_name = f"{ch['name']} ({ch['id']})"
            break
            
    lead_text = (
        "🔥 **НОВЫЙ ЛИД В ВОРОНКЕ (Closer Hub)**\n\n"
        f"👤 **Пользователь:** {username_str}\n"
        f"🆔 **Telegram ID:** `{user_id}`\n"
        f"🎁 **Выданный бонус:** `{chosen_bonus}`\n"
        f"📊 **Ответы на опрос:**\n"
        f"  🔹 *Опыт:* {q1}\n"
        f"  🔹 *Цель:* {q2}\n"
        f"  🔹 *Капитал:* {q3}\n"
        f"📢 **Источник (канал):** {source_channel_name}\n"
        f"🔗 **Трафик (UTM/Ref):** `{traffic_source}`\n"
        f"📅 **Дата входа:** {join_date}\n\n"
        f"💬 [ОТКРЫТЬ ДИАЛОГ С КЛИЕНТОМ]({chat_link})"
    )
    
    try:
        await bot.send_message(
            chat_id=config.CLOSER_NOTIFY_CHAT_ID,
            text=lead_text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        await database.set_closer_notified(user_id, 1)
        logger.info(f"Lead notification successfully pushed to Closer Hub for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to push lead notification to Closer Hub: {e}", exc_info=True)

# -------------------------------------------------------------
# PUBLIC SCHEDULING MANAGEMENT
# -------------------------------------------------------------

def schedule_subscription_nudge(bot: Bot, user_id: int):
    """Schedules a one-off subscription check & nudge after FOLLOW_UP_DELAYS[0] minutes."""
    cancel_active_jobs_for_user(user_id)
    
    delay_minutes = config.FOLLOW_UP_DELAYS[0]
    run_time = datetime.now(pytz.utc) + timedelta(minutes=delay_minutes)
    
    job_id = f"nudge_{user_id}"
    scheduler.add_job(
        send_subscription_nudge,
        trigger="date",
        run_date=run_time,
        args=[bot, user_id],
        id=job_id,
        replace_existing=True
    )
    logger.info(f"Scheduled nudge for user {user_id} at {run_time} (ID: {job_id})")

def schedule_warmup_sequence(bot: Bot, user_id: int):
    """
    Schedules both the main progressive content plan and long-term retention sequences.
    Calculates future delivery dates using FOLLOW_UP_DELAYS.
    """
    # Cancel any outstanding jobs just in case
    cancel_active_jobs_for_user(user_id)
    
    now = datetime.now(pytz.utc)
    
    # 1. Schedule the 8 message types Warm-up Content Plan
    for i, seq in enumerate(config.CONTENT_PLAN):
        delay_idx = seq["delay_index"]
        if delay_idx >= len(config.FOLLOW_UP_DELAYS):
            continue
            
        delay_minutes = config.FOLLOW_UP_DELAYS[delay_idx]
        run_time = now + timedelta(minutes=delay_minutes)
        
        job_id = f"warmup_{user_id}_{i}"
        scheduler.add_job(
            send_warmup_message,
            trigger="date",
            run_date=run_time,
            args=[bot, user_id, i],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Scheduled content plan message #{i} ({seq['type']}) for user {user_id} at {run_time}")
        
    # 2. Schedule the Retention Sequence (Day 7, 14, 30)
    for j, ret in enumerate(config.RETENTION_PLAN):
        delay_idx = ret["delay_index"]
        if delay_idx >= len(config.FOLLOW_UP_DELAYS):
            continue
            
        delay_minutes = config.FOLLOW_UP_DELAYS[delay_idx]
        run_time = now + timedelta(minutes=delay_minutes)
        
        job_id = f"retention_{user_id}_{j}"
        scheduler.add_job(
            send_retention_message,
            trigger="date",
            run_date=run_time,
            args=[bot, user_id, j],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Scheduled retention re-engagement #{j} for user {user_id} at {run_time}")

def cancel_active_jobs_for_user(user_id: int):
    """Safely cancels all outstanding nudge, warm-up, retention, or pressure jobs scheduled for a user."""
    # Cancel nudge job
    nudge_id = f"nudge_{user_id}"
    try:
        if scheduler.get_job(nudge_id):
            scheduler.remove_job(nudge_id)
            logger.info(f"Cancelled nudge job for user {user_id}")
    except Exception as e:
        logger.debug(f"Failed to cancel nudge job: {e}")
        
    # Cancel warmup jobs
    for i in range(len(config.CONTENT_PLAN)):
        warmup_id = f"warmup_{user_id}_{i}"
        try:
            if scheduler.get_job(warmup_id):
                scheduler.remove_job(warmup_id)
                logger.info(f"Cancelled warmup job {warmup_id}")
        except Exception as e:
            logger.debug(f"Failed to cancel warmup job {warmup_id}: {e}")
            
    # Cancel retention jobs
    for j in range(len(config.RETENTION_PLAN)):
        ret_id = f"retention_{user_id}_{j}"
        try:
            if scheduler.get_job(ret_id):
                scheduler.remove_job(ret_id)
                logger.info(f"Cancelled retention job {ret_id}")
        except Exception as e:
            logger.debug(f"Failed to cancel retention job {ret_id}: {e}")

    # Cancel pressure jobs (Feature 3)
    for k in range(5):
        pressure_id = f"pressure_{user_id}_{k}"
        try:
            if scheduler.get_job(pressure_id):
                scheduler.remove_job(pressure_id)
                logger.info(f"Cancelled pressure job {pressure_id}")
        except Exception as e:
            logger.debug(f"Failed to cancel pressure job {pressure_id}: {e}")

# -------------------------------------------------------------
# FUNNEL ROUTING ASSISTANT
# -------------------------------------------------------------

# CHANGED: Completely upgraded to auto-deliver personalized bonus & immediately send dark CTA card
async def transition_to_step_4(bot: Bot, user_id: int):
    """
    Transition helper to step 4 (congratulations and personalized bonus delivery),
    followed immediately by transition to Step 5 (final dark-themed CTA post).
    """
    # 1. Update database to Stage 4 (Subscribed & Ready for warming)
    await database.set_user_funnel_stage(user_id, 4)
    
    # 2. Cancel the outstanding nudge job since they successfully verified
    cancel_active_jobs_for_user(user_id)
    
    # 3. Present Step 4 visual & auto-delivered personalized bonus
    user = await database.get_user(user_id)
    if not user:
        return
        
    persona = config.get_persona_for_user(user)
    
    # Resolve the personalized bonus dynamically based on user quiz answers
    bonus_val = user.get("bonus_variant")
    if not bonus_val or bonus_val not in persona["bonus_contents"]:
        # Fallback in case it wasn't saved correctly
        bonus_val = config.get_personalized_bonus(
            persona["id"], 
            user.get("quiz_q1", "beginner"), 
            user.get("quiz_q2", "passive_income"), 
            user.get("quiz_q3", "under_500")
        )
        
    bonus_text = persona["bonus_contents"].get(bonus_val, "")
    congrats_text = f"{config.STEP_4_CONGRATS_TEXT}\n\n{bonus_text}"
    
    # Congratulations / bonus reveal photo (image_4)
    congrats_photo = persona["images"].get("image_4", config.IMAGE_4)
    
    # Deliver the bonus
    await safe_send(bot, user_id, congrats_text, photo=congrats_photo)
    logger.info(f"Successfully delivered personalized bonus '{bonus_val}' to user {user_id} (Stage 4)")
    
    # 4. Schedule progressive multi-day warm-up & long-term retention sequences
    schedule_warmup_sequence(bot, user_id)
    
    # 5. Trigger CRM notification push to Closer Hub group chat
    await notify_closer_hub(bot, user_id)
    
    # 6. Instantly transition to Stage 5 (Deliver Final Dark CTA Card)
    await database.set_user_funnel_stage(user_id, 5)
    
    # Dark style final CTA card visual (image_5)
    dark_photo = persona["images"].get("image_5")
    
    # Formulate dark CTA caption
    cta_text = config.DARK_CTA_CAPTION.format(
        persona_name=persona["name"],
        niche=persona["niche"]
    )
    
    kb = keyboards.get_dark_cta_keyboard(config.PRIVATE_CLUB_LINK)
    
    await safe_send(bot, user_id, cta_text, photo=dark_photo, kb=kb)
    logger.info(f"Successfully transitioned user {user_id} to Step 5 (Dark CTA Card delivered)")

# -------------------------------------------------------------
# FEATURE 3: PRESSURE LEAD FUNNEL ("ДОЖИМ") FUNCTIONS
# -------------------------------------------------------------

async def start_pressure_funnel(bot: Bot, user_id: int):
    """Starts the re-engagement pressure lead funnel for a cold/inactive user."""
    logger.info(f"Starting pressure lead funnel for user {user_id}...")
    import datetime as dt_mod
    now_str = dt_mod.datetime.now(dt_mod.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    await database.set_user_status(user_id, "pressure")
    await database.set_pressure_started_at(user_id, now_str)
    schedule_pressure_sequence(bot, user_id)

async def send_pressure_message(bot: Bot, user_id: int, index: int):
    """Sends a single scheduled pressure re-engagement message."""
    user = await database.get_user(user_id)
    if not user or user.get("is_blocked") or user.get("status") != "pressure":
        logger.info(f"Skipping pressure message #{index} for user {user_id} (blocked, not in pressure status, or not found)")
        return
        
    if index >= len(config.PRESSURE_PLAN):
        return
        
    seq = config.PRESSURE_PLAN[index]
    
    # Resolve assigned marketing persona
    persona = config.get_persona_for_user(user)
    
    # Format text placeholders
    text = seq["text"].format(
        persona_name=persona["name"],
        niche=persona["niche"]
    )
    
    kb = None
    if "keyboard" in seq:
        kb = keyboards.get_custom_keyboard(seq["keyboard"])
        
    # Resolve persona-specific image override if available (stage X -> image_X)
    image_url = seq.get("image")
    stage_img_key = f"image_{seq['stage']}"
    if persona and "images" in persona and stage_img_key in persona["images"]:
        image_url = persona["images"][stage_img_key]
        
    # Send message safely
    sent = await safe_send(bot, user_id, text, photo=image_url, kb=kb)
    
    if sent:
        # Increment messages_sent counter for ERR
        await database.increment_user_messages_sent(user_id)
        
        # After Day 5 with no response (index == 4, i.e., final stage 5 breakup message): mark status = "lost"
        if index == len(config.PRESSURE_PLAN) - 1:
            await database.set_user_status(user_id, "lost")
            logger.info(f"User {user_id} reached end of pressure funnel without responding. Marked status as 'lost'.")

def schedule_pressure_sequence(bot: Bot, user_id: int):
    """Registers all 5 pressure re-engagement jobs using APScheduler."""
    cancel_active_jobs_for_user(user_id)
    
    now = datetime.now(pytz.utc)
    for i, seq in enumerate(config.PRESSURE_PLAN):
        delay_idx = seq["delay_index"]
        if delay_idx >= len(config.FOLLOW_UP_DELAYS):
            continue
            
        delay_minutes = config.FOLLOW_UP_DELAYS[delay_idx]
        run_time = now + timedelta(minutes=delay_minutes)
        
        job_id = f"pressure_{user_id}_{i}"
        scheduler.add_job(
            send_pressure_message,
            trigger="date",
            run_date=run_time,
            args=[bot, user_id, i],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Scheduled pressure message #{i} (stage {seq['stage']}) for user {user_id} at {run_time} (ID: {job_id})")

async def check_inactive_leads(bot: Bot):
    """
    Daily cron job running every 24 hours.
    Scans for cold/inactive leads and triggers start_pressure_funnel() for them.
    """
    logger.info("Running daily check_inactive_leads cron check...")
    inactive_user_ids = await database.get_inactive_leads_for_pressure()
    
    triggered_count = 0
    for u_id in inactive_user_ids:
        try:
            await start_pressure_funnel(bot, u_id)
            triggered_count += 1
        except Exception as e:
            logger.error(f"Failed to start pressure funnel for user {u_id}: {e}")
            
    logger.info(f"check_inactive_leads completed. Triggered pressure funnel for {triggered_count} users.")

async def handle_user_activity(bot: Bot, user_id: int):
    """Resets user status from 'pressure', 'cold', or 'lost' to 'active' on new activity, and cancels outstanding pressure jobs."""
    user = await database.get_user(user_id)
    if user:
        status = user.get("status")
        if status in ["pressure", "cold", "lost"]:
            await database.set_user_status(user_id, "active")
            cancel_active_jobs_for_user(user_id)
            logger.info(f"User {user_id} became active again. Cancelled pressure jobs and set status to 'active'.")

# -------------------------------------------------------------
# STARTUP RESTORATION / RECOVERY LOGIC
# -------------------------------------------------------------

async def restore_scheduled_jobs(bot: Bot):
    """
    Scans the database upon bot startup and reschedules all active jobs for users.
    Ensures that if the bot is restarted, users don't get 'stuck' or lose their messages.
    """
    logger.info("Restoring active scheduled jobs from SQLite database...")
    users = await database.get_all_users()
    now_utc = datetime.now(pytz.utc)
    
    restored_count = 0
    for u in users:
        user_id = u["telegram_id"]
        stage = u["этап_воронки"]
        is_blocked = u.get("is_blocked", 0)
        status_name = u.get("status", "active")
        
        # Skip restoring jobs for blocked or lost/inactive users unless they are in pressure state!
        if is_blocked or status_name == "blocked":
            continue
            
        # Parse their join date (дата_входа)
        try:
            join_dt = datetime.strptime(u["дата_входа"], "%Y-%m-%d %H:%M:%S")
            # The date is stored directly as UTC naive. Convert to localized UTC object.
            join_dt = join_dt.replace(tzinfo=pytz.utc)
        except Exception as date_err:
            logger.error(f"Error parsing join date for user {user_id}: {date_err}")
            continue
            
        if status_name == "pressure":
            # Reschedule remaining pressure messages relative to pressure_started_at
            pressure_start_str = u.get("pressure_started_at")
            if not pressure_start_str:
                pressure_start_str = u["дата_входа"]
                
            try:
                pressure_dt = datetime.strptime(pressure_start_str, "%Y-%m-%d %H:%M:%S")
                pressure_dt = pressure_dt.replace(tzinfo=pytz.utc)
            except Exception as e:
                logger.error(f"Error parsing pressure start date for user {user_id}: {e}")
                continue
                
            for k, seq in enumerate(config.PRESSURE_PLAN):
                delay_idx = seq["delay_index"]
                if delay_idx >= len(config.FOLLOW_UP_DELAYS):
                    continue
                delay_minutes = config.FOLLOW_UP_DELAYS[delay_idx]
                pressure_time = pressure_dt + timedelta(minutes=delay_minutes)
                
                if pressure_time > now_utc:
                    scheduler.add_job(
                        send_pressure_message,
                        trigger="date",
                        run_date=pressure_time,
                        args=[bot, user_id, k],
                        id=f"pressure_{user_id}_{k}",
                        replace_existing=True
                    )
                    restored_count += 1
                    
        elif status_name == "active":
            if stage == 2:
                # User is prompted to subscribe, they need a subscription check nudge.
                # Calculate when the nudge should run
                delay_minutes = config.FOLLOW_UP_DELAYS[0]
                nudge_time = join_dt + timedelta(minutes=delay_minutes)
                
                if nudge_time > now_utc:
                    # Schedule nudge for the remaining time
                    scheduler.add_job(
                        send_subscription_nudge,
                        trigger="date",
                        run_date=nudge_time,
                        args=[bot, user_id],
                        id=f"nudge_{user_id}",
                        replace_existing=True
                    )
                    restored_count += 1
                else:
                    # Nudge time has passed while bot was offline. Trigger it immediately!
                    scheduler.add_job(
                        send_subscription_nudge,
                        trigger="date",
                        run_date=now_utc + timedelta(seconds=5), # 5 seconds delay to allow bot startup
                        args=[bot, user_id],
                        id=f"nudge_{user_id}",
                        replace_existing=True
                    )
                    restored_count += 1
                    
            # CHANGED: Allow stage 4 and stage 5
            elif stage in [4, 5]:
                # User has selected a bonus, and is receiving warm-ups & retentions.
                # Schedule only warmup/content plan jobs that are still in the future!
                for i, seq in enumerate(config.CONTENT_PLAN):
                    delay_idx = seq["delay_index"]
                    if delay_idx >= len(config.FOLLOW_UP_DELAYS):
                        continue
                    delay_minutes = config.FOLLOW_UP_DELAYS[delay_idx]
                    warmup_time = join_dt + timedelta(minutes=delay_minutes)
                    
                    if warmup_time > now_utc:
                        scheduler.add_job(
                            send_warmup_message,
                            trigger="date",
                            run_date=warmup_time,
                            args=[bot, user_id, i],
                            id=f"warmup_{user_id}_{i}",
                            replace_existing=True
                        )
                        restored_count += 1
                        
                # Reschedule future long-term retention jobs
                for j, ret in enumerate(config.RETENTION_PLAN):
                    delay_idx = ret["delay_index"]
                    if delay_idx >= len(config.FOLLOW_UP_DELAYS):
                        continue
                    delay_minutes = config.FOLLOW_UP_DELAYS[delay_idx]
                    retention_time = join_dt + timedelta(minutes=delay_minutes)
                    
                    if retention_time > now_utc:
                        scheduler.add_job(
                            send_retention_message,
                            trigger="date",
                            run_date=retention_time,
                            args=[bot, user_id, j],
                            id=f"retention_{user_id}_{j}",
                            replace_existing=True
                        )
                        restored_count += 1
                        
    logger.info(f"Startup recovery completed. Restored {restored_count} active jobs.")

# NEW: Added auto-posting and manager scheduler task registration on startup
async def start_scheduler_tasks(bot: Bot):
    """Starts the Telethon userbots and registers auto-posting, check_inactive_leads, and follow-up periodic jobs."""
    import autoposter
    import accounts
    
    # 1. Start Telethon manager userbot sessions
    await accounts.start_manager_accounts()
    
    # 2. Register auto-posting cron jobs
    autoposter.schedule_channel_posts(bot)
    
    # 3. Register manager followup periodic checking loop
    accounts.schedule_manager_loops()
    
    # 4. Register daily re-engagement check_inactive_leads cron running every 24h
    job_id = "check_inactive_leads_daily"
    scheduler.add_job(
        check_inactive_leads,
        trigger="interval",
        hours=24,
        args=[bot],
        id=job_id,
        replace_existing=True
    )
    logger.info(f"Scheduled check_inactive_leads daily interval job (ID: {job_id})")
    
    logger.info("Auto-posting, check_inactive_leads, and userbot check loops registered successfully.")
