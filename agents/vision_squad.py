from google.adk.agents import Agent
from modules.llm_bridge import GroqModel, GeminiVisionModel
from modules.stealth_browser import StealthBrowser

# Initialize Models
groq_llm = GroqModel().get_model()
gemini_vision = GeminiVisionModel() # Has internal rate limiter

# --- Tools ---

async def analyze_viewport(page, screenshot_path: str) -> str:
    """
    Analyzes the screenshot using Gemini Vision and returns a JSON description 
    of form fields, buttons, and labels, mapped to SoM IDs.
    """
    # 1. Inject Visual Tags
    script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modules", "scripts", "tag_elements.js")
    with open(script_path, "r") as f:
        js_payload = f.read()
    await page.evaluate(js_payload)

    # 2. Capture Tagged Screenshot
    await page.screenshot(path=screenshot_path)

    prompt = """
    Analyze this job application page. Every interactive element has been tagged with a red number (SoM ID).
    Return a JSON object with:
    1. "page_type": ("form", "review", "success", "login", "other")
    2. "elements": List of interactive objects: {"id": SoM_ID, "label": text, "type": input/button, "purpose": e.g., "submit_button"}.
    3. "errors": Any visible error messages.
    Focus on elements needed for application (e.g., 'First Name', 'Submit').
    """
    print(f"[Tool:Vision] Analyzing tagged {screenshot_path}...")
    result = gemini_vision.analyze_image(screenshot_path, prompt)
    return result if result else "{'error': 'Vision Analysis Failed'}"

# --- Agents ---

vision_agent = Agent(
    name="vision_agent",
    model=groq_llm, 
    description="See the tagged page and extract form elements by SoM ID.",
    instruction="Use the `analyze_viewport` tool. Return a structured JSON where elements are identified by their 'id' (the red number)." ,
    tools=[analyze_viewport]
)

navigation_agent = Agent(
    name="navigation_agent",
    model=groq_llm,
    description="Decides the next action using SoM IDs.",
    instruction="Given the UI map (with SoM IDs), decide what to click or type. Return JSON with 'action', 'som_id', and 'value' (if typing)."
)

scroll_agent = Agent(
    name="scroll_agent",
    model=groq_llm,
    description="Scrolls the page to find elements.",
    instruction="Return JSON: {'action': 'scroll', 'direction': 'down', 'amount': 500}"
)
