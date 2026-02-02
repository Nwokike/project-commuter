"""
Browser Automation Tools using Playwright
Includes screenshot streaming and intervention mode support
"""

import asyncio
import base64
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None
_page: Optional[Page] = None
_intervention_mode: bool = False
_screenshot_callback = None


async def get_browser() -> Browser:
    """Get or create browser instance."""
    global _browser
    if _browser is None or not _browser.is_connected():
        playwright = await async_playwright().start()
        _browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
    return _browser


async def get_page() -> Page:
    """Get or create page instance with stealth settings."""
    global _context, _page
    browser = await get_browser()
    
    if _context is None:
        _context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
    
    if _page is None or _page.is_closed():
        _page = await _context.new_page()
        await _page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
    
    return _page


def set_screenshot_callback(callback):
    """Set callback for streaming screenshots to dashboard."""
    global _screenshot_callback
    _screenshot_callback = callback


def is_intervention_mode() -> bool:
    """Check if intervention mode is active."""
    return _intervention_mode


def set_intervention_mode(active: bool):
    """Enable or disable intervention mode."""
    global _intervention_mode
    _intervention_mode = active


async def navigate_to_url(url: str) -> dict:
    """
    Navigate browser to a URL.
    
    Args:
        url: The URL to navigate to
        
    Returns:
        dict with status and current URL
    """
    try:
        page = await get_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(1)
        
        screenshot = await take_screenshot()
        
        return {
            "status": "success",
            "url": page.url,
            "title": await page.title(),
            "screenshot": screenshot.get("screenshot_base64", "")
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def click_element(selector: Optional[str] = None, x: Optional[int] = None, y: Optional[int] = None) -> dict:
    """
    Click an element by selector or coordinates.
    
    Args:
        selector: CSS selector to click (optional)
        x: X coordinate to click (optional)
        y: Y coordinate to click (optional)
        
    Returns:
        dict with status
    """
    try:
        page = await get_page()
        
        if selector:
            await page.click(selector, timeout=5000)
        elif x is not None and y is not None:
            await page.mouse.click(x, y)
        else:
            return {"status": "error", "error": "Must provide selector or coordinates"}
        
        await asyncio.sleep(0.5)
        screenshot = await take_screenshot()
        
        return {
            "status": "success",
            "screenshot": screenshot.get("screenshot_base64", "")
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def type_text(selector: Optional[str] = None, text: str = "", press_enter: bool = False) -> dict:
    """
    Type text into an element or at current focus.
    
    Args:
        selector: CSS selector to type into (optional)
        text: Text to type
        press_enter: Whether to press Enter after typing
        
    Returns:
        dict with status
    """
    try:
        page = await get_page()
        
        if selector:
            await page.fill(selector, text)
        else:
            await page.keyboard.type(text)
        
        if press_enter:
            await page.keyboard.press("Enter")
        
        await asyncio.sleep(0.5)
        screenshot = await take_screenshot()
        
        return {
            "status": "success",
            "screenshot": screenshot.get("screenshot_base64", "")
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def take_screenshot() -> dict:
    """
    Take a screenshot of the current page.
    
    Returns:
        dict with base64 encoded screenshot
    """
    try:
        page = await get_page()
        screenshot_bytes = await page.screenshot(type="png")
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        
        if _screenshot_callback:
            await _screenshot_callback(screenshot_base64)
        
        return {
            "status": "success",
            "screenshot_base64": screenshot_base64
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def get_page_content() -> dict:
    """
    Get the text content and interactive elements from the page.
    
    Returns:
        dict with page content and clickable elements
    """
    try:
        page = await get_page()
        
        content = await page.evaluate("""
            () => {
                const getElements = () => {
                    const elements = [];
                    const clickables = document.querySelectorAll('a, button, input, select, textarea, [role="button"], [onclick]');
                    
                    clickables.forEach((el, idx) => {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            elements.push({
                                index: idx,
                                tag: el.tagName.toLowerCase(),
                                text: el.textContent?.trim().substring(0, 100) || '',
                                type: el.type || '',
                                placeholder: el.placeholder || '',
                                name: el.name || '',
                                id: el.id || '',
                                x: Math.round(rect.x + rect.width/2),
                                y: Math.round(rect.y + rect.height/2)
                            });
                        }
                    });
                    return elements;
                };
                
                return {
                    title: document.title,
                    url: window.location.href,
                    text: document.body.innerText.substring(0, 5000),
                    elements: getElements().slice(0, 50)
                };
            }
        """)
        
        return {"status": "success", **content}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def scroll_page(direction: str = "down", amount: int = 500) -> dict:
    """
    Scroll the page.
    
    Args:
        direction: 'up' or 'down'
        amount: pixels to scroll
        
    Returns:
        dict with status
    """
    try:
        page = await get_page()
        scroll_amount = amount if direction == "down" else -amount
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(0.3)
        
        screenshot = await take_screenshot()
        
        return {
            "status": "success",
            "screenshot": screenshot.get("screenshot_base64", "")
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def close_browser():
    """Close the browser instance."""
    global _browser, _context, _page
    if _browser:
        await _browser.close()
        _browser = None
        _context = None
        _page = None
