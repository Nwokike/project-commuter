# Project Commuter - AI Job Application Assistant

## Overview
An AI-powered job application automation system built with Google's Agent Development Kit (ADK). The system uses browser automation (Playwright) with AI agents (Groq LLMs) to search and apply for jobs interactively.

**Key Features:**
- **Interactive Agent:** Waits for your commands (not auto-running).
- **Real-time Dashboard:** Streams browser screenshots to a web interface.
- **Intervention Mode:** Allows you to take control when CAPTCHA/login appears.
- **Privacy-Focused:** Uses DuckDuckGo for searches; no API keys required for search.
- **Stateless Design:** No database required; uses ADK session state management (ideal for cloud deployment like Render).
- **Groq-Powered:** Uses fast, efficient Llama models for logic and vision.

## Project Architecture


```

project_commuter/
├── agents/                    # ADK Agents
│   ├── **init**.py

│   ├── root_agent.py         # Main orchestrator (interactive chat)
│   ├── vision_agent.py       # Screenshot analysis, CAPTCHA detection
│   ├── scout_agent.py        # Job searching
│   └── ops_agent.py          # Form filling & applications
├── tools/                     # Agent Tools
│   ├── **init**.py
│   ├── browser_tools.py      # Playwright browser automation
│   └── search_tools.py       # DuckDuckGo job search
├── models/                    # Model Configuration
│   ├── **init**.py
│   └── groq_config.py        # Groq models with fallback chains
├── static/                    # Frontend Dashboard
│   ├── index.html
│   ├── css/styles.css
│   └── js/app.js
├── server.py                  # FastAPI + WebSocket server
├── requirements.txt
└── render.yaml                # Render deployment config

```

## Tech Stack

### Backend
- **Google ADK 1.23.0** - Agent Development Kit for multi-agent orchestration
- **LiteLLM** - Unified API for Groq models
- **FastAPI** - Async web framework with WebSocket support
- **Playwright** - Browser automation (headless)
- **DuckDuckGo Search** - No-API-key job searching

### Frontend
- Vanilla HTML/CSS/JS
- WebSocket for real-time updates
- Interactive screenshot viewer with click-to-control

## How to Use

### 1. Setup & Installation
**Locally:**
```bash
pip install -r requirements.txt
playwright install chromium
python server.py

```

**Environment Variables:**
Create a `.env` file (or set in your cloud provider):

* `GROQ_API_KEY` - Your Groq API key

### 2. Fill Your Profile

Open the dashboard (default: `http://localhost:5000` or your Render URL). Enter your name, email, phone, location, job titles, and skills in the sidebar form. Click "Save Profile".

### 3. Chat with the Agent

Type messages like:

* "Hi, how are you?" (normal conversation)
* "Search for software engineer jobs in San Francisco"
* "Apply to the first job in the list"
* "Navigate to linkedin.com/jobs"

### 4. Intervention Mode

When the agent encounters a login page or CAPTCHA:

* The **INTERVENTION REQUIRED** badge appears.
* A live browser screenshot is displayed.
* **Click on the screenshot** to interact with the browser directly.
* **Type in the text box** to send keystrokes.
* Click **Resume** when finished.

## Session State Management

The app uses ADK's `InMemorySessionService`.

* **User Prefs:** Stored with `user:` prefix.
* **Session Data:** Temporary data (current search results) lives only as long as the server is running.
* **Note for Cloud Hosting:** On free tier hosting (like Render), data resets when the instance spins down.

## Disclaimer

This tool is strictly for educational and research purposes. Please respect the Terms of Service of any platform you interact with. The authors are not responsible for account suspensions or misuse.
