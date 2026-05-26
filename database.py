# database.py
import aiosqlite
from datetime import datetime, timezone
import logging

DB_PATH = "funnel_bot.db"

logger = logging.getLogger(__name__)

# CHANGED: Global variable to hold a single persistent database connection (TASK 3)
_db_connection = None

# CHANGED: Helper function to get the shared database connection (TASK 3)
def get_db():
    global _db_connection
    if _db_connection is None:
        raise RuntimeError("Database connection not initialized. Call init_db() first.")
    return _db_connection

# CHANGED: Helper function to close the shared database connection (TASK 3)
async def close_db():
    global _db_connection
    if _db_connection is not None:
        await _db_connection.close()
        logger.info("Database connection closed successfully.")
        _db_connection = None

async def init_db():
    """Initializes the SQLite database, creates the users table, and sets up indexes."""
    global _db_connection
    # CHANGED: Initialize the persistent global database connection (TASK 3)
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(DB_PATH)
        
    db = get_db()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            дата_входа TEXT NOT NULL,
            оффер TEXT,
            статус_подписки INTEGER DEFAULT 0,
            этап_воронки INTEGER DEFAULT 1,
            is_blocked INTEGER DEFAULT 0
        )
    """)
    # Perform dynamic migration if is_blocked is missing in existing setups
    try:
        await db.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0")
    except Exception:
        # Column already exists
        pass
    
    # CHANGED: Create database indexes to optimize queries (TASK 6)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_stage ON users(этап_воронки);")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_blocked ON users(is_blocked);")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_stage_blocked ON users(этап_воронки, is_blocked);")
    
    await db.commit()
    logger.info("Database initialized successfully.")

async def add_or_update_user(telegram_id: int, username: str) -> bool:
    """
    Creates a new user or updates the username if the user already exists.
    Updates the join date (дата_входа) to current UTC time on re-entry (TASK 2).
    Sets the funnel stage (этап_воронки) back to 1 if starting fresh.
    """
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()  # CHANGED: Reusing persistent connection (TASK 3)
    # Check if user exists
    async with db.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
        row = await cursor.fetchone()
        
    if row is None:
        # New user - ensure blocked state is 0 initially
        await db.execute("""
            INSERT INTO users (telegram_id, username, дата_входа, статус_подписки, этап_воронки, is_blocked)
            VALUES (?, ?, ?, 0, 1, 0)
        """, (telegram_id, username, now_str))
        logger.info(f"New user registered: {telegram_id} (@{username})")
        is_new = True
    else:
        # Existing user - update username, reset blocked state, reset stage to 1, and update registration date to current UTC (TASK 2)
        # CHANGED: Updated дата_входа to now_str on re-entry
        await db.execute("""
            UPDATE users 
            SET username = ?, этап_воронки = 1, is_blocked = 0, дата_входа = ?
            WHERE telegram_id = ?
        """, (username, now_str, telegram_id))
        logger.info(f"Existing user re-entered: {telegram_id} (@{username}). UTC timestamp updated.")
        is_new = False
        
    await db.commit()
    return is_new

async def get_user(telegram_id: int) -> dict | None:
    """Retrieves user data by telegram_id and returns it as a dictionary."""
    db = get_db()  # CHANGED: Reusing persistent connection (TASK 3)
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
        row = await cursor.fetchone()
        if row:
            return dict(row)
    return None

async def set_user_offer(telegram_id: int, offer: str):
    """Sets the chosen offer and moves the user to stage 2 (prompted to subscribe)."""
    db = get_db()  # CHANGED: Reusing persistent connection (TASK 3)
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
    db = get_db()  # CHANGED: Reusing persistent connection (TASK 3)
    await db.execute("""
        UPDATE users
        SET статус_подписки = ?
        WHERE telegram_id = ?
    """, (status_val, telegram_id))
    await db.commit()
    logger.info(f"User {telegram_id} subscription status set to {status_val}.")

async def set_user_funnel_stage(telegram_id: int, stage: int):
    """Updates the user's current stage in the marketing funnel."""
    db = get_db()  # CHANGED: Reusing persistent connection (TASK 3)
    await db.execute("""
        UPDATE users
        SET этап_воронки = ?
        WHERE telegram_id = ?
    """, (stage, telegram_id))
    await db.commit()
    logger.info(f"User {telegram_id} funnel stage set to {stage}.")

async def set_user_blocked(telegram_id: int, blocked: bool):
    """Updates the user's blocked status (when they block/unblock the bot)."""
    status_val = 1 if blocked else 0
    db = get_db()  # CHANGED: Reusing persistent connection (TASK 3)
    await db.execute("""
        UPDATE users
        SET is_blocked = ?
        WHERE telegram_id = ?
    """, (status_val, telegram_id))
    await db.commit()
    logger.info(f"User {telegram_id} is_blocked set to {status_val}.")

async def get_all_users() -> list[dict]:
    """Retrieves all users from the database."""
    db = get_db()  # CHANGED: Reusing persistent connection (TASK 3)
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM users") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_funnel_stats() -> dict:
    """Calculates conversion and funnel stage statistics using optimized grouped queries (TASK 5)."""
    db = get_db()  # CHANGED: Reusing persistent connection (TASK 3)
    
    # CHANGED: Optimized from 6 individual queries to exactly 2 grouped queries
    stage_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    
    # Query 1: Group and count non-blocked users by funnel stage
    async with db.execute("SELECT этап_воронки, COUNT(*) FROM users WHERE is_blocked = 0 GROUP BY этап_воронки") as cursor:
        async for row in cursor:
            stage = row[0]
            count = row[1]
            if stage in stage_counts:
                stage_counts[stage] = count
                
    # Query 2: Count blocked users
    async with db.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1") as cursor:
        row = await cursor.fetchone()
        blocked = row[0] or 0
        
    total = sum(stage_counts.values()) + blocked
    conversion = (stage_counts[4] / total) * 100 if total > 0 else 0.0
    
    return {
        "total": total,
        "stage_1": stage_counts[1],
        "stage_2": stage_counts[2],
        "stage_3": stage_counts[3],
        "stage_4": stage_counts[4],
        "blocked": blocked,
        "conversion": conversion
    }


