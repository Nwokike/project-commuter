import os
import json
import asyncio
from google.adk.agents import Agent
from google.adk.model import Model
from google.adk.types import RunContext

from modules.llm_bridge import GroqModel
from modules.stealth_browser import browser_instance # Import the singleton

# Initialize Models
groq_llm = GroqModel(model_name="groq/llama-3.3-70b-versatile").get_model()
gemini_model = Model(model="gemini-2.5-flash-preview") 

# --- Tools (Connected to Browser) ---

async def execute_browser_action(context: RunContext, action: str, som_id: int, value: str = "") -> str:
    """
    Executes a physical action on the browser using the StealthBrowser singleton.
    """
    print(f"[Navigator] ⚡ Executing: {action} on ID {som_id} (Value: '{value}')")
    
    # Ensure browser is running (lazy start if needed, though Orchestrator should have started it)
    if not browser_instance.page:
        print("[Navigator] Browser not running! Attempting launch...")
        await browser_instance.launch()

    selector = f"[data-som-id='{som_id}']"
    
    if action == "click":
        success = await browser_instance.human_click(selector)
        return "CLICK_SUCCESS" if success else "CLICK_FAILED_NOT_VISIBLE"
        
    elif action == "type":
        await browser_instance.human_type(selector, value)
        return "TYPE_SUCCESS"
        
    elif action == "scroll":
        # Simple scroll implementation
        await browser_instance.page.mouse.wheel(0, 500)
        return "SCROLL_SUCCESS"
        
    elif action == "wait":
        await asyncio.sleep(2)
        return "WAIT_SUCCESS"
        
    elif action == "sos":
        return "SOS_TRIGGERED"

    return "UNKNOWN_ACTION"

# --- Agents ---

# 1. Vision Agent (Type C: Pure Model / Multimodal)
vision_agent = Agent(
    name="vision_agent",
    model=gemini_model, 
    description="The Eyes. Analyzes the visual state of the browser.",
    instruction="""
    You are the Visionary. You receive a screenshot of a web page where interactive elements are tagged with red numbers (SoM IDs).
    
    Your Goal: Analyze the page and decide the next step to apply for the job.
    
    Output Strict JSON ONLY:
    {
        "page_type": "login" | "form" | "review" | "success" | "captcha",
        "action": "click" | "type" | "scroll" | "wait" | "sos",
        "target_som_id": <int>,
        "value": "<text to type if action is type>",
        "reasoning": "<brief explanation>"
    }
    
    If you see a form field like "First Name", output action="type".
    If you see a "Submit" or "Next" button, output action="click".
    If you see a CAPTCHA or are confused, output action="sos".
    """
)

# 2. Navigation Agent (Type B: Custom Tool)
navigation_agent = Agent(
    name="navigation_agent",
    model=groq_llm,
    description="The Hands. Executes the decision made by the Visionary.",
    instruction="""
    You are the Navigator. You receive a JSON instruction from the Visionary.
    Your job is to execute it using the `execute_browser_action` tool.
    
    If action is "click", call execute_browser_action("click", target_som_id).
    If action is "type", call execute_browser_action("type", target_som_id, value).
    """,
    tools=[execute_browser_action]
)