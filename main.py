import asyncio
import os
from dotenv import load_dotenv

from google.adk import Runner
from google.genai import types
from agents.orchestrator import orchestrator_agent
from modules.db import init_db

# Load Environment
load_dotenv()

async def main():
    print("[System] Initializing Project Commuter v2.1 (ADK Native)...")
    
    # 1. Initialize Infrastructure
    init_db()
    
    # 2. Setup ADK Runner
    from google.adk.sessions import InMemorySessionService
    
    # Initialize the session service separately so we can access it
    session_service = InMemorySessionService()
    
    runner = Runner(
        agent=orchestrator_agent, 
        session_service=session_service, 
        app_name="ProjectCommuter"
    )

    print("[System] Orchestrator is online. Waiting for instructions...")
    
    # --- CRITICAL FIX: Create the session before using it ---
    session_id = "session_1"
    user_id = "local_user"
    
    # Ensure the session exists in the service
    if hasattr(session_service, "create_session"):
        # Synchronous creation
        session_service.create_session(session_id=session_id, user_id=user_id)
    elif hasattr(session_service, "async_create_session"):
        # Async creation (common in newer ADK versions)
        await session_service.async_create_session(session_id=session_id, user_id=user_id)
    else:
        # Fallback manual creation if methods differ (rare)
        from google.adk.sessions import Session
        session_service.sessions[session_id] = Session(id=session_id, user_id=user_id)

    # 3. Start the Loop
    initial_prompt = "Check the system status and decide what to do next."
    
    content = types.Content(role="user", parts=[types.Part(text=initial_prompt)])
    
    # Now run with the pre-created session_id
    async for event in runner.run(user_id=user_id, session_id=session_id, new_message=content):
        print(f"[{event.type}]: {event}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[System] Shutdown requested.")