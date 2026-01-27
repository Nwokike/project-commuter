<div align="center">

# 🐜 Project Commuter
### The Local-First Autonomous Job Agent
**Stop Applying. Start Interviewing.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-BSD_3--Clause-green.svg)](LICENSE)
[![Powered By](https://img.shields.io/badge/AI-Groq_%7C_Gemini-purple)](https://groq.com)
[![Stealth](https://img.shields.io/badge/Stealth-Playwright-orange)](https://playwright.dev)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Features](#-key-features) • [Installation](#-quick-start) • [Architecture](#-architecture) • [Dashboard](#-mission-control)

</div>

---

## 🚀 What is Project Commuter?

**Project Commuter** is an intelligent, autonomous agent that navigates the modern job market for you. Unlike cloud-based "spam bots" that get banned instantly, Commuter runs **locally on your machine**, using your own browser profile to apply for jobs with human-like precision.

It employs a **"Squad" of AI Agents**—powered by **Llama 4 Scout (via Groq)** and **Gemini 2.5 Flash**—to find listings, analyze UI visual states, solve navigation challenges, and tailor your CV to every single application.

> **"It doesn't just click buttons. It sees the screen, thinks about the form, and types like a human."**

## ✨ Key Features (SEO Optimized)

* **🕵️‍♂️ True Stealth Mode**: Uses **Playwright Stealth** with biometric typing patterns (variable latency, micro-hesitations) and Bezier-curve mouse movements to bypass anti-bot detection.
* **👁️ Multimodal Vision (SoM)**: Integrates **Gemini Vision** with "Set-of-Mark" tagging to visually understand web pages, effectively solving "dynamic UI" problems that break traditional scrapers.
* **🧠 Local RAG Brain**: Stores your CV and GitHub history in **SQLite/ChromaDB**. It doesn't hallucinate skills; it cites your actual experience when answering application questions.
* **🛡️ Cost-Optimized Swarm**: Implements a "Waterfall" model strategy (Flash → Flash Lite → Llama 4) to run 24/7 purely on **Free Tier** API limits (20 RPD / 500k TPD).
* **📡 Neural Feed Dashboard**: A **Streamlit** command center that visualizes the agent's internal monologue and decision-making process in real-time.
* **🆘 Human-in-the-Loop**: The **SOS Protocol** detects CAPTCHAs or complex logic hurdles and pauses for your input, ensuring 0% account ban rate.

## 🛠️ The Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Orchestration** | **Google ADK** (Agent Dev Kit) | Managing the agent state machine |
| **Logic Engine** | **Groq** (Llama 3.1 8B / 4 Scout) | Complex reasoning & JSON parsing |
| **Vision Engine** | **Gemini 2.5 Flash** | UI Analysis & Screenshot processing |
| **Automation** | **Playwright** (Async) | Browser control & fingerprint spoofing |
| **Memory** | **SQLite** | Local storage for CV & past answers |
| **UI** | **Streamlit** | Mission Control Dashboard |

## ⚡ Quick Start

### Prerequisites
* Python 3.10+
* Google Chrome installed
* API Keys for **Groq** and **Google Gemini**

### Installation

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/Nwokike/project-commuter.git](https://github.com/Nwokike/project-commuter.git)
    cd project-commuter
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    playwright install chrome
    ```

3.  **Configure Environment**
    Create a `.env` file in the root directory:
    ```env
    GROQ_API_KEY=gsk_...
    GEMINI_API_KEY=AIza...
    ```

4.  **Launch the System**
    ```bash
    python "python launcher.py"
    ```

## 🎮 Mission Control

Once launched, the bot will automatically open the dashboard in your browser (`http://localhost:8501`).

* **Step 1:** Go to the **Mission Control** tab.
* **Step 2:** Upload your **CV (PDF)**.
* **Step 3:** Enter your target **Job Title** (e.g., "Remote Python Engineer").
* **Step 4:** Click **"Save Configuration & Open Gate"**.

The bot will then initiate the **Scout Squad** to find jobs and the **Navigator Squad** to apply.

## 🏗️ Architecture

Project Commuter isn't a script; it's a **Multi-Agent System**.
See [ARCHITECTURE.md](ARCHITECTURE.md) for a deep dive into the **Scout**, **Vision**, **Brain**, and **Ops** squads.

## 🤝 Contributing

We are building the future of autonomous personal agents. Whether you're a prompt engineer, a Python wizard, or a UI designer, we want your help!
See [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

## ⚠️ Disclaimer

*This tool is strictly for educational and research purposes. Please respect the Terms of Service of any platform you interact with. The authors are not responsible for account suspensions or misuse.*

---
<div align="center">
    <b>Star this repo 🌟 if you want to hire an AI to get hired!</b>
</div>