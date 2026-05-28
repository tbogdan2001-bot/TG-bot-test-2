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
# CHANGED: Keitaro subid tracking — extract start_param as keitaro_subid, pass to DB, send PostBack on subscription

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
from postback import send_keitaro_postback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Rate limiting: track last /start time per user
last_start_times = {}


# =============================================================================
# STEP 1: /start command — Quiz funnel entry point
# =============================================================================

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
    # Keitaro subid — полный start_param является уникальным ID клика (e.g. AFF.122.42sasafaf43)
    keitaro_subid = start_param
    await database.add_or_update_user(
        telegram_id=user_id,
        username=username,
        source_channel=source_channel,
        utm_source=utm_source,
        utm_campaign=utm_campaign,
        traffic_source=traffic_source,
        subid=keitaro_subid
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
        except Exception as photo_err:
            logger.warning(f"Photo send failed for {user_id}: {photo_err}. Sending text only.")
            await message.answer(text=text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer(text=text, reply_markup=kb, parse_mode="Markdown")


# =============================================================================
# STEP 2: Quiz Q1/Q2/Q3 handlers
# =============================================================================

@dp.callback_query(F.data.startswith("q1:"))
async def handle_q1_selection(callback: CallbackQuery):
    """Step 2a: Q1 answer selected — save and present Q2."""
    user_id = callback.from_user.id
    q1_value = callback.data.split(":")[1]
    logger.info(f"User {user_id} answered Q1: {q1_value}")
    
    await scheduler.handle_user_activity(bot, user_id)
    await database.save_quiz_answer(user_id, "q1", q1_value)
    
    user = await database.get_user(user_id)
    persona = config.get_persona_for_user(user)
    
    text = config.Q2_TEXT.format(
        persona_name=persona["name"]
    )
    kb = keyboards.get_q2_keyboard()
    
    try:
        await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data.startswith("q2:"))
async def handle_q2_selection(callback: CallbackQuery):
    """Step 2b: Q2 answer selected — save and present Q3 with mid-point image."""
    user_id = callback.from_user.id
    q2_value = callback.data.split(":")[1]
    logger.info(f"User {user_id} answered Q2: {q2_value}")
    
    await scheduler.handle_user_activity(bot, user_id)
    await database.save_quiz_answer(user_id, "q2", q2_value)
    
    user = await database.get_user(user_id)
    persona = config.get_persona_for_user(user)
    
    text = config.Q3_TEXT.format(
        persona_name=persona["name"]
    )
    kb = keyboards.get_q3_keyboard()
    mid_image = persona["images"].get("image_3")
    
    try:
        if mid_image:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=mid_image, caption=text, parse_mode="Markdown"),
                reply_markup=kb
            )
        else:
            await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data.startswith("q3:"))
async def handle_q3_selection(callback: CallbackQuery):
    """Step 2c: Q3 answer selected — resolve persona bonus, prompt subscription."""
    user_id = callback.from_user.id
    q3_value = callback.data.split(":")[1]
    logger.info(f"User {user_id} answered Q3: {q3_value}")
    
    await scheduler.handle_user_activity(bot, user_id)
    await database.save_quiz_answer(user_id, "q3", q3_value)
    await database.set_user_stage(user_id, 2)
    
    user = await database.get_user(user_id)
    persona = config.get_persona_for_user(user)
    
    channel_link = config.get_channel_link_for_user(user)
    channel_name = config.get_channel_name_for_user(user)
    
    text = config.SUBSCRIBE_PROMPT_TEXT.format(
        persona_name=persona["name"],
        channel_name=channel_name
    )
    kb = keyboards.get_subscription_keyboard(channel_link)
    subscribe_image = persona["images"].get("image_2")
    
    try:
        if subscribe_image:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=subscribe_image, caption=text, parse_mode="Markdown"),
                reply_markup=kb
            )
        else:
            await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()
    
    # Schedule nudge if user doesn't subscribe in time
    await scheduler.schedule_subscription_nudge(bot, user_id)


# =============================================================================
# STEP 3: Subscription verification
# =============================================================================

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

        # Отправляем PostBack в Кейтаро для фиксации конверсии
        user_subid = user.get("subid", "") if user else ""
        if user_subid and config.KEITARO_POSTBACK_URL:
            await send_keitaro_postback(user_subid, config.KEITARO_POSTBACK_URL)

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
        
        if new_status in ("kicked", "left"):
            await database.set_user_blocked(user_id, True)
            logger.info(f"User {user_id} blocked/left the bot.")
        elif new_status == "member":
            await database.set_user_blocked(user_id, False)
            logger.info(f"User {user_id} unblocked the bot.")
    except Exception as e:
        logger.error(f"Error in on_my_chat_member_update: {e}")


@dp.message_reaction()
async def on_message_reaction(update: MessageReactionUpdated):
    """Tracks emoji reactions for ERR analytics."""
    try:
        user_id = update.user.id if update.user else None
        if user_id:
            await database.increment_reactions(user_id)
            logger.debug(f"Reaction from {user_id} tracked.")
    except Exception as e:
        logger.error(f"Error in on_message_reaction: {e}")


@dp.message()
async def handle_any_message(message: Message):
    """Catch-all handler for any text reply — increments reply count for ERR tracking."""
    try:
        user_id = message.from_user.id
        await database.increment_replies(user_id)
        await scheduler.handle_user_activity(bot, user_id)
        logger.debug(f"Reply from {user_id} tracked.")
    except Exception as e:
        logger.error(f"Error in handle_any_message: {e}")


# =============================================================================
# ADMIN COMMANDS
# =============================================================================

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Basic admin dashboard."""
    if message.from_user.id != config.ADMIN_ID:
        return
    stats = await database.get_admin_stats()
    text = config.format_admin_stats(stats)
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("admin_full"))
async def cmd_admin_full(message: Message):
    """Extended admin dashboard with ERR and re-engagement metrics."""
    if message.from_user.id != config.ADMIN_ID:
        return
    stats = await database.get_admin_stats()
    text = config.format_admin_stats_full(stats)
    await message.answer(text, parse_mode="Markdown")


# =============================================================================
# BOT STARTUP
# =============================================================================

async def on_startup():
    await database.init_db()
    await scheduler.start_scheduler(bot)
    logger.info("Bot started successfully.")


async def on_shutdown():
    await scheduler.stop_scheduler()
    logger.info("Bot stopped.")


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    logger.info("Starting bot polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
