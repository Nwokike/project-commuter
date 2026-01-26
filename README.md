# 🐜 Project Commuter: The Undetectable Job Agent

Project Commuter is an autonomous, local-first job application agent designed to run on your own hardware using your actual browser session. Unlike cloud-based bots, Commuter utilizes your residential IP and existing Chrome profile to blend in with human behavior.

## 🚀 Key Features

- **Local-First Stealth**: Binds to your local Chrome profile (cookies, history, logins).
- **1-Agent-1-Tool Architecture**: Built with Google ADK for modularity and high-fidelity control.
- **Zero Hallucination Mandate**: Uses a 3-level waterfall logic (Memory -> Context RAG -> Human SOS) to ensure 0% hallucination.
- **Multimodal Vision**: Uses Gemini 3 Flash to "see" and interact with forms rather than relying on brittle DOM parsers.
- **Hybrid Intelligence**: Groq (Llama 3.3) for fast text logic and Gemini for vision tasks.
- **Human-in-the-Loop**: Seamless SOS notifications to your mobile (Pushover/Telegram) when the bot needs help with a unique question.

## 🛠 Tech Stack

- **Runtime**: Python 3.13
- **Orchestration**: Google Agent Development Kit (ADK)
- **Intelligence**: LiteLLM (Groq) & `google-genai` (Gemini)
- **Browser**: Playwright Stealth
- **Database**: SQLite (Local Memory)
- **Dashboard**: Streamlit

## 📋 Prerequisites

1.  **Python 3.13+**
2.  **API Keys**:
    - [Groq API Key](https://console.groq.com/)
    - [Google AI Studio (Gemini) API Key](https://aistudio.google.com/)
    - [Pushover](https://pushover.net/) (Optional, for mobile alerts)
3.  **Chrome Browser**: Installed on the host machine.

## ⚙️ Setup

1.  **Clone & Install**:
    ```bash
    git clone https://github.com/yourusername/project_commuter.git
    cd project_commuter
    pip install -r requirements.txt
    ```

2.  **Configuration**:
    Create a `.env` file in the root directory:
    ```env
    GROQ_API_KEY=your_groq_key
    GEMINI_API_KEY=your_gemini_key
    # Optionally:
    PUSHOVER_USER_KEY=...
    PUSHOVER_API_TOKEN=...
    ```

3.  **Close Chrome**: Ensure all your actual Chrome windows are closed before starting.

## 🚀 Running

Start the Flight Deck (Dashboard):
```bash
streamlit run dashboard.py
```

Start the Agent Swarm (Orchestrator):
```bash
python main.py
```

## ⚖️ Disclaimer

**Automating job applications violates the Terms of Service of platforms like LinkedIn and Indeed.** Use of this software carries a risk of account restriction or permanent ban. This project is for educational and research purposes only. The authors take no responsibility for any consequences of its use.

.
