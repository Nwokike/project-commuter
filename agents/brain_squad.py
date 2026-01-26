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
    Using a strict distance threshold (0.4) for reliability.
    """
    results = vector_store.query(question, n_results=1)
    # distance < 0.4 means high similarity
    if results['documents'] and results['distances'][0][0] < 0.4: 
        answer = results['documents'][0][0]
        id_ = results['ids'][0][0]
        print(f"[Brain] 🧠 Found answer in bank: {answer}")
        return f"FOUND: {answer} (ID: {id_})"
    
    # Optional: Log the miss for human review or future learning
    print(f"[Brain] ❓ No clear match in answer bank for: {question}")
    return "NOT_FOUND"

def rag_search(query: str) -> str:
    """
    Semantic search in GitHub summary and CV text via ChromaDB.
    Ensures context is truncated to fit within model context windows.
    """
    results = vector_store.query(query, n_results=5) # Get more chunks for better coverage
    
    if not results['documents'] or not results['documents'][0]:
        return "NO_CONTEXT_FOUND"
    
    # Join documents and truncate to ~3000 chars to be safe with Llama-3 70b limits
    full_context = "\n---\n".join(results['documents'][0])
    truncated_context = full_context[:3000]
    
    if len(full_context) > 3000:
        truncated_context += "\n[...Context Truncated...]"
        
    return truncated_context

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
