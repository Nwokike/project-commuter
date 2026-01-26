import hashlib
import sqlite3
from google.adk.agents import Agent
from google.adk.tools import google_search
from modules.llm_bridge import GroqModel
from modules.db import get_connection

# Initialize LLM
groq_llm = GroqModel().get_model()

# --- Tools ---

def check_db_exists(job_url: str) -> str:
    """
    Checks if a job URL already exists in the database. 
    Returns "EXISTS" or "NEW".
    """
    job_hash = hashlib.md5(job_url.encode()).hexdigest()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM job_queue WHERE job_hash = ?", (job_hash,))
    row = cursor.fetchone()
    conn.close()
    return f"EXISTS ({row[0]})" if row else "NEW"

def add_to_queue(url: str, company: str, title: str) -> str:
    """
    Adds a verified job to the SQLite queue.
    """
    job_hash = hashlib.md5(url.encode()).hexdigest()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO job_queue (job_hash, url, company, title, status) VALUES (?, ?, ?, ?, 'PENDING')",
            (job_hash, url, company, title)
        )
        conn.commit()
        return "ADDED"
    except sqlite3.IntegrityError:
        return "DUPLICATE_ERROR"
    finally:
        conn.close()

# --- Agents ---

job_search_agent = Agent(
    name="job_search_agent",
    model=groq_llm,
    description="Generates optimized search URLs for LinkedIn/Indeed.",
    instruction="Given user criteria, generate a valid LinkedIn Jobs search URL. Return ONLY the URL."
)

listing_parser_agent = Agent(
    name="listing_parser_agent",
    model=groq_llm,
    description="Extracts structured data from job HTML snippets.",
    instruction="Extract Job Title, Company, URL, and Easy Apply status from HTML. Return as JSON."
)

duplicate_check_agent = Agent(
    name="duplicate_check_agent",
    model=groq_llm,
    description="Checks database for duplicates.",
    instruction="Use the `check_db_exists` tool to determine if a URL is new.",
    tools=[check_db_exists]
)

skeptic_agent = Agent(
    name="skeptic_agent",
    model=groq_llm,
    description="Checks for scam reports.",
    instruction="Search for company scam reviews. Return 'RISK' if multiple negative reports found, else 'SAFE'.",
    tools=[google_search]
)
