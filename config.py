# config.py
# ==========================================
# FULLY CONFIGURABLE TEMPLATE FOR TELEGRAM WARM-UP BOT
# All text and funnel parameters reside here.
# ==========================================

# 1. Telegram Connection Configuration
BOT_TOKEN = ""                  # Insert your Telegram Bot Token from @BotFather
CHANNEL_ID = "-1002222222222"    # Target channel ID (e.g., -100xxxxxxxxx or @username)
CHANNEL_LINK = "https://t.me/example_channel"  # Link for users to join the channel
CHANNEL_NAME = "Crypto Inside 📈"  # Display name of the channel

# 2. Marketing Persona / Niche
PERSONA_NAME = "Александр"
PERSONA_DESCRIPTION = "Опытный криптоинвестор с 7-летним стажем и основатель закрытого клуба"
NICHE = "криптовалюты, арбитраж трафика и пассивный доход"

# 3. Media Assets (URLs or Local Absolute/Relative File Paths)
IMAGE_1 = "https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=1080" # Step 1 (Welcome / Start)
IMAGE_2 = "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1080" # Step 2 (Subscribe Call)
IMAGE_4 = "https://images.unsplash.com/photo-1513151233558-d860c5398176?w=1080" # Step 4 (Congratulations & Bonus delivery)

# 4. Funnel Bonus Options (Step 4)
BONUS_OPTIONS = [
    {"label": "🎁 Секретный DeFi Гайд", "value": "bonus_defi"},
    {"label": "🎁 Чек-лист: Безопасный Старт 2026", "value": "bonus_checklist"},
]

# Delays in minutes
# FOLLOW_UP_DELAYS[0] is the subscription reminder (Step 2b, e.g. 30 minutes)
# FOLLOW_UP_DELAYS[1:] are the subsequent days of automated warm-up sequences
FOLLOW_UP_DELAYS = [30, 60, 1440, 2880, 4320]

# 5. Core Funnel Texts (Allows full translation/modification of messages)
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

# 6. Delivered Bonus Contents (What users receive when selecting a bonus)
BONUS_CONTENTS = {
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

# 7. Warm-up Sequence Elements (Custom messages delivered sequentially by APScheduler)
# Each item will be triggered at `FOLLOW_UP_DELAYS[delay_index]` relative to the subscription timestamp.
WARMUP_SEQUENCES = [
    {
        "delay_index": 1,  # FOLLOW_UP_DELAYS[1] = 60 minutes
        "text": (
            "👋 Привет! Это {persona_name}. Надеюсь, вы уже начали изучать приветственный бонус!\n\n"
            "В нашей сфере ({niche}) критически важно уметь отделять сигналы от шума. "
            "Большинство новичков теряют свои депозиты в первые же недели просто потому, что слушают псевдо-экспертов.\n\n"
            "В следующем сообщении я расскажу о проверенной методике анализа рынка. Оставайтесь на связи!"
        ),
        "image": "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=1080"
    },
    {
        "delay_index": 2,  # FOLLOW_UP_DELAYS[2] = 1440 minutes (24 hours)
        "text": (
            "📈 **Реальный Кейс: Путь Дмитрия**\n\n"
            "Хочу поделиться историей Дмитрия, одного из участников моего комьюнити. Он пришел ко мне, "
            "имея $200 свободных средств и абсолютный ноль знаний в {niche}.\n\n"
            "За первый месяц работы по моей системе он сделал **+140% к депозиту**, просто четко следуя "
            "правилам риск-менеджмента. \n\n"
            "Хочешь узнать секреты его успеха? Мы разберем их подробно в моем основном канале {channel_name}!"
        ),
        "image": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1080"
    },
    {
        "delay_index": 3,  # FOLLOW_UP_DELAYS[3] = 2880 minutes (48 hours)
        "text": (
            "🚫 **Топ-3 Смертельные Ошибки в Инвестициях**\n\n"
            "Сегодня поговорим про психологию:\n"
            "1. Покупка активов на эмоциях (FOMO).\n"
            "2. Вложение последних/заемных денег.\n"
            "3. Отсутствие четкой торговой стратегии.\n\n"
            "Никогда не рискуй более чем 2-3% от своего общего банка на одну сделку! "
            "Держи это золотое правило в голове, и ты сразу окажешься впереди 95% конкурентов."
        ),
        "image": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1080"
    },
    {
        "delay_index": 4,  # FOLLOW_UP_DELAYS[4] = 4320 minutes (72 hours)
        "text": (
            "🔥 **Эксклюзивное предложение для подписчиков этого бота!**\n\n"
            "Только сегодня я открываю **3 места** на бесплатную личную 15-минутную консультацию со мной ({persona_name}).\n\n"
            "Мы созвонимся, разберем твою точку А и составим индивидуальную стратегию выхода на доход в {niche}.\n\n"
            "Забронируй встречу прямо сейчас по кнопке ниже, пока места не заняли! 👇"
        ),
        "image": "https://images.unsplash.com/photo-1521737711867-e3b904737c88?w=1080",
        "keyboard": [
            [{"text": "🗓 Забронировать консультацию", "url": "https://calendly.com/example-session"}]
        ]
    }
]
