import os
import time
from functools import wraps
from dotenv import load_dotenv

from google.adk.models.lite_llm import LiteLlm
from google import genai

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

# Initialize GenAI Client
client = genai.Client(api_key=GEMINI_API_KEY)


def rate_limit(rpm):
    """
    Decorator to enforce a strict Request Per Minute (RPM) limit.
    """
    interval = 60.0 / rpm
    last_call = 0

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal last_call
            elapsed = time.time() - last_call
            if elapsed < interval:
                sleep_time = interval - elapsed
                print(f"[RateLimit] Sleeping for {sleep_time:.2f}s to respect {rpm} RPM...")
                time.sleep(sleep_time)
            result = func(*args, **kwargs)
            last_call = time.time()
            return result
        return wrapper
    return decorator


class GroqModel:
    """
    Wrapper for Groq via LiteLLM.
    Used for all TEXT-based logic agents (Scout, Decision, Context, etc.).
    """
    def __init__(self, model_name="groq/llama-3.3-70b-versatile"):
        self.model = LiteLlm(
            model=model_name,
            api_key=GROQ_API_KEY
        )

    def get_model(self):
        return self.model


class GeminiVisionModel:
    """
    Wrapper for Gemini Vision. Enforces strict 5 RPM limit for 2026 Free Tier.
    """
    def __init__(self, model_name="gemini-3-flash"):
        self.model_name = model_name

    @rate_limit(rpm=4)
    def analyze_image(self, image_path, prompt):
        """Analyzes an image file with a prompt using google-genai Client."""
        print(f"[GeminiVision] Analyzing {image_path}...")
        try:
            import PIL.Image
            img = PIL.Image.open(image_path)
            response = client.models.generate_content(
                model=self.model_name,
                contents=[prompt, img]
            )
            return response.text
        except Exception as e:
            print(f"[GeminiVision] Error: {e}")
            return None
