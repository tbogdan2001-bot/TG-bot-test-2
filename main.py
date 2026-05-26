# main.py
import asyncio
import logging
import sys
from datetime import datetime  # CHANGED: Added datetime import for rate limiting (TASK 8)

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

import config
import database
import keyboards
import scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Initialize Bot and Dispatcher
if not config.BOT_TOKEN:
    logger.critical("BOT_TOKEN is empty! Please set it in config.py before launching the bot.")
    sys.exit("Critical Error: BOT_TOKEN is missing.")

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# CHANGED: In-memory rate limiting dictionary for /start command (TASK 8)
last_start_times = {}

# -------------------------------------------------------------
# LIFECYCLE HANDLERS
# -------------------------------------------------------------

async def on_startup():
    """Triggered when the bot starts polling."""
    logger.info("Starting bot services...")
    
    # 1. Initialize SQLite Database Schema
    await database.init_db()
    
    # 2. Start the AsyncIOScheduler
    scheduler.scheduler.start()
    logger.info("APScheduler started.")
    
    # 3. Restore all active scheduled jobs (Nudges & Warmups)
    await scheduler.restore_scheduled_jobs(bot)

async def on_shutdown():
    """Triggered when the bot stops polling."""
    logger.info("Shutting down bot services...")
    
    # Safely close scheduler
    if scheduler.scheduler.running:
        scheduler.scheduler.shutdown(wait=True)
        logger.info("APScheduler shut down.")
        
    # CHANGED: Close persistent database connection on shutdown (TASK 3)
    await database.close_db()

# CHANGED: Global error handler decorator (TASK 7)
@dp.errors()
async def global_error_handler(event, exception):
    logger.error(f"Unhandled exception: {exception}", exc_info=True)
    return True

# -------------------------------------------------------------
# BOT MESSAGE AND CALLBACK HANDLERS
# -------------------------------------------------------------

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """
    Step 1: Welcome message /start.
    Saves the user, resets funnel state, and requests experience level.
    """
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    
    # CHANGED: Implement standard datetime rate limiting of 10 seconds (TASK 8)
    now = datetime.now()
    if user_id in last_start_times:
        time_elapsed = (now - last_start_times[user_id]).total_seconds()
        if time_elapsed < 10:
            logger.info(f"Rate limit triggered for user {user_id}. Ignoring /start request.")
            return
            
    last_start_times[user_id] = now
    
    logger.info(f"User {user_id} (@{username}) triggered /start")
    
    # Cancel any active jobs if this is a re-entry
    scheduler.cancel_active_jobs_for_user(user_id)
    
    # Add/update user in DB
    await database.add_or_update_user(user_id, username)
    
    # Build personalized welcome text
    text = config.WELCOME_TEXT.format(
        persona_name=config.PERSONA_NAME,
        persona_description=config.PERSONA_DESCRIPTION,
        niche=config.NICHE
    )
    
    kb = keyboards.get_offer_keyboard()
    
    # Send welcome photo (or text if photo fails or is not provided)
    if config.IMAGE_1:
        try:
            await message.answer_photo(
                photo=config.IMAGE_1,
                caption=text,
                reply_markup=kb,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send welcome photo: {e}. Falling back to text.")
            await message.answer(text=text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer(text=text, reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin-only command to view real-time funnel statistics."""
    # Check if sender is the owner from config
    if message.from_user.id != config.ADMIN_ID:
        return

    stats = await database.get_funnel_stats()
    text = (
        "📊 *Статистика воронки*\n\n"
        f"👥 Всего пользователей: {stats['total']}\n"
        f"📩 Этап 1 (старт): {stats['stage_1']}\n"
        f"📢 Этап 2 (подписка): {stats['stage_2']}\n"
        f"✅ Этап 3 (подтвердили): {stats['stage_3']}\n"
        f"🎁 Этап 4 (бонус): {stats['stage_4']}\n"
        f"🚫 Заблокировали бота: {stats['blocked']}\n\n"
        f"📈 Конверсия (старт→бонус): {stats['conversion']:.1f}%"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("choose_offer:"))
async def handle_offer_selection(callback: CallbackQuery):
    """
    Step 2: Handles Novice / Experienced selection.
    Saves decision to DB, prompts channel subscription, and schedules the nudge task.
    """
    user_id = callback.from_user.id
    offer_selected = callback.data.split(":")[1]
    
    logger.info(f"User {user_id} selected offer level: {offer_selected}")
    
    # Save selected offer in database and advance to Stage 2
    await database.set_user_offer(user_id, offer_selected)
    
    # Schedule the 30-minute nudge (FOLLOW_UP_DELAYS[0])
    scheduler.schedule_subscription_nudge(bot, user_id)
    
    # Prepare Step 2 subscription invite
    text = config.SUBSCRIBE_CALL_TEXT.format(
        channel_name=config.CHANNEL_NAME
    )
    kb = keyboards.get_subscribe_keyboard()
    
    # Send Step 2 message with image
    try:
        if config.IMAGE_2:
            try:
                # Answer query first to prevent loading state on buttons
                await callback.answer()
                await bot.send_photo(
                    chat_id=user_id,
                    photo=config.IMAGE_2,
                    caption=text,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
                # Delete the welcome message to keep chat tidy
                await callback.message.delete()
            except Exception as e:
                logger.error(f"Failed to send image 2: {e}, sending text only")
                await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")
        else:
            await callback.answer()
            await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in handle_offer_selection callback: {e}")

@dp.callback_query(F.data == "check_subscription")
async def handle_subscription_check(callback: CallbackQuery):
    """
    Step 3: Triggered when user clicks "Я подписался".
    Verifies subscription using get_chat_member.
    If subscribed: transitions to Step 4.
    If not: displays a retry warning.
    """
    user_id = callback.from_user.id
    logger.info(f"User {user_id} clicked subscription verification")
    
    # Call Telegram API to check sub
    is_subscribed = await scheduler.check_member_status(bot, config.CHANNEL_ID, user_id)
    
    # Update DB
    await database.set_user_subscription(user_id, is_subscribed)
    
    if is_subscribed:
        # Success!
        await callback.answer("✅ Подписка подтверждена!", show_alert=False)
        try:
            await callback.message.delete()
        except Exception as delete_err:
            logger.debug(f"Could not delete message: {delete_err}")
            
        await scheduler.transition_to_step_4(bot, user_id)
    else:
        # Not subscribed
        await callback.answer("❌ Подписка не найдена!", show_alert=True)
        retry_text = "⚠️ **Подписка не найдена.**\n\nПожалуйста, подпишитесь на наш канал по кнопке ниже и попробуйте снова 👇"
        kb = keyboards.get_retry_subscription_keyboard()
        
        try:
            # Edit existing message or send a fresh one if it's a photo caption
            if callback.message.photo:
                # If the message contains a photo, we edit the caption
                await callback.message.edit_caption(caption=retry_text, reply_markup=kb, parse_mode="Markdown")
            else:
                await callback.message.edit_text(text=retry_text, reply_markup=kb, parse_mode="Markdown")
        except Exception as edit_err:
            logger.error(f"Error editing message for subscription retry: {edit_err}")
            # Fallback: send fresh message
            await bot.send_message(chat_id=user_id, text=retry_text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("select_bonus:"))
async def handle_bonus_selection(callback: CallbackQuery):
    """
    Step 4 Callback: Triggered when user clicks a dynamic bonus button.
    Delivers the selected bonus content, sets stage to 4, and launches the daily warm-up scheduler.
    """
    user_id = callback.from_user.id
    bonus_value = callback.data.split(":")[1]
    
    logger.info(f"User {user_id} chosen bonus: {bonus_value}")
    
    # Ensure bonus exists in our config
    if bonus_value not in config.BONUS_CONTENTS:
        await callback.answer("⚠️ Бонус не найден", show_alert=True)
        return
        
    await callback.answer("🎁 Бонус отправлен!", show_alert=False)
    
    # 1. Update DB to Stage 4 (Bonus delivered, receiving warm-ups)
    await database.set_user_funnel_stage(user_id, 4)
    
    # 2. Schedule progressive multi-day warm-up messages
    scheduler.schedule_warmup_sequence(bot, user_id)
    
    # 3. Deliver the bonus text
    bonus_text = config.BONUS_CONTENTS[bonus_value]
    
    try:
        # Delete the congratulations message to keep chat clean
        await callback.message.delete()
    except Exception as e:
        logger.debug(f"Failed to delete step 4 congrats message: {e}")
        
    try:
        await bot.send_message(
            chat_id=user_id,
            text=bonus_text,
            parse_mode="Markdown",
            disable_web_page_preview=False
        )
        logger.info(f"Successfully delivered bonus {bonus_value} to user {user_id}")
    except Exception as e:
        logger.error(f"Could not send bonus to user {user_id}: {e}")

# -------------------------------------------------------------
# MAIN STARTUP FUNCTION
# -------------------------------------------------------------

async def main():
    # Register startup and shutdown tasks in Dispatcher
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Begin bot polling loop
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Critical error in main loop: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")


