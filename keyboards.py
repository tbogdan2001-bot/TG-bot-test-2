# keyboards.py
# CHANGED: Added comment block listing updates (FEATURE 1 & 6)
# - Adjusted get_subscribe_keyboard, get_nudge_keyboard, get_retry_subscription_keyboard to take channel_link
# - Adjusted get_bonus_keyboard to take persona config dynamically

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config

def get_offer_keyboard() -> InlineKeyboardMarkup:
    """Returns the keyboard for Step 1 (Offer choice)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🐣 Новичок", callback_data="choose_offer:beginner")
    builder.button(text="🚀 Опытный", callback_data="choose_offer:expert")
    builder.adjust(2)  # Two buttons side-by-side
    return builder.as_markup()

def get_subscribe_keyboard(channel_link: str = None) -> InlineKeyboardMarkup:
    """
    Returns the keyboard for Step 2 (Channel subscription invitation).
    CHANGED: Accepts channel_link parameter to support multiple channels (FEATURE 1)
    """
    link = channel_link if channel_link else config.CHANNEL_LINK
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Подписаться", url=link)
    builder.button(text="✅ Я подписался", callback_data="check_subscription")
    builder.adjust(1)  # Stacking buttons vertically for visual prominence
    return builder.as_markup()

def get_nudge_keyboard(channel_link: str = None) -> InlineKeyboardMarkup:
    """
    Returns the keyboard for Step 2b (Subscription nudge/reminder).
    CHANGED: Accepts channel_link parameter to support multiple channels (FEATURE 1)
    """
    link = channel_link if channel_link else config.CHANNEL_LINK
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Получить бонус", url=link)
    builder.button(text="✅ Я подписался", callback_data="check_subscription")
    builder.adjust(1)
    return builder.as_markup()

def get_retry_subscription_keyboard(channel_link: str = None) -> InlineKeyboardMarkup:
    """
    Returns the keyboard shown when subscription verification fails.
    CHANGED: Accepts channel_link parameter to support multiple channels (FEATURE 1)
    """
    link = channel_link if channel_link else config.CHANNEL_LINK
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Подписаться", url=link)
    builder.button(text="🔄 Попробовать снова", callback_data="check_subscription")
    builder.adjust(1)
    return builder.as_markup()

def get_bonus_keyboard(persona: dict) -> InlineKeyboardMarkup:
    """
    Dynamically builds and returns the keyboard for Step 4 based on persona config.
    CHANGED: Accepts persona config parameter dynamically (FEATURE 6)
    """
    builder = InlineKeyboardBuilder()
    for option in persona["bonus_options"]:
        builder.button(
            text=option["label"], 
            callback_data=f"select_bonus:{option['value']}"
        )
    builder.adjust(1)  # Vertical stack for readability
    return builder.as_markup()

def get_custom_keyboard(buttons_data: list[list[dict]]) -> InlineKeyboardMarkup:
    """
    Utility to build arbitrary keyboards (e.g., in warm-up sequences).
    Format of buttons_data: [[{"text": "Btn 1", "url": "https://..."}, ...], ...]
    """
    builder = InlineKeyboardBuilder()
    for row in buttons_data:
        for btn in row:
            if "url" in btn:
                builder.button(text=btn["text"], url=btn["url"])
            elif "callback_data" in btn:
                builder.button(text=btn["text"], callback_data=btn["callback_data"])
    builder.adjust(len(row) if buttons_data else 1)
    return builder.as_markup()

