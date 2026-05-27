# main.py
# CHANGED: Upgraded Telegram Sales Funnel Bot into a complete 3-step Quiz Funnel:
# - CommandStart presents Q1: Experience Level choice using inline keyboards
# - Added handle_q1_selection callback saving Q1 and presenting Q2
# - Added handle_q2_selection callback saving Q2, swapping to image_3 (quiz mid-point) and presenting Q3
# - Added handle_q3_selection callback saving Q3, resolving personalized bonus, setting stage to 2,
#   swapping to image_2 (subscribe prompt) and scheduling nudge
# - Upgraded check_subscription handler to call upgraded scheduler transition
# - Upgraded /admin and /admin_full dashboards to display quiz Q1/Q2/Q3 distributions and top paths
# - Added ChatMemberUpdated block/unblock handler tracking unsubscribe events
# - Added MessageReactionUpdated reaction listener for ERR analytics
# - Added catch-all reply message handler incrementing replies and resetting re-engagement states
# - Upgraded /admin with manager groups rotation mapping
# - Upgraded /admin_full with ERR metrics and re-engagement tracking metrics

import asyncio
import logging
import sys
from datetime import datetime

import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, ChatMemberUpdated, MessageReactionUpdated, ErrorEvent

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
        logging.FileHandler(os.path.join(config.BASE_DIR, "bot.log"), encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Initialize Bot and Dispatcher
if not config.BOT_TOKEN:
    logger.critical("BOT_TOKEN is empty! Please configure it in .env before launching the bot.")
    sys.exit("Critical Error: BOT_TOKEN is missing.")

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Support @router decorator as requested in Feature 1
router = dp

# In-memory rate limiting dictionary for /start command
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
    
    # 3. Restore all active scheduled jobs (Nudges & Warmups & Pressure Funnels)
    await scheduler.restore_scheduled_jobs(bot)
    
    # 4. Start Telethon userbots and schedule auto-posting / manager followups / lead check loops
    await scheduler.start_scheduler_tasks(bot)

async def on_shutdown():
    """Triggered when the bot stops polling."""
    logger.info("Shutting down bot services...")
    
    # Safely close scheduler
    if scheduler.scheduler.running:
        scheduler.scheduler.shutdown(wait=True)
        logger.info("APScheduler shut down.")
        
    # Close persistent database connection on shutdown
    await database.close_db()

# Global error handler decorator
@dp.errors()
async def global_error_handler(event: ErrorEvent):
    logger.error(f"Unhandled exception: {event.exception}", exc_info=True)
    return True

# -------------------------------------------------------------
# BOT MESSAGE AND CALLBACK HANDLERS
# -------------------------------------------------------------

@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject = None):
    """
    Step 1: Welcome message /start.
    Resets funnel state, parses traffic referral params, and initiates Q1 of the quiz.
    """
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    
    # Implement standard datetime rate limiting of 10 seconds
    now = datetime.now()
    if user_id in last_start_times:
        time_elapsed = (now - last_start_times[user_id]).total_seconds()
        if time_elapsed < 10:
            logger.info(f"Rate limit triggered for user {user_id}. Ignoring /start request.")
            return
            
    last_start_times[user_id] = now
    
    # Parse referral start parameters to extract source channel and UTM source/campaign
    start_param = command.args if command and command.args else ""
    
    source_channel = ""
    utm_source = ""
    utm_campaign = ""
    traffic_source = start_param
    
    if start_param:
        parts = start_param.split("_utm_")
        ref_part = parts[0]
        
        if ref_part.startswith("ref_"):
            source_channel = ref_part[4:]
        else:
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
            if start_param.startswith("utm_"):
                utm_part = start_param[4:]
                utm_subparts = utm_part.split("_", 1)
                utm_source = utm_subparts[0]
                if len(utm_subparts) > 1:
                    utm_campaign = utm_subparts[1]
            elif not source_channel:
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
    
    # Add/update user in DB including traffic tracking variables (will reset new quiz columns to empty/NULL)
    await database.add_or_update_user(
        telegram_id=user_id,
        username=username,
        source_channel=source_channel,
        utm_source=utm_source,
        utm_campaign=utm_campaign,
        traffic_source=traffic_source
    )
    
    # Retrieve dynamic assigned marketing persona for personalized assets
    user = await database.get_user(user_id)
    persona = config.get_persona_for_user(user)
    
    # Build welcome text using expert details & present Q1
    text = config.WELCOME_TEXT.format(
        persona_name=persona["name"],
        persona_description=persona["description"],
        niche=persona["niche"]
    )
    
    kb = keyboards.get_q1_keyboard()
    
    # Retrieve step 1 photo directly from assigned persona assets
    welcome_photo = persona["images"].get("image_1")
    
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
    """Admin-only command to view real-time funnel statistics and manager-group mappings."""
    if message.from_user.id != config.ADMIN_ID:
        return

    stats = await database.get_funnel_stats()
    text = (
        "📊 *Статистика воронки*\n\n"
        f"👥 Всего пользователей: {stats['total']}\n"
        f"📩 Этап 1 (приветствие/квиз): {stats['stage_1']}\n"
        f"📢 Этап 2 (подписка): {stats['stage_2']}\n"
        f"✅ Этап 3 (подтвердили): {stats['stage_3']}\n"
        f"🎁 Этап 4 (получили бонус): {stats['stage_4']}\n"
        f"💎 Этап 5 (закрытый клуб): {stats['stage_5']}\n"
        f"🚫 Заблокировали бота: {stats['blocked']}\n\n"
        f"📈 Конверсия (старт→бонус): {stats['conversion']:.1f}%"
    )
    
    # FEATURE 4: Fetch Multi-Group Manager Assignments mapping
    mapping = await database.get_manager_assignments_mapping()
    mapping_text = "\n\n👥 Менеджеры → Группы:\n"
    for session, groups in mapping.items():
        if not groups:
            mapping_text += f"• {session}: —\n"
        else:
            group_names = ", ".join([g["name"] for g in groups])
            mapping_text += f"• {session}: {group_names}\n"
            
    text += mapping_text
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("admin_full"))
async def cmd_admin_full(message: Message):
    """Admin-only command to view detailed multi-dimensional funnel stats, quiz answers, CRM leads, and ERR engagement metrics."""
    if message.from_user.id != config.ADMIN_ID:
        return

    stats = await database.get_full_stats()
    
    # Stages format
    stages_text = (
        f"  🔹 Шаг 1 (Приветствие/Квиз): {stats['stages'][1]}\n"
        f"  🔹 Шаг 2 (Ожидание подписки): {stats['stages'][2]}\n"
        f"  🔹 Шаг 3 (Подтвердили, ожидают): {stats['stages'][3]}\n"
        f"  🔹 Шаг 4 (Получили бонус): {stats['stages'][4]}\n"
        f"  🔹 Шаг 5 (Вступили в закрытый клуб): {stats['stages'][5]}"
    )
    
    # Quiz breakdowns format
    q1_text = "\n".join([f"  🔸 {ans}: {count}" for ans, count in stats["q1_breakdown"].items()]) or "  (Нет данных)"
    q2_text = "\n".join([f"  🔸 {ans}: {count}" for ans, count in stats["q2_breakdown"].items()]) or "  (Нет данных)"
    q3_text = "\n".join([f"  🔸 {ans}: {count}" for ans, count in stats["q3_breakdown"].items()]) or "  (Нет данных)"
    
    # Popular paths format
    paths_text = ""
    for path in stats["popular_paths"]:
        paths_text += f"  🔹 {path['path']} — {path['count']} раз(а)\n"
    if not paths_text:
        paths_text = "  (Нет данных)"
        
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
        "📊 **ПОЛНАЯ СТАТИСТИКА ВОРОНКИ (Closer & Quiz Hub)**\n\n"
        f"👥 **Всего пользователей:** {stats['total']}\n\n"
        "🚦 **По этапам воронки (активные):**\n"
        f"{stages_text}\n\n"
        "❓ **Распределение ответов квиза:**\n"
        "👉 *Q1 (Уровень опыта):*\n"
        f"{q1_text}\n"
        "👉 *Q2 (Главная цель):*\n"
        f"{q2_text}\n"
        "👉 *Q3 (Капитал):*\n"
        f"{q3_text}\n\n"
        "🏆 **Топ популярных путей квиза:**\n"
        f"{paths_text}\n"
        "📢 **По каналам трафика:**\n"
        f"{channels_text}\n"
        "🎯 **По источникам (Топ-10 UTM):**\n"
        f"{utm_text}\n"
        "💼 **Работа с лидами:**\n"
        f"  ✅ Передано в CRM (Closer Hub): {stats['closer_leads']}\n\n"
        "❄️ **Удержание (Retention & Pressure Status):**\n"
        f"  🟢 Активные (active): {stats['statuses'].get('active', 0)}\n"
        f"  🔵 Холодные (cold): {stats['statuses'].get('cold', 0)}\n"
        f"  🔴 Заблокировали бота: {stats['statuses'].get('blocked', 0)}\n\n"
        "📊 ERR Аналитика:\n"
        f"• Сообщений отправлено: {stats['messages_sent']}\n"
        f"• Реакций получено: {stats['reactions_received']}\n"
        f"• Ответов получено: {stats['replies_received']}\n"
        f"• ERR: {stats['err']:.1f}%\n\n"
        "🔥 Дожим (Pressure Funnel):\n"
        f"• В дожиме: {stats['statuses'].get('pressure', 0)}\n"
        f"• Потеряно: {stats['statuses'].get('lost', 0)}\n\n"
        f"📈 **Конверсия (Старт → Бонус):** {stats['conversion']:.1f}%"
    )
    
    await message.answer(text, parse_mode="Markdown")

# CHANGED: Added CallbackQuery handlers for 3-step Quiz Decision Tree
@dp.callback_query(F.data.startswith("quiz_q1:"))
async def handle_q1_selection(callback: CallbackQuery):
    """Handles Q1 (Experience level) callback. Saves choice and advances to Q2."""
    user_id = callback.from_user.id
    answer = callback.data.split(":")[1]
    logger.info(f"User {user_id} answered Q1: {answer}")
    
    # Intercept user activity to pull out of pressure sequence
    await scheduler.handle_user_activity(bot, user_id)
    
    await database.set_user_quiz_q1(user_id, answer)
    await callback.answer()
    
    q2_text = "**Вопрос 2: Какова ваша главная цель?**"
    try:
        # Edit caption since the start post contains a photo
        await callback.message.edit_caption(
            caption=q2_text,
            reply_markup=keyboards.get_q2_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to edit Q1 caption: {e}")
        await callback.message.answer(text=q2_text, reply_markup=keyboards.get_q2_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("quiz_q2:"))
async def handle_q2_selection(callback: CallbackQuery):
    """Handles Q2 (Main Goal) callback. Saves choice, updates image to image_3 (mid-point), and advances to Q3."""
    user_id = callback.from_user.id
    answer = callback.data.split(":")[1]
    logger.info(f"User {user_id} answered Q2: {answer}")
    
    # Intercept user activity to pull out of pressure sequence
    await scheduler.handle_user_activity(bot, user_id)
    
    await database.set_user_quiz_q2(user_id, answer)
    await callback.answer()
    
    user = await database.get_user(user_id)
    persona = config.get_persona_for_user(user)
    
    # Swaps photo to image_3 (quiz mid-point visual)
    image_3 = persona["images"].get("image_3")
    q3_text = "**Вопрос 3: Какой ваш стартовый капитал?**"
    
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=image_3,
                caption=q3_text,
                parse_mode="Markdown"
            ),
            reply_markup=keyboards.get_q3_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to edit Q2 media: {e}")
        await callback.message.answer_photo(
            photo=image_3,
            caption=q3_text,
            reply_markup=keyboards.get_q3_keyboard(),
            parse_mode="Markdown"
        )

@dp.callback_query(F.data.startswith("quiz_q3:"))
async def handle_q3_selection(callback: CallbackQuery):
    """Handles Q3 (Starting Capital) callback. Saves choice, resolves personalized bonus, and displays Step 2 Sub prompt."""
    user_id = callback.from_user.id
    answer = callback.data.split(":")[1]
    logger.info(f"User {user_id} answered Q3: {answer}")
    
    # Intercept user activity to pull out of pressure sequence
    await scheduler.handle_user_activity(bot, user_id)
    
    user_data = await database.get_user(user_id)
    persona = config.get_persona_for_user(user_data)
    
    q1 = user_data.get("quiz_q1", "beginner")
    q2 = user_data.get("quiz_q2", "passive_income")
    q3 = answer
    
    # Resolve the personalized bonus variant based on Q1-Q3 combinations
    bonus_variant = config.get_personalized_bonus(persona["id"], q1, q2, q3)
    await database.set_user_quiz_q3(user_id, q3, bonus_variant)
    await callback.answer()
    
    # Schedule the subscription check nudge
    scheduler.schedule_subscription_nudge(bot, user_id)
    
    # Retrieve source channel credentials
    channel_link = config.CHANNEL_LINK
    channel_name = config.CHANNEL_NAME
    source_channel_id = user_data.get("source_channel")
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
    
    # Retrieve image_2 (subscribe prompt photo)
    image_2 = persona["images"].get("image_2")
    
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=image_2,
                caption=text,
                parse_mode="Markdown"
            ),
            reply_markup=kb
        )
    except Exception as e:
        logger.error(f"Failed to transition to Q3 subscribe prompt: {e}")
        await callback.message.answer_photo(
            photo=image_2,
            caption=text,
            reply_markup=kb,
            parse_mode="Markdown"
        )

@dp.callback_query(F.data == "check_subscription")
async def handle_subscription_check(callback: CallbackQuery):
    """
    Step 3: Triggered when user clicks "Я подписался".
    Verifies subscription using get_chat_member.
    If subscribed: transitions to Step 4 (delivering bonus + dark club visual).
    If not: displays a retry warning.
    """
    user_id = callback.from_user.id
    logger.info(f"User {user_id} clicked subscription verification")
    
    # Intercept user activity to pull out of pressure sequence
    await scheduler.handle_user_activity(bot, user_id)
    
    user = await database.get_user(user_id)
    if not user:
        await callback.answer("⚠️ Пользователь не найден")
        return
        
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
            
        # Transitions user to Step 4 (Auto-delivers personalized bonus) and immediately to Step 5 (Dark CTA Card)
        await scheduler.transition_to_step_4(bot, user_id)
    else:
        # Not subscribed
        await callback.answer("❌ Подписка не найдена!", show_alert=True)
        retry_text = "⚠️ **Подписка не найдена.**\n\nПожалуйста, подпишитесь на наш канал по кнопке ниже и попробуйте снова 👇"
        
        channel_link = config.CHANNEL_LINK
        source_channel_id = user.get("source_channel")
        if source_channel_id:
            for ch in config.CHANNELS:
                if ch["id"] == source_channel_id:
                    channel_link = ch["link"]
                    break
                    
        kb = keyboards.get_retry_subscription_keyboard(channel_link)
        
        try:
            if callback.message.photo:
                await callback.message.edit_caption(caption=retry_text, reply_markup=kb, parse_mode="Markdown")
            else:
                await callback.message.edit_text(text=retry_text, reply_markup=kb, parse_mode="Markdown")
        except Exception as edit_err:
            logger.error(f"Error editing message for subscription retry: {edit_err}")
            await bot.send_message(chat_id=user_id, text=retry_text, reply_markup=kb, parse_mode="Markdown")

# Legacy select bonus handler kept for full backward compatibility
@dp.callback_query(F.data.startswith("select_bonus:"))
async def handle_bonus_selection(callback: CallbackQuery):
    """Step 4 Callback: Kept for backward compatibility."""
    user_id = callback.from_user.id
    bonus_value = callback.data.split(":")[1]
    logger.info(f"Legacy bonus callback invoked by {user_id}: {bonus_value}")
    
    # Intercept user activity to pull out of pressure sequence
    await scheduler.handle_user_activity(bot, user_id)
    
    await callback.answer("🎁 Бонус отправлен!", show_alert=False)
    await scheduler.transition_to_step_4(bot, user_id)

# -------------------------------------------------------------
# NEW REAL-TIME EVENT AND CATCH-ALL HANDLERS
# -------------------------------------------------------------

@dp.my_chat_member()
async def on_my_chat_member_update(update: ChatMemberUpdated):
    """Listens for block and unblock events to track subscribe/unsubscribe statuses."""
    try:
        user_id = update.from_user.id
        new_status = update.new_chat_member.status
        if new_status == "kicked":
            logger.info(f"User {user_id} blocked the bot (unsubscribe event).")
            await database.set_user_blocked(user_id, True)
            await database.set_user_subscription(user_id, False)
        elif new_status == "member":
            logger.info(f"User {user_id} unblocked the bot (subscribe event).")
            await database.set_user_blocked(user_id, False)
    except Exception as e:
        logger.error(f"Error handling chat member update: {e}", exc_info=True)

# FEATURE 1: MessageReactionUpdated registered via @router
@router.message_reaction()
async def handle_message_reaction(event: MessageReactionUpdated):
    """Listens to message reaction additions/removals in real-time to compute the ERR."""
    try:
        user_id = event.chat.id
        old_reactions = event.old_reaction or []
        new_reactions = event.new_reaction or []
        diff = len(new_reactions) - len(old_reactions)
        
        if diff != 0:
            await database.update_user_reactions(user_id, diff)
            logger.info(f"User {user_id} modified their reaction. Old count: {len(old_reactions)}, new count: {len(new_reactions)}. Diff: {diff}")
    except Exception as e:
        logger.error(f"Error in message reaction tracking: {e}", exc_info=True)

# FEATURE 1: Catch-all handler for replies
@dp.message()
async def handle_user_message(message: Message):
    """Catch-all message handler to register user replies and count replies for ERR."""
    try:
        # Ignore bot commands
        if message.text and message.text.startswith("/"):
            return
            
        user_id = message.from_user.id
        logger.info(f"Received reply from user {user_id}: {message.text or 'non-text message'}")
        
        # Reset pressure/cold statuses and cancel outstanding pressure jobs
        await scheduler.handle_user_activity(bot, user_id)
        
        # Increment replies counter in SQLite
        await database.increment_user_replies(user_id)
    except Exception as e:
        logger.error(f"Error in handle_user_message reply tracking: {e}", exc_info=True)

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
