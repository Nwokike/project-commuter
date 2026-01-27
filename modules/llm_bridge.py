import os
import time
import asyncio
from dotenv import load_dotenv

# Import ADK components
from google.adk.models.lite_llm import LiteLlm
from google.adk.models import Gemini
from google.genai import types

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

class GroqModel:
    """
    Wrapper for Groq via LiteLLM.
    Used for high-volume text logic (Scout, Orchestrator).
    """
    def __init__(self, model_name="groq/llama-3.3-70b-versatile"):
        self.model = LiteLlm(
            model=model_name,
            api_key=GROQ_API_KEY
        )

    def get_model(self):
        return self.model

class GeminiFallbackClient:
    """
    A smart wrapper that manages a pool of Gemini models.
    Implements the 'Waterfall' fallback strategy to maximize Free Tier limits.
    """
    def __init__(self):
        # Priority Order:
        # 1. Flash 2.5 (Standard, 20 RPD)
        # 2. Flash Lite (Backup, 10 RPD)
        # 3. Flash 3.0 (High Intelligence, 20 RPD - Last Resort)
        self.model_names = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3-flash"
        ]
        
        # Initialize ADK wrappers for each
        self.clients = [Gemini(model=name) for name in self.model_names]
        self.name = "GeminiFallbackSwarm"

    async def generate_content_async(self, contents, **kwargs):
        """
        Attempts to generate content using the model pool.
        If one fails (429/404/500), it tries the next.
        """
        last_error = None
        
        for i, client in enumerate(self.clients):
            model_name = self.model_names[i]
            try:
                # print(f"[Bridge] ⚡ Attempting generation with {model_name}...")
                
                # ADK Runner passes 'contents' and kwargs. We forward them.
                async for chunk in client.generate_content_async(contents, **kwargs):
                    yield chunk
                
                # If we finish the loop without error, we are done.
                return

            except Exception as e:
                error_str = str(e)
                # Check for rate limits or not found errors
                if "429" in error_str or "Rate limit" in error_str or "404" in error_str:
                    print(f"[Bridge] ⚠️ {model_name} exhausted or unavailable. Switching to next...")
                    last_error = e
                    continue # Try next model
                else:
                    # If it's a real error (like bad request), maybe we shouldn't retry?
                    # For stability, we try anyway unless it's the last one.
                    print(f"[Bridge] ❌ {model_name} Error: {e}")
                    last_error = e

        # If all failed
        print("[Bridge] 💥 All Gemini models exhausted.")
        raise last_error

    # Support synchronous call just in case (though ADK v2 prefers async)
    def generate_content(self, contents, **kwargs):
        raise NotImplementedError("Use generate_content_async for the Fallback Client")