from google.adk.agents import Agent
from modules.llm_bridge import GroqModel
from modules.db import get_connection

# Initialize LLM
groq_llm = GroqModel().get_model()

# --- Tools ---

def trigger_sos(job_url: str, question: str) -> str:
    """
    Sets the job status to SOS and logs the question.
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Log the SOS event
    cursor.execute("INSERT INTO application_logs (job_hash, action, details) VALUES ('SOS', 'SOS_TRIGGERED', ?)", (f"{job_url} :: {question}",))
    conn.commit()
    conn.close()
    
    print(f"[SOS] CRITICAL: Bot needs help with: {question}")
    return "SOS_TRIGGERED"

def check_user_response(question_hash: str) -> str:
    """
    Checks if the user has provided an answer in the answer_bank manually.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT answer_text FROM answer_bank WHERE question_hash = ? AND source = 'USER_OVERRIDE'", (question_hash,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "WAITING"

# --- Agents ---

sos_agent = Agent(
    name="sos_agent",
    model=groq_llm,
    description="Calls for help when confidence is low.",
    instruction="Use `trigger_sos` to alert the user.",
    tools=[trigger_sos]
)

liaison_agent = Agent(
    name="liaison_agent",
    model=groq_llm,
    description="Checks if the user has replied.",
    instruction="Use `check_user_response` to see if we can proceed.",
    tools=[check_user_response]
)
