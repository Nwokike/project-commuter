from google.adk.agents import Agent
from modules.llm_bridge import GroqModel, GeminiVisionModel
from modules.stealth_browser import StealthBrowser

# Initialize Models
groq_llm = GroqModel().get_model()
gemini_vision = GeminiVisionModel() # Has internal rate limiter

# --- Tools ---

def analyze_viewport(screenshot_path: str) -> str:
    """
    Analyzes the screenshot using Gemini Vision and returns a JSON description 
    of form fields, buttons, and labels.
    """
    prompt = """
    Analyze this job application page. Return a JSON object with:
    1. "page_type": ("form", "review", "success", "login", "other")
    2. "elements": List of input fields (id, label, type, coordinates) and buttons.
    3. "errors": Any visible error messages.
    Focus on finding 'First Name', 'Last Name', 'Email', 'Resume Upload', 'Submit', 'Next'.
    """
    print(f"[Tool:Vision] Analyzing {screenshot_path}...")
    result = gemini_vision.analyze_image(screenshot_path, prompt)
    return result if result else "{'error': 'Vision Analysis Failed'}"

# --- Agents ---

vision_agent = Agent(
    name="vision_agent",
    model=groq_llm, 
    description="See the page and extract form elements.",
    instruction="Use the `analyze_viewport` tool to analyze the screenshot. Return a structured JSON of form elements." ,
    tools=[analyze_viewport]
)

navigation_agent = Agent(
    name="navigation_agent",
    model=groq_llm,
    description="Decides the next browser action.",
    instruction="Given the UI map, decide the next action (click, type, scroll). Return JSON with 'action', 'selector', and 'value'."
)

scroll_agent = Agent(
    name="scroll_agent",
    model=groq_llm,
    description="Scrolls the page to find elements.",
    instruction="Return JSON: {'action': 'scroll', 'direction': 'down', 'amount': 500}"
)
