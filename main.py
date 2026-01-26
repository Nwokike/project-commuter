import asyncio
import os
from dotenv import load_dotenv

from google.adk.runtime import Runtime
from agents.orchestrator import orchestrator_agent
from modules.db import init_db

# Load Environment
load_dotenv()

async def main():
    print("[System] Initializing Project Commuter v2.1 (ADK Native)...")
    
    # 1. Initialize Infrastructure
    init_db()
    
    # 2. Setup ADK Runtime
    # The Runtime manages the event loop, tool execution, and memory.
    runtime = Runtime(
        agent=orchestrator_agent,
        # We can add a specialized memory or history provider here in Phase 2
    )

    print("[System] Orchestrator is online. Waiting for instructions...")
    
    # 3. Start the Loop
    # In a real deployment, this might be triggered by a Cron or a Streamlit event.
    # For now, we give it a kickstart command.
    
    initial_prompt = "Check the system status and decide what to do next."
    
    async for event in runtime.run(initial_prompt):
        # The runtime yields events (Thought, Call, Result, Answer)
        # We can log these to the console or dashboard
        if event.type == "thought":
            print(f"🤖 [Thought]: {event.content}")
        elif event.type == "tool_call":
            print(f"🛠️ [Tool Call]: {event.tool_name} -> {event.tool_input}")
        elif event.type == "tool_result":
            print(f"✅ [Result]: {event.tool_output}")
        elif event.type == "answer":
            print(f"🏁 [Final Answer]: {event.content}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[System] Shutdown requested.")