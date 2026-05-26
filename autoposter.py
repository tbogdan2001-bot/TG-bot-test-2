# autoposter.py
# NEW: Auto-posting module for Telegram channels
# Integrates with ai_content.py to generate unique channel posts on a daily schedule,
# rotatively choosing between 8 content types, publishing them, and logging to SQLite.

import logging
from datetime import datetime, timezone
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

import config
import database
import ai_content
from scheduler import scheduler  # Accessing the shared APScheduler instance

logger = logging.getLogger(__name__)

# List of 8 content types in order of rotation
ROTATION_TYPES = [
    "market_review",
    "news",
    "success_case",
    "expert_tip",
    "community_poll",
    "story",
    "premium_teaser",
    "celebration"
]

async def post_to_channel(bot: Bot, channel_id: str, content: str, photo_url: str = None):
    """
    Safely publishes a message or photo to a Telegram channel.
    Handles exceptions and logs results.
    """
    try:
        # Convert string channel_id to integer if it is numeric or starts with '-'
        target_id = channel_id
        if channel_id.startswith("-") or channel_id.isdigit():
            target_id = int(channel_id)

        if photo_url:
            try:
                await bot.send_photo(
                    chat_id=target_id,
                    photo=photo_url,
                    caption=content,
                    parse_mode="Markdown"
                )
                logger.info(f"Successfully posted photo to channel {channel_id}.")
                return
            except Exception as photo_err:
                logger.error(f"Failed to send photo to channel {channel_id}: {photo_err}. Falling back to text only.")
                # Fallback to sending text message below
        
        await bot.send_message(
            chat_id=target_id,
            text=content,
            parse_mode="Markdown"
        )
        logger.info(f"Successfully posted text to channel {channel_id}.")
    except TelegramForbiddenError:
        logger.error(f"Bot was kicked or doesn't have post permissions in channel {channel_id}.")
    except Exception as e:
        logger.error(f"Failed to post content to channel {channel_id}: {e}", exc_info=True)

async def execute_autopost_for_channel(bot: Bot, ch: dict):
    """
    Executes the generation and posting process for a single channel.
    Rotates the content type, invokes Gemini generator, publishes, and logs.
    """
    channel_id = ch["channel_id"]
    channel_name = ch["name"]
    persona_id = ch["persona_id"]
    
    logger.info(f"Running autopost generation for channel '{channel_name}' ({channel_id})...")
    
    # 1. Resolve assigned persona config
    persona = config.PERSONAS.get(persona_id)
    if not persona:
        logger.error(f"Persona '{persona_id}' for channel '{channel_id}' not found. Skipping.")
        return
        
    # 2. Get the next rotating content type index
    last_index = await database.get_last_post_index(ch["id"])
    next_index = (last_index + 1) % len(ROTATION_TYPES)
    content_type = ROTATION_TYPES[next_index]
    
    logger.info(f"Channel '{ch['id']}' rotated from index {last_index} to {next_index} (Type: {content_type}).")
    
    # 3. Generate high-converting post text
    post_text = await ai_content.generate_post(persona, content_type, persona["niche"])
    
    # 4. Resolve photo (if any is configured in persona images, let's use it dynamically!)
    # We can rotate photo based on next_index or use a default welcome/subscribe asset
    photo_url = None
    if "images" in persona:
        # e.g., map even/odd indices or pull specific images
        img_key = f"image_{(next_index % 3) + 1}"  # cycles through image_1, image_2, image_4 (which are the keys in PERSONAS)
        if img_key not in persona["images"]:
            img_key = "image_1"
        photo_url = persona["images"].get(img_key)
        
    # 5. Publish to channel
    await post_to_channel(bot, channel_id, post_text, photo_url)
    
    # 6. Log post to SQLite database
    await database.log_channel_post(ch["id"], content_type, next_index, post_text)

async def post_all_channels(bot: Bot):
    """Triggers automated posting for all channels configured in config.CHANNELS."""
    logger.info("Executing global daily autopost sequence...")
    for ch in config.CHANNELS:
        try:
            await execute_autopost_for_channel(bot, ch)
        except Exception as e:
            logger.error(f"Error executing autopost for channel {ch.get('name')}: {e}", exc_info=True)

def schedule_channel_posts(bot: Bot):
    """
    Schedules cron-based autoposting jobs for configured UTC times.
    Invoked on bot startup.
    """
    logger.info("Setting up auto-posting schedules...")
    
    for post_time in config.POSTING_SCHEDULE:
        try:
            hour_str, minute_str = post_time.split(":")
            hour = int(hour_str)
            minute = int(minute_str)
            
            job_id = f"autopost_{hour:02d}_{minute:02d}"
            
            scheduler.add_job(
                post_all_channels,
                trigger="cron",
                hour=hour,
                minute=minute,
                args=[bot],
                id=job_id,
                replace_existing=True
            )
            logger.info(f"Scheduled daily auto-posting job at {hour:02d}:{minute:02d} UTC (ID: {job_id})")
        except Exception as e:
            logger.error(f"Failed to schedule auto-post job for time '{post_time}': {e}", exc_info=True)
