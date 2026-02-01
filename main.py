import asyncio
import os
import time
from dotenv import load_dotenv

from google.adk import Runner
from google.genai import types
from agents.orchestrator import orchestrator_agent
from modules.db import init_db, log_thought, get_config, save_config
from google.adk.sessions import InMemorySessionService
from modules.stealth_browser import browser_instance

load_dotenv()

async def main():
    print("[System] Initializing Project Commuter v2.1 (Refactored)...")
    init_db()

    # --- 1. Launch Browser & Dashboard ---
    # We use the new Persistent Profile (No cloning)
    print("[System] 🚀 Launching Flight Deck (Persistent Profile)...")
    try:
        if not browser_instance.page:
            await browser_instance.launch()
        
        print("[System] 🖥️ Opening Mission Control in Bot Browser...")
        await browser_instance.page.goto("http://localhost:5000")
        
        # Open a secondary tab for the work
        work_page = await browser_instance.browser_context.new_page()
        browser_instance.page = work_page 
        
    except Exception as e:
        print(f"[System] ⚠️ Browser Launch Warning: {e}")

    # --- 2. The Startup Gate ---
    print("[System] 🛑 Checking Configuration Gate...")
    
    while True:
        cv_text = get_config("cv_text")
        search_query = get_config("search_query")
        
        if cv_text and search_query:
            print(f"[System] ✅ Gate Open! Query: '{search_query}' (CV Length: {len(cv_text)})")
            break 
        
        print(f"[System] ⏳ WAITING: Query='{search_query}', CV_Len={len(cv_text) if cv_text else 0}")
        if not cv_text:
             print("[Debug] CV Missing in DB.")
        if not search_query:
             print("[Debug] Query Missing in DB.")
        
        print(f"[System] ⏳ WAITING: Please upload CV and set Search Query in Mission Control (http://localhost:8000)")
        log_thought("System", "Gate Closed: Waiting for User Configuration in Mission Control.")
        await asyncio.sleep(5)

    print("[System] Orchestrator is online. Managing queue...")
    save_config("system_status", "RUNNING")
    
    # --- 3. The Infinite Loop ---
    while True:
        try:
            # Check for Global Stop/SOS from Dashboard
            status = get_config("system_status")
            if status != "RUNNING":
                print(f"[System] ⏸️ System Paused ({status}). Waiting...")
                await asyncio.sleep(5)
                continue

            session_service = InMemorySessionService()
            session_id = f"orch_session_{int(time.time())}"
            user_id = "local_user"
            app_name = "ProjectCommuter"
            
            # ADK Session Setup
            if hasattr(session_service, "create_session"):
                await session_service.create_session(session_id=session_id, user_id=user_id, app_name=app_name)
            elif hasattr(session_service, "async_create_session"):
                await session_service.async_create_session(session_id=session_id, user_id=user_id, app_name=app_name)
            
            runner = Runner(
                agent=orchestrator_agent, 
                session_service=session_service, 
                app_name=app_name
            )

            current_query = get_config("search_query")
            
            # Pulse Prompt
            # We explicitly ask the Orchestrator to check its new status tool
            pulse_prompt = f"Check status. If queue empty, find '{current_query}' jobs. If feed found, process it. If jobs pending, apply. Do ONE thing."
            content = types.Content(role="user", parts=[types.Part(text=pulse_prompt)])
            
            print(f"\n[System] 💓 Pulse (Session: {session_id[-4:]})")
            
            orchestrator_response = []
            
            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                if event.content and event.content.role == "model":
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                orchestrator_response.append(part.text)

            final_thought = "".join(orchestrator_response)
            if final_thought:
                # Log only if substantial
                if len(final_thought) > 10:
                    log_thought("Orchestrator", final_thought)

            # OPTIMIZED: 10 Second Cooldown
            # 30s was too slow. 10s is enough to be polite but efficient.
            print("[System] 💤 Cooling down (10s)...")
            await asyncio.sleep(10)

        except KeyboardInterrupt:
            print("\n[System] Shutdown requested.")
            break
        except Exception as e:
            print(f"[System] ⚠️ Error in main loop: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
