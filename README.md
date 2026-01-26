# 🐜 Project Commuter

An autonomous, local-first job application agent built with Google ADK, Playwright, and multimodal LLMs. Designed for high fidelity, stealth, and human-in-the-loop reliability.

## 🚀 Key Features

- **Local-First Architecture**: Runs on your residents IP to maximize trust scores and avoid cloud-bot detection.
- **Stealth Browser Engine**: Uses Playwright with biometric typing, bezier-curve mouse movements, and profile cloning to mimic human behavior.
- **Set-of-Mark (SoM) Vision**: Intelligent UI analysis using Gemini Vision to identify interactive elements via visual tags.
- **Semantic Memory**: Persistent SQLite and ChromaDB storage for CV context and previous application answers.
- **Human-in-the-Loop (SOS)**: Automatically pauses and alerts the user via a Streamlit dashboard when encountering complex questions or CAPTCHAs.

## 🛠️ Technology Stack

- **Orchestration**: Google ADK (Agent Development Kit)
- **Intelligence**: Groq (Llama 3.3 70B) & Gemini 2.5 Flash
- **Automation**: Playwright (Stealth Mode)
- **Storage**: SQLite & ChromaDB
- **Interface**: Streamlit

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Nwokike/project-commuter.git
   cd project-commuter
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chrome
   ```

3. **Configure Environment**:
   Create a `.env` file with your API keys:
   ```env
   GROQ_API_KEY=your_groq_key
   GEMINI_API_KEY=your_gemini_key
   ```

## 🚦 Usage

Launch the unified system (Dashboard + Bot):
```bash
python "python launcher.py"
```

The dashboard will be available at `http://localhost:8501`.

## 🏗️ Architecture

Project Commuter uses a "Squad" pattern to separate concerns:
- **Scout Squad**: Finds and parses job listings.
- **Vision Squad**: Analyzes the browser state and executes actions.
- **Brain Squad**: Provides semantic context and decision arbiter.
- **Ops Squad**: Handles SOS triggers and human intervention.

---
*Disclaimer: This tool is for educational purposes. Use responsibly and adhere to job platform terms of service.*