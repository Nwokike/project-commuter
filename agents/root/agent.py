"""
Root Agent - LinkedIn Sniper Orchestrator
Strictly coordinates the CV-based LinkedIn application process.
"""

from google.adk.agents import Agent
from models.groq_config import get_fast_model
from agents.vision.agent import vision_agent
from agents.scout.agent import scout_agent
from agents.ops.agent import ops_agent

ROOT_INSTRUCTION = """You are the Project Commuter Orchestrator, specifically configured as a **LinkedIn Sniper**.

## Your Goal
To apply for "Easy Apply" jobs on LinkedIn using the user's uploaded CV context.

## Your State
You have access to the user's session state:
- Name: {user:full_name}
- CV Summary: {user:experience_summary}

## Critical Rules
1. **CV Check**: 
   - Check `{user:full_name}`. 
   - If it is "Candidate", ask the user to upload a CV.
   - If it is a real name (e.g., "Onyeka Nwokike"), assume the CV is valid and proceed.
2. **LinkedIn Only**: You strictly enforce the LinkedIn scope.
3. **Login Check**: Before starting a search, remind the user to ensure they are logged into LinkedIn in the browser view.

## Delegation Strategy
- **Searching**: Delegate to **Scout Agent**.
- **Applying**: Delegate to **Ops Agent**.
- **Visuals**: Delegate to **Vision Agent** to check for login screens.

## Interaction Style
- Be concise.
- If the user says "Open linkedin", delegate to the Ops Agent to navigate there.
"""

def initialize_session_state(callback_context):
    state = callback_context.state
    state.setdefault("user:full_name", "Candidate")
    state.setdefault("user:email", "Not specified")
    state.setdefault("user:phone", "")
    state.setdefault("user:location", "Not specified")
    state.setdefault("user:job_titles", [])
    state.setdefault("user:skills", [])
    state.setdefault("user:experience_summary", "No CV uploaded yet.")
    state.setdefault("user:education", "")
    state.setdefault("discovered_jobs", [])

root_agent = Agent(
    model=get_fast_model(),
    name="root_agent",
    description="Main orchestrator for the LinkedIn Sniper workflow.",
    instruction=ROOT_INSTRUCTION,
    sub_agents=[vision_agent, scout_agent, ops_agent],
    before_agent_callback=initialize_session_state,
)
