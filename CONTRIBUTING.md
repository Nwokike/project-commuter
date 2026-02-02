# Contributing to Project Commuter

Thank you for your interest

We are building a precision tool. To maintain the quality and reliability of this agent, we enforce strict contribution guidelines.

## 🟢 Philosophy
1.  **LinkedIn Only:** Do not submit PRs adding support for Indeed, Glassdoor, or other sites. We do one thing perfectly.
2.  **Visual First:** Do not write code that relies on complex XPath or CSS selectors. If the AI can't "see" it via Visual SOM, improve the Vision Agent, not the selectors.
3.  **Zero Persistence:** Do not add database dependencies (Postgres, SQLite). The app must remain stateless and cloud-native.

## 🛠️ Development Guidelines

### Pull Requests
* **Descriptive Titles:** Use conventional commits (e.g., `feat: add resume parsing`, `fix: stealth module import`).
* **Test on Render:** Before submitting, ensure your code runs in a stateless environment (no local file writes).

### Style Guide
* **Type Hinting:** All Python functions must be typed.
    ```python
    # Good
    def search(query: str) -> dict: ...
    
    # Bad
    def search(query): ...
    ```
* **Async/Await:** All I/O operations must be non-blocking.

## 🐛 Reporting Bugs
If you find a case where the Visual SOM fails (e.g., clicks the wrong button):
1.  Check the **Neural Feed** logs.
2.  Take a screenshot of the "tagged" image if possible.
3.  Open an issue with the tag `[Vision Failure]`.

Let's build the ultimate autonomous agent. 🎯
