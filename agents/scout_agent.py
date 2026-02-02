"""
Scout Agent - LinkedIn Specialist
STRICTLY confined to searching LinkedIn for jobs.
"""

from google.adk.agents import LlmAgent
from models.groq_config import get_research_model
from tools.search_tools import search_jobs

# Custom wrapper to FORCE LinkedIn searches
def search_linkedin_jobs(query: str, location: str = "") -> dict:
    """
    Search strictly for LinkedIn job postings.
    The agent cannot override the site filter.
    """
    # Force the query to look only at LinkedIn
    refined_query = f"site:linkedin.com/jobs {query} {location}"
    return search_jobs(query=refined_query, max_results=8)


SCOUT_INSTRUCTION = """You are a LinkedIn Search Specialist.

Your ONLY purpose is to find job listings on LinkedIn using the `search_linkedin_jobs` tool.

### Rules:
1. **LinkedIn Only**: Do not search Indeed, Glassdoor, or company websites.
2. **Search Query**: When the user asks for "Python jobs", you must search for "Python". The tool automatically adds "site:linkedin.com".
3. **Output**: Present the found jobs clearly with their Titles and URLs.

If the user asks for anything unrelated to LinkedIn jobs, politely decline."""

scout_agent = LlmAgent(
    model=get_research_model(),
    name="scout_agent", 
    description="Searches for jobs strictly on LinkedIn.",
    instruction=SCOUT_INSTRUCTION,
    tools=[search_linkedin_jobs],
)
