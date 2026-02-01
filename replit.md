# Project Commuter

## Overview
Project Commuter is an AI-powered job application automation system. It uses browser automation (Playwright) combined with AI agents (Google ADK) to help automate job searching and applications.

## Architecture
- **Backend**: FastAPI (Python) serving on port 5000
- **Frontend**: Static HTML/CSS/JS dashboard served by FastAPI
- **Database**: SQLite (stored in `data/bot_memory.db`)
- **Browser Automation**: Playwright with stealth mode (headless on Replit)
- **AI Framework**: Google ADK (Agent Development Kit)

## Project Structure
```
├── api_server.py       # FastAPI server - main entry point
├── main.py             # Bot orchestration logic
├── launcher.py         # Simple launcher script
├── agents/             # AI agent definitions
│   ├── orchestrator.py # Main orchestrator agent
│   ├── brain_squad.py  # Brain/reasoning agents
│   ├── ops_squad.py    # Operations agents
│   ├── scout_squad.py  # Job scouting agents
│   └── vision_squad.py # Visual analysis agents
├── modules/            # Core modules
│   ├── db.py           # SQLite database operations
│   ├── stealth_browser.py # Playwright browser wrapper
│   ├── llm_bridge.py   # LLM integration
│   ├── ingestion.py    # Data ingestion
│   ├── vector_store.py # Vector storage
│   └── scripts/        # Browser injection scripts
└── static/             # Frontend files
    ├── index.html
    ├── css/styles.css
    └── js/app.js
```

## Running the Application
The application runs via `python api_server.py` which:
1. Starts FastAPI server on port 5000
2. Spawns the bot orchestrator as a background task
3. Serves the dashboard at `/`

## Key Features
- CV/Resume upload and parsing
- Job search automation
- WebSocket-based real-time feed
- Visual cortex for browser screenshots
- Agent thought logging

## Environment
- Python 3.11
- Playwright (Chromium, headless mode on Replit)
- FastAPI + Uvicorn

## Notes
- Browser runs in headless mode on Replit
- Database stored in `data/` directory
- Screenshots stored as `latest_view.png`
