import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bot_memory.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS job_queue (
    job_hash TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    company TEXT,
    title TEXT,
    status TEXT DEFAULT 'PENDING', -- PENDING, APPLIED, REJECTED, IGNORED, SOS
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS answer_bank (
    question_hash TEXT PRIMARY KEY,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    source TEXT, -- USER_OVERRIDE, CONTEXT_ENGINE
    context_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS application_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_hash TEXT,
    action TEXT,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_hash) REFERENCES job_queue(job_hash)
);
"""

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
