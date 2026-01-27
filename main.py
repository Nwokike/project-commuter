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
    print("[System] Initializing Project Commuter v2.1 (Eco Mode)...")
    init_db()

    # --- Launch Browser ---
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
    
    while True:
        try:
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

            # Pulse
            query = get_config("search_query") or "software engineer"
            
            # SIMPLIFIED PROMPT to stop hallucinations
            pulse_prompt = f"1. Check status. 2. If no pending jobs, scout for '{query}'. 3. If pending job exists, apply. DO NOT ARGUE. JUST CALL THE TOOL."
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

            # INCREASED COOLDOWN: 15s prevents hitting 30 RPM and saves daily tokens
            print("[System] 💤 Cooling down (15s)...")
            await asyncio.sleep(15)

        except KeyboardInterrupt:
            print("\n[System] Shutdown requested.")
            break
        except Exception as e:
            print(f"[System] ⚠️ Error in main loop: {e}")
            # Longer sleep on error to let rate limits reset
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())