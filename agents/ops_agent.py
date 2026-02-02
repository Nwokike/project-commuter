"""
Ops Agent - Form Filling and Job Application
Handles the actual application process using deep reasoning models.
"""

from google.adk.agents import LlmAgent
from models.groq_config import get_reasoning_model
from tools.browser_tools import (
    navigate_to_url,
    click_element,
    type_text,
    take_screenshot,
    get_page_content,
    scroll_page,
)

OPS_INSTRUCTION = """You are an Ops Agent specialized in filling out job application forms.

Your responsibilities:
1. **Navigate to Job Pages**: Go to job listing URLs
2. **Fill Application Forms**: Enter user information from their CV/profile
3. **Upload Documents**: Handle resume/CV upload fields
4. **Submit Applications**: Complete the application process
5. **Track Progress**: Update session state with application status

User profile information available in state:
- {user:full_name} - Full name
- {user:email} - Email address  
- {user:phone} - Phone number
- {user:location} - Current location
- {user:experience_summary} - Work experience summary
- {user:skills} - List of skills
- {user:education} - Education background

When filling forms:
1. First use get_page_content() to understand the form structure
2. Match form fields to user profile data
3. Fill fields one by one, taking screenshots after each action
4. If you encounter a login page or CAPTCHA, STOP and report intervention needed

After each action, report status:
{
    "action_taken": "description of what you did",
    "current_page": "description of current page state",
    "next_step": "what should happen next",
    "needs_intervention": true/false,
    "intervention_reason": "reason if intervention needed"
}

Be careful and methodical. Verify each field before submitting."""

ops_agent = LlmAgent(
    model=get_reasoning_model(),  # Uses GPT-OSS 120B or Qwen 32B
    name="ops_agent",
    description="Fills out job application forms using browser automation and user profile information",
    instruction=OPS_INSTRUCTION,
    tools=[
        navigate_to_url,
        click_element,
        type_text,
        take_screenshot,
        get_page_content,
        scroll_page,
    ],
)
