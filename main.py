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
    print("[System] Initializing Project Commuter v2.1 (Phase 3: Eco Mode)...")
    init_db()

    # --- 1. Launch Browser & Dashboard ---
    print("[System] 🧬 Cloning Chrome Profile & Launching Flight Deck...")
    try:
        if not browser_instance.page:
            await browser_instance.launch()
        
        # Open Dashboard in the first tab
        print("[System] 🖥️ Opening Dashboard in Bot Browser...")
        await browser_instance.page.goto("http://localhost:8501")
        
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
            print(f"[System] ✅ Gate Open! Query: '{search_query}'")
            break 
        
        print(f"[System] ⏳ WAITING: Please upload CV and set Search Query in Dashboard (http://localhost:8501)")
        log_thought("System", "Gate Closed: Waiting for User Configuration in Mission Control.")
        await asyncio.sleep(5)

    print("[System] Orchestrator is online. Managing queue...")
    save_config("system_status", "RUNNING")
    
    # --- 3. The Infinite Loop (Eco Mode) ---
    while True:
        try:
            # Check for Global Stop/SOS from Dashboard
            if get_config("system_status") != "RUNNING":
                print("[System] ⏸️ System Paused/SOS. Waiting...")
                await asyncio.sleep(5)
                continue

            session_service = InMemorySessionService()
            session_id = f"orch_session_{int(time.time())}"
            user_id = "local_user"
            app_name = "ProjectCommuter"
            
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
            pulse_prompt = f"Check status. If queue empty, find '{current_query}' jobs. If jobs pending, apply. Do ONE thing."
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
                log_thought("Orchestrator", final_thought)

            # ECO MODE: 30 Second Cooldown
            # This ensures we don't spam the API unnecessarily while waiting for page loads
            print("[System] 💤 Cooling down (30s)...")
            await asyncio.sleep(30)

        except KeyboardInterrupt:
            print("\n[System] Shutdown requested.")
            break
        except Exception as e:
            print(f"[System] ⚠️ Error in main loop: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())