# 🐜 Project Commuter v2.0: The Robust Job Agent

Project Commuter is an autonomous, local-first job application agent. Version 2.0 introduces high-fidelity vision and semantic reasoning to ensure 100% reliability and undetectable operation.

## 🚀 Key Features v2.0

- **Set-of-Mark (SoM) Vision**: Eliminates selector brittleness by visually tagging page elements.
- **Semantic Brain (RAG)**: Uses **ChromaDB** for vector-based semantic search across your CV and GitHub context.
- **State Machine Orchestrator**: A robust, exception-resilient core that persists progress.
- **Dynamic Stealth**: Sophisticated fingerprinting that mirrors your exact hardware and software stack.
- **Async-First**: Built on Google ADK's async runner for maximum responsiveness.

## 🛠 Tech Stack

- **Runtime**: Python 3.13
- **Orchestration**: Google Agent Development Kit (ADK)
- **Intelligence**: Groq (Llama 3.3) & Gemini 3 Flash
- **Vector Store**: ChromaDB
- **Browser**: Playwright Stealth + Advanced Spoofing
- **Dashboard**: Streamlit

## 📋 Prerequisites

1.  **Python 3.13+**
2.  **API Keys**:
    - [Groq API Key](https://console.groq.com/)
    - [Google AI Studio (Gemini) API Key](https://aistudio.google.com/)
3.  **Chrome Browser**: Installed locally.

## ⚙️ Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configuration**:
    Ensure your `.env` has `GROQ_API_KEY` and `GEMINI_API_KEY`.

3.  **Seed the Brain**:
    Add your CV (PDF/Text) and GitHub summary to the `data/` directory.

## 🚀 Running

Start the Dashboard (Flight Deck):
```bash
streamlit run dashboard.py
```

Start the Agent (Orchestrator):
```bash
python main.py
```

## ⚖️ Disclaimer
This project is for educational purposes. Use at your own risk.
