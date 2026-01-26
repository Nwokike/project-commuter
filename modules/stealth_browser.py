import asyncio
import random
import os
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# Standard Windows Chrome User Data path
DEFAULT_USER_DATA_DIR = os.path.join(os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data")

class StealthBrowser:
    def __init__(self, headless=False):
        self.headless = headless
        self.browser_context = None
        self.page = None
        self.playwright = None

    async def launch(self):
        """
        Launches Chrome with persistent context to use existing cookies/login.
        User MUST close their actual Chrome browser before running this.
        """
        self.playwright = await async_playwright().start()
        
        user_data_dir = os.getenv("CHROME_USER_DATA_DIR", DEFAULT_USER_DATA_DIR)
        
        print(f"[StealthBrowser] Launching with profile: {user_data_dir}")
        
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            # Mask WebGL (basic)
             "--disable-webgl", 
             "--disable-webgl2",
        ]

        try:
            self.browser_context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome", # Use actual Chrome, not Chromium
                headless=self.headless,
                args=args,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" # Hardcoded recent UA to match OS
            )
            
            self.page = self.browser_context.pages[0] if self.browser_context.pages else await self.browser_context.new_page()
            
            # Apply Stealth
            await stealth_async(self.page)
            
            # Extra Patching
            await self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("[StealthBrowser] Browser launched successfully.")
            return self.page

        except Exception as e:
            print(f"[StealthBrowser] CRITICAL ERROR: Could not launch browser. Is Chrome open? {e}")
            raise e

    async def human_type(self, selector, text):
        """Types with random delays."""
        await self.page.click(selector)
        for char in text:
            await self.page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))
        await asyncio.sleep(random.uniform(0.5, 1.0))

    async def human_click(self, selector):
        """Moves mouse in a curve (simple approximation) then clicks."""
        # Get element box
        box = await self.page.locator(selector).bounding_box()
        if not box:
            print(f"[StealthBrowser] Cannot click {selector}, element not visible.")
            return

        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2
        
        # Simple "human" move: randomize start and steps
        await self.page.mouse.move(target_x + random.randint(-10, 10), target_y + random.randint(-10, 10), steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.1, 0.3))
        await self.page.mouse.click(target_x, target_y)
    
    async def close(self):
        if self.browser_context:
            await self.browser_context.close()
        if self.playwright:
            await self.playwright.stop()
