import asyncio
import os
from dotenv import load_dotenv

from google.adk import Runner
from agents.orchestrator import orchestrator_agent
from modules.db import init_db

# Load Environment
load_dotenv()

async def main():
    print("[System] Initializing Project Commuter v2.1 (ADK Native)...")
    
    # 1. Initialize Infrastructure
    init_db()
    
    # 2. Setup ADK Runner
    # The Runner manages the event loop and agent execution.
    runner = Runner(agent=orchestrator_agent)

    print("[System] Orchestrator is online. Waiting for instructions...")
    
    # 3. Start the Loop
    initial_prompt = "Check the system status and decide what to do next."
    
    # Runner.run usually takes user_id and session_id as well
    for event in runner.run(user_id="local_user", session_id="session_1", new_message=initial_prompt):
        # Handle events (Simplified for compatibility)
        print(f"[{event.type}]: {event}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[System] Shutdown requested.")