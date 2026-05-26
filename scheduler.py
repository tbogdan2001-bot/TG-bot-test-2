# scheduler.py
from datetime import datetime, timedelta
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
import pytz

import config
import database
import keyboards

logger = logging.getLogger(__name__)

# Initialize the scheduler with UTC timezone
scheduler = AsyncIOScheduler(timezone=pytz.utc)

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
    logger.info(f"Running scheduled subscription nudge check for user {user_id}")
    
    # 1. Double check current subscription via API
    is_subscribed = await check_member_status(bot, config.CHANNEL_ID, user_id)
    
    # 2. Update status in Database
    await database.set_user_subscription(user_id, is_subscribed)
    
    user = await database.get_user(user_id)
    if not user:
        return

    # If the user is subscribed but hasn't reached stage 3/4 yet, let's advance them!
    if is_subscribed:
        if user["этап_воронки"] < 3:
            await database.set_user_funnel_stage(user_id, 3)
            await transition_to_step_4(bot, user_id)
        return

    # If not subscribed, send nudge (Step 2b)
    try:
        kb = keyboards.get_nudge_keyboard()
        
        # We can send Nudge with IMAGE_2 or just text. Let's send photo for aesthetic premium feel
        if config.IMAGE_2:
            try:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=config.IMAGE_2,
                    caption=config.NUDGE_TEXT,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
            except Exception as photo_err:
                logger.error(f"Failed to send nudge photo: {photo_err}, sending text only")
                await bot.send_message(
                    chat_id=user_id,
                    text=config.NUDGE_TEXT,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=config.NUDGE_TEXT,
                reply_markup=kb,
                parse_mode="Markdown"
            )
        logger.info(f"Nudge sent successfully to user {user_id}")
    except Exception as e:
        logger.error(f"Could not send nudge to user {user_id}: {e}")

async def send_warmup_message(bot: Bot, user_id: int, sequence_index: int):
    """
    Sends the scheduled progressive warm-up message to the user.
    Only executes if the user is in stage 4 (active subscribed user receiving warm-ups).
    """
    user = await database.get_user(user_id)
    if not user or user["этап_воронки"] != 4:
        logger.info(f"Skipping warm-up {sequence_index} for user {user_id} (not in stage 4)")
        return
        
    # Get the sequence data
    if sequence_index >= len(config.WARMUP_SEQUENCES):
        return
        
    seq = config.WARMUP_SEQUENCES[sequence_index]
    text = seq["text"].format(
        persona_name=config.PERSONA_NAME,
        persona_description=config.PERSONA_DESCRIPTION,
        niche=config.NICHE,
        channel_name=config.CHANNEL_NAME
    )
    
    # Custom keyboard if specified, otherwise None
    kb = None
    if "keyboard" in seq:
        kb = keyboards.get_custom_keyboard(seq["keyboard"])
        
    image_url = seq.get("image")
    
    try:
        if image_url:
            try:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=image_url,
                    caption=text,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
            except Exception as photo_err:
                logger.error(f"Failed to send warm-up photo: {photo_err}, sending text only")
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=kb,
                parse_mode="Markdown"
            )
        logger.info(f"Warmup message {sequence_index} sent to user {user_id}")
    except Exception as e:
        logger.error(f"Could not send warm-up {sequence_index} to user {user_id}: {e}")

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
    Schedules the full progressive warm-up sequence for a user.
    Calculates future delivery dates using FOLLOW_UP_DELAYS[1:].
    """
    # Cancel any outstanding jobs just in case
    cancel_active_jobs_for_user(user_id)
    
    now = datetime.now(pytz.utc)
    
    for i, seq in enumerate(config.WARMUP_SEQUENCES):
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
        logger.info(f"Scheduled warm-up #{i} for user {user_id} at {run_time} (ID: {job_id})")

def cancel_active_jobs_for_user(user_id: int):
    """Safely cancels all outstanding nudge or warm-up jobs scheduled for a user."""
    # Cancel nudge job
    nudge_id = f"nudge_{user_id}"
    try:
        if scheduler.get_job(nudge_id):
            scheduler.remove_job(nudge_id)
            logger.info(f"Cancelled nudge job for user {user_id}")
    except Exception as e:
        logger.debug(f"Failed to cancel nudge job: {e}")
        
    # Cancel warmup jobs
    for i in range(len(config.WARMUP_SEQUENCES)):
        warmup_id = f"warmup_{user_id}_{i}"
        try:
            if scheduler.get_job(warmup_id):
                scheduler.remove_job(warmup_id)
                logger.info(f"Cancelled warmup job {warmup_id}")
        except Exception as e:
            logger.debug(f"Failed to cancel warmup job {warmup_id}: {e}")

# -------------------------------------------------------------
# FUNNEL ROUTING ASSISTANT
# -------------------------------------------------------------

async def transition_to_step_4(bot: Bot, user_id: int):
    """Transition helper to step 4 (congratulations and bonus selection markup)."""
    # 1. Update database to Stage 3 (Subscribed)
    await database.set_user_funnel_stage(user_id, 3)
    
    # 2. Cancel the outstanding nudge job since they successfully verified
    cancel_active_jobs_for_user(user_id)
    
    # 3. Present Step 4 visual & markup
    kb = keyboards.get_bonus_keyboard()
    congrats_text = (
        "🎉 **Поздравляю! Подписка успешно подтверждена!**\n\n"
        "Вы получили полный доступ к воронке полезных материалов.\n\n"
        "Теперь выберите один из гарантированных бонусов ниже, чтобы начать обучение 👇"
    )
    
    try:
        if config.IMAGE_4:
            try:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=config.IMAGE_4,
                    caption=congrats_text,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
            except Exception as photo_err:
                logger.error(f"Failed to send step 4 photo: {photo_err}, sending text only")
                await bot.send_message(
                    chat_id=user_id,
                    text=congrats_text,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=congrats_text,
                reply_markup=kb,
                parse_mode="Markdown"
            )
        logger.info(f"Successfully transitioned user {user_id} to Step 4")
    except Exception as e:
        logger.error(f"Error executing step 4 delivery for user {user_id}: {e}")

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
        
        # Parse their join date (дата_входа)
        try:
            join_dt = datetime.strptime(u["дата_входа"], "%Y-%m-%d %H:%M:%S")
            # Localize database datetime (naive) to bot local timezone, then convert to UTC
            # Since datetime.now() was used, we treat it as local time.
            local_tz = datetime.now().astimezone().tzinfo
            join_dt = join_dt.replace(tzinfo=local_tz).astimezone(pytz.utc)
        except Exception as date_err:
            logger.error(f"Error parsing join date for user {user_id}: {date_err}")
            continue
            
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
                
        elif stage == 4:
            # User has selected a bonus, and is receiving warm-ups.
            # Schedule only warm-up jobs that are still in the future!
            for i, seq in enumerate(config.WARMUP_SEQUENCES):
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
                    
    logger.info(f"Startup recovery completed. Restored {restored_count} active jobs.")
