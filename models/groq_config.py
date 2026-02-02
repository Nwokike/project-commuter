"""
Groq Model Configuration with Intelligent Fallback
Optimized for rate limits and token budgets
"""

import os
from google.adk.models.lite_llm import LiteLlm

GROQ_MODELS = {
    "fast": {
        "primary": "groq/llama-3.1-8b-instant",
        "fallback": "groq/llama3-8b-8192",
        "tpd_limit": 500_000,
        "description": "Fast text tasks, orchestration"
    },
    "reasoning": {
        "primary": "groq/qwen-qwq-32b", 
        "fallback": "groq/llama-3.3-70b-versatile",
        "tpd_limit": 500_000,
        "description": "Complex reasoning tasks"
    },
    "vision": {
        "primary": "groq/meta-llama/llama-4-scout-17b-16e-instruct",
        "fallback": "groq/meta-llama/llama-4-maverick-17b-128e-instruct",
        "tpd_limit": 500_000,
        "description": "Screenshot analysis, CAPTCHA detection"
    }
}


def get_fast_model() -> LiteLlm:
    """Get fast model for quick text tasks and orchestration."""
    return LiteLlm(model=GROQ_MODELS["fast"]["primary"])


def get_vision_model() -> LiteLlm:
    """Get vision-capable model for screenshot analysis."""
    return LiteLlm(model=GROQ_MODELS["vision"]["primary"])


def get_reasoning_model() -> LiteLlm:
    """Get reasoning model for complex decision making."""
    return LiteLlm(model=GROQ_MODELS["reasoning"]["primary"])
