"""
Browser Automation Tools using Playwright
Includes Visual SOM (Set-of-Mark) for reliable clicking
"""

import asyncio
import base64
import io
from typing import Optional, Dict
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from playwright_stealth import stealth_async
from PIL import Image, ImageDraw, ImageFont

_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None
_page: Optional[Page] = None
_intervention_mode: bool = False
_screenshot_callback = None

# Global map to store element locations from the last screenshot
# Format: { "1": {"x": 100, "y": 200, "description": "Submit Button"} }
_som_map: Dict[str, dict] = {}


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
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
    
    if _page is None or _page.is_closed():
        _page = await _context.new_page()
        await stealth_async(_page)
    
    return _page


def set_screenshot_callback(callback):
    global _screenshot_callback
    _screenshot_callback = callback


def set_intervention_mode(active: bool):
    global _intervention_mode
    _intervention_mode = active


def is_intervention_mode() -> bool:
    return _intervention_mode


async def _tag_screenshot(screenshot_bytes: bytes, page: Page) -> str:
    """
    Internal: Draw bounding boxes (Visual SOM) on the screenshot.
    Populates _som_map with clickable coordinates.
    """
    global _som_map
    _som_map.clear()
    
    # 1. Get all interactive elements via JS
    elements = await page.evaluate("""() => {
        const items = [];
        const selector = 'button, a, input, select, textarea, [role="button"]';
        document.querySelectorAll(selector).forEach((el) => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden') {
                items.push({
                    x: rect.x,
                    y: rect.y,
                    w: rect.width,
                    h: rect.height,
                    tag: el.tagName,
                    text: el.innerText.substring(0, 20) || el.getAttribute('aria-label') || ''
                });
            }
        });
        return items;
    }""")
    
    # 2. Process Image with PIL
    image = Image.open(io.BytesIO(screenshot_bytes))
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.load_default()
    except:
        font = None

    # 3. Draw boxes and assign IDs
    for idx, el in enumerate(elements):
        tag_id = str(idx + 1)
        x, y, w, h = el['x'], el['y'], el['w'], el['h']
        
        # Save to map for clicking later
        center_x = x + w / 2
        center_y = y + h / 2
        _som_map[tag_id] = {"x": center_x, "y": center_y, "desc": el['text']}
        
        # Draw Box (Green for distinction)
        draw.rectangle([x, y, x + w, y + h], outline="#00ff00", width=2)
        
        # Draw ID Label
        # Draw a small background for the text
        draw.rectangle([x, y, x + 20, y + 15], fill="#00ff00")
        draw.text((x + 2, y + 1), tag_id, fill="black", font=font)

    # 4. Convert back to base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


async def navigate_to_url(url: str) -> dict:
    """Navigate to a URL and return tagged screenshot."""
    try:
        page = await get_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2) # Wait for renders
        
        return await take_screenshot()
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def click_element(element_id: Optional[str] = None, selector: Optional[str] = None) -> dict:
    """
    Click an element using its Visual ID (preferred) or selector.
    
    Args:
        element_id: The number shown in the green box on the screenshot (e.g., "42")
        selector: Fallback CSS selector
    """
    try:
        page = await get_page()
        
        if element_id and element_id in _som_map:
            # CLICK BY ID (Reliable)
            coords = _som_map[element_id]
            print(f"Clicking ID {element_id} at {coords['x']}, {coords['y']}")
            await page.mouse.click(coords['x'], coords['y'])
        elif selector:
            # Fallback
            await page.click(selector)
        else:
            return {"status": "error", "error": "Provide element_id (from screenshot) or selector"}
        
        await asyncio.sleep(1)
        return await take_screenshot()
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def type_text(text: str, element_id: Optional[str] = None, selector: Optional[str] = None) -> dict:
    """Type text into an element."""
    try:
        page = await get_page()
        
        if element_id and element_id in _som_map:
            coords = _som_map[element_id]
            await page.mouse.click(coords['x'], coords['y'])
        elif selector:
            await page.click(selector)
            
        await page.keyboard.type(text)
        await asyncio.sleep(0.5)
        
        return await take_screenshot()
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def take_screenshot() -> dict:
    """Take a screenshot, apply Visual SOM tags, and stream to UI."""
    try:
        page = await get_page()
        png_bytes = await page.screenshot(type="png")
        
        # Apply SOM Tags
        tagged_base64 = await _tag_screenshot(png_bytes, page)
        
        # Stream to Dashboard
        if _screenshot_callback:
            await _screenshot_callback(tagged_base64)
        
        return {
            "status": "success",
            "screenshot_base64": tagged_base64,
            "interactive_elements_count": len(_som_map)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def scroll_page(direction: str = "down") -> dict:
    """Scroll and update screenshot."""
    try:
        page = await get_page()
        delta = 500 if direction == "down" else -500
        await page.evaluate(f"window.scrollBy(0, {delta})")
        await asyncio.sleep(0.5)
        return await take_screenshot()
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def close_browser():
    global _browser
    if _browser:
        await _browser.close()
