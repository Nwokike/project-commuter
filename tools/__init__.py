"""
Project Commuter - Agent Tools
Browser automation, search, and CV parsing tools
"""

from .browser_tools import (
    navigate_to_url,
    click_element,
    type_text,
    take_screenshot,
    get_page_content,
    scroll_page,
)
from .search_tools import (
    search_jobs, 
    search_web, 
    search_company_info, 
    search_job_boards
)

__all__ = [
    "navigate_to_url",
    "click_element", 
    "type_text",
    "take_screenshot",
    "get_page_content",
    "scroll_page",
    "search_jobs",
    "search_web",
    "search_company_info",
    "search_job_boards"
]
