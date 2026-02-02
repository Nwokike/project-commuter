"""
Groq Model Configuration with Intelligent Fallback
Optimized for rate limits and token budgets using the full model arsenal.
"""

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
    "llama-maverick": "groq/meta-llama/llama-4-maverick-17b-128e-instruct",
    
    # Research / Context Heavy
    "kimi-k2": "groq/moonshotai/kimi-k2-instruct",
    "kimi-k2-old": "groq/moonshotai/kimi-k2-instruct-0905",
}

# Configuration of Role-Based Hierarchies
# The agent will attempt to use these in order (conceptual fallback)
GROQ_MODELS = {
    "orchestrator": {
        "primary": MODEL_REGISTRY["llama-70b"],     # Smartest coordinator
        "secondary": MODEL_REGISTRY["gpt-20b"],     # Strong generalist
        "tertiary": MODEL_REGISTRY["gpt-20b-safe"], # Safe backup
        "fallback": MODEL_REGISTRY["llama-8b"],     # Ultimate speed/backup
        "description": "Orchestration and chat interaction"
    },
    "reasoning": {
        "primary": MODEL_REGISTRY["gpt-120b"],      # Deepest thinker for forms
        "secondary": MODEL_REGISTRY["qwen-32b"],    # Strong logic backup
        "tertiary": MODEL_REGISTRY["gpt-20b"],      # Reuse 20B as requested
        "fallback": MODEL_REGISTRY["llama-70b"],    # Very capable fallback
        "description": "Complex reasoning and decision making"
    },
    "vision": {
        "primary": MODEL_REGISTRY["llama-scout"],
        "fallback": MODEL_REGISTRY["llama-maverick"],
        "description": "Screenshot analysis and CAPTCHA detection"
    },
    "research": {
        "primary": MODEL_REGISTRY["kimi-k2"],       # Good with large context
        "secondary": MODEL_REGISTRY["kimi-k2-old"],
        "fallback": MODEL_REGISTRY["llama-70b"],
        "description": "Web search synthesis and research"
    }
}


def get_fast_model() -> LiteLlm:
    """Get the primary model for orchestration (Root Agent)."""
    # Uses Llama 3.3 70B by default for best instruction following
    return LiteLlm(model=GROQ_MODELS["orchestrator"]["primary"])


def get_reasoning_model() -> LiteLlm:
    """Get the primary model for complex tasks (Ops Agent)."""
    # Uses GPT-OSS 120B for deep reasoning on form logic
    return LiteLlm(model=GROQ_MODELS["reasoning"]["primary"])


def get_vision_model() -> LiteLlm:
    """Get the primary vision model (Vision Agent)."""
    return LiteLlm(model=GROQ_MODELS["vision"]["primary"])


def get_research_model() -> LiteLlm:
    """Get the primary research model (Scout Agent)."""
    return LiteLlm(model=GROQ_MODELS["research"]["primary"])
