# config.py
# Loads all bot configuration from .env file via python-dotenv.
# Supports running both as .py script and compiled .exe (PyInstaller).

import os
import sys
from dotenv import load_dotenv

# Resolve base directory: works in both .py and compiled .exe
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load .env from the same folder as the script/exe
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=dotenv_path)

# ── Core Bot Settings ──────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# ── CRM Lead Forwarding ────────────────────────────────────────────────────────
CLOSER_NOTIFY_CHAT_ID = int(os.getenv("CLOSER_NOTIFY_CHAT_ID", "0"))

# ── Channel Settings ───────────────────────────────────────────────────────────
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/your_channel")
CHANNEL_NAME = os.getenv("CHANNEL_NAME", "Our Channel")

# ── Google Gemini AI ───────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Telethon Multi-Account Manager ────────────────────────────────────────────
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
MANAGER_1_PHONE = os.getenv("MANAGER_1_PHONE", "")

# ── Keitaro PostBack ───────────────────────────────────────────────────────────
KEITARO_POSTBACK_URL = os.getenv("KEITARO_POSTBACK_URL", "")

# ── Manager Accounts (Telethon userbot sessions) ───────────────────────────────
# Add more entries here if you have multiple manager accounts
MANAGER_ACCOUNTS = [
    {
        "session": "manager_1",
        "phone": MANAGER_1_PHONE,
        "persona_id": "default",
    },
]

# ── Manager Target Groups ──────────────────────────────────────────────────────
# Groups where userbots watch for new members and send first-contact messages
MANAGER_GROUPS = [
    # Example: {"group_id": -1001234567890, "name": "My Group"}
]

# ── Personas ───────────────────────────────────────────────────────────────────
PERSONAS = {
    "default": {
        "name": "Alex",
        "niche": "trading & investments",
    },
}

# ── Userbot Message Scripts ────────────────────────────────────────────────────
FIRST_MESSAGE_SCRIPT = (
    "Hi! I saw you just joined {group_name}. "
    "I'm {persona_name} — I help people get started with {niche}. "
    "Feel free to ask me anything!"
)

FOLLOWUP_SCRIPTS = [
    # Day 1
    "Hey! Just checking in. Did you have a chance to explore the channel? — {persona_name}",
    # Day 3
    "Hi again! I wanted to share something useful about {niche}. Let me know if you're interested! — {persona_name}",
    # Day 5
    "Last message from me 😊 Check out our main channel for daily insights: {channel_link} — {persona_name}",
]
