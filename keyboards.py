# keyboards.py
# CHANGED: Replaced standard binary offer selection with a 3-step quiz keyboard structure
# - Created get_q1_keyboard() for Q1: Experience Level
# - Created get_q2_keyboard() for Q2: Main Goal
# - Created get_q3_keyboard() for Q3: Starting Capital
# - Added get_dark_cta_keyboard() for Step 5 Private Club registration link

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config

# CHANGED: Added 3-step Quiz Keyboard Builders
def get_q1_keyboard() -> InlineKeyboardMarkup:
    """Returns the keyboard for Q1 (Experience level choice)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🐣 Новичок", callback_data="quiz_q1:beginner")
    builder.button(text="📈 Есть опыт", callback_data="quiz_q1:experienced")
    builder.button(text="🏆 Профессионал", callback_data="quiz_q1:professional")
    builder.adjust(1)  # Stacking vertically for premium mobile-friendly layout
    return builder.as_markup()

def get_q2_keyboard() -> InlineKeyboardMarkup:
    """Returns the keyboard for Q2 (Main Goal choice)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Пассивный доход", callback_data="quiz_q2:passive_income")
    builder.button(text="📊 Активный трейдинг", callback_data="quiz_q2:active_trading")
    builder.button(text="🎓 Обучение", callback_data="quiz_q2:learning")
    builder.adjust(1)
    return builder.as_markup()

def get_q3_keyboard() -> InlineKeyboardMarkup:
    """Returns the keyboard for Q3 (Starting Capital choice)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 До $500", callback_data="quiz_q3:under_500")
    builder.button(text="💳 $500 - $5000", callback_data="quiz_q3:between_500_5000")
    builder.button(text="💎 От $5000", callback_data="quiz_q3:above_5000")
    builder.adjust(1)
    return builder.as_markup()


# CHANGED: Added Dark CTA post button
def get_dark_cta_keyboard(club_link: str = None) -> InlineKeyboardMarkup:
    """Returns the final CTA button pointing to the private club channel/chat."""
    link = club_link if club_link else config.PRIVATE_CLUB_LINK
    builder = InlineKeyboardBuilder()
    builder.button(text="💎 Войти в закрытый клуб", url=link)
    builder.adjust(1)
    return builder.as_markup()


# Funnel keyboards kept for full backward compatibility
def get_subscribe_keyboard(channel_link: str = None) -> InlineKeyboardMarkup:
    """Returns the keyboard for Step 2 (Channel subscription invitation)."""
    link = channel_link if channel_link else config.CHANNEL_LINK
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Подписаться", url=link)
    builder.button(text="✅ Я подписался", callback_data="check_subscription")
    builder.adjust(1)
    return builder.as_markup()

def get_nudge_keyboard(channel_link: str = None) -> InlineKeyboardMarkup:
    """Returns the keyboard for Step 2b (Subscription nudge/reminder)."""
    link = channel_link if channel_link else config.CHANNEL_LINK
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Получить бонус", url=link)
    builder.button(text="✅ Я подписался", callback_data="check_subscription")
    builder.adjust(1)
    return builder.as_markup()

def get_retry_subscription_keyboard(channel_link: str = None) -> InlineKeyboardMarkup:
    """Returns the keyboard shown when subscription verification fails."""
    link = channel_link if channel_link else config.CHANNEL_LINK
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Подписаться", url=link)
    builder.button(text="🔄 Попробовать снова", callback_data="check_subscription")
    builder.adjust(1)
    return builder.as_markup()

def get_bonus_keyboard(persona: dict) -> InlineKeyboardMarkup:
    """Dynamically builds and returns the keyboard for Step 4 based on persona config."""
    builder = InlineKeyboardBuilder()
    for option in persona["bonus_options"]:
        builder.button(
            text=option["label"], 
            callback_data=f"select_bonus:{option['value']}"
        )
    builder.adjust(1)
    return builder.as_markup()

def get_custom_keyboard(buttons_data: list[list[dict]]) -> InlineKeyboardMarkup:
    """Utility to build arbitrary keyboards (e.g., in warm-up sequences)."""
    builder = InlineKeyboardBuilder()
    for row in buttons_data:
        for btn in row:
            if "url" in btn:
                builder.button(text=btn["text"], url=btn["url"])
            elif "callback_data" in btn:
                builder.button(text=btn["text"], callback_data=btn["callback_data"])
    builder.adjust(len(row) if buttons_data else 1)
    return builder.as_markup()
