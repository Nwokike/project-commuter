import os
import json
import asyncio
from google.adk.agents import Agent
from google.adk.models import Gemini

from modules.llm_bridge import GroqModel
from modules.stealth_browser import browser_instance # Import the singleton

# Initialize Models
groq_llm = GroqModel(model_name="groq/llama-3.3-70b-versatile").get_model()
gemini_model = Gemini(model="gemini-2.5-flash-preview")

# --- Tools (Connected to Browser) ---

async def process_visual_state(context) -> str:
    """
    Captures the current browser state, asks the Visionary for a decision,
    and returns the JSON instruction.
    """
    print("[Navigator] 📸 Capturing visual state...")
    screenshot_path = await browser_instance.get_screenshot()
    
    # Run the vision agent with the screenshot
    # ADK models typically support local image paths in strings or specific attachments
    prompt = f"Analyze this screenshot from {screenshot_path} and tell me the next move."
    
    # We use agent.run which handles the multimodal input if the model supports it
    response = vision_agent.run(prompt)
    return response

async def execute_browser_action(context, action: str, som_id: int = -1, value: str = "") -> str:
    """
    Executes a physical action on the browser using the StealthBrowser singleton.
    """
    print(f"[Navigator] ⚡ Executing: {action} on ID {som_id} (Value: '{value}')")
    
    # Ensure browser is running
    if not browser_instance.page:
        print("[Navigator] Browser not running! Attempting launch...")
        await browser_instance.launch()

    if action == "wait":
        await asyncio.sleep(2)
        return "WAIT_SUCCESS"
        
    if action == "sos":
        return "SOS_TRIGGERED"

    selector = f"[data-som-id='{som_id}']"
    
    if action == "click":
        success = await browser_instance.human_click(selector)
        if success:
            await asyncio.sleep(1.5) # Wait for transition
            return "CLICK_SUCCESS"
        return "CLICK_FAILED_NOT_VISIBLE"
        
    elif action == "type":
        # Brain Integration: If value is missing or generic, we'd normally call the Brain Squad
        # For now, we assume the Navigator or Visionary provides the value
        await browser_instance.human_type(selector, value)
        await asyncio.sleep(0.5)
        return "TYPE_SUCCESS"
        
    elif action == "scroll":
        await browser_instance.page.mouse.wheel(0, 500)
        await asyncio.sleep(1)
        return "SCROLL_SUCCESS"

    return "UNKNOWN_ACTION"

# --- Agents ---

# 1. Vision Agent (Type C: Pure Model / Multimodal)
vision_agent = Agent(
    name="vision_agent",
    model=gemini_model, 
    description="The Eyes. Analyzes the visual state of the browser.",
    instruction="""
    You are the Visionary. You receive a screenshot of a web page with SoM tags (red numbers).
    
    Your Goal: Decide the next step to apply for the job.
    
    Output Strict JSON ONLY:
    {
        "page_type": "login" | "form" | "review" | "success" | "captcha",
        "action": "click" | "type" | "scroll" | "wait" | "sos",
        "target_som_id": <int>,
        "value": "<text if action is type>",
        "reasoning": "<brief explanation>"
    }
    
    - If you see a field like "First Name", "Email", use action="type".
    - If you see "Next", "Submit", "Continue", use action="click".
    - If you see a CAPTCHA or are stuck, use action="sos".
    """
)

# 2. Navigation Agent (Type B: Custom Tool)
navigation_agent = Agent(
    name="navigation_agent",
    model=groq_llm,
    description="The Hands. Executes the decision made by the Visionary.",
    instruction="""
    You are the Navigator. Your goal is to complete the job application.
    
    Loop:
    1. Call `process_visual_state` to get the next instruction (JSON).
    2. Parse the JSON and call `execute_browser_action` with the correct parameters.
    3. If `page_type` is "success" or `action` is "sos", STOP and report.
    4. Otherwise, continue the loop.
    
    You must be precise. If the Visionary says "click" on ID 5, you call `execute_browser_action("click", 5)`.
    """,
    tools=[process_visual_state, execute_browser_action]
)
