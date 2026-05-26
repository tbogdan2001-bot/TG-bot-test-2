# database.py
# CHANGED: Added comment block listing updates (FEATURE 1, 2, 4, 5, 6)
# - Added safe column migration in init_db() for traffic, closer, and retention columns
# - Updated add_or_update_user to support traffic tracking parameters and reset them on re-entry
# - Added closer and retention status updating helpers
# - Added get_full_stats() multi-dimensional analytics database query

import aiosqlite
from datetime import datetime, timezone
import logging

DB_PATH = "funnel_bot.db"

logger = logging.getLogger(__name__)

# Global variable to hold a single persistent database connection (TASK 3)
_db_connection = None

# Helper function to get the shared database connection (TASK 3)
def get_db():
    global _db_connection
    if _db_connection is None:
        raise RuntimeError("Database connection not initialized. Call init_db() first.")
    return _db_connection

# Helper function to close the shared database connection (TASK 3)
async def close_db():
    global _db_connection
    if _db_connection is not None:
        await _db_connection.close()
        logger.info("Database connection closed successfully.")
        _db_connection = None

async def init_db():
    """Initializes the SQLite database, creates the users table, and sets up indexes."""
    global _db_connection
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
    
    # CHANGED: Added safe column migration for all new fields (FEATURE 1, 2, 4, 5)
    columns_to_add = [
        ("is_blocked", "INTEGER DEFAULT 0"),
        ("source_channel", "TEXT"),
        ("utm_source", "TEXT"),
        ("utm_campaign", "TEXT"),
        ("traffic_source", "TEXT"),
        ("closer_notified", "INTEGER DEFAULT 0"),
        ("retention_stage", "INTEGER DEFAULT 0"),
        ("status", "TEXT DEFAULT 'active'")
    ]
    for col_name, col_type in columns_to_add:
        try:
            await db.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except Exception:
            # Column already exists
            pass
            
    # Create database indexes to optimize queries (TASK 6)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_stage ON users(этап_воронки);")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_blocked ON users(is_blocked);")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_stage_blocked ON users(этап_воронки, is_blocked);")
    
    # NEW: Initialize channel autopost logs and manager session message tables
    await db.execute("""
        CREATE TABLE IF NOT EXISTS channel_post_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            content_type TEXT NOT NULL,
            post_index INTEGER NOT NULL,
            post_text TEXT NOT NULL,
            posted_at TEXT NOT NULL
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS manager_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT NOT NULL,
            target_user_id INTEGER NOT NULL,
            step INTEGER NOT NULL,
            sent_at TEXT NOT NULL,
            replied INTEGER DEFAULT 0
        )
    """)
    
    await db.commit()
    logger.info("Database initialized successfully.")

async def add_or_update_user(
    telegram_id: int, 
    username: str, 
    source_channel: str = "", 
    utm_source: str = "", 
    utm_campaign: str = "", 
    traffic_source: str = ""
) -> bool:
    """
    Creates a new user or updates the username if the user already exists.
    Updates the join date (дата_входа) to current UTC time on re-entry (TASK 2).
    CHANGED: Restores/refreshes traffic and referral tracking parameters on re-entry (FEATURE 1 & 2).
    """
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    # Check if user exists
    async with db.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
        row = await cursor.fetchone()
        
    if row is None:
        # New user
        await db.execute("""
            INSERT INTO users (
                telegram_id, username, дата_входа, статус_подписки, этап_воронки, is_blocked,
                source_channel, utm_source, utm_campaign, traffic_source, closer_notified, retention_stage, status
            )
            VALUES (?, ?, ?, 0, 1, 0, ?, ?, ?, ?, 0, 0, 'active')
        """, (telegram_id, username, now_str, source_channel, utm_source, utm_campaign, traffic_source))
        logger.info(f"New user registered: {telegram_id} (@{username}) via: {source_channel}")
        is_new = True
    else:
        # Existing user - update username, reset blocked state, reset stage to 1, reset closer/retention, and update tracking (FEATURE 1, 2, 4, 5)
        await db.execute("""
            UPDATE users 
            SET username = ?, этап_воронки = 1, is_blocked = 0, дата_входа = ?,
                source_channel = ?, utm_source = ?, utm_campaign = ?, traffic_source = ?,
                closer_notified = 0, retention_stage = 0, status = 'active'
            WHERE telegram_id = ?
        """, (username, now_str, source_channel, utm_source, utm_campaign, traffic_source, telegram_id))
        logger.info(f"Existing user re-entered: {telegram_id} (@{username}). Date and tracking refreshed.")
        is_new = False
        
    await db.commit()
    return is_new

async def get_user(telegram_id: int) -> dict | None:
    """Retrieves user data by telegram_id and returns it as a dictionary."""
    db = get_db()
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
        row = await cursor.fetchone()
        if row:
            return dict(row)
    return None

async def set_user_offer(telegram_id: int, offer: str):
    """Sets the chosen offer and moves the user to stage 2 (prompted to subscribe)."""
    db = get_db()
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
    db = get_db()
    await db.execute("""
        UPDATE users
        SET статус_подписки = ?
        WHERE telegram_id = ?
    """, (status_val, telegram_id))
    await db.commit()
    logger.info(f"User {telegram_id} subscription status set to {status_val}.")

async def set_user_funnel_stage(telegram_id: int, stage: int):
    """Updates the user's current stage in the marketing funnel."""
    db = get_db()
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
    status_text = "blocked" if blocked else "active"
    db = get_db()
    # CHANGED: Sync overall status with blocked state (FEATURE 5)
    await db.execute("""
        UPDATE users
        SET is_blocked = ?, status = ?
        WHERE telegram_id = ?
    """, (status_val, status_text, telegram_id))
    await db.commit()
    logger.info(f"User {telegram_id} is_blocked set to {status_val}. Status set to {status_text}.")

# CHANGED: Added set_closer_notified helper (FEATURE 4)
async def set_closer_notified(telegram_id: int, notified: int):
    """Updates the user's closer notified state (FEATURE 4)."""
    db = get_db()
    await db.execute("""
        UPDATE users
        SET closer_notified = ?
        WHERE telegram_id = ?
    """, (notified, telegram_id))
    await db.commit()
    logger.info(f"User {telegram_id} closer_notified set to {notified}.")

# CHANGED: Added set_user_retention_stage helper (FEATURE 5)
async def set_user_retention_stage(telegram_id: int, stage: int):
    """Updates the user's retention sequence stage (FEATURE 5)."""
    db = get_db()
    await db.execute("""
        UPDATE users
        SET retention_stage = ?
        WHERE telegram_id = ?
    """, (stage, telegram_id))
    await db.commit()
    logger.info(f"User {telegram_id} retention stage set to {stage}.")

# CHANGED: Added set_user_status helper (FEATURE 5)
async def set_user_status(telegram_id: int, status: str):
    """Updates the user's overall system status (e.g., active, cold, blocked) (FEATURE 5)."""
    db = get_db()
    await db.execute("""
        UPDATE users
        SET status = ?
        WHERE telegram_id = ?
    """, (status, telegram_id))
    await db.commit()
    logger.info(f"User {telegram_id} status set to {status}.")

async def get_all_users() -> list[dict]:
    """Retrieves all users from the database."""
    db = get_db()
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM users") as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_funnel_stats() -> dict:
    """Calculates conversion and funnel stage statistics using optimized grouped queries (TASK 5)."""
    db = get_db()
    
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

# CHANGED: Added get_full_stats() multi-dimensional analytics database query (FEATURE 1, 2, 4, 5)
async def get_full_stats() -> dict:
    """
    Calculates comprehensive multi-dimensional funnel statistics for the /admin_full command,
    including channels, traffic sources, stages, leads sent to closer, and retention/cold statuses.
    """
    db = get_db()
    
    # 1. Total users count
    async with db.execute("SELECT COUNT(*) FROM users") as c:
        total = (await c.fetchone())[0] or 0
        
    # 2. Stages breakdown (for non-blocked active/cold users)
    stage_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    async with db.execute("SELECT этап_воронки, COUNT(*) FROM users WHERE is_blocked = 0 GROUP BY этап_воронки") as cursor:
        async for row in cursor:
            stage_idx = row[0]
            if stage_idx in stage_counts:
                stage_counts[stage_idx] = row[1]
            
    # 3. Channels breakdown
    channel_counts = {}
    async with db.execute("SELECT source_channel, COUNT(*) FROM users GROUP BY source_channel") as cursor:
        async for row in cursor:
            ch_name = row[0] or "Прямой вход"
            channel_counts[ch_name] = row[1]
            
    # 4. Traffic sources breakdown (top 10 UTM sources)
    utm_source_counts = {}
    async with db.execute("""
        SELECT utm_source, utm_campaign, COUNT(*) 
        FROM users 
        WHERE utm_source IS NOT NULL AND utm_source != '' 
        GROUP BY utm_source, utm_campaign 
        ORDER BY COUNT(*) DESC 
        LIMIT 10
    """) as cursor:
        async for row in cursor:
            utm_source_counts[f"{row[0]} ({row[1]})"] = row[2]
            
    # 5. Closer notified leads
    async with db.execute("SELECT COUNT(*) FROM users WHERE closer_notified = 1") as c:
        closer_leads = (await c.fetchone())[0] or 0
        
    # 6. Retention/status states
    status_counts = {"active": 0, "cold": 0, "blocked": 0}
    async with db.execute("SELECT status, COUNT(*) FROM users GROUP BY status") as cursor:
        async for row in cursor:
            status_name = row[0]
            if status_name in status_counts:
                status_counts[status_name] = row[1]
            
    conversion = (stage_counts[4] / total) * 100 if total > 0 else 0.0
    
    return {
        "total": total,
        "stages": stage_counts,
        "channels": channel_counts,
        "utm_sources": utm_source_counts,
        "closer_leads": closer_leads,
        "statuses": status_counts,
        "conversion": conversion
    }

# NEW: Added tables and query helper functions for Channel Autoposting and Multi-Account Manager Systems
async def log_channel_post(channel_id: str, content_type: str, post_index: int, post_text: str):
    """Logs an automated channel post in the database."""
    db = get_db()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    await db.execute("""
        INSERT INTO channel_post_log (channel_id, content_type, post_index, post_text, posted_at)
        VALUES (?, ?, ?, ?, ?)
    """, (channel_id, content_type, post_index, post_text, now_str))
    await db.commit()
    logger.info(f"Logged channel post for channel '{channel_id}' with index {post_index}.")

async def get_last_post_index(channel_id: str) -> int:
    """Retrieves the index of the last posted content type for a given channel. Returns -1 if none exist."""
    db = get_db()
    async with db.execute("""
        SELECT post_index FROM channel_post_log
        WHERE channel_id = ?
        ORDER BY id DESC LIMIT 1
    """, (channel_id,)) as cursor:
        row = await cursor.fetchone()
        if row:
            return row[0]
    return -1

async def log_manager_message(session_name: str, target_user_id: int, step: int):
    """Logs an outgoing or first-contact message sent by a Telethon manager account."""
    db = get_db()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    await db.execute("""
        INSERT INTO manager_messages (session_name, target_user_id, step, sent_at, replied)
        VALUES (?, ?, ?, ?, 0)
    """, (session_name, target_user_id, step, now_str))
    await db.commit()
    logger.info(f"Logged manager message from session '{session_name}' to user {target_user_id} (Step {step}).")

async def get_pending_followups(session_name: str, step: int, hours_since: float) -> list[int]:
    """
    Retrieves a list of target user IDs who received message at `step` from `session_name`
    at least `hours_since` ago, and have not yet replied or been sent a higher step.
    """
    db = get_db()
    db.row_factory = aiosqlite.Row
    async with db.execute("""
        SELECT m1.target_user_id 
        FROM manager_messages m1
        WHERE m1.session_name = ? 
          AND m1.step = ? 
          AND m1.replied = 0
          AND (julianday('now') - julianday(m1.sent_at)) * 24 >= ?
          AND NOT EXISTS (
              SELECT 1 FROM manager_messages m2
              WHERE m2.session_name = m1.session_name 
                AND m2.target_user_id = m1.target_user_id 
                AND m2.step > m1.step
          )
    """, (session_name, step, hours_since)) as cursor:
        rows = await cursor.fetchall()
        return [row["target_user_id"] for row in rows]

async def mark_replied(session_name: str, target_user_id: int):
    """Marks all messages for a specific user and session as replied, halting followups."""
    db = get_db()
    await db.execute("""
        UPDATE manager_messages
        SET replied = 1
        WHERE session_name = ? AND target_user_id = ?
    """, (session_name, target_user_id))
    await db.commit()
    logger.info(f"Marked user {target_user_id} as replied for manager session '{session_name}'.")

