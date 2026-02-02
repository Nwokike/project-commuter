# Project Commuter - AI Job Application Assistant

## Overview
An AI-powered job application automation system built with Google's Agent Development Kit (ADK). The system uses browser automation (Playwright) with AI agents (Groq LLMs) to search and apply for jobs interactively.

**Key Features:**
- Interactive agent that waits for your commands (not auto-running)
- Real-time browser screenshots streamed to dashboard
- Intervention Mode: Take control when CAPTCHA/login appears
- Groq models with smart fallback (no Gemini dependency)
- DuckDuckGo for privacy-focused job searching
- No database - uses ADK session state management

## Project Architecture

```
project_commuter/
├── agents/                    # ADK Agents
│   ├── __init__.py           
│   ├── root_agent.py         # Main orchestrator (interactive chat)
│   ├── vision_agent.py       # Screenshot analysis, CAPTCHA detection
│   ├── scout_agent.py        # Job searching
│   └── ops_agent.py          # Form filling & applications
├── tools/                     # Agent Tools
│   ├── __init__.py
│   ├── browser_tools.py      # Playwright browser automation
│   └── search_tools.py       # DuckDuckGo job search
├── models/                    # Model Configuration
│   ├── __init__.py
│   └── groq_config.py        # Groq models with fallback chains
├── static/                    # Frontend Dashboard
│   ├── index.html
│   ├── css/styles.css
│   └── js/app.js
├── server.py                  # FastAPI + WebSocket server
├── requirements.txt
└── replit.md
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

### AI Models (Groq)
| Model | Use Case | Rate Limit |
|-------|----------|------------|
| llama-3.1-8b-instant | Fast tasks, orchestration | 500K TPD |
| llama-4-scout-17b | Vision/screenshot analysis | 500K TPD |
| qwen-qwq-32b | Complex reasoning | 500K TPD |
| llama-4-maverick-17b | Vision fallback | 500K TPD |

## How to Use

### 1. Fill Your Profile
Enter your name, email, phone, location, job titles, and skills in the sidebar form. Click "Save Profile".

### 2. Chat with the Agent
Type messages like:
- "Hi, how are you?" (normal conversation)
- "Search for software engineer jobs in San Francisco"
- "Apply to the first job in the list"
- "Navigate to linkedin.com/jobs"

### 3. Intervention Mode
When the agent encounters a login page or CAPTCHA:
- The **INTERVENTION REQUIRED** badge appears
- Live browser screenshot is displayed
- **Click on the screenshot** to click in the browser
- **Type in the text box** to send keystrokes
- Click **Resume** when finished

## Session State Management

Uses ADK's InMemorySessionService with prefixes:
- `user:` - User preferences (persists across sessions)
- `temp:` - Temporary data (current invocation only)
- No prefix - Session-scoped data

No SQLite database is used.

## Environment Variables

Required secrets in Replit:
- `GROQ_API_KEY` - Your Groq API key

Optional (fallback):
- `GEMINI_API_KEY` - Gemini API key (emergency fallback only)

## Recent Changes

**February 2, 2026 - Complete Rebuild**
- Migrated to proper ADK project structure
- Replaced SQLite with session state management
- Added Intervention Mode for CAPTCHA/login handling
- Built new dashboard with real-time WebSocket updates
- Implemented Groq-only model chain (no Gemini dependency)
- Made agent fully interactive (no auto-polling)

## Running the Project

The server runs on port 5000:
```bash
python server.py
```

Dashboard accessible at: http://0.0.0.0:5000
