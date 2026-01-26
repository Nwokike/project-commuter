from google.adk.agents import Agent
from google.adk.types import RunContext

from modules.llm_bridge import GroqModel

# Import Sub-Squads
from agents.scout_squad import job_search_agent
from agents.vision_squad import vision_agent, navigation_agent
from agents.ops_squad import sos_agent

# Initialize the Brain for the Orchestrator
# UPDATED: Explicitly using 'groq/llama-3.3-70b-versatile' as requested
orchestrator_model = GroqModel(model_name="groq/llama-3.3-70b-versatile").get_model()

# --- Orchestrator Tools (Delegation) ---

def dispatch_to_scout(context: RunContext, search_query: str) -> str:
    """
    Delegates the task of finding new jobs to the Scout Squad.
    """
    print(f"[Orchestrator] 📡 Dispatching to Scout with query: {search_query}")
    # In a full implementation, you'd run the sub-agent here.
    return "Scout Agent has been scheduled. (Mock Response for Phase 2)"

def dispatch_to_navigator(context: RunContext, job_url: str) -> str:
    """
    Delegates the task of applying to a specific job to the Navigator/Vision Squad.
    """
    print(f"[Orchestrator] 🧭 Dispatching to Navigator for: {job_url}")
    return "Navigator Agent started application process. (Mock Response for Phase 2)"

def check_status(context: RunContext) -> str:
    """
    Checks the system state (time, pending jobs).
    """
    from modules.db import get_connection
    import pandas as pd
    
    conn = get_connection()
    try:
        # Check queue depth
        pending = pd.read_sql("SELECT COUNT(*) FROM job_queue WHERE status='PENDING'", conn).iloc[0,0]
        return f"System Status: ONLINE. Pending Jobs: {pending}"
    except Exception as e:
        return f"System Status: DB ERROR ({e})"
    finally:
        conn.close()

# --- The Orchestrator Agent ---

orchestrator_agent = Agent(
    name="orchestrator_agent",
    model=orchestrator_model,
    description="The Chief Operations Officer. Manages the lifecycle of the job search.",
    instruction="""
    You are the Orchestrator of Project Commuter.
    Your goal is to manage the job application process efficiently and safely.
    
    Your responsibilities:
    1. Check the system status using `check_status`.
    2. If there are pending jobs (> 0), dispatch the Navigator using `dispatch_to_navigator` for the next job.
    3. If there are NO pending jobs (0), dispatch the Scout using `dispatch_to_scout`.
    4. Maintain a "human-like" pace. Do not rush.
    
    Do not perform the search or application yourself. Always delegate.
    """,
    tools=[check_status, dispatch_to_scout, dispatch_to_navigator]
)