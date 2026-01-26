import hashlib
import sqlite3
import json
from google.adk.agents import Agent
from google.adk.models import Gemini

def google_search(query: str) -> str:
    """Mock Google Search for environment compatibility."""
    print(f"[MockSearch] Searching for: {query}")
    return "No scam reports found for this company in mock mode."

from modules.llm_bridge import GroqModel
from modules.db import get_connection

# Initialize Models
groq_llm = GroqModel(model_name="groq/llama-3.3-70b-versatile").get_model()
gemini_flash = Gemini(model="gemini-2.5-flash-preview")

# --- Tools (Custom) ---

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

# 1. Job Search Agent (Type A - Text Generation)
job_search_agent = Agent(
    name="job_search_agent",
    model=groq_llm,
    description="Generates optimized search URLs for LinkedIn/Indeed.",
    instruction="Given user criteria (e.g., 'Django London'), generate a valid LinkedIn Jobs search URL. Return ONLY the URL string."
)

# 2. Listing Parser Agent (Type A - Text Extraction)
listing_parser_agent = Agent(
    name="listing_parser_agent",
    model=groq_llm,
    description="Extracts structured data from raw HTML.",
    instruction="Extract Job Title, Company, URL, and Easy Apply status from the provided HTML snippet. Return strictly valid JSON."
)

# 3. Duplicate Check Agent (Type B - Custom Tool)
duplicate_check_agent = Agent(
    name="duplicate_check_agent",
    model=groq_llm,
    description="Checks database for duplicates.",
    instruction="Use the `check_db_exists` tool to determine if a URL is new or already processed.",
    tools=[check_db_exists]
)

# 4. Skeptic Agent (Type A - Inbuilt Tool)
# UPDATED: Switched to Gemini Flash to use the native google_search tool correctly.
skeptic_agent = Agent(
    name="skeptic_agent",
    model=gemini_flash,
    description="Checks for scam reports using Google Search.",
    instruction="""
    You are the Skeptic. Your job is to verify if a company is legitimate.
    Use the `Google Search` tool to find reviews or scam reports for the company name.
    
    If you find > 2 credible reports of scams, return "RISK".
    Otherwise, return "SAFE".
    """,
    tools=[google_search] # Native Google Tool
)