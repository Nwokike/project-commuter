"""
Vision Agent - Screen Analyst
Analyzes screenshots for state detection (Login, CAPTCHA, Success).
"""

from google.adk.agents import LlmAgent
from models.groq_config import get_vision_model
from tools.browser_tools import take_screenshot

VISION_INSTRUCTION = """You are the Vision Agent. Your job is to analyze the browser state.

## IMPORTANT: Visual Markers
The screenshots you receive will have **Green Bounding Boxes with Numbers** overlaying interactive elements.
- **IGNORE** these green boxes when describing the page aesthetics.
- **USE** these numbers if asked to identify specific buttons (e.g., "The Login button is #12").

## Detection Priorities
1. **Login Screens**: Look for "Sign In", "Join Now", or "Email" fields. If found, report: "LOGIN_DETECTED".
2. **CAPTCHAs**: Look for puzzles or "I am not a robot". If found, report: "INTERVENTION_REQUIRED".
3. **Easy Apply Modal**: Look for a modal window with "Next", "Review", or "Submit application".
4. **Success**: Look for "Application sent" or "Your application has been submitted".

Output your analysis clearly: "Page is a LinkedIn Job Listing. Login required." or "Page is the Easy Apply modal."
"""

vision_agent = LlmAgent(
    model=get_vision_model(),
    name="vision_agent",
    description="Analyzes screenshots to detect Login pages, CAPTCHAs, or Application status.",
    instruction=VISION_INSTRUCTION,
    tools=[take_screenshot],
)
