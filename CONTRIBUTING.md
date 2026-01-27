# Contributing to Project Commuter

First off, thank you for considering contributing to Project Commuter! 🐜

We are building the world's most robust **Local-First Job Agent**. To keep this project accessible and safe for everyone, please follow these guidelines.

## 🛠️ How to Contribute

### 1. Reporting Bugs
If the bot gets stuck on a specific job board layout:
1.  Check the **Neural Feed** in your dashboard.
2.  If the bot triggered an **SOS**, note the `sos_message` (e.g., "Agent stuck. Action: sos. Reason: CAPTCHA detected").
3.  Take a screenshot of the error log or the browser state if visible.
4.  Open an Issue with the tag `[Bug]` and include the SOS reason.

### 2. Suggesting Features
Have an idea for a new "Squad"?
* Open an Issue with the tag `[Feature Request]`.
* Explain *why* this agent is needed (e.g., "Networking Agent to message recruiters").

### 3. Submitting Pull Requests
1.  **Fork** the repo and create your branch from `main`.
2.  **Test** your changes locally.
3.  Ensure you adhere to the **Privacy First** principle (no user data should ever leave the local machine).
4.  Submit your PR!

## 🧪 Development Setup

The project uses a modular "Squad" structure.
* `agents/`: Contains the logic for specific roles.
* `modules/`: Contains shared tools (DB, Browser, LLM Bridge).

**Style Guide**:
* Use `asyncio` for all I/O bound tasks.
* Type hint every function (`def my_func(x: int) -> str:`).
* Keep `main.py` clean; logic belongs in `agents/`.

## 📜 Code of Conduct

* **Be Respectful**: We are all here to learn and build.
* **Be Ethical**: Do not contribute code designed to spam, harass, or maliciously scrape platforms. This project is for personal automation only.
