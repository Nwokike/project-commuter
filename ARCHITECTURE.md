# System Architecture

## Overview
Project Commuter represents a shift from "DOM-based automation" to "Visual-based automation." Instead of relying on fragile CSS selectors that break when LinkedIn updates their UI, we rely on **Visual Set-of-Mark (SOM)** and LLM reasoning.

## The Core Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Brain** | Groq (Llama 3.3 70B) | High-speed reasoning and orchestration. |
| **Vision** | Groq (Llama Vision) | Analyzing screenshots for state detection. |
| **Parser** | Groq (Llama 3.1 8B) | Extracting structured data from PDF CVs. |
| **Hands** | Playwright + Stealth | Undetectable browser interaction. |
| **UI** | FastAPI + WebSockets | Real-time "Neural Feed" streaming. |

## The Visual SOM Protocol

The most critical innovation in Project Commuter is the **Visual SOM Loop**:

1.  **Capture:** The browser takes a raw screenshot.
2.  **Tagging:** An internal algorithm scans the DOM for interactive elements (`<a>`, `<button>`, `<input>`).
3.  **Overlay:** We use `Pillow` to draw **Bounding Boxes** and **Numeric IDs** directly onto the image pixels.
4.  **Reasoning:** The image is sent to the Vision Agent.
    * *Input:* Image with labeled buttons.
    * *Prompt:* "Click the 'Easy Apply' button."
    * *Output:* "Action: click_element(id='12')"
5.  **Execution:** The system maps ID `12` back to the exact X/Y coordinates and performs a human-like click.

## Agent Hierarchy

### 1. Root Orchestrator (`root_agent.py`)
* **Role:** The Boss.
* **Responsibility:** Enforces the "CV First" rule. It will not allow automation to proceed unless a User Profile exists in the session state.

### 2. Scout Agent (`scout_agent.py`)
* **Role:** The Filter.
* **Constraint:** Hardcoded to `site:linkedin.com`. It ignores all other job boards to maintain scope and reliability.

### 3. Ops Agent (`ops_agent.py`)
* **Role:** The Sniper.
* **Specialty:** Trained specifically on the multi-step "Easy Apply" modal. It knows how to handle "Next," "Review," and "Submit" sequences.

## Data Flow
**Privacy First:** All processing happens in memory.
* **Session State:** Your CV data lives in RAM (`InMemorySessionService`).
* **Persistence:** None. If the server restarts, the data is wiped. This is a privacy feature, not a bug.
