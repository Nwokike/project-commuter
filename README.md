# Project Commuter: The "Easy-Apply" Local Job Agent

**Context:** Local Host, SQLite, Google ADK (with Groq API & Gemini API)

**Objective:** An undetectable, autonomous job application agent that runs locally, learns from user input, and never fails.

## 1. Core Philosophy: "The Commuter"

Unlike cloud bots that get banned for using datacenter IPs (AWS/Azure), **The Commuter** behaves like a background service on your local machine (like Dropbox or Spotify).

* **Host:** Local PC.
* **Network:** Residential Wi-Fi (Trust Score: 100/100).
* **Availability:** Runs only during human hours (e.g., 9 AM - 5 PM).
* **Persistence:** SQLite (Local file). No cloud database costs or latency.
* **Interface:** A "Fast ADK Web" Dashboard for monitoring and "SOS" interventions.

## 2. The Infrastructure Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Orchestrator** | **Google ADK** | Manages the agent hierarchy and state. |
| **Brain** | **Gemini 2.5 Flash** | The intelligence engine. |
| **Eyes & Hands** | **Playwright (Python)** | Browser automation (Stealth Mode enabled). |
| **Memory** | **SQLite** | A single file (`bot_memory.db`) storing jobs and answers. |
| **UI** | **Streamlit** | Local web dashboard running on `http://localhost:8501`. |

## 3. The "Ant Army" Agent Roster (Strict ADK Compliance)

**Rule:** Every agent has **exactly one** primary responsibility and tool type.

* **Type A:** Uses Inbuilt Tools (Search/Code) - *Cannot use Custom Tools*.
* **Type B:** Uses Custom Tools - *Cannot use Inbuilt Tools*.
* **Type C:** Pure Model (Reasoning/Vision) - *No Tools*.

### **Agent 0: The Orchestrator (Type C - Pure)**
* **Role:** The Manager.
* **Tool:** None.
* **Function:** receives the high-level goal ("Apply to Django jobs in EMEA") and delegates to sub-agents via structured prompting. It maintains the "Session State".

### **Agent 1: The Researcher (Type A - Inbuilt)**
* **Role:** Legitimacy Checker.
* **Tool:** `Google Search` (Inbuilt).
* **Task:** If a company name looks suspicious, this agent Googles it.
    * *Input:* "Verify company 'TechCorp123'".
    * *Output:* "Legit" or "Scam".

### **Agent 2: The Scout (Type B - Custom)**
* **Role:** The Fetcher.
* **Tool:** `fetch_job_feed(query, location)`
* **Task:** Navigate to LinkedIn Search, scroll safely, and return a raw list of Job URLs. It does *not* analyze them.

### **Agent 3: The Gatekeeper (Type B - Custom)**
* **Role:** The Deduplicator.
* **Tool:** `check_db_duplicates(job_url_list)`
* **Task:** Checks `bot_memory.db`. Returns only the URLs that have *not* been applied to yet.

### **Agent 4: The Navigator (Type B - Custom)**
* **Role:** The Driver.
* **Tool:** `browser_control(action, selector, value)`
* **Task:** Executes physical actions in the browser.
    * Actions: `goto`, `click`, `type`, `scroll`, `upload_file`.
    * *Stealth Logic:* Moves mouse in Bezier curves, not straight lines.

### **Agent 5: The Photographer (Type B - Custom)**
* **Role:** The Eye.
* **Tool:** `capture_screenshot()`
* **Task:** Takes a screenshot of the current browser viewport and returns the binary image data.

### **Agent 6: The Visionary (Type C - Pure Model)**
* **Role:** The Analyst.
* **Tool:** None (Uses Native Multimodal Vision).
* **Task:** Accepts the Screenshot from Agent 5.
    * *Prompt:* "Analyze this form. Return the X,Y coordinates of the 'Next' button, or extract the question text if it's a form."
    * *Output:* JSON `{ "action": "click", "coordinates": [400, 500] }` OR `{ "status": "question", "text": "How many years of Python?" }`.

### **Agent 7: The Archivist (Type B - Custom)**
* **Role:** The Librarian.
* **Tool:** `query_answer_bank(question_text)`
* **Task:** Queries SQLite for a matching answer.
    * *Logic:* Fuzzy matching (Levenshtein distance) to find similar past questions.

### **Agent 8: The Liaison (Type B - Custom)**
* **Role:** The SOS Signaler.
* **Tool:** `trigger_dashboard_alert(screenshot, question_text)`
* **Task:** Updates the Streamlit Dashboard state to "PAUSED" and waits for human input.

## 4. The Database Schema (SQLite)

File: `bot_memory.db`

```sql
-- Table 1: Track applied jobs to prevent duplicates
CREATE TABLE applied_jobs (
    job_hash TEXT PRIMARY KEY,   -- MD5 of the Job URL
    job_url TEXT,
    company_name TEXT,
    status TEXT,                 -- 'APPLIED', 'FAILED', 'IGNORED'
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table 2: The Brain (Learns your answers)
CREATE TABLE answer_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_pattern TEXT,       -- e.g., "%years%experience%python%"
    answer_text TEXT,            -- e.g., "5"
    last_used DATETIME
);

-- Table 3: Session Config
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);
-- Insert Default: resume_path = "C:/Users/AntiGravity/CV.pdf"

```

## 5. The "Full Proof" Workflow (State Machine)

**State 1: Initialization**

* User opens Dashboard -> Clicks "Start".
* **Orchestrator** wakes up.

**State 2: Scouting**

* **Scout** runs `fetch_job_feed("Python", "London")`. Returns 10 URLs.
* **Gatekeeper** checks DB. 3 are duplicates. 7 remain.

**State 3: The Application Loop (For Each Job)**

1. **Navigator** goes to Job URL.
2. **Photographer** takes Screenshot.
3. **Visionary** analyzes Screenshot.
* *If "Easy Apply" button:* -> **Navigator** clicks it.
* *If Form Field:* -> Extract Question ("Do you have a Visa?").


4. **Archivist** checks DB for "Visa".
* *Match Found:* -> **Navigator** types "Yes".
* *No Match:* -> **GOTO STATE 4 (SOS).**


5. **Visionary** checks for "Submit" or errors.
6. **Scribe** updates DB (`status='APPLIED'`).

**State 4: The SOS Protocol (Human-in-the-Loop)**

* **Liaison** pauses the loop.
* **Dashboard** flashes RED.
* **UI shows:** The Screenshot + The Question.
* **User Action:** You type "Yes" in the dashboard.
* **System Action:**
1. **Archivist** saves ("Do you have a Visa?" = "Yes") to DB.
2. **Navigator** types "Yes".
3. Loop Resumes.



## 6. Implementation Guide

### **Folder Structure**

```text
/project_commuter
│
├── /agents               # strict_adk_agents
│   ├── orchestrator.py
│   ├── researcher.py
│   ├── scout.py
│   ├── navigator.py
│   └── ... (one file per agent)
│
├── /tools                # Custom Tool Definitions
│   ├── browser_tools.py  # Playwright logic
│   ├── db_tools.py       # SQLite logic
│   └── ui_tools.py       # Streamlit interaction
│
├── /interface
│   └── dashboard.py      # Streamlit App (The UI)
│
├── bot_memory.db         # Created automatically
├── main.py               # Entry point
└── requirements.txt      # playwright, streamlit, google-generativeai

```

### **Critical Code Snippets (Logic Only)**

**1. The Stealth Browser Launch (tools/browser_tools.py)**
*Must use specific flags to avoid detection.*

```python
async def launch_stealth_browser():
    async with async_playwright() as p:
        # Use local Chrome profile to keep cookies/session logged in
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="C:/Users/User/AppData/Local/Google/Chrome/User Data",
            channel="chrome",
            headless=False,  # Visible for safety, can be hidden later
            args=["--disable-blink-features=AutomationControlled"]
        )
        return browser

```

**2. The SOS Trigger (interface/dashboard.py)**
*This runs in a separate thread/process to the bot.*

```python
# Streamlit Logic
if st.session_state.get('sos_active'):
    st.error("⚠️ BOT NEEDS HELP")
    st.image(st.session_state['screenshot'])
    st.write(f"Question: {st.session_state['current_question']}")
    
    user_answer = st.text_input("Your Answer:")
    if st.button("Resume Bot"):
        save_to_db(st.session_state['current_question'], user_answer)
        st.session_state['sos_active'] = False
        release_bot_lock()

```

### **Execution Checklist**

1. **Day 1:** Set up `bot_memory.db` and the basic Streamlit UI. Verify Playwright can open LinkedIn with your existing cookies (no login required).
2. **Day 2:** Build the **Scout** and **Gatekeeper**. Ensure it can find jobs and ignore duplicates.
3. **Day 3:** Implement the **Visionary** + **SOS Protocol**. Run it on 5 jobs. Train the database with your answers.