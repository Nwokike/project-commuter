import asyncio
import sqlite3
from google.adk.agents import Agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from modules.llm_bridge import GroqModel
from modules.db import log_thought  # NEW: Import logger

# Import Sub-Squads
from agents.scout_squad import job_search_agent, add_to_queue
from agents.vision_squad import navigation_agent
# Note: Vision Agent is called internally by Navigator

# Initialize the Brain for the Orchestrator
orchestrator_model = GroqModel(model_name="groq/llama-3.3-70b-versatile").get_model()

# --- Helper to Run Sub-Agents ---

async def run_sub_agent(agent: Agent, prompt: str) -> str:
    """
    Helper to execute a sub-agent using a temporary Runner.
    Logs the output to the Neural Feed.
    """
    print(f"[Orchestrator] 🔄 Spawning sub-runner for {agent.name}...")
    
    # 1. Setup Session Service
    session_service = InMemorySessionService()
    session_id = "sub_session"
    user_id = "orchestrator"
    app_name = f"SubRunner_{agent.name}"
    
    # 2. Explicitly create the session
    if hasattr(session_service, "create_session"):
        await session_service.create_session(session_id=session_id, user_id=user_id, app_name=app_name)
    elif hasattr(session_service, "async_create_session"):
        await session_service.async_create_session(session_id=session_id, user_id=user_id, app_name=app_name)
    else:
        try:
            from google.adk.sessions import Session
            session_service.sessions[session_id] = Session(id=session_id, user_id=user_id)
        except Exception as e:
            print(f"[Orchestrator] Warning: Could not create session manually: {e}")

    # 3. Create a fresh runner
    sub_runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name=app_name
    )
    
    response_text = []
    
    # 4. Create the input message
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    
    # 5. Run async
    try:
        async for event in sub_runner.run_async(
            user_id=user_id, 
            session_id=session_id, 
            new_message=msg
        ):
            if event.content and event.content.role == "model":
                 if hasattr(event.content, 'parts'):
                     for part in event.content.parts:
                         if hasattr(part, 'text') and part.text:
                             response_text.append(part.text)
                             
    except Exception as e:
        error_msg = f"Sub-Agent Crash: {e}"
        print(f"[Orchestrator] ⚠️ {error_msg}")
        log_thought(agent.name, error_msg)
        return error_msg
    
    final_result = "".join(response_text)
    
    # LOGGING: Capture the sub-agent's work
    # This captures "Scout found URL..." or "Navigator clicked..."
    if final_result:
        log_thought(agent.name, final_result)
        
    return final_result if final_result else "Task Completed (No text output)"

# --- Orchestrator Tools ---

async def dispatch_to_scout(search_query: str) -> str:
    """
    Delegates the task of finding new jobs to the Scout Squad.
    """
    print(f"[Orchestrator] 📡 Dispatching to Scout with query: {search_query}")
    
    # Log the intent
    log_thought("Orchestrator", f"Dispatching Scout: '{search_query}'")
    
    safe_prompt = f"Create a search URL for: '{search_query}'. Return ONLY the URL string. Do not call any tools."
    result_url = await run_sub_agent(job_search_agent, safe_prompt)
    
    clean_url = result_url.strip().replace("`", "").replace('"', "")
    
    if "http" in clean_url:
        print(f"[Orchestrator] 📥 Adding found feed to Job Queue: {clean_url}")
        status = add_to_queue(
            url=clean_url, 
            company="LinkedIn Search", 
            title=f"Feed: {search_query}"
        )
        return f"Scout Agent found URL: {clean_url}. Database Status: {status}"
    else:
        return f"Scout Agent failed to return a valid URL. Result: {result_url}"

async def dispatch_to_navigator(job_url: str) -> str:
    """
    Delegates the task of applying to a specific job to the Navigator/Vision Squad.
    """
    print(f"[Orchestrator] 🧭 Dispatching to Navigator for: {job_url}")
    
    # Log the intent
    log_thought("Orchestrator", f"Dispatching Navigator: {job_url}")
    
    # Navigate
    from modules.stealth_browser import browser_instance
    if not browser_instance.page:
        await browser_instance.launch()
        
    try:
        await browser_instance.page.goto(job_url)
        # Wait a bit for render
        await asyncio.sleep(4)
        
        # Execute Navigation Agent
        result = await run_sub_agent(navigation_agent, f"Start applying to {job_url}")
        
        # Mark as APPLIED in DB (Safety fallback)
        from modules.db import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE job_queue SET status='APPLIED' WHERE url=?", (job_url,))
        conn.commit()
        conn.close()
        
        return f"Navigator finished. Job marked APPLIED. Result: {result}"
        
    except Exception as e:
        return f"Navigator Failed: {e}"

def check_status() -> str:
    """
    Checks the system state and returns the NEXT AVAILABLE JOB URL.
    """
    from modules.db import get_connection
    import pandas as pd
    
    conn = get_connection()
    try:
        # Get count
        pending_count = pd.read_sql("SELECT COUNT(*) FROM job_queue WHERE status='PENDING'", conn).iloc[0,0]
        
        # Get the actual next URL
        next_job = pd.read_sql("SELECT url FROM job_queue WHERE status='PENDING' ORDER BY created_at ASC LIMIT 1", conn)
        
        if not next_job.empty:
            next_url = next_job.iloc[0, 0]
            status_msg = f"System Status: ONLINE. Pending Jobs: {pending_count}. NEXT JOB URL: {next_url}"
        else:
            status_msg = f"System Status: ONLINE. Pending Jobs: 0. No jobs to process."
            
        return status_msg
            
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
    You are the Orchestrator.
    
    Loop:
    1. Call `check_status`.
    2. IF "Pending Jobs: 0", call `dispatch_to_scout` with the user's search query.
    3. IF "NEXT JOB URL" is provided, call `dispatch_to_navigator` with that URL.
    
    Perform ONE action per turn.
    """,
    tools=[check_status, dispatch_to_scout, dispatch_to_navigator]
)