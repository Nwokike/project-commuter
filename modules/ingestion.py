import json
import pdfplumber
import requests
import os

def ingest_cv(pdf_path):
    """
    Parses a PDF CV and returns the full text.
    """
    if not os.path.exists(pdf_path):
        print(f"[Ingestion] Warning: CV not found at {pdf_path}")
        return ""
    
    print(f"[Ingestion] Parsing CV: {pdf_path}")
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"[Ingestion] Error parsing CV: {e}")
    return text.strip()

def ingest_github(username):
    """
    Fetches non-forked, >0 star repositories for a GitHub user.
    """
    print(f"[Ingestion] Fetching GitHub for: {username}")
    url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100"
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"[Ingestion] GitHub API Error: {resp.status_code}")
            return []
        
        repos = resp.json()
        summary = []
        for repo in repos:
            if not repo.get("fork") and repo.get("stargazers_count", 0) > 0:
                summary.append({
                    "name": repo["name"],
                    "description": repo["description"],
                    "language": repo["language"],
                    "topics": repo.get("topics", []),
                    "html_url": repo["html_url"]
                })
        
        # Save to JSON
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "github_summary.json")
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
            
        return summary
    except Exception as e:
        print(f"[Ingestion] Error fetching GitHub: {e}")
        return []
