# config.py
# CHANGED: Added comprehensive comments and new sections (FEATURE 1, 2, 3, 4, 5, 6)
# ==============================================================================
# FULLY CONFIGURABLE PLATFORM FOR TELEGRAM WARM-UP & RETENTION FUNNELS ("СХЕМНЫЙ ТРАФ")
# All text, personas, channels, content plans, and closer credentials reside here.
# ==============================================================================
import os
from dotenv import load_dotenv

load_dotenv()

# 1. Telegram Connection Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")          # Default channel backup
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/example_channel")
CHANNEL_NAME = os.getenv("CHANNEL_NAME", "Crypto Inside 📈")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# CHANGED: Closer CRM Forwarding Destination Chat ID (FEATURE 4)
CLOSER_NOTIFY_CHAT_ID = os.getenv("CLOSER_NOTIFY_CHAT_ID", "")
if CLOSER_NOTIFY_CHAT_ID.startswith("-") or CLOSER_NOTIFY_CHAT_ID.isdigit():
    CLOSER_NOTIFY_CHAT_ID = int(CLOSER_NOTIFY_CHAT_ID)


# CHANGED: Multi-Account Persona Support Configuration Profiles (FEATURE 6)
# Each profile contains specialized persona names, niches, assets, and bonuses.
# This enables completely different marketing funnels from a single bot instance.
PERSONAS = {
    "alexander": {
        "id": "alexander",
        "name": "Александр",
        "description": "Опытный криптоинвестор с 7-летним стажем и основатель закрытого клуба",
        "niche": "криптовалюты, арбитраж трафика и пассивный доход",
        "images": {
            "image_1": "https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=1080",
            "image_2": "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1080",
            "image_4": "https://images.unsplash.com/photo-1513151233558-d860c5398176?w=1080",
        },
        "bonus_options": [
            {"label": "🎁 Секретный DeFi Гайд", "value": "bonus_defi"},
            {"label": "🎁 Чек-лист: Безопасный Старт 2026", "value": "bonus_checklist"},
        ],
        "bonus_contents": {
            "bonus_defi": (
                "🎉 **Ваш DeFi Гайд успешно разблокирован!**\n\n"
                "В этом руководстве мы разложили по полочкам:\n"
                "1️⃣ Что такое фарминг и стейкинг простыми словами\n"
                "2️⃣ Пошаговый алгоритм покупки первой монеты\n"
                "3️⃣ Топ-3 кошелька для безопасного хранения активов\n\n"
                "🔗 [Читать гайд в Notion](https://example.com/defi-notion-guide)\n\n"
                "Обязательно изучи его! Скоро я пришлю тебе первый секретный совет."
            ),
            "bonus_checklist": (
                "🎉 **Ваш Чек-лист по безопасности в 2026 году готов!**\n\n"
                "Защити свои средства от мошенников:\n"
                "1️⃣ Правило двухфакторной аутентификации (2FA)\n"
                "2️⃣ Как распознать фишинговые сайты за 5 секунд\n"
                "3️⃣ Памятка по хранению сид-фразы\n\n"
                "🔗 [Скачать Чек-лист в PDF](https://example.com/safety-checklist-2026.pdf)\n\n"
                "Сохрани себе этот файл! Через час я пришлю тебе важную информацию."
            )
        }
    },
    "elena": {
        "id": "elena",
        "name": "Елена",
        "description": "Эксперт по инвестициям в зарубежную недвижимость и пассивному доходу",
        "niche": "инвестиции в недвижимость Бали, Дубая и Таиланда",
        "images": {
            "image_1": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=1080",
            "image_2": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=1080",
            "image_4": "https://images.unsplash.com/photo-1512403754473-278556139b0a?w=1080",
        },
        "bonus_options": [
            {"label": "🎁 Каталог: ТОП-5 вилл 2026", "value": "bonus_villas"},
            {"label": "🎁 Руководство: ROI 15%+ годовых", "value": "bonus_roi"},
        ],
        "bonus_contents": {
            "bonus_villas": (
                "🎉 **Каталог инвест-вилл успешно разблокирован!**\n\n"
                "Внутри вы найдете:\n"
                "1️⃣ Объекты на стадии котлована с доходностью от 30% на перепродаже\n"
                "2️⃣ Виллы с гарантированной арендой от отельных операторов\n"
                "🔗 [Скачать каталог вилл PDF](https://example.com/bali-villas-2026.pdf)\n\n"
                "Изучите объекты! Скоро я пришлю вам первый аналитический обзор рынка."
            ),
            "bonus_roi": (
                "🎉 **Руководство по доходности недвижимости разблокировано!**\n\n"
                "Основные разделы:\n"
                "1️⃣ Как рассчитать реальный чистый ROI объекта\n"
                "2️⃣ Налоги и скрытые расходы при покупке за рубежом\n"
                "🔗 [Открыть руководство Notion](https://example.com/roi-guide-notion)\n\n"
                "Сохраните себе ссылку! Скоро я пришлю вам полезные расчеты."
            )
        }
    }
}


# CHANGED: Multi-Channel / Multi-Group Referral Link Assignments (FEATURE 1)
# Links users to a specific source channel and matches them to a unique marketing persona.
CHANNELS = [
    {
        "id": "crypto_channel",
        "link": "https://t.me/crypto_inside_channel",
        "name": "Crypto Inside Channel 📈",
        "persona_id": "alexander",
        "channel_id": "-1002222222222"  # Target verification ID (FEATURE 1)
    },
    {
        "id": "estate_channel",
        "link": "https://t.me/estate_invest_channel",
        "name": "Real Estate Global 🏢",
        "persona_id": "elena",
        "channel_id": "-1003333333333"  # Target verification ID (FEATURE 1)
    }
]

DEFAULT_PERSONA_ID = "alexander"

def get_persona_for_user(user: dict) -> dict:
    """Dynamically resolves the assigned persona config for a user based on their source channel (FEATURE 6)"""
    source_channel_id = user.get("source_channel")
    persona_id = DEFAULT_PERSONA_ID
    
    if source_channel_id:
        for ch in CHANNELS:
            if ch["id"] == source_channel_id:
                persona_id = ch["persona_id"]
                break
                
    return PERSONAS.get(persona_id, PERSONAS[DEFAULT_PERSONA_ID])

def get_channel_id_for_user(user: dict) -> str:
    """Dynamically resolves target verification channel ID based on source channel (FEATURE 1)"""
    source_channel_id = user.get("source_channel")
    if source_channel_id:
        for ch in CHANNELS:
            if ch["id"] == source_channel_id:
                return ch.get("channel_id", CHANNEL_ID)
    return CHANNEL_ID


# CHANGED: Delays in minutes (FEATURE 3 & 5)
# FOLLOW_UP_DELAYS[0] is the subscription nudge check (Step 2b) (e.g. 30 mins)
# FOLLOW_UP_DELAYS[1:5] are the main content plan stages (e.g. 1h, 24h, 48h, 72h)
# FOLLOW_UP_DELAYS[5:8] are the long-term retention stages (e.g. Day 7, Day 14, Day 30)
FOLLOW_UP_DELAYS = [30, 60, 1440, 2880, 4320, 10080, 20160, 43200]


# 4. Core Funnel Texts (Allows full translation/modification of messages)
WELCOME_TEXT = (
    "👋 Приветствую! Меня зовут **{persona_name}**.\n\n"
    "Я — {persona_description}.\n\n"
    "Добро пожаловать в мой интерактивный бот-помощник! Моя цель — помочь тебе освоить **{niche}** и выйти на стабильный доход без лишнего риска.\n\n"
    "Перед тем, как мы начнем, выбери свой текущий уровень опыта ниже 👇"
)

SUBSCRIBE_CALL_TEXT = (
    "🔥 Отличный выбор!\n\n"
    "Чтобы получить доступ к закрытым материалам и забрать гарантированные подарки, "
    "тебе необходимо подписаться на мой официальный канал: **{channel_name}**.\n\n"
    "Подпишись по кнопке ниже и нажми «Я подписался» 👇"
)

NUDGE_TEXT = (
    "⌛ **Количество бонусов ограничено!**\n\n"
    "Мы заметили, что ты еще не подписался на наш канал. Подпишись прямо сейчас и мгновенно забери свой приветственный бонус 🎁"
)

ALREADY_SUBSCRIBED_NUDGE = "✅ Вы уже подписаны! Забирайте свои бонусы ниже."

STEP_4_CONGRATS_TEXT = (
    "🎉 **Поздравляю! Подписка успешно подтверждена!**\n\n"
    "Вы получили полный доступ к воронке полезных материалов.\n\n"
    "Теперь выберите один из гарантированных бонусов ниже, чтобы начать 👇"
)


# CHANGED: Extended Warm-up Sequence Content Plan Supporting 8 Message Types (FEATURE 3)
# Allows configuring highly dynamic warm-up sequences mapping to specialized types.
# Placeholders like {persona_name}, {niche}, and {channel_name} are resolved dynamically.
CONTENT_PLAN = [
    {
        "type": "market_review",
        "delay_index": 1,  # FOLLOW_UP_DELAYS[1] = 60 minutes
        "text": (
            "📊 **{persona_name} // ОБЗОР РЫНКА ({niche})**\n\n"
            "👋 Привет! Надеюсь, вы уже начали изучать приветственный бонус!\n\n"
            "Давайте разберем, что происходит в сфере {niche} прямо сейчас. "
            "Крупный капитал активно заходит в перспективные активы, пока розничные инвесторы паникуют. "
            "В следующем сообщении я поделюсь реальным кейсом, как сделать на этом прибыль!"
        ),
        "image": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1080"
    },
    {
        "type": "success_case",
        "delay_index": 2,  # FOLLOW_UP_DELAYS[2] = 1440 minutes (24 hours)
        "text": (
            "📈 **КЕЙС УСПЕХА: +180% чистой прибыли**\n\n"
            "Хочу показать вам путь Дмитрия, одного из участников нашего закрытого клуба.\n\n"
            "Дмитрий пришел с нулевым опытом в {niche}. За месяц работы по моей системе "
            "он окупил вложения и сформировал стабильный пассивный доход. "
            "Это еще раз доказывает: системный подход побеждает хаос!"
        ),
        "image": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1080"
    },
    {
        "type": "failure_case",
        "delay_index": 3,  # FOLLOW_UP_DELAYS[3] = 2880 minutes (48 hours)
        "text": (
            "🚫 **РАЗБОР ОШИБКИ: Слив $1,500 на эмоциях**\n\n"
            "Сегодня поговорим о психологии инвестиций.\n\n"
            "Большинство новичков теряют свои депозиты в {niche} из-за синдрома FOMO "
            "(страха упущенной выгоды). Они покупают активы на пике и продают на низах. "
            "Запомните золотое правило: никогда не рискуйте суммой более 2% от депозита на одну сделку!"
        ),
        "image": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1080"
    },
    {
        "type": "audience_qa",
        "delay_index": 4,  # FOLLOW_UP_DELAYS[4] = 4320 minutes (72 hours)
        "text": (
            "❓ **ОТВЕТЫ НА ВОПРОСЫ ПОДПИСЧИКОВ**\n\n"
            "Меня часто спрашивают: «С какого капитала лучше начать инвестировать в {niche}?»\n\n"
            "Мой ответ — начните с небольшой комфортной суммы (от $100), чтобы протестировать механику. "
            "Если хотите получить разбор вашей личной ситуации лично от меня ({persona_name}), забронируйте встречу ниже! 👇"
        ),
        "image": "https://images.unsplash.com/photo-1521737711867-e3b904737c88?w=1080",
        "keyboard": [
            [{"text": "🗓 Забронировать бесплатную консультацию", "url": "https://calendly.com/example-session"}]
        ]
    }
]


# CHANGED: Retention Sequence Configurations for Long-Term Engagement (FEATURE 5)
# Days 7, 14, and 30 messages to reactivate and warm up cold traffic.
RETENTION_PLAN = [
    {
        "stage": 1,
        "type": "expert_tip",
        "delay_index": 5,  # FOLLOW_UP_DELAYS[5] = 10080 minutes (Day 7)
        "text": (
            "👋 Привет! Это {persona_name}. Давно не общались!\n\n"
            "В сфере {niche} вышли важные обновления. Я подготовил короткий совет: "
            "сейчас лучшее время для переоценки своего портфеля и фиксации прибыли по перегретым позициям. "
            "Подробности читайте в основном канале!"
        )
    },
    {
        "stage": 2,
        "type": "free_content",
        "delay_index": 6,  # FOLLOW_UP_DELAYS[6] = 20160 minutes (Day 14)
        "text": (
            "🎁 **СВЕЖИЙ МАТЕРИАЛ ДЛЯ ВАС!**\n\n"
            "Я записал новый подробный видео-гайд о том, как диверсифицировать доходы в {niche} "
            "и получать стабильный пассивный доход в долларах.\n\n"
            "🔗 [Смотреть видео-гайд бесплатно](https://example.com/retention-video-guide)"
        )
    },
    {
        "stage": 3,
        "type": "promo_offer",
        "delay_index": 7,  # FOLLOW_UP_DELAYS[7] = 43200 minutes (Day 30)
        "text": (
            "🔥 **ПОСЛЕДНИЙ ШАНС ДЛЯ ВАС**\n\n"
            "Это {persona_name}. Я закрываю набор на индивидуальное наставничество по {niche}. "
            "Осталось последнее свободное место со скидкой 50%.\n\n"
            "Если вы хотите начать зарабатывать под моим руководством — нажимайте кнопку ниже прямо сейчас! 👇"
        ),
        "keyboard": [
            [{"text": "📥 Занять место", "url": "https://t.me/example_closer_username"}]
        ]
    }
]
