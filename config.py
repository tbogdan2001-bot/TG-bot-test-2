# config.py
# CHANGED: Expanded persona image structures from 3 to 5 images (image_1, image_2, image_3, image_4, image_5)
# - Added Unsplash URLs for image_3 (quiz mid-point) and image_5 (dark-style final CTA card)
# - Added PRIVATE_CLUB_LINK environment variable fallback
# - Added DARK_CTA_CAPTION closing text template
# - Implemented get_personalized_bonus() to dynamically map quiz answer combinations to appropriate bonuses
# - Extended FOLLOW_UP_DELAYS for Day 4 and Day 5 pressure funnel re-engagement without breaking indices
# - Added MANAGER_GROUPS for Multi-Group Manager Rotation support
# - Added PRESSURE_PLAN containing 5 messages over 5 days for re-engaging inactive leads

import os
import sys
from dotenv import load_dotenv

# Resolve absolute directory where bot is running (handles PyInstaller compilation)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def check_and_interactive_config():
    env_path = os.path.join(BASE_DIR, ".env")
    
    config_values = {}
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        config_values[k.strip()] = v.strip()
        except Exception:
            pass
            
    placeholders = {
        "BOT_TOKEN": ["YOUR_BOT_TOKEN_HERE", ""],
        "ADMIN_ID": ["987654321", "0", ""],
        "TELEGRAM_API_ID": ["1234567", "0", ""],
        "TELEGRAM_API_HASH": ["your_api_hash_here", ""],
        "MANAGER_1_PHONE": ["+380000000000", ""]
    }
    
    needs_setup = False
    for key, bad_vals in placeholders.items():
        val = config_values.get(key, "")
        if val in bad_vals:
            needs_setup = True
            break
            
    # If the file does not exist, automatically generate a template to help the user configure it on a new computer
    if needs_setup and not os.path.exists(env_path):
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("# Telegram Bot Funnel Configuration Template\n")
                f.write("# Copy this file to .env and insert your real production values.\n\n")
                f.write("BOT_TOKEN=YOUR_BOT_TOKEN_HERE\n")
                f.write("ADMIN_ID=987654321           # Your Telegram User ID to access /admin and /admin_full\n")
                f.write("CLOSER_NOTIFY_CHAT_ID=-1002222222222\n")
                f.write("CHANNEL_ID=-1002222222222\n")
                f.write("CHANNEL_LINK=https://t.me/crypto_inside_channel\n")
                f.write("CHANNEL_NAME=Crypto Inside 📈\n")
                f.write("GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE\n")
                f.write("TELEGRAM_API_ID=1234567\n")
                f.write("TELEGRAM_API_HASH=your_api_hash_here\n")
                f.write("MANAGER_1_PHONE=+380000000000\n")
        except Exception:
            pass

    # Check if we can interact (we need stdin and isatty)
    is_interactive = sys.stdin and sys.stdin.isatty()
    
    if needs_setup and is_interactive:
        print("\n=========================================================")
        print("   🚀 НАСТРОЙКА TELEGRAM-БОТА // INTERACTIVE SETUP   ")
        print("=========================================================")
        print(" Привет! Обнаружены незаполненные или шаблонные настройки.")
        print(" Пожалуйста, укажите ваши данные ниже для настройки .env:\n")

        # 1. BOT_TOKEN
        bot_token = config_values.get("BOT_TOKEN", "")
        if bot_token in placeholders["BOT_TOKEN"]:
            while True:
                val = input("🔑 Введите ТОКЕН БОТА (BOT_TOKEN) от @BotFather: ").strip()
                if val and val not in placeholders["BOT_TOKEN"]:
                    bot_token = val
                    break
                print("❌ Токен не может быть пустым. Пожалуйста, введите корректный токен.")

        # 2. ADMIN_ID
        admin_id = config_values.get("ADMIN_ID", "")
        if admin_id in placeholders["ADMIN_ID"]:
            while True:
                val = input("👤 Введите ваш Telegram User ID (ADMIN_ID): ").strip()
                if val.isdigit() and val != "0":
                    admin_id = val
                    break
                print("❌ ID должен состоять только из цифр. Получить его можно в @userinfobot.")

        # 3. TELEGRAM_API_ID
        api_id = config_values.get("TELEGRAM_API_ID", "")
        if api_id in placeholders["TELEGRAM_API_ID"]:
            while True:
                val = input("🆔 Введите API ID от my.telegram.org (TELEGRAM_API_ID): ").strip()
                if val.isdigit() and val != "0":
                    api_id = val
                    break
                print("❌ API ID должен быть числовым.")

        # 4. TELEGRAM_API_HASH
        api_hash = config_values.get("TELEGRAM_API_HASH", "")
        if api_hash in placeholders["TELEGRAM_API_HASH"]:
            while True:
                val = input("🔐 Введите API HASH от my.telegram.org (TELEGRAM_API_HASH): ").strip()
                if val and val not in placeholders["TELEGRAM_API_HASH"]:
                    api_hash = val
                    break
                print("❌ API HASH не может быть пустым.")

        # 5. MANAGER_1_PHONE
        phone = config_values.get("MANAGER_1_PHONE", "")
        if phone in placeholders["MANAGER_1_PHONE"]:
            while True:
                val = input("📱 Введите телефон МЕНЕДЖЕРА 1 (например +380991234567): ").strip()
                if val.startswith("+") and len(val) > 7:
                    phone = val
                    break
                print("❌ Номер должен начинаться с + и содержать код страны.")

        # 6. GEMINI_API_KEY
        gemini_key = config_values.get("GEMINI_API_KEY", "")
        if gemini_key in ["YOUR_GEMINI_API_KEY_HERE", ""]:
            val = input("🤖 Введите Google Gemini API Key (Enter чтобы пропустить): ").strip()
            if val and val != "YOUR_GEMINI_API_KEY_HERE":
                gemini_key = val
            else:
                gemini_key = ""

        closer_chat = config_values.get("CLOSER_NOTIFY_CHAT_ID", "-1002222222222")

        # Save back to .env file inside BASE_DIR
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("# Telegram Bot Funnel Configuration\n")
                f.write("# Generated automatically via Interactive setup wizard\n\n")
                f.write(f"BOT_TOKEN={bot_token}\n")
                f.write(f"ADMIN_ID={admin_id}\n")
                f.write(f"CLOSER_NOTIFY_CHAT_ID={closer_chat}\n")
                f.write("CHANNEL_ID=-1002222222222\n")
                f.write("CHANNEL_LINK=https://t.me/+Ciz3NPZiQ88yMGVh\n")
                f.write("CHANNEL_NAME=Crypto Inside 📈\n")
                f.write(f"GEMINI_API_KEY={gemini_key}\n")
                f.write(f"TELEGRAM_API_ID={api_id}\n")
                f.write(f"TELEGRAM_API_HASH={api_hash}\n")
                f.write(f"MANAGER_1_PHONE={phone}\n")
            print("\n[УСПЕХ] Настройки успешно записаны в .env файл!")
            print("=========================================================\n")
        except Exception as e:
            print(f"\n❌ Ошибка при записи файла .env: {e}")
            print("=========================================================\n")

    # Load from resolved path
    load_dotenv(env_path, override=True)

# Run interactive config check
check_and_interactive_config()

# 1. Telegram Connection Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")          # Default channel backup
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/+Ciz3NPZiQ88yMGVh")
CHANNEL_NAME = os.getenv("CHANNEL_NAME", "Crypto Inside 📈")
admin_id_raw = os.getenv("ADMIN_ID", "0")
ADMIN_ID = int(admin_id_raw) if admin_id_raw.isdigit() else 0

# Closer CRM Forwarding Destination Chat ID
CLOSER_NOTIFY_CHAT_ID = os.getenv("CLOSER_NOTIFY_CHAT_ID", "")
if CLOSER_NOTIFY_CHAT_ID.startswith("-") or CLOSER_NOTIFY_CHAT_ID.isdigit():
    CLOSER_NOTIFY_CHAT_ID = int(CLOSER_NOTIFY_CHAT_ID)

# CHANGED: Private Club link configuration
PRIVATE_CLUB_LINK = os.getenv("PRIVATE_CLUB_LINK", "https://t.me/+joinchat_example")

# Keitaro PostBack URL configuration loaded from environment
KEITARO_POSTBACK_URL = os.getenv("KEITARO_POSTBACK_URL", "")

# Redis Connection URL
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Closer Telegram Username (for Day 30 retention link)
CLOSER_USERNAME = os.getenv("CLOSER_USERNAME", "example_closer_username")


# CHANGED: Multi-Account Persona Support Configuration Profiles expanded to 5 images
PERSONAS = {
    "alexander": {
        "id": "alexander",
        "name": "Александр",
        "description": "Опытный криптоинвестор с 7-летним стажем и основатель закрытого клуба",
        "niche": "криптовалюты, арбитраж трафика и пассивный доход",
        "images": {
            "image_1": os.getenv("ALEXANDER_IMAGE_1", "https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=1080"),
            "image_2": os.getenv("ALEXANDER_IMAGE_2", "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1080"),
            "image_3": os.getenv("ALEXANDER_IMAGE_3", "https://images.unsplash.com/photo-1642790106117-e829e14a795f?w=1080"),  # Quiz mid-point chart visual
            "image_4": os.getenv("ALEXANDER_IMAGE_4", "https://images.unsplash.com/photo-1513151233558-d860c5398176?w=1080"),  # Congrats
            "image_5": os.getenv("ALEXANDER_IMAGE_5", "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=1080"),  # Dark style final CTA card
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
            "image_1": os.getenv("ELENA_IMAGE_1", "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=1080"),
            "image_2": os.getenv("ELENA_IMAGE_2", "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=1080"),
            "image_3": os.getenv("ELENA_IMAGE_3", "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=1080"),  # Quiz mid-point real estate/architectural chart
            "image_4": os.getenv("ELENA_IMAGE_4", "https://images.unsplash.com/photo-1512403754473-278556139b0a?w=1080"),  # Congrats
            "image_5": os.getenv("ELENA_IMAGE_5", "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=1080"),  # Dark luxury estate final CTA card
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

# Multi-Channel / Multi-Group Referral Link Assignments
CHANNELS = [
    {
        "id": "crypto_channel",
        "link": "https://t.me/crypto_inside_channel",
        "name": "Crypto Inside Channel 📈",
        "persona_id": "alexander",
        "channel_id": "-1002222222222"
    },
    {
        "id": "estate_channel",
        "link": "https://t.me/estate_invest_channel",
        "name": "Real Estate Global 🏢",
        "persona_id": "elena",
        "channel_id": "-1003333333333"
    }
]

DEFAULT_PERSONA_ID = "alexander"

def get_persona_for_user(user: dict) -> dict:
    """Dynamically resolves the assigned persona config for a user based on their source channel"""
    source_channel_id = user.get("source_channel")
    persona_id = DEFAULT_PERSONA_ID
    
    if source_channel_id:
        for ch in CHANNELS:
            if ch["id"] == source_channel_id:
                persona_id = ch["persona_id"]
                break
                
    return PERSONAS.get(persona_id, PERSONAS[DEFAULT_PERSONA_ID])

def get_channel_id_for_user(user: dict) -> str:
    """Dynamically resolves target verification channel ID based on source channel"""
    source_channel_id = user.get("source_channel")
    if source_channel_id:
        for ch in CHANNELS:
            if ch["id"] == source_channel_id:
                return ch.get("channel_id", CHANNEL_ID)
    return CHANNEL_ID

# CHANGED: Added quiz answer combination personalized bonus resolver
def get_personalized_bonus(persona_id: str, q1: str, q2: str, q3: str) -> str:
    """Dynamically resolves the personalized bonus content based on quiz responses."""
    # We map combinations to bonus options:
    # Beginner -> DeFi guide / Villas catalog
    # Experienced or Professional -> Safe start checklist / ROI guide
    if persona_id == "alexander":
        if q1 == "beginner":
            return "bonus_defi"
        else:
            return "bonus_checklist"
    else:  # elena
        if q1 == "beginner":
            return "bonus_villas"
        else:
            return "bonus_roi"

# Delays in minutes
# FOLLOW_UP_DELAYS[0] is the subscription nudge check (Step 2b) (e.g. 30 mins)
# FOLLOW_UP_DELAYS[1:5] are the main content plan stages (e.g. 1h, 24h, 48h, 72h)
# FOLLOW_UP_DELAYS[5:8] are the long-term retention stages (e.g. Day 7, Day 14, Day 30)
# FOLLOW_UP_DELAYS[8:10] are the new Day 4 and Day 5 pressure funnel stages (5760 and 7200 minutes)
# Append new delays to keep all existing indices fully compatible.
FOLLOW_UP_DELAYS = [30, 60, 1440, 2880, 4320, 10080, 20160, 43200, 5760, 7200]

# 4. Core Funnel Texts (Allows full translation/modification of messages)
WELCOME_TEXT = (
    "👋 Приветствую! Меня зовут **{persona_name}**.\n\n"
    "Я — {persona_description}.\n\n"
    "Добро пожаловать в мой интерактивный бот-помощник! Моя цель — помочь тебе освоить **{niche}** и выйти на стабильный доход без лишнего риска.\n\n"
    "Перед тем, как выдать тебе персональный бонус, давай пройдём короткий опрос из 3 вопросов 👇\n\n"
    "**Вопрос 1: Какой у тебя уровень опыта в инвестициях?**"
)

SUBSCRIBE_CALL_TEXT = (
    "🔥 **Опрос завершен! Подходящий для тебя бонус подобран!**\n\n"
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
    "Вы успешно прошли опрос и получили полный доступ к воронке полезных материалов.\n\n"
    "На основе ваших ответов я подготовил индивидуальный результат:"
)

# CHANGED: Added closing dark-themed post template
DARK_CTA_CAPTION = (
    "🔥 **ДОБРО ПОЖАЛОВАТЬ В ЗАКРЫТЫЙ КЛУБ // {persona_name}**\n\n"
    "Вы успешно прошли опрос, получили свой персональный бонус и подтвердили подписку!\n\n"
    "Теперь перед вами открывается уникальная возможность — войти в наше приватное сообщество по **{niche}**.\n\n"
    "**Что вас ждет внутри закрытого клуба:**\n"
    "1️⃣ Ежедневная инсайдерская аналитика рынка\n"
    "2️⃣ Совместные сделки и разбор инвест-идей\n"
    "3️⃣ Прямой доступ к сильному окружению и единомышленникам\n\n"
    "👇 Нажмите кнопку ниже прямо сейчас, чтобы занять свое место в клубе совершенно бесплатно!"
)

# Extended Warm-up Sequence Content Plan Supporting 8 Message Types
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

# Retention Sequence Configurations for Long-Term Engagement
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
            "Это {persona_name}. Я закрываю набор на индивидуальное наставничество по {niche}.\n\n"
            "Осталось последнее свободное место со скидкой 50%. Если вы хотите начать зарабатывать под моим руководством — нажимайте кнопку ниже прямо сейчас! 👇"
        ),
        "keyboard": [
            [{"text": "📥 Занять место", "url": f"https://t.me/{CLOSER_USERNAME}"}]
        ]
    }
]

# ==============================================================================
# NEW: AI CONTENT & AUTOPOSTING & MULTI-ACCOUNT MANAGER SYSTEM CONFIGURATION
# ==============================================================================

# AI Content Generation
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Auto-posting schedule (UTC times)
POSTING_SCHEDULE = ["09:00", "17:00"]

# Manager accounts (Telethon userbots)
api_id_raw = os.getenv("TELEGRAM_API_ID", "0")
TELEGRAM_API_ID = int(api_id_raw) if api_id_raw.isdigit() else 0
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")

MANAGER_ACCOUNTS = [
    {
        "session": "manager_1",
        "persona_id": "alexander",  # must match a key in PERSONAS dict
        "groups": [],  # dynamically monitored from database mapping
        "phone": os.getenv("MANAGER_1_PHONE", "")
    }
]

# MANAGER_GROUPS configuration list for Feature 3 manager rotation
MANAGER_GROUPS = [
    {"group_id": "-1002222222222", "name": "Crypto Discussion 💬"},
    {"group_id": "-1003333333333", "name": "Estate Talk 🏢"},
    {"group_id": "-1004444444444", "name": "Arbitrage Club 📈"}
]

# Pressure Sequence (Дожим) for cold/inactive leads
PRESSURE_PLAN = [
    {
        "stage": 1,
        "delay_index": 2,  # FOLLOW_UP_DELAYS[2] = 1440 minutes (Day 1)
        "type": "hook",
        "text": (
            "🎯 **{persona_name} // КОЕ-ЧТО ИНТЕРЕСНОЕ ДЛЯ ВАС**\n\n"
            "Привет! Я заметил, что вы интересовались темой **{niche}**, но так и не решились сделать первый шаг. "
            "Почему большинство людей так и остаются на месте? Из-за страха неизвестности.\n\n"
            "Я подготовил для вас небольшую инсайдерскую информацию, которая развеет все сомнения. Интересно? 😉"
        ),
        "image": "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1080"
    },
    {
        "stage": 2,
        "delay_index": 3,  # FOLLOW_UP_DELAYS[3] = 2880 minutes (Day 2)
        "type": "social_proof",
        "text": (
            "📈 **РЕЗУЛЬТАТЫ НАШИХ УЧАСТНИКОВ**\n\n"
            "Посмотрите на результаты одного из наших учеников в сфере **{niche}**!\n\n"
            "Он тоже начинал с нуля, сомневался и откладывал на потом. Но применив мою пошаговую систему, "
            "он заработал первые деньги уже через неделю! Никакой магии — чистая математика и алгоритмы."
        ),
        "image": "https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=1080"
    },
    {
        "stage": 3,
        "delay_index": 4,  # FOLLOW_UP_DELAYS[4] = 4320 minutes (Day 3)
        "type": "urgency",
        "text": (
            "⏳ **ВРЕМЯ УХОДИТ!**\n\n"
            "Бронь на ваше специальное предложение по {niche} сгорает.\n\n"
            "Количество мест в закрытой группе ограничено, и я физически не смогу "
            "держать место для вас дольше. Не упустите свой шанс начать зарабатывать на лучших условиях!"
        ),
        "image": "https://images.unsplash.com/photo-1508962914676-134849a727f0?w=1080"
    },
    {
        "stage": 4,
        "delay_index": 8,  # FOLLOW_UP_DELAYS[8] = 5760 minutes (Day 4)
        "type": "direct_offer",
        "text": (
            "🔥 **СПЕЦИАЛЬНОЕ ПРЕДЛОЖЕНИЕ ДЛЯ ВАС**\n\n"
            "Хватит сомневаться и откладывать жизнь на завтра! "
            "Вот ваша персональная ссылка на вступление в наше приватное сообщество по **{niche}**.\n\n"
            "Нажимайте на кнопку ниже прямо сейчас, забирайте свою скидку и занимайте место! 👇"
        ),
        "image": "https://images.unsplash.com/photo-1553729459-beb747028b4e?w=1080",
        "keyboard": [
            [{"text": "📥 Вступить по спец. условиям", "url": f"https://t.me/{CLOSER_USERNAME}"}]
        ]
    },
    {
        "stage": 5,
        "delay_index": 9,  # FOLLOW_UP_DELAYS[9] = 7200 minutes (Day 5)
        "type": "breakup",
        "text": (
            "💔 **ФИНАЛЬНОЕ УВЕДОМЛЕНИЕ // {persona_name}**\n\n"
            "Похоже, сфера {niche} сейчас вас не интересует. Это абсолютно нормально, у каждого свои приоритеты.\n\n"
            "Я удаляю вашу бронь. Это мое последнее сообщение вам. "
            "Если вы всё же решите изменить свою жизнь — вы знаете, где меня найти. Удачи!"
        ),
        "image": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1080"
    }
]

# Communication scripts
FIRST_MESSAGE_SCRIPT = (
    "Привет! Рад видеть тебя в нашей группе. 👋\n\n"
    "Меня зовут {persona_name}. Я вижу, что ты интересуешься сферой {niche}.\n"
    "Специально для новых участников я подготовил полезный подарок! Хочешь получить?"
)

FOLLOWUP_SCRIPTS = [
    # Day 1 Followup (24 hours)
    (
        "👋 Привет! Вчера писал тебе насчет подарка по {niche}. Заметил, что ты не ответил.\n\n"
        "Специально для тебя я выложил бесплатный гайд, который поможет тебе сэкономить кучу времени. Скинуть ссылку?"
    ),
    # Day 3 Followup (72 hours)
    (
        "🔥 Привет! Всё ещё актуальна тема заработка на {niche}?\n\n"
        "Мы сейчас запускаем новый закрытый поток участников, и осталось буквально 2 места. Если интересно получить подробности, просто напиши мне «ИНТЕРЕСНО» в ответ."
    ),
    # Day 5 Followup (120 hours)
    (
        "Привет! Последний раз пишу тебе по поводу {niche}.\n\n"
        "Если ты действительно хочешь выйти на стабильный доход и не терять время зря — это твой финальный шанс. "
        "Посмотри наш официальный канал: {channel_link}. Если надумаешь — пиши, я всегда на связи. Удачи!"
    )
]
