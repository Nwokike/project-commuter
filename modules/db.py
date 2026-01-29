import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bot_memory.db")

SCHEMA = """
-- 1. Job Queue
CREATE TABLE IF NOT EXISTS job_queue (
    job_hash TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    company TEXT,
    title TEXT,
    status TEXT DEFAULT 'PENDING', -- PENDING, APPLIED, REJECTED, IGNORED, SOS, PROCESSED
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Answer Bank
CREATE TABLE IF NOT EXISTS answer_bank (
    question_hash TEXT PRIMARY KEY,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    source TEXT, -- USER_OVERRIDE, CONTEXT_ENGINE
    context_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Application Logs
CREATE TABLE IF NOT EXISTS application_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_hash TEXT,
    action TEXT,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_hash) REFERENCES job_queue(job_hash)
);

-- 4. User Configuration
CREATE TABLE IF NOT EXISTS user_config (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- 5. Agent Thoughts
CREATE TABLE IF NOT EXISTS agent_thoughts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_name TEXT,
    thought_content TEXT,
    visual_context_path TEXT
);
"""

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # CRITICAL FIX: Enable Write-Ahead Logging for concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at {DB_PATH}")

def save_config(key: str, value: str):
    """Helper to upsert configuration values."""
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO user_config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_config(key: str) -> str:
    """Helper to retrieve configuration values."""
    conn = get_connection()
    row = conn.execute("SELECT value FROM user_config WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row[0] if row else None

# Global hook for broadcasting to WebSockets (Injected by api_server.py)
_broadcast_hook = None

def register_broadcast_hook(func):
    global _broadcast_hook
    _broadcast_hook = func

def log_thought(agent_name: str, content: str, image_path: str = None):
    """Helper to log an agent's internal thought process."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO agent_thoughts (agent_name, thought_content, visual_context_path) VALUES (?, ?, ?)",
        (agent_name, content, image_path)
    )
    conn.commit()
    conn.close()

    # Broadcast to Mission Control
    if _broadcast_hook:
        try:
            payload = {
                "type": "log",
                "agent": agent_name,
                "payload": content
            }
            if image_path:
                 # Signal to update image
                 _broadcast_hook({"type": "image_update"})
            
            _broadcast_hook(payload)
        except Exception as e:
            print(f"Broadcast failed: {e}")

if __name__ == "__main__":
    init_db()
