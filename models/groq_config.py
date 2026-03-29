"""
Groq Model Configuration with Intelligent Fallback
Optimized for rate limits and token budgets using the full model arsenal.
"""

import os
from google.adk.models.lite_llm import LiteLlm

# Full definition of available models
MODEL_REGISTRY = {
    # High Intelligence / Orchestration
    "llama-70b": "groq/llama-3.3-70b-versatile",
    "gpt-20b": "groq/openai/gpt-oss-20b",
    "gpt-20b-safe": "groq/openai/gpt-oss-safeguard-20b",
    
    # Fast / Fallback
    "llama-8b": "groq/llama-3.1-8b-instant",
    
    # Deep Reasoning / Complex Forms
    "gpt-120b": "groq/openai/gpt-oss-120b",
    "qwen-32b": "groq/qwen/qwen3-32b",
    
    # Vision
    "llama-scout": "groq/meta-llama/llama-4-scout-17b-16e-instruct",
    
    # Research / Context Heavy
    "kimi-k2": "groq/moonshotai/kimi-k2-instruct",
    "kimi-k2-old": "groq/moonshotai/kimi-k2-instruct-0905",
}

# Configuration of Role-Based Hierarchies
GROQ_MODELS = {
    "orchestrator": {
        "primary": MODEL_REGISTRY["llama-70b"],
        "secondary": MODEL_REGISTRY["gpt-20b"],
        "tertiary": MODEL_REGISTRY["gpt-20b-safe"],
        "fallback": MODEL_REGISTRY["llama-8b"],
        "description": "Orchestration and chat interaction"
    },
    "reasoning": {
        "primary": MODEL_REGISTRY["gpt-120b"],
        "secondary": MODEL_REGISTRY["qwen-32b"],
        "tertiary": MODEL_REGISTRY["gpt-20b"],
        "fallback": MODEL_REGISTRY["llama-70b"],
        "description": "Complex reasoning and decision making"
    },
    "vision": {
        "primary": MODEL_REGISTRY["llama-scout"],
        "description": "Screenshot analysis and CAPTCHA detection"
    },
    "research": {
        "primary": MODEL_REGISTRY["kimi-k2"],
        "secondary": MODEL_REGISTRY["kimi-k2-old"],
        "fallback": MODEL_REGISTRY["llama-70b"],
        "description": "Web search synthesis and research"
    },
    "parser": {
        "primary": MODEL_REGISTRY["llama-8b"], # Fast 8B for parsing CVs
        "description": "Data extraction from text"
    }
}


def get_fast_model() -> LiteLlm:
    """Get the primary model for orchestration (Root Agent)."""
    return LiteLlm(
        model=GROQ_MODELS["orchestrator"]["primary"],
        api_key=os.getenv("GROQ_API_KEY"),
        fallbacks=[
            GROQ_MODELS["orchestrator"]["secondary"],
            GROQ_MODELS["orchestrator"]["tertiary"],
            GROQ_MODELS["orchestrator"]["fallback"]
        ]
    )

def get_reasoning_model() -> LiteLlm:
    """Get the primary model for complex tasks (Ops Agent)."""
    return LiteLlm(
        model=GROQ_MODELS["reasoning"]["primary"],
        api_key=os.getenv("GROQ_API_KEY"),
        fallbacks=[
            GROQ_MODELS["reasoning"]["secondary"],
            GROQ_MODELS["reasoning"]["tertiary"],
            GROQ_MODELS["reasoning"]["fallback"]
        ]
    )

def get_vision_model() -> LiteLlm:
    """Get the primary vision model (Vision Agent)."""
    return LiteLlm(
        model=GROQ_MODELS["vision"]["primary"],
        api_key=os.getenv("GROQ_API_KEY")
    )

def get_research_model() -> LiteLlm:
    """Get the primary research model (Scout Agent)."""
    return LiteLlm(
        model=GROQ_MODELS["research"]["primary"],
        api_key=os.getenv("GROQ_API_KEY"),
        fallbacks=[
            GROQ_MODELS["research"]["secondary"],
            GROQ_MODELS["research"]["fallback"]
        ]
    )

def get_parser_model() -> LiteLlm:
    """Get the fast model for CV parsing."""
    return LiteLlm(
        model=GROQ_MODELS["parser"]["primary"],
        api_key=os.getenv("GROQ_API_KEY")
    )
