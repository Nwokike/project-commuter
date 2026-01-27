import os
import json
import asyncio
import time
import random
from google.adk.agents import Agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService, Session
from google.genai import types

from modules.llm_bridge import GroqModel, GeminiFallbackClient
from modules.stealth_browser import browser_instance
from modules.db import log_thought, save_config, get_config

# --- Models ---
# Groq: Handles the logic of "Clicking" and "Typing" (High Volume)
groq_llm = GroqModel(model_name="groq/llama-3.1-8b-instant").get_model()

# Gemini: Handles the "Seeing" (Low Volume, High Intelligence)
vision_model = GeminiFallbackClient()

# --- Session Management (Memory Fix) ---
# We use a global variable to persist the Vision Agent's memory *during* a job application.
# It gets reset when the job is done or an SOS occurs.
_current_vision_session_id = None

def get_vision_session_id():
    global _current_vision_session_id
    if _current_vision_session_id is None:
        # Create a fresh ID for a new job application cycle
        _current_vision_session_id = f"vis_{int(time.time())}_{random.randint(1000, 9999)}"
        print(f"[Vision] 🧠 New Memory Session Started: {_current_vision_session_id}")
    return _current_vision_session_id

def reset_vision_memory():
    global _current_vision_session_id
    print(f"[Vision] 🧹 Wiping Memory (Session {_current_vision_session_id} ended).")
    _current_vision_session_id = None

# --- Helper: The Persistent Vision Runner ---
async def run_vision_task(agent, prompt, image_path):
    """
    Runs a vision check with a PERSISTENT session ID.
    """
    session_id = get_vision_session_id()
    
    # Explicitly Register the Session
    session_service = InMemorySessionService()
    # We must check if it exists or create it, but InMemoryService resets on re-instantiation 
    # in this simple script. For true persistence in ADK, we'd pass the service around.
    # However, since ADK local storage is file-based or memory-based, re-declaring it 
    # with the SAME ID should recover the history if it's persisting to disk/memory correctly.
    # Note: In this lightweight 'InMemory' version, we rely on the ADK's internal handling.
    
    # CRITICAL: We pass the session_id to the runner.
    session_service.sessions[session_id] = Session(id=session_id, user_id="nav_user")
    
    runner = Runner(
        agent=agent, 
        session_service=session_service, 
        app_name="VisionRunner"
    )
    
    try:
        with open(image_path, "rb") as f:
            img_bytes = f.read()
            
        msg = types.Content(role="user", parts=[
            types.Part(text=prompt),
            types.Part(inline_data=types.Blob(mime_type="image/png", data=img_bytes))
        ])
        
        resp_text = []
        async for event in runner.run_async(user_id="nav_user", session_id=session_id, new_message=msg):
            if event.content and event.content.role == "model":
                 if hasattr(event.content, 'parts'):
                     for part in event.content.parts:
                         if hasattr(part, 'text') and part.text:
                             resp_text.append(part.text)
        
        result = "".join(resp_text)
        
        # Clean JSON markdown if present
        if "```json" in result: 
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result: 
            result = result.split("```")[1].strip()
        
        log_thought("Visionary", result, image_path)
        return result
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "resource_exhausted" in error_msg.lower():
            print("\n[Vision] 🛑 RATE LIMIT HIT (Gemini). Sleeping for 60s to recharge...")
            log_thought("System", "Vision API Quota Exceeded. Pausing for 60s...")
            await asyncio.sleep(60)
            return json.dumps({"page_type": "rate_limit", "action": "wait", "reasoning": "Quota Recharge"})
            
        print(f"[Vision] ⚠️ Error: {error_msg}")
        return json.dumps({"page_type": "error", "action": "wait", "reasoning": "API Error"})

# --- Tool: Process Visual State ---
async def process_visual_state(context) -> str:
    print("[Navigator] 📸 Capturing visual state...")
    try:
        screenshot_path = await browser_instance.get_screenshot()
    except Exception as e:
        return json.dumps({"page_type": "error", "action": "wait", "reasoning": "Screenshot failed"})
    
    # UPDATED PROMPT: Explicitly handle Success and common failures
    prompt = """
    Analyze this screenshot (red tags = SoM IDs).
    Return JSON ONLY. No markdown.
    
    Rules:
    1. If "Application submitted" or "Success" -> action="success"
    2. If Login Screen -> action="sos"
    3. If CAPTCHA -> action="sos"
    4. If "Easy Apply" button -> action="click"
    5. If Form Input -> action="type"
    6. If "Next" or "Submit" -> action="click"
    7. If "Review" -> action="click"
    
    Format: {"page_type": "login|form|success|error", "action": "click|type|wait|sos|success", "target_som_id": 12, "value": "text", "reasoning": "..."}
    """
    
    print("[Navigator] 👁️ Sending to Vision (Cost: 1 Request)...")
    return await run_vision_task(vision_agent, prompt, screenshot_path)

# --- Tool: Execute Action ---
async def execute_browser_action(context, action: str, som_id: str = "-1", value: str = "") -> str:
    print(f"[Navigator] ⚡ Executing: {action} on ID {som_id}")
    
    # 1. SUCCESS Handling (Exit Condition)
    if action == "success":
        print("\n[Navigator] 🎉 Application Successful!")
        reset_vision_memory() # Clear memory for next job
        return "SUCCESS"

    # 2. SOS Handling
    if action == "sos":
        print("\n🚨 SOS TRIGGERED! Waiting for user in Dashboard...")
        save_config("system_status", "SOS")
        save_config("sos_message", f"Agent stuck. Action: {action}. Please help.")
        reset_vision_memory() # Clear memory
        return "SOS_TRIGGERED"

    # 3. Safety Throttle
    print("[Navigator] ⏳ Throttling 5s (Eco Mode)...")
    await asyncio.sleep(5) 

    if not browser_instance.page:
        await browser_instance.launch()

    # Sanitizer
    try:
        clean_id_str = "".join(filter(str.isdigit, str(som_id)))
        if not clean_id_str and action != "wait":
            return f"ACTION_ERROR: Invalid ID '{som_id}'"
        clean_id = int(clean_id_str) if clean_id_str else -1
    except Exception as e:
        return f"ACTION_ERROR: Invalid ID format '{som_id}'"

    selector = f"[data-som-id='{clean_id}']"
    try:
        if action == "click":
            await browser_instance.human_click(selector)
            return "CLICK_SUCCESS"
        elif action == "type":
            await browser_instance.human_type(selector, value)
            return "TYPE_SUCCESS"
        elif action == "wait":
            return "WAIT_SUCCESS"
    except Exception as e:
        return f"ACTION_ERROR: {e}"
        
    return "UNKNOWN_ACTION"

# --- Agent Definitions ---
vision_agent = Agent(
    name="vision_agent", 
    model=vision_model, 
    description="Visual Analyzer", 
    instruction="Output JSON."
)

# UPDATED INSTRUCTION: Explicit exit condition
navigation_agent = Agent(
    name="navigation_agent",
    model=groq_llm,
    description="Browser Operator",
    instruction="""
    You are the Browser Operator.
    
    Loop:
    1. Call `process_visual_state` to see the screen.
    2. Call `execute_browser_action` with the parameters from step 1.
    3. IF `execute_browser_action` returns "SUCCESS", STOP and return "JOB_APPLIED".
    4. IF `execute_browser_action` returns "SOS_TRIGGERED", STOP and return "SOS".
    """,
    tools=[process_visual_state, execute_browser_action]
)
