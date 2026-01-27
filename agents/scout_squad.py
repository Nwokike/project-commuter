import hashlib
import sqlite3
import urllib.parse
from google.adk.agents import Agent
from google.adk.models import Gemini

from modules.llm_bridge import GroqModel, GeminiFallbackClient
from modules.db import get_connection

# Initialize Models (Uses the Fallback Swarm we built earlier)
groq_llm = GroqModel().get_model()
gemini_fallback = GeminiFallbackClient()

# --- Tools (Custom) ---

def generate_search_url(query: str) -> str:
    """
    Constructs a LinkedIn Job Search URL with strict 'Easy Apply' filtering.
    """
    base_url = "https://www.linkedin.com/jobs/search/?"
    params = {
        "keywords": query,
        "f_AL": "true",  # CRITICAL: Forces 'Easy Apply' filter
        "sortBy": "R",   # Sort by Relevance
        "f_TPR": "r86400" # Past 24 hours (Keep it fresh)
    }
    final_url = base_url + urllib.parse.urlencode(params)
    print(f"[Scout] Generated URL: {final_url}")
    return final_url

def check_db_exists(job_url: str) -> str:
    """
    Checks if a job URL already exists in the database. 
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

def google_search(query: str) -> str:
    """Mock Google Search for environment compatibility."""
    # In a real deployment, this would hit SerpAPI or Google Custom Search
    return "No scam reports found (Mock)."

# --- Agents ---

# 1. Job Search Agent
job_search_agent = Agent(
    name="job_search_agent",
    model=groq_llm,
    description="Generates safe, optimized search URLs.",
    instruction="""
    Your goal is to start a job search.
    You MUST use the `generate_search_url` tool to create the link.
    Do not guess the URL. Do not create one yourself.
    Return ONLY the URL provided by the tool.
    """,
    tools=[generate_search_url]
)

# 2. Listing Parser Agent
listing_parser_agent = Agent(
    name="listing_parser_agent",
    model=groq_llm,
    description="Extracts structured data from raw HTML.",
    instruction="Extract Job Title, Company, URL, and Easy Apply status from the provided HTML snippet. Return strictly valid JSON."
)

# 3. Duplicate Check Agent
duplicate_check_agent = Agent(
    name="duplicate_check_agent",
    model=groq_llm,
    description="Checks database for duplicates.",
    instruction="Use the `check_db_exists` tool to determine if a URL is new or already processed.",
    tools=[check_db_exists]
)

# 4. Skeptic Agent
skeptic_agent = Agent(
    name="skeptic_agent",
    model=gemini_fallback,
    description="Checks for scam reports.",
    instruction="""
    You are the Skeptic. Verify if a company is legitimate.
    Use `Google Search` to find reviews.
    If you find > 2 credible scam reports, return "RISK". Otherwise, return "SAFE".
    """,
    tools=[google_search]
)