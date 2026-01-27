import os
import json
import asyncio
from google.adk.agents import Agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from modules.llm_bridge import GroqModel, GeminiFallbackClient
from modules.stealth_browser import browser_instance
from modules.db import log_thought # Import the logging helper

# Initialize Models
groq_llm = GroqModel(model_name="groq/llama-3.3-70b-versatile").get_model()

# UPDATED: Use the Fallback Client instead of a single model
vision_model = GeminiFallbackClient()

# --- Helper to Run Vision Agent ---

async def run_vision_task(agent: Agent, prompt: str, image_path: str) -> str:
    print(f"[Vision] 👁️ Analyzing {image_path}...")

    session_service = InMemorySessionService()
    session_id = "vision_session"
    user_id = "navigator"
    app_name = "VisionRunner"

    if hasattr(session_service, "create_session"):
        await session_service.create_session(session_id=session_id, user_id=user_id, app_name=app_name)
    elif hasattr(session_service, "async_create_session"):
        await session_service.async_create_session(session_id=session_id, user_id=user_id, app_name=app_name)
    else:
        try:
            from google.adk.sessions import Session
            session_service.sessions[session_id] = Session(id=session_id, user_id=user_id)
        except:
            pass

    runner = Runner(agent=agent, session_service=session_service, app_name=app_name)

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            
        parts = [
            types.Part(text=prompt),
            types.Part(inline_data=types.Blob(mime_type="image/png", data=image_bytes))
        ]
        msg = types.Content(role="user", parts=parts)
        
    except Exception as e:
        print(f"[Vision] ⚠️ Error loading image: {e}. Fallback to text only.")
        msg = types.Content(role="user", parts=[types.Part(text=f"{prompt}\n(Image could not be loaded: {e})")])

    response_text = []
    try:
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
            if event.content and event.content.role == "model":
                if hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text.append(part.text)
    except Exception as e:
        print(f"[Vision] 💥 Runner Error: {e}")
        return json.dumps({
            "page_type": "error", 
            "action": "wait", 
            "reasoning": f"Vision API Error: {e}"
        })

    result = "".join(response_text)
    
    # Clean output
    if "```json" in result:
        result = result.split("```json")[1].split("```")[0].strip()
    elif "```" in result:
        result = result.split("```")[1].strip()
        
    # LOGGING: Save thought to DB for Dashboard
    log_thought("Visionary", result, image_path)
        
    return result

# --- Tools ---

async def process_visual_state(context) -> str:
    print("[Navigator] 📸 Capturing visual state...")
    try:
        screenshot_path = await browser_instance.get_screenshot()
    except Exception as e:
        print(f"[Navigator] ❌ Screenshot failed: {e}")
        return json.dumps({"page_type": "error", "action": "wait", "reasoning": "Screenshot failed"})
    
    prompt = """
    Analyze this screenshot. The red numbers are SoM tags.
    
    CRITICAL SECURITY RULES:
    1. If you see a Login Screen (username/password fields), return action="sos". Do NOT try to type credentials.
    2. If you see a CAPTCHA, return action="sos".
    3. If you see a "Page Not Found" error, click "Home" or "Feed".
    
    Output Strict JSON ONLY:
    {
        "page_type": "login" | "form" | "review" | "success" | "captcha" | "error" | "other",
        "action": "click" | "type" | "scroll" | "wait" | "sos",
        "target_som_id": <int>,
        "value": "<text if action is type>",
        "reasoning": "<brief explanation>"
    }
    """
    
    # Reduced wait time because we now have fallback models!
    # Was 20s, now 5s is safe.
    await asyncio.sleep(5) 
    
    response = await run_vision_task(vision_agent, prompt, screenshot_path)
    print(f"[Visionary] 🧠 Decision: {response}")
    return response

async def execute_browser_action(context, action: str, som_id: int = -1, value: str = "") -> str:
    print(f"[Navigator] ⚡ Executing: {action} on ID {som_id} (Value: '{value}')")
    
    if not browser_instance.page:
        await browser_instance.launch()

    if action == "wait":
        await asyncio.sleep(2)
        return "WAIT_SUCCESS"
        
    if action == "sos":
        print("\n" + "="*50)
        print("🚨 SOS TRIGGERED: The bot needs your help!")
        print("   Please interact with the browser window manually.")
        print("="*50 + "\n")
        return "SOS_TRIGGERED"

    selector = f"[data-som-id='{som_id}']"
    
    try:
        if action == "click":
            success = await browser_instance.human_click(selector)
            if success:
                await asyncio.sleep(1.5)
                return "CLICK_SUCCESS"
            return "CLICK_FAILED_NOT_VISIBLE"
            
        elif action == "type":
            await browser_instance.human_type(selector, value)
            await asyncio.sleep(0.5)
            return "TYPE_SUCCESS"
            
        elif action == "scroll":
            await browser_instance.page.mouse.wheel(0, 500)
            await asyncio.sleep(1)
            return "SCROLL_SUCCESS"
    except Exception as e:
        return f"ACTION_ERROR: {e}"

    return "UNKNOWN_ACTION"

# --- Agents ---

vision_agent = Agent(
    name="vision_agent",
    model=vision_model,  # Using Fallback Client
    description="The Eyes. Analyzes the visual state of the browser.",
    instruction="Analyze the screenshot and decide the next step. Return strictly JSON."
)

navigation_agent = Agent(
    name="navigation_agent",
    model=groq_llm,
    description="The Hands. Executes the decision made by the Visionary.",
    instruction="""
    You are the Navigator.
    1. Call `process_visual_state`.
    2. Parse JSON.
    3. Call `execute_browser_action`.
    
    If action is "sos", STOP and return "SOS_TRIGGERED".
    Repeat until page_type is "success".
    """,
    tools=[process_visual_state, execute_browser_action]
)