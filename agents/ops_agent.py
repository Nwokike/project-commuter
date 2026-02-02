"""
Ops Agent - LinkedIn Easy Apply Sniper
Uses Visual SOM (Set-of-Mark) to click buttons by ID.
"""

from google.adk.agents import LlmAgent
from models.groq_config import get_reasoning_model
from tools.browser_tools import (
    navigate_to_url,
    click_element,
    type_text,
    take_screenshot,
    scroll_page,
)

OPS_INSTRUCTION = """You are the LinkedIn Easy Apply Sniper.

Your goal is to navigate to a job URL and apply using the "Easy Apply" workflow.

### CRITICAL: How to See & Click
You do NOT click using X/Y coordinates.
1. Look at the screenshot provided.
2. You will see **Green Boxes with Numbers** (e.g., "12", "45") on interactive elements.
3. To click a button, use `click_element(element_id="12")`.
4. **NEVER** guess a selector if an ID is visible.

### The "Easy Apply" Workflow
1. **Login Check**: If you see a "Sign In" page, STOP. Ask the user to log in manually via the dashboard.
2. **Start**: Navigate to the job URL.
3. **Identify**: Find the button labeled "Easy Apply" (Look for its Number ID).
4. **Apply Loop**:
   - Click "Easy Apply".
   - If a modal appears, find the "Next" or "Review" button IDs.
   - If input is needed (e.g., Phone), use `type_text(element_id="...", text=...)`.
   - **Submit**: Click "Submit application".

### Context
User Data: {user:full_name}, {user:email}, {user:phone}, {user:skills}
CV Summary: {user:experience_summary}

Always confirm what you see before clicking: "I see the Easy Apply button at ID 14, clicking now..." """

ops_agent = LlmAgent(
    model=get_reasoning_model(),
    name="ops_agent",
    description="Applies to jobs using Visual SOM (Clicking by ID numbers).",
    instruction=OPS_INSTRUCTION,
    tools=[
        navigate_to_url,
        click_element,
        type_text,
        take_screenshot,
        scroll_page,
    ],
)
