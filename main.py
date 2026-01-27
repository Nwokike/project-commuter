import asyncio
import os
import time
from dotenv import load_dotenv

from google.adk import Runner
from google.genai import types
from agents.orchestrator import orchestrator_agent
from modules.db import init_db, log_thought, get_config
from google.adk.sessions import InMemorySessionService
from modules.stealth_browser import browser_instance

load_dotenv()

async def main():
    print("[System] Initializing Project Commuter v2.1 (Stateless Mode)...")
    init_db()

    # --- Launch Browser & Dashboard ---
    print("[System] 🧬 Cloning Chrome Profile & Launching Flight Deck...")
    try:
        if not browser_instance.page:
            await browser_instance.launch()
        
        print("[System] 🖥️ Opening Dashboard in Bot Browser...")
        await browser_instance.page.goto("http://localhost:8501")
        
        work_page = await browser_instance.browser_context.new_page()
        browser_instance.page = work_page 
        
    except Exception as e:
        print(f"[System] ⚠️ Browser Launch Warning: {e}")

    print("[System] Orchestrator is online. Managing queue...")
    
    # Infinite Control Loop
    while True:
        try:
            # 1. Create a FRESH Session Service
            session_service = InMemorySessionService()
            session_id = f"orch_session_{int(time.time())}"
            user_id = "local_user"
            app_name = "ProjectCommuter"
            
            if hasattr(session_service, "create_session"):
                await session_service.create_session(session_id=session_id, user_id=user_id, app_name=app_name)
            elif hasattr(session_service, "async_create_session"):
                await session_service.async_create_session(session_id=session_id, user_id=user_id, app_name=app_name)
            
            # 2. Create Runner
            runner = Runner(
                agent=orchestrator_agent, 
                session_service=session_service, 
                app_name=app_name
            )

            # 3. Pulse
            # Fetch config dynamically every loop
            query = get_config("search_query") or "software engineer"
            
            pulse_prompt = f"Check status. If queue empty, find '{query}' jobs. If jobs pending, apply. Do ONE thing."
            content = types.Content(role="user", parts=[types.Part(text=pulse_prompt)])
            
            print(f"\n[System] 💓 Pulse (Session: {session_id[-4:]})")
            
            orchestrator_response = []
            
            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                # Capture Orchestrator's text response
                if event.content and event.content.role == "model":
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                orchestrator_response.append(part.text)

            # Log the Orchestrator's high-level thought
            final_thought = "".join(orchestrator_response)
            if final_thought:
                log_thought("Orchestrator", final_thought)

            # 4. Cooldown
            print("[System] 💤 Cooling down (5s)...")
            await asyncio.sleep(5)

        except KeyboardInterrupt:
            print("\n[System] Shutdown requested.")
            break
        except Exception as e:
            print(f"[System] ⚠️ Error in main loop: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())