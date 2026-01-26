import json
import os
import sqlite3
from google.adk.agents import Agent
from modules.llm_bridge import GroqModel
from modules.db import get_connection

# Initialize LLM
groq_llm = GroqModel().get_model()

# --- Tools ---

def query_answer_bank(question: str) -> str:
    """
    Fuzzy searches the SQLite answer bank for a similar question.
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Simple likeness check for now. In production, use vector embeddings (optional upgrade).
    cursor.execute("SELECT answer_text, source FROM answer_bank WHERE question_text LIKE ?", (f"%{question}%",))
    row = cursor.fetchone()
    conn.close()
    if row:
        return f"FOUND: {row[0]} (Source: {row[1]})"
    return "NOT_FOUND"

def rag_search(query: str) -> str:
    """
    Searches GitHub summary and CV text for keywords.
    """
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    
    # Github
    gh_path = os.path.join(data_dir, "github_summary.json")
    gh_context = ""
    if os.path.exists(gh_path):
        with open(gh_path, "r") as f:
            repos = json.load(f)
            # Naive text match
            for r in repos:
                if query.lower() in str(r).lower():
                    gh_context += f"Repo: {r['name']} ({r['language']}). "
    
    # CV
    # Assuming CV text is just ingested on fly or stored. Let's assume we read the raw PDF if needed 
    # or we should have saved the text. For now, we'll suggest looking at the file.
    # In a full RAG, we'd have a vector store.
    
    if not gh_context:
        return "NO_CONTEXT_FOUND"
    return gh_context

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
