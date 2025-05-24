
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_seen TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO users (user_id, username, first_seen) VALUES (?, ?, ?)",
            (user_id, username, now)
        )
        conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(first_seen) = DATE('now')")
    today = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(first_seen) >= DATE('now', '-7 days')")
    week = cursor.fetchone()[0]

    conn.close()
    return total, today, week
