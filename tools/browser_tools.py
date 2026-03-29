"""
Browser Automation Tools using Nodriver
Includes Visual SOM (Set-of-Mark) for reliable clicking
"""

import asyncio
import base64
import io
import os
import tempfile
from typing import Optional, Dict
import nodriver as uc
from PIL import Image, ImageDraw, ImageFont

_browser: Optional[uc.Browser] = None
_page: Optional[uc.Tab] = None
_intervention_mode: bool = False
_screenshot_callback = None

# Global map to store element locations from the last screenshot
# Format: { "1": {"x": 100, "y": 200, "desc": "Submit Button"} }
_som_map: Dict[str, dict] = {}


async def get_browser() -> uc.Browser:
    """Get or create browser instance using nodriver."""
    global _browser
    if _browser is None or getattr(_browser, 'stopped', True):
        # Starts native Chrome on the machine. Automatically bypasses detection.
        # We use a custom user_data_dir to persistently store cookies/logins between runs.
        profile_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chrome_profile"))
        _browser = await uc.start(user_data_dir=profile_path)
    return _browser


async def get_page() -> uc.Tab:
    """Get or create the main tab instance."""
    global _page, _browser
    browser = await get_browser()
    
    # Check if we have an active page
    if _page is None:
        _page = browser.main_tab
    return _page


def set_screenshot_callback(callback):
    global _screenshot_callback
    _screenshot_callback = callback


def set_intervention_mode(active: bool):
    global _intervention_mode
    _intervention_mode = active


def is_intervention_mode() -> bool:
    return _intervention_mode


async def _tag_screenshot(screenshot_bytes: bytes, page: uc.Tab) -> str:
    """
    Internal: Draw bounding boxes (Visual SOM) on the screenshot.
    Populates _som_map with clickable coordinates.
    """
    global _som_map
    _som_map.clear()
    
    # 1. Get all interactive elements via JS
    js_query = """
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
                    text: el.innerText ? el.innerText.substring(0, 20) : el.getAttribute('aria-label') || ''
                });
            }
        });
        return items;
    """
    # Evaluate executes JS directly in the tab and returns results
    elements = await page.evaluate(js_query)
    
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
        draw.rectangle([x, y, x + 20, y + 15], fill="#00ff00")
        draw.text((x + 2, y + 1), tag_id, fill="black", font=font)

    # 4. Convert back to base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


async def take_screenshot() -> dict:
    """Take a screenshot, apply Visual SOM tags, and stream to UI."""
    try:
        page = await get_page()
        
        # Save to temporary file since nodriver outputs screenshots to disk
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_name = f.name
            
        await page.save_screenshot(temp_name)
        
        with open(temp_name, "rb") as image_file:
            png_bytes = image_file.read()
            
        os.remove(temp_name)
        
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


async def navigate_to_url(url: str) -> dict:
    """Navigate to a URL and return tagged screenshot."""
    try:
        page = await get_page()
        await page.get(url)
        await asyncio.sleep(2) # Wait for renders
        return await take_screenshot()
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def click_element(element_id: Optional[str] = None, selector: Optional[str] = None) -> dict:
    """
    Click an element using its Visual ID (preferred) or selector.
    """
    try:
        page = await get_page()
        
        if element_id and element_id in _som_map:
            # CLICK BY ID (Reliable layout coordinates)
            coords = _som_map[element_id]
            print(f"Clicking ID {element_id} at {coords['x']}, {coords['y']}")
            await page.mouse_click(int(coords['x']), int(coords['y']))
        elif selector:
            # Fallback Native Node Driver Selector
            el = await page.select(selector)
            if el:
                await el.click()
            else:
                return {"status": "error", "error": "Element not found by selector"}
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
            cx, cy = int(coords['x']), int(coords['y'])
            # Click to gain focus
            await page.mouse_click(cx, cy)
            
            # Use JS to inject text accurately into coordinate-based elements
            safe_text = text.replace('"', '\\"').replace('\n', '\\n')
            await page.evaluate(f'''
                (() => {{
                    let el = document.elementFromPoint({cx}, {cy});
                    if (el) {{
                        el.focus();
                        el.value = "{safe_text}";
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }})()
            ''')
        elif selector:
            el = await page.select(selector)
            if el:
               await el.click()
               await asyncio.sleep(0.5)
               await el.send_keys(text)
            else:
                return {"status": "error", "error": "Element not found by selector"}
        else:
            return {"status": "error", "error": "Provide element_id (from screenshot) or selector"}
            
        await asyncio.sleep(0.5)
        return await take_screenshot()
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def scroll_page(direction: str = "down") -> dict:
    """Scroll and update screenshot."""
    try:
        page = await get_page()
        if direction == "down":
            await page.scroll_down(500)
        else:
            await page.scroll_up(500)
        await asyncio.sleep(0.5)
        return await take_screenshot()
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def close_browser():
    global _browser
    if _browser and not getattr(_browser, 'stopped', True):
        _browser.stop()
