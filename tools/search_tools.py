"""
Job Search Tools using DuckDuckGo
No API keys required - privacy-focused search
"""

from duckduckgo_search import DDGS
from typing import Optional


def search_jobs(
    query: str,
    location: str = "",
    max_results: int = 10
) -> dict:
    """
    Search for jobs using DuckDuckGo.
    
    Args:
        query: Job search query (e.g., "software engineer python")
        location: Location to search in (e.g., "San Francisco, CA")
        max_results: Maximum number of results to return
        
    Returns:
        dict with job search results
    """
    try:
        search_query = f"{query} jobs"
        if location:
            search_query += f" {location}"
        
        with DDGS() as ddgs:
            results = []
            for result in ddgs.text(search_query, max_results=max_results):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "description": result.get("body", ""),
                    "source": "DuckDuckGo"
                })
            
            return {
                "status": "success",
                "query": search_query,
                "results": results,
                "count": len(results)
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "results": []
        }


def search_company_info(company_name: str) -> dict:
    """
    Search for information about a company.
    
    Args:
        company_name: Name of the company to research
        
    Returns:
        dict with company information
    """
    try:
        with DDGS() as ddgs:
            results = []
            for result in ddgs.text(f"{company_name} company about careers", max_results=5):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "description": result.get("body", "")
                })
            
            return {
                "status": "success",
                "company": company_name,
                "info": results
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def search_job_boards(job_title: str, location: str = "") -> dict:
    """
    Search major job boards for a specific role.
    
    Args:
        job_title: The job title to search for
        location: Location preference
        
    Returns:
        dict with job board URLs
    """
    job_boards = [
        {"name": "LinkedIn", "url": f"https://www.linkedin.com/jobs/search/?keywords={job_title.replace(' ', '%20')}&location={location.replace(' ', '%20')}"},
        {"name": "Indeed", "url": f"https://www.indeed.com/jobs?q={job_title.replace(' ', '+')}&l={location.replace(' ', '+')}"},
        {"name": "Glassdoor", "url": f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={job_title.replace(' ', '%20')}&locT=C&locKeyword={location.replace(' ', '%20')}"},
    ]
    
    return {
        "status": "success",
        "job_title": job_title,
        "location": location,
        "job_boards": job_boards
    }
