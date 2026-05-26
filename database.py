# database.py
import aiosqlite
from datetime import datetime
import logging

DB_PATH = "funnel_bot.db"

logger = logging.getLogger(__name__)

async def init_db():
    """Initializes the SQLite database and creates the users table if it does not exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                дата_входа TEXT NOT NULL,
                оффер TEXT,
                статус_подписки INTEGER DEFAULT 0,
                этап_воронки INTEGER DEFAULT 1
            )
        """)
        await db.commit()
    logger.info("Database initialized successfully.")

async def add_or_update_user(telegram_id: int, username: str) -> bool:
    """
    Creates a new user or updates the username if the user already exists.
    Maintains the original join date (дата_входа) for deduplication.
    Sets the funnel stage (этап_воронки) back to 1 if starting fresh.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if user exists
        async with db.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            
        if row is None:
            # New user
            await db.execute("""
                INSERT INTO users (telegram_id, username, дата_входа, статус_подписки, этап_воронки)
                VALUES (?, ?, ?, 0, 1)
            """, (telegram_id, username, now_str))
            logger.info(f"New user registered: {telegram_id} (@{username})")
            is_new = True
        else:
            # Existing user - update username and reset funnel stage to 1 (re-entry)
            await db.execute("""
                UPDATE users 
                SET username = ?, этап_воронки = 1
                WHERE telegram_id = ?
            """, (username, telegram_id))
            logger.info(f"Existing user re-entered: {telegram_id} (@{username})")
            is_new = False
            
        await db.commit()
        return is_new

async def get_user(telegram_id: int) -> dict | None:
    """Retrieves user data by telegram_id and returns it as a dictionary."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    return None

async def set_user_offer(telegram_id: int, offer: str):
    """Sets the chosen offer and moves the user to stage 2 (prompted to subscribe)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET оффер = ?, этап_воронки = 2
            WHERE telegram_id = ?
        """, (offer, telegram_id))
        await db.commit()
    logger.info(f"User {telegram_id} chose offer: {offer}. Stage set to 2.")

async def set_user_subscription(telegram_id: int, subscribed: bool):
    """Updates the user's subscription status."""
    status_val = 1 if subscribed else 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET статус_подписки = ?
            WHERE telegram_id = ?
        """, (status_val, telegram_id))
        await db.commit()
    logger.info(f"User {telegram_id} subscription status set to {status_val}.")

async def set_user_funnel_stage(telegram_id: int, stage: int):
    """Updates the user's current stage in the marketing funnel."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET этап_воронки = ?
            WHERE telegram_id = ?
        """, (stage, telegram_id))
        await db.commit()
    logger.info(f"User {telegram_id} funnel stage set to {stage}.")

async def get_all_users() -> list[dict]:
    """Retrieves all users from the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
