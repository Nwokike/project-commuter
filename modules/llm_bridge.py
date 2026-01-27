import os
import asyncio
from dotenv import load_dotenv

# Import ADK components
from google.adk.models.lite_llm import LiteLlm
from google.adk.models import Gemini
from pydantic import PrivateAttr

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

class GroqFallbackClient(LiteLlm):
    """
    A smart wrapper that manages a pool of Groq models.
    Implements 'Waterfall' fallback to handle TPD limits.
    """
    # CRITICAL FIX 1: Corrected Model IDs (500k TPD models first)
    _model_names: list = PrivateAttr(default=[
        "groq/llama-3.1-8b-instant",                   # Tier 1: Proven Stability (500k Limit)
        "groq/meta-llama/llama-4-scout-17b-16e-instruct", # Tier 2: The New 17B (500k Limit)
        "groq/llama-3.3-70b-versatile"                 # Tier 3: Smartest (100k Limit - Use only if others fail)
    ])
    _clients: list = PrivateAttr(default=[])

    def __init__(self):
        # Initialize parent with the primary model
        super().__init__(model="groq/llama-3.1-8b-instant", api_key=GROQ_API_KEY)
        
        # Initialize wrappers for each model in the chain
        self._clients = [
            LiteLlm(model=name, api_key=GROQ_API_KEY) 
            for name in self._model_names
        ]

    async def generate_content_async(self, contents, **kwargs):
        last_error = None
        
        # CRITICAL FIX 2: Argument Cleaning
        # The ADK tries to pass 'model="old_name"' in kwargs. We MUST remove it
        # so the backup client uses its OWN internal model name.
        if 'model' in kwargs:
            del kwargs['model']
        
        for i, client in enumerate(self._clients):
            model_name = self._model_names[i]
            try:
                # ADK Runner passes 'contents' and kwargs. We forward them.
                async for chunk in client.generate_content_async(contents, **kwargs):
                    yield chunk
                
                # If success, return immediately
                return

            except Exception as e:
                error_str = str(e)
                # Catch Rate Limits (429), Not Found (404), and Tool Errors (400)
                if any(err in error_str for err in ["429", "404", "Rate limit", "400", "not found"]):
                    print(f"[Bridge] ⚠️ {model_name} failed. Switching to next...")
                    last_error = e
                    continue 
                else:
                    # If it's a critical error (like Auth), log it
                    print(f"[Bridge] ❌ {model_name} Critical Error: {e}")
                    last_error = e

        print("[Bridge] 💥 All Groq models exhausted.")
        if last_error:
            raise last_error
        else:
             raise Exception("Unknown error in Groq Fallback Client")

    def generate_content(self, contents, **kwargs):
        raise NotImplementedError("Use generate_content_async for the Fallback Client")


class GroqModel:
    """
    Factory class that returns the Fallback Client.
    """
    def __init__(self, model_name=None):
        self.model = GroqFallbackClient()

    def get_model(self):
        return self.model


class GeminiFallbackClient(Gemini):
    """
    A smart wrapper that manages a pool of Gemini models.
    """
    _model_names: list = PrivateAttr(default=[
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3-flash"
    ])
    _clients: list = PrivateAttr(default=[])

    def __init__(self):
        super().__init__(model="gemini-2.5-flash")
        self._clients = [Gemini(model=name) for name in self._model_names]

    async def generate_content_async(self, contents, **kwargs):
        last_error = None
        
        # Clean kwargs for Gemini too
        if 'model' in kwargs:
            del kwargs['model']
        
        for i, client in enumerate(self._clients):
            model_name = self._model_names[i]
            try:
                async for chunk in client.generate_content_async(contents, **kwargs):
                    yield chunk
                return

            except Exception as e:
                error_str = str(e)
                # Catch Rate Limits
                if any(err in error_str for err in ["429", "404", "Rate limit", "quota"]):
                    print(f"[Bridge] ⚠️ {model_name} exhausted. Switching to next...")
                    last_error = e
                    continue 
                else:
                    print(f"[Bridge] ❌ {model_name} Error: {e}")
                    last_error = e

        print("[Bridge] 💥 All Gemini models exhausted.")
        if last_error:
            raise last_error
        else:
             raise Exception("Unknown error in Gemini Fallback Client")

    def generate_content(self, contents, **kwargs):
        raise NotImplementedError("Use generate_content_async for the Fallback Client")