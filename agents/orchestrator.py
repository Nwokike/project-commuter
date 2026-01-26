from google.adk.agents import Agent

from modules.llm_bridge import GroqModel

# Import Sub-Squads
from agents.scout_squad import job_search_agent
from agents.vision_squad import vision_agent, navigation_agent
from agents.ops_squad import sos_agent

# Initialize the Brain for the Orchestrator
# UPDATED: Explicitly using 'groq/llama-3.3-70b-versatile' as requested
orchestrator_model = GroqModel(model_name="groq/llama-3.3-70b-versatile").get_model()

# --- Orchestrator Tools (Delegation) ---

def dispatch_to_scout(context, search_query: str) -> str:
    """
    Delegates the task of finding new jobs to the Scout Squad.
    """
    print(f"[Orchestrator] 📡 Dispatching to Scout with query: {search_query}")
    # Run the scout agent to generate search URL and find jobs
    # This might require a chain of agents in a real scenario, 
    # but for now we call the main entry point for searching.
    result = job_search_agent.run(search_query)
    return f"Scout Agent completed: {result}"

def dispatch_to_navigator(context, job_url: str) -> str:
    """
    Delegates the task of applying to a specific job to the Navigator/Vision Squad.
    """
    print(f"[Orchestrator] 🧭 Dispatching to Navigator for: {job_url}")
    # Navigate to the job URL first
    async def _navigate():
        if not browser_instance.page:
            await browser_instance.launch()
        await browser_instance.page.goto(job_url)
        await asyncio.sleep(2) # Wait for page load
    
    import asyncio
    from modules.stealth_browser import browser_instance
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(_navigate())
    else:
        loop.run_until_complete(_navigate())

    # Now run the navigation agent loop (usually this would be managed by a higher-level loop)
    # For now, we trigger the agent once to start the process.
    result = navigation_agent.run(f"Start applying to {job_url}")
    return f"Navigator Agent dispatched: {result}"

def check_status(context) -> str:
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