import asyncio
from google.adk.agents import Agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from modules.llm_bridge import GroqModel

# Import Sub-Squads
from agents.scout_squad import job_search_agent
from agents.vision_squad import vision_agent, navigation_agent
from agents.ops_squad import sos_agent

# Initialize the Brain for the Orchestrator
orchestrator_model = GroqModel(model_name="groq/llama-3.3-70b-versatile").get_model()

# --- Helper to Run Sub-Agents ---

async def run_sub_agent(agent: Agent, prompt: str) -> str:
    """
    Helper to execute a sub-agent using a temporary Runner.
    This replaces the invalid agent.run() call and handles session creation.
    """
    print(f"[Orchestrator] 🔄 Spawning sub-runner for {agent.name}...")
    
    # 1. Setup Session Service
    session_service = InMemorySessionService()
    session_id = "sub_session"
    user_id = "orchestrator"
    
    # 2. Explicitly create the session to avoid ValueError
    # We check multiple methods to ensure compatibility with your ADK version
    if hasattr(session_service, "create_session"):
        await session_service.create_session(session_id=session_id, user_id=user_id)
    elif hasattr(session_service, "async_create_session"):
        await session_service.async_create_session(session_id=session_id, user_id=user_id)
    else:
        # Fallback: Manually insert session if helper methods are missing
        try:
            from google.adk.sessions import Session
            session_service.sessions[session_id] = Session(id=session_id, user_id=user_id)
        except Exception as e:
            print(f"[Orchestrator] Warning: Could not create session manually: {e}")

    # 3. Create a fresh runner for this task
    sub_runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name=f"SubRunner_{agent.name}"
    )
    
    response_text = []
    
    # 4. Create the input message
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    
    # 5. Run async
    async for event in sub_runner.run_async(
        user_id=user_id, 
        session_id=session_id, 
        new_message=msg
    ):
        # Capture the model's final text response
        if event.source == "model" and event.content:
             # Handle different content structures safely
             if hasattr(event.content, 'parts'):
                 for part in event.content.parts:
                     if hasattr(part, 'text') and part.text:
                         response_text.append(part.text)
    
    final_result = "".join(response_text)
    return final_result if final_result else "Task Completed (No text output)"

# --- Orchestrator Tools (Delegation) ---

async def dispatch_to_scout(search_query: str) -> str:
    """
    Delegates the task of finding new jobs to the Scout Squad.
    """
    print(f"[Orchestrator] 📡 Dispatching to Scout with query: {search_query}")
    
    # EXECUTE THE SUB-AGENT PROPERLY via Helper
    result = await run_sub_agent(job_search_agent, search_query)
    
    return f"Scout Agent completed: {result}"

async def dispatch_to_navigator(job_url: str) -> str:
    """
    Delegates the task of applying to a specific job to the Navigator/Vision Squad.
    """
    print(f"[Orchestrator] 🧭 Dispatching to Navigator for: {job_url}")
    
    # Navigate to the job URL first using the global browser instance
    from modules.stealth_browser import browser_instance
    if not browser_instance.page:
        await browser_instance.launch()
    await browser_instance.page.goto(job_url)
    await asyncio.sleep(2) # Wait for page load
    
    # EXECUTE THE SUB-AGENT PROPERLY via Helper
    result = await run_sub_agent(navigation_agent, f"Start applying to {job_url}")
    
    return f"Navigator Agent dispatched: {result}"

def check_status() -> str:
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