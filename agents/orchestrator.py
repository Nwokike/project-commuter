import asyncio
import sqlite3
import pandas as pd
from google.adk.agents import Agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from modules.llm_bridge import GroqModel
from modules.db import log_thought, get_connection
from modules.stealth_browser import browser_instance

# Import Sub-Squads
from agents.scout_squad import job_search_agent, add_to_queue
from agents.vision_squad import navigation_agent

# Initialize the Brain for the Orchestrator
orchestrator_model = GroqModel(model_name="groq/llama-3.3-70b-versatile").get_model()

# --- Helper to Run Sub-Agents ---

async def run_sub_agent(agent: Agent, prompt: str) -> str:
    """
    Helper to execute a sub-agent using a temporary Runner.
    Logs the output to the Neural Feed.
    """
    print(f"[Orchestrator] 🔄 Spawning sub-runner for {agent.name}...")
    
    session_service = InMemorySessionService()
    session_id = "sub_session"
    user_id = "orchestrator"
    app_name = f"SubRunner_{agent.name}"
    
    # Explicitly create the session
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

    sub_runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name=app_name
    )
    
    response_text = []
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    
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
    if final_result:
        log_thought(agent.name, final_result)
        
    return final_result if final_result else "Task Completed (No text output)"

# --- Orchestrator Tools ---

async def dispatch_to_scout(search_query: str) -> str:
    """
    Delegates the task of generating a Search Feed URL to the Scout Squad.
    """
    print(f"[Orchestrator] 📡 Dispatching to Scout with query: {search_query}")
    log_thought("Orchestrator", f"Dispatching Scout: '{search_query}'")
    
    safe_prompt = f"Create a search URL for: '{search_query}'. Return ONLY the URL string. Do not call any tools."
    result_url = await run_sub_agent(job_search_agent, safe_prompt)
    
    clean_url = result_url.strip().replace("`", "").replace('"', "")
    
    if "http" in clean_url:
        print(f"[Orchestrator] 📥 Adding Search Feed to Job Queue: {clean_url}")
        # We mark 'LinkedIn Search' as the company so we can identify it as a Feed later
        status = add_to_queue(
            url=clean_url, 
            company="LinkedIn Search", 
            title=f"Feed: {search_query}"
        )
        return f"Scout found Feed URL: {clean_url}. Database Status: {status}"
    else:
        return f"Scout failed to return a valid URL. Result: {result_url}"

async def process_search_feed(feed_url: str) -> str:
    """
    Opens a Search Feed URL, scrolls to load jobs, and extracts individual job links.
    Adds found jobs to the queue and marks the feed as PROCESSED.
    """
    print(f"[Orchestrator] 🚜 Harvesting jobs from Feed: {feed_url}")
    log_thought("Orchestrator", "Harvesting jobs from Search Feed...")

    if not browser_instance.page:
        await browser_instance.launch()

    try:
        # 1. Go to the Feed
        await browser_instance.page.goto(feed_url)
        await asyncio.sleep(5) # Wait for initial load

        # 2. Scroll to trigger lazy loading (Simple scroll down)
        await browser_instance.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(3)
        await browser_instance.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(3)

        # 3. Extract Links using JS (Robust approach for 2026)
        # We look for links that look like job viewings
        links = await browser_instance.page.evaluate("""
            () => {
                const anchors = Array.from(document.querySelectorAll('a'));
                return anchors
                    .map(a => a.href)
                    .filter(href => href.includes('/jobs/view/') || href.includes('currentJobId='));
            }
        """)

        # Deduplicate
        unique_links = list(set(links))
        added_count = 0
        
        # 4. Add to Database
        for link in unique_links:
            # Clean URL to base version
            clean_link = link.split('?')[0] if '?' in link else link
            
            # Use specific add_to_queue tool
            res = add_to_queue(clean_link, "Pending Analysis", "New Opportunity")
            if res == "ADDED":
                added_count += 1

        # 5. Mark Feed as PROCESSED in DB
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE job_queue SET status='PROCESSED' WHERE url=?", (feed_url,))
        conn.commit()
        conn.close()

        result_msg = f"Harvested {added_count} new jobs from feed. Feed marked PROCESSED."
        log_thought("Orchestrator", result_msg)
        return result_msg

    except Exception as e:
        error_msg = f"Feed Processing Failed: {e}"
        print(f"[Orchestrator] ⚠️ {error_msg}")
        return error_msg

async def dispatch_to_navigator(job_url: str) -> str:
    """
    Delegates the task of applying to a specific job to the Navigator/Vision Squad.
    """
    print(f"[Orchestrator] 🧭 Dispatching to Navigator for: {job_url}")
    log_thought("Orchestrator", f"Dispatching Navigator: {job_url}")
    
    if not browser_instance.page:
        await browser_instance.launch()
        
    try:
        await browser_instance.page.goto(job_url)
        await asyncio.sleep(4)
        
        # Execute Navigation Agent
        result = await run_sub_agent(navigation_agent, f"Start applying to {job_url}")
        
        # Mark as APPLIED in DB
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
    Checks the system state.
    Prioritizes processing 'Search Feeds' (lists of jobs) before applying to 'Single Jobs'.
    """
    conn = get_connection()
    try:
        # 1. Check for Unprocessed Search Feeds
        feed_row = pd.read_sql(
            "SELECT url FROM job_queue WHERE status='PENDING' AND company='LinkedIn Search' LIMIT 1", 
            conn
        )
        
        if not feed_row.empty:
            feed_url = feed_row.iloc[0, 0]
            return f"ACTION_REQUIRED: FOUND_FEED. URL: {feed_url}"

        # 2. Check for Pending Jobs
        job_row = pd.read_sql(
            "SELECT url FROM job_queue WHERE status='PENDING' AND company != 'LinkedIn Search' ORDER BY created_at ASC LIMIT 1", 
            conn
        )
        
        if not job_row.empty:
            job_url = job_row.iloc[0, 0]
            return f"ACTION_REQUIRED: FOUND_JOB. URL: {job_url}"
            
        return "STATUS: QUEUE_EMPTY. Please dispatch Scout."
            
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
    You are the Orchestrator. Manage the Job Queue accurately.
    
    Loop:
    1. Call `check_status`.
    2. DECIDE based on status:
       - IF "FOUND_FEED" -> Call `process_search_feed(url)`.
       - IF "FOUND_JOB"  -> Call `dispatch_to_navigator(url)`.
       - IF "QUEUE_EMPTY" -> Call `dispatch_to_scout(user_query)`.
    
    Perform ONE action per turn.
    """,
    tools=[check_status, dispatch_to_scout, process_search_feed, dispatch_to_navigator]
)
