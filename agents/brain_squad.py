import json
import os
import sqlite3
from google.adk.agents import Agent
from modules.llm_bridge import GroqModel
from modules.db import get_connection

# Initialize LLM
groq_llm = GroqModel().get_model()

from modules.vector_store import vector_store

# --- Tools ---

def query_answer_bank(question: str) -> str:
    """
    Semantic search for a similar question in the answer bank.
    """
    results = vector_store.query(question, n_results=1)
    if results['documents'] and results['distances'][0][0] < 0.5: # Confidence threshold
        return f"FOUND: {results['documents'][0][0]} (ID: {results['ids'][0][0]})"
    return "NOT_FOUND"

def rag_search(query: str) -> str:
    """
    Semantic search in GitHub summary and CV text via ChromaDB.
    """
    results = vector_store.query(query, n_results=3)
    
    if not results['documents'][0]:
        return "NO_CONTEXT_FOUND"
    
    context = " ".join(results['documents'][0])
    return context

# --- Agents ---

# 8. MemoryAgent
memory_agent = Agent(
    name="memory_agent",
    model=groq_llm,
    description="Check if we have answered this before.",
    instruction="Use `query_answer_bank` to find existing answers.",
    tools=[query_answer_bank]
)

# 9. ContextAgent
context_agent = Agent(
    name="context_agent",
    model=groq_llm,
    description="Derive answers from User's background.",
    instruction="""
    Use `rag_search` to find relevant experience in GitHub/CV. 
    Synthesize an answer based ONLY on that evidence. 
    If unsure, say "UNSURE".
    """,
    tools=[rag_search]
)

# 10. DecisionAgent
decision_agent = Agent(
    name="decision_agent",
    model=groq_llm,
    description="Final arbiter of what to type.",
    instruction="""
    Compare Memory result and Context result.
    1. If Memory found -> Use Memory.
    2. If Context found strong evidence -> Use Context.
    3. Else -> Return "SOS".
    """
)
