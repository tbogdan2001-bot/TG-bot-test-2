# main.py
# CHANGED: Added comment block listing updates (FEATURE 1, 2, 4, 5, 6)
# - CommandStart takes CommandObject parameter to parse deep-link start params
# - Implemented multi-channel start tracking and UTM campaign parsing
# - Personalized start greetings and photos mapped to dynamic assigned personas
# - Mapped Step 2 and Step 3 subscription verify links dynamically to user source channel
# - Added CRM notify_closer_hub trigger upon Stage 4 transition
# - Added get_full_stats() /admin_full stats command restricted to config.ADMIN_ID

import asyncio
import logging
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command, CommandObject
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

# In-memory rate limiting dictionary for /start command (TASK 8)
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
        
    # Close persistent database connection on shutdown (TASK 3)
    await database.close_db()

# Global error handler decorator (TASK 7)
@dp.errors()
async def global_error_handler(event, exception):
    logger.error(f"Unhandled exception: {exception}", exc_info=True)
    return True

# -------------------------------------------------------------
# BOT MESSAGE AND CALLBACK HANDLERS
# -------------------------------------------------------------

@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject = None):
    """
    Step 1: Welcome message /start.
    Saves the user, parses traffic referral params, resets funnel state, and requests level.
    """
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    
    # Implement standard datetime rate limiting of 10 seconds (TASK 8)
    now = datetime.now()
    if user_id in last_start_times:
        time_elapsed = (now - last_start_times[user_id]).total_seconds()
        if time_elapsed < 10:
            logger.info(f"Rate limit triggered for user {user_id}. Ignoring /start request.")
            return
            
    last_start_times[user_id] = now
    
    # CHANGED: Parse referral start parameters to extract source channel and UTM source/campaign (FEATURE 1 & 2)
    start_param = command.args if command and command.args else ""
    
    source_channel = ""
    utm_source = ""
    utm_campaign = ""
    traffic_source = start_param
    
    if start_param:
        # Format e.g., ref_crypto_channel_utm_facebook_retarget
        parts = start_param.split("_utm_")
        ref_part = parts[0]
        
        if ref_part.startswith("ref_"):
            source_channel = ref_part[4:]
        else:
            # Fallback checking if it direct matches a channel id
            matched_ch = False
            for ch in config.CHANNELS:
                if ref_part == ch["id"]:
                    source_channel = ref_part
                    matched_ch = True
                    break
            if not matched_ch:
                source_channel = ref_part
                
        if len(parts) > 1:
            utm_part = parts[1]
            utm_subparts = utm_part.split("_", 1)
            utm_source = utm_subparts[0]
            if len(utm_subparts) > 1:
                utm_campaign = utm_subparts[1]
        else:
            # Check if start param is a pure UTM sequence (e.g. utm_facebook_ads)
            if start_param.startswith("utm_"):
                utm_part = start_param[4:]
                utm_subparts = utm_part.split("_", 1)
                utm_source = utm_subparts[0]
                if len(utm_subparts) > 1:
                    utm_campaign = utm_subparts[1]
            elif not source_channel:
                # Basic string splitting fallback
                subparts = start_param.split("_", 1)
                utm_source = subparts[0]
                if len(subparts) > 1:
                    utm_campaign = subparts[1]

    logger.info(
        f"User {user_id} (@{username}) entered start funnel. "
        f"Channel: '{source_channel}', UTM: '{utm_source}/{utm_campaign}'"
    )
    
    # Cancel any active jobs if this is a re-entry
    scheduler.cancel_active_jobs_for_user(user_id)
    
    # Add/update user in DB including traffic tracking variables (FEATURE 1 & 2)
    await database.add_or_update_user(
        telegram_id=user_id,
        username=username,
        source_channel=source_channel,
        utm_source=utm_source,
        utm_campaign=utm_campaign,
        traffic_source=traffic_source
    )
    
    # CHANGED: Retrieve dynamic assigned marketing persona for personalized assets (FEATURE 6)
    user = await database.get_user(user_id)
    persona = config.get_persona_for_user(user)
    
    # Build personalized welcome text using expert details
    text = config.WELCOME_TEXT.format(
        persona_name=persona["name"],
        persona_description=persona["description"],
        niche=persona["niche"]
    )
    
    kb = keyboards.get_offer_keyboard()
    
    # CHANGED: Retrieve step 1 photo directly from assigned persona assets (FEATURE 6)
    welcome_photo = persona["images"].get("image_1", config.IMAGE_1)
    
    # Send welcome photo (or text if photo fails or is not provided)
    if welcome_photo:
        try:
            await message.answer_photo(
                photo=welcome_photo,
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

# CHANGED: Added detailed admin_full dashboard handler (FEATURE 1, 2, 4, 5)
@dp.message(Command("admin_full"))
async def cmd_admin_full(message: Message):
    """Admin-only command to view detailed multi-dimensional funnel statistics, channels, and CRM leads."""
    if message.from_user.id != config.ADMIN_ID:
        return

    stats = await database.get_full_stats()
    
    # Stages format
    stages_text = (
        f"  🔹 Шаг 1 (Приветствие): {stats['stages'][1]}\n"
        f"  🔹 Шаг 2 (Подписка): {stats['stages'][2]}\n"
        f"  🔹 Шаг 3 (Подтвердили): {stats['stages'][3]}\n"
        f"  🔹 Шаг 4 (Получили бонус): {stats['stages'][4]}"
    )
    
    # Channels format
    channels_text = ""
    for ch, count in stats["channels"].items():
        channels_text += f"  📢 {ch}: {count}\n"
    if not channels_text:
        channels_text = "  (Нет данных)"
        
    # UTM sources format
    utm_text = ""
    for utm, count in stats["utm_sources"].items():
        utm_text += f"  🔗 {utm}: {count}\n"
    if not utm_text:
        utm_text = "  (Нет данных)"
        
    text = (
        "📊 **ПОЛНАЯ СТАТИСТИКА ВОРОНКИ (Closer & Traffic Hub)**\n\n"
        f"👥 **Всего пользователей:** {stats['total']}\n\n"
        "🚦 **По этапам воронки (активные):**\n"
        f"{stages_text}\n\n"
        "📢 **По каналам трафика:**\n"
        f"{channels_text}\n"
        "🎯 **По источникам (Топ-10 UTM):**\n"
        f"{utm_text}\n"
        "💼 **Работа с лидами:**\n"
        f"  ✅ Передано в CRM (Closer Hub): {stats['closer_leads']}\n\n"
        "❄️ **Удержание (Retention Status):**\n"
        f"  🟢 Активные (active): {stats['statuses'].get('active', 0)}\n"
        f"  🔵 Холодные (cold): {stats['statuses'].get('cold', 0)}\n"
        f"  🔴 Заблокировали бота: {stats['statuses'].get('blocked', 0)}\n\n"
        f"📈 **Конверсия (Старт → Бонус):** {stats['conversion']:.1f}%"
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
    
    # CHANGED: Retrieve source channel credentials and custom invite links dynamically (FEATURE 1)
    user = await database.get_user(user_id)
    channel_link = config.CHANNEL_LINK
    channel_name = config.CHANNEL_NAME
    
    source_channel_id = user.get("source_channel")
    if source_channel_id:
        for ch in config.CHANNELS:
            if ch["id"] == source_channel_id:
                channel_link = ch["link"]
                channel_name = ch["name"]
                break
                
    text = config.SUBSCRIBE_CALL_TEXT.format(
        channel_name=channel_name
    )
    kb = keyboards.get_subscribe_keyboard(channel_link)
    
    # CHANGED: Retrieve expert image 2 asset directly from assigned marketing persona config (FEATURE 6)
    persona = config.get_persona_for_user(user)
    subscribe_photo = persona["images"].get("image_2", config.IMAGE_2)
    
    # Send Step 2 message with image
    try:
        if subscribe_photo:
            try:
                # Answer query first to prevent loading state on buttons
                await callback.answer()
                await bot.send_photo(
                    chat_id=user_id,
                    photo=subscribe_photo,
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
    
    user = await database.get_user(user_id)
    if not user:
        await callback.answer("⚠️ Пользователь не найден")
        return
        
    # CHANGED: Dynamically check subscription against source channel verification ID (FEATURE 1)
    target_channel_id = config.get_channel_id_for_user(user)
    is_subscribed = await scheduler.check_member_status(bot, target_channel_id, user_id)
    
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
        
        # CHANGED: Dynamically fetch custom referral join links (FEATURE 1)
        channel_link = config.CHANNEL_LINK
        source_channel_id = user.get("source_channel")
        if source_channel_id:
            for ch in config.CHANNELS:
                if ch["id"] == source_channel_id:
                    channel_link = ch["link"]
                    break
                    
        kb = keyboards.get_retry_subscription_keyboard(channel_link)
        
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
    
    user = await database.get_user(user_id)
    if not user:
        await callback.answer("⚠️ Пользователь не найден", show_alert=True)
        return
        
    # CHANGED: Dynamically retrieve bonus configurations based on assigned expert persona profile (FEATURE 6)
    persona = config.get_persona_for_user(user)
    
    if bonus_value not in persona["bonus_contents"]:
        await callback.answer("⚠️ Бонус не найден", show_alert=True)
        return
        
    await callback.answer("🎁 Бонус отправлен!", show_alert=False)
    
    # 1. Update DB to Stage 4 (Bonus delivered, receiving warm-ups)
    await database.set_user_funnel_stage(user_id, 4)
    
    # 2. Schedule progressive multi-day warm-up & long-term retention sequence (FEATURE 3 & 5)
    scheduler.schedule_warmup_sequence(bot, user_id)
    
    # 3. CHANGED: Trigger CRM notification push to Closer Hub group chat (FEATURE 4)
    await scheduler.notify_closer_hub(bot, user_id)
    
    # 4. Deliver the bonus text
    bonus_text = persona["bonus_contents"][bonus_value]
    
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
