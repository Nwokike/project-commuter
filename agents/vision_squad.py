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

# --- Helper: The Amnesiac Vision Runner ---
async def run_vision_task(agent, prompt, image_path):
    """
    Runs a SINGLE vision check with a FRESH session ID.
    This prevents the 'Token Explosion' by ensuring no chat history is sent.
    """
    # 1. Generate a random session ID to force a fresh context window
    session_id = f"vis_{int(time.time())}_{random.randint(1000, 9999)}"
    
    # 2. CRITICAL FIX: Explicitly Register the Session
    # We must manually create the Session object so the ADK knows it exists.
    session_service = InMemorySessionService()
    session_service.sessions[session_id] = Session(id=session_id, user_id="nav_user")
    
    # Create Runner
    runner = Runner(
        agent=agent, 
        session_service=session_service, 
        app_name="VisionRunner"
    )
    
    try:
        # Load the image
        with open(image_path, "rb") as f:
            img_bytes = f.read()
            
        # Construct the message
        msg = types.Content(role="user", parts=[
            types.Part(text=prompt),
            types.Part(inline_data=types.Blob(mime_type="image/png", data=img_bytes))
        ])
        
        # Execute (Stateless)
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
        
        # Log the thought for the Dashboard
        log_thought("Visionary", result, image_path)
        return result
        
    except Exception as e:
        error_msg = str(e)
        
        # --- CRITICAL: Honest Rate Limit Handling ---
        # If we hit a 429, we don't swap models (it's often an account ban). 
        # We SLEEP for 60 seconds.
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
    
    prompt = """
    Analyze this screenshot (red tags = SoM IDs).
    Return JSON ONLY. No markdown.
    
    Rules:
    1. If Login Screen -> action="sos"
    2. If CAPTCHA -> action="sos"
    3. If "Easy Apply" button -> action="click"
    4. If Form Input -> action="type"
    5. If Submit -> action="click"
    
    Format: {"page_type": "login|form|success|error", "action": "click|type|wait|sos", "target_som_id": 12, "value": "text", "reasoning": "..."}
    """
    
    print("[Navigator] 👁️ Sending to Vision (Cost: 1 Request)...")
    return await run_vision_task(vision_agent, prompt, screenshot_path)

# --- Tool: Execute Action ---
# CRITICAL FIX: som_id is now type 'str' to accept "null" or "job_title" without crashing
async def execute_browser_action(context, action: str, som_id: str = "-1", value: str = "") -> str:
    print(f"[Navigator] ⚡ Executing: {action} on ID {som_id}")
    
    # 1. SOS Handling
    if action == "sos":
        print("\n🚨 SOS TRIGGERED! Waiting for user in Dashboard...")
        save_config("system_status", "SOS")
        save_config("sos_message", f"Agent stuck. Action: {action}. Please help.")
        return "SOS_TRIGGERED"

    # 2. Safety Throttle (The Groq Saver)
    # We enforce a 20s sleep between actions. 
    # This keeps us well below the 6,000 TPM limit of Llama 3.1 8B.
    print("[Navigator] ⏳ Throttling 20s to save API tokens...")
    await asyncio.sleep(20)

    # 3. Execution
    if not browser_instance.page:
        await browser_instance.launch()

    # Sanitizer: Try to convert hallucinated ID to int
    try:
        # Remove any non-numeric characters if the AI returns "ID: 12"
        clean_id_str = "".join(filter(str.isdigit, str(som_id)))
        if not clean_id_str:
            return f"ACTION_ERROR: Invalid ID '{som_id}' - could not extract number"
        clean_id = int(clean_id_str)
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

navigation_agent = Agent(
    name="navigation_agent",
    model=groq_llm,
    description="Browser Operator",
    instruction="Loop: 1. `process_visual_state` 2. `execute_browser_action`. If SOS, return 'SOS'.",
    tools=[process_visual_state, execute_browser_action]
)
