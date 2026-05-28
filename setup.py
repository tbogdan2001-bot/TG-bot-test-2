#!/usr/bin/env python3
# setup.py — Интерактивная настройка бота через терминал
# Запусти: python setup.py
# Результат: создаётся .env с твоими данными

import os
import sys

SEP = "=" * 60

def ask(prompt, default="", secret=False):
    """Запрашивает ввод у пользователя."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    while True:
        try:
            val = input(full_prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nНастройка прервана.")
            sys.exit(0)
        if val == "" and default != "":
            return default
        if val:
            return val
        print("  ⚠️  Поле обязательно для заполнения. Попробуй снова.")

def ask_optional(prompt, default=""):
    """Запрашивает необязательное поле."""
    if default:
        full_prompt = f"{prompt} [{default}] (Enter чтобы пропустить): "
    else:
        full_prompt = f"{prompt} (Enter чтобы пропустить): "
    try:
        val = input(full_prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\nНастройка прервана.")
        sys.exit(0)
    return val if val else default

def confirm(prompt):
    """Да/Нет вопрос."""
    while True:
        try:
            val = input(f"{prompt} [д/н]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return False
        if val in ("д", "y", "yes", "да"):
            return True
        if val in ("н", "n", "no", "нет"):
            return False

def main():
    print()
    print(SEP)
    print("  НАСТРОЙКА TELEGRAM BOT FUNNEL")
    print("  Отвечай на вопросы — .env создастся автоматически")
    print(SEP)
    print()

    # ── 1. BOT TOKEN ──────────────────────────────────────────────
    print("📌 ШАГ 1: Токен бота")
    print("   Получи у @BotFather командой /newbot или /mybots")
    print("   Формат: 1234567890:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print()
    bot_token = ask("BOT_TOKEN")
    print()

    # ── 2. ADMIN ID ───────────────────────────────────────────────
    print("📌 ШАГ 2: Твой Telegram ID (для доступа к /admin)")
    print("   Узнай свой ID у @userinfobot")
    print()
    admin_id = ask("ADMIN_ID (числа)")
    print()

    # ── 3. КАНАЛ ──────────────────────────────────────────────────
    print("📌 ШАГ 3: Основной канал подписки")
    print("   CHANNEL_ID — числовой ID канала (формат: -1001234567890)")
    print("   Узнать ID: добавь @getmyid_bot в канал как админа")
    print()
    channel_id = ask("CHANNEL_ID (например: -1001234567890)")
    channel_link = ask("CHANNEL_LINK (например: https://t.me/mychannel)")
    channel_name = ask("CHANNEL_NAME (например: Crypto Inside 📈)")
    print()

    # ── 4. CRM / CLOSER ───────────────────────────────────────────
    print("📌 ШАГ 4: CRM — куда слать уведомления о новых лидах")
    print("   Это ID группы или канала где ты хочешь получать лиды")
    print("   Формат: -1001234567890")
    print()
    closer_chat_id = ask_optional("CLOSER_NOTIFY_CHAT_ID", "0")
    print()

    # ── 5. KEITARO ────────────────────────────────────────────────
    print("📌 ШАГ 5: Кейтаро PostBack URL")
    print("   Формат: https://ВАШ_ДОМЕН/postback?subid={subid}&status=approved")
    print("   Если Кейтаро не используешь — нажми Enter")
    print()
    keitaro_url = ask_optional("KEITARO_POSTBACK_URL", "")
    print()

    # ── 6. TELETHON / МЕНЕДЖЕРЫ ───────────────────────────────────
    print("📌 ШАГ 6: Telethon API (для мультиаккаунт-менеджеров)")
    print("   Получи на https://my.telegram.org → API development tools")
    print("   Если не используешь — нажми Enter для пропуска")
    print()
    tg_api_id = ask_optional("TELEGRAM_API_ID", "0")
    tg_api_hash = ask_optional("TELEGRAM_API_HASH", "")
    manager_phone = ask_optional("MANAGER_1_PHONE (формат: +380XXXXXXXXX)", "")
    print()

    # ── 7. GEMINI ─────────────────────────────────────────────────
    print("📌 ШАГ 7: Google Gemini API Key (для AI-контента)")
    print("   Получи на https://aistudio.google.com/app/apikey")
    print("   Если не используешь — нажми Enter")
    print()
    gemini_key = ask_optional("GEMINI_API_KEY", "")
    print()

    # ── SUMMARY ───────────────────────────────────────────────────
    print(SEP)
    print("  ПРОВЕРЬ ДАННЫЕ ПЕРЕД СОХРАНЕНИЕМ:")
    print(SEP)
    print(f"  BOT_TOKEN              : {bot_token[:20]}...")
    print(f"  ADMIN_ID               : {admin_id}")
    print(f"  CHANNEL_ID             : {channel_id}")
    print(f"  CHANNEL_LINK           : {channel_link}")
    print(f"  CHANNEL_NAME           : {channel_name}")
    print(f"  CLOSER_NOTIFY_CHAT_ID  : {closer_chat_id}")
    print(f"  KEITARO_POSTBACK_URL   : {keitaro_url if keitaro_url else '(не задан)'}")
    print(f"  TELEGRAM_API_ID        : {tg_api_id}")
    print(f"  TELEGRAM_API_HASH      : {tg_api_hash[:8] + '...' if tg_api_hash else '(не задан)'}")
    print(f"  MANAGER_1_PHONE        : {manager_phone if manager_phone else '(не задан)'}")
    print(f"  GEMINI_API_KEY         : {gemini_key[:10] + '...' if gemini_key else '(не задан)'}")
    print(SEP)
    print()

    if not confirm("Всё верно? Сохранить .env?"):
        print()
        print("Отменено. Запусти setup.py снова чтобы ввести данные заново.")
        sys.exit(0)

    # ── ЗАПИСЬ .env ───────────────────────────────────────────────
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

    env_content = f"""# .env — Конфигурация Telegram Bot Funnel
# Создано setup.py автоматически

# 1. Telegram Bot Token (от @BotFather)
BOT_TOKEN={bot_token}

# 2. Admin Telegram ID
ADMIN_ID={admin_id}

# 3. CRM Lead Forwarding
CLOSER_NOTIFY_CHAT_ID={closer_chat_id}

# 4. Default Channel
CHANNEL_ID={channel_id}
CHANNEL_LINK={channel_link}
CHANNEL_NAME={channel_name}

# 5. Google Gemini AI
GEMINI_API_KEY={gemini_key}

# 6. Telethon Multi-Account Manager
TELEGRAM_API_ID={tg_api_id}
TELEGRAM_API_HASH={tg_api_hash}

# 7. Manager Userbot
MANAGER_1_PHONE={manager_phone}

# 8. Keitaro PostBack
KEITARO_POSTBACK_URL={keitaro_url}
"""

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    print()
    print(SEP)
    print("  ✅ .env успешно создан!")
    print(f"  Расположение: {env_path}")
    print()
    print("  Теперь запусти бота:")
    print("    python main.py")
    print(SEP)
    print()
    input("Нажми Enter чтобы выйти...")

if __name__ == "__main__":
    main()
