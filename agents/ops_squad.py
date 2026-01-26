import time
import hashlib
from google.adk.agents import Agent
from google.adk.model import Model
from google.adk.types import RunContext

from modules.llm_bridge import GroqModel
from modules.db import get_connection

# Initialize LLM
groq_llm = GroqModel(model_name="groq/llama-3.3-70b-versatile").get_model()

# --- Tools ---

def trigger_sos(context: RunContext, job_url: str, question_text: str) -> str:
    """
    Triggers the SOS state. Logs the event and pauses the bot to wait for human intervention.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Create a unique hash for this question so the UI can reference it
    question_hash = hashlib.md5(question_text.encode()).hexdigest()
    
    # 2. Log the SOS event
    print(f"[SOS] 🚨 CRITICAL: Bot needs help with: '{question_text}' (Hash: {question_hash})")
    cursor.execute(
        "INSERT INTO application_logs (job_hash, action, details) VALUES (?, 'SOS_TRIGGERED', ?)", 
        (job_url, f"{question_hash}::{question_text}")
    )
    
    # 3. Update the global config to alert the Dashboard (optional, if using polling UI)
    # cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('sos_active', ?)", (question_hash,))
    
    conn.commit()
    conn.close()
    
    return f"SOS_TRIGGERED:{question_hash}"

def wait_for_user_response(context: RunContext, question_hash: str) -> str:
    """
    Actively polls the database for a user-provided answer to a specific question.
    Timeout after 5 minutes (300 seconds) to prevent infinite hanging.
    """
    print(f"[Liaison] ⏳ Waiting for user answer to hash: {question_hash}...")
    
    timeout = 300  # 5 minutes
    poll_interval = 2  # 2 seconds
    start_time = time.time()
    
    while (time.time() - start_time) < timeout:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check answer_bank for a manual override
        cursor.execute(
            "SELECT answer_text FROM answer_bank WHERE question_hash = ? AND source = 'USER_OVERRIDE'", 
            (question_hash,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            answer = row[0]
            print(f"[Liaison] ✅ User provided answer: '{answer}'")
            return f"USER_ANSWER:{answer}"
        
        time.sleep(poll_interval)
    
    print("[Liaison] ❌ Timed out waiting for user.")
    return "TIMEOUT"

# --- Agents ---

# 1. SOS Agent (Type B: Custom Tool)
# Triggered when the Visionary or Brain is stuck.
sos_agent = Agent(
    name="sos_agent",
    model=groq_llm,
    description="The Emergency Operator. Call this to stop the bot and ask for help.",
    instruction="""
    You are the SOS Agent.
    Your only job is to raise the alarm.
    
    1. Call `trigger_sos` with the current job URL and the question text.
    2. The tool will return a 'question_hash'.
    3. Return this hash to the Liaison Agent.
    """,
    tools=[trigger_sos]
)

# 2. Liaison Agent (Type B: Custom Tool)
# Handles the "Waiting Room".
liaison_agent = Agent(
    name="liaison_agent",
    model=groq_llm,
    description="The Patient Waiter. Polls for human input.",
    instruction="""
    You are the Liaison. You bridge the gap between the bot and the human.
    
    1. You receive a `question_hash` from the SOS Agent.
    2. Call `wait_for_user_response(question_hash)`.
    3. If it returns "USER_ANSWER:...", pass that answer back to the Navigator.
    4. If it returns "TIMEOUT", abort this job application.
    """,
    tools=[wait_for_user_response]
)