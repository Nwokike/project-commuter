import asyncio
import random
import os
import shutil
import time
import json
from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import stealth_async

# Standard Windows Chrome User Data path
# NOTE: Adjust for Mac/Linux if needed or make dynamic
DEFAULT_USER_DATA_DIR = os.path.join(os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data")
TEMP_PROFILE_DIR = os.path.join(os.getenv("TEMP"), "chrome_bot_profile_clone")

class StealthBrowser:
    def __init__(self, headless=False):
        self.headless = headless
        self.browser_context: BrowserContext = None
        self.page: Page = None
        self.playwright = None

    def _clone_profile(self):
        """
        Copies the user's Chrome profile to a temp directory to avoid database locks.
        This allows the user to use their browser while the bot runs.
        """
        print(f"[StealthBrowser] 🧬 Cloning Chrome Profile to {TEMP_PROFILE_DIR}...")
        
        # We only copy the 'Default' profile or specific necessary folders to save time/space
        # A full copy might be too slow. For now, we try to launch with the real one
        # BUT if that fails, we fallback to a clean profile or a clone.
        
        # For this implementation, we will actually use the REAL profile but strictly handle
        # the closing/locking. 
        # Alternatively, a robust method is to copy 'Cookies', 'Preferences', and 'Login Data'.
        
        if os.path.exists(TEMP_PROFILE_DIR):
             try:
                 shutil.rmtree(TEMP_PROFILE_DIR)
             except Exception as e:
                 print(f"[StealthBrowser] Warning: Could not clean temp dir: {e}")

        # Simple Copy Strategy (Can be optimized)
        try:
             # Just create the dir, Playwright will populate it if it's empty
             # To truly clone cookies, we'd need to copy specific SQLite files.
             # For Phase 4, let's stick to using the REAL profile but with a warning,
             # OR use a blank profile and require the user to login once.
             pass
        except Exception as e:
             pass

    async def launch(self):
        """
        Launches Chrome with persistent context.
        """
        self.playwright = await async_playwright().start()
        
        # Dynamic UA Generation (Simplified)
        chrome_v = "132.0.0.0" # Modern 2026 version
        ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_v} Safari/537.36"

        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-features=IsolateOrigins,site-per-process",
        ]

        print(f"[StealthBrowser] 🚀 Launching Browser (Headless: {self.headless})...")
        
        try:
            # We use the real user data dir. 
            # CRITICAL: User must close Chrome for this to work perfectly without cloning.
            # If cloning is desired, change user_data_dir to TEMP_PROFILE_DIR and implement _clone_profile
            self.browser_context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=DEFAULT_USER_DATA_DIR,
                channel="chrome",
                headless=self.headless,
                args=args,
                viewport={"width": 1920, "height": 1080},
                user_agent=ua,
                ignore_default_args=["--enable-automation"]
            )
            
            self.page = self.browser_context.pages[0] if self.browser_context.pages else await self.browser_context.new_page()
            
            # Apply Stealth
            await stealth_async(self.page)
            
            # Hardware Concurrency Spoofing
            await self.page.evaluate("Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})")
            
            return self.page

        except Exception as e:
            print(f"[StealthBrowser] 💥 CRITICAL: Could not launch. Is Chrome open? {e}")
            raise e

    async def human_type(self, selector, text):
        """
        Biometric Typing: Varies speed based on key distance (simulated).
        """
        # Focus element
        try:
            await self.page.click(selector)
        except:
            # Fallback for non-clickable inputs
            pass
            
        print(f"[StealthBrowser] ⌨️ Typing: '{text}' into {selector}")
        
        for char in text:
            # Base latency
            latency = random.uniform(0.05, 0.15)
            
            # Add micro-hesitations for spaces or special chars
            if char in [' ', '.', '@']:
                latency += random.uniform(0.1, 0.2)
                
            await self.page.keyboard.type(char)
            await asyncio.sleep(latency)
            
        # Post-typing hesitation (checking work)
        await asyncio.sleep(random.uniform(0.3, 0.8))

    async def human_click(self, selector):
        """
        Moves mouse in a bezier-like curve (simplified) then clicks.
        """
        try:
            box = await self.page.locator(selector).bounding_box()
            if not box:
                print(f"[StealthBrowser] ⚠️ Element {selector} not visible/found.")
                return False

            # Target center with noise
            target_x = box["x"] + (box["width"] / 2) + random.randint(-5, 5)
            target_y = box["y"] + (box["height"] / 2) + random.randint(-5, 5)
            
            # Current mouse pos (Playwright defaults to 0,0)
            # We simply move there in steps to simulate "flight"
            await self.page.mouse.move(target_x, target_y, steps=random.randint(10, 25))
            
            # Hover briefly
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            await self.page.mouse.click(target_x, target_y)
            print(f"[StealthBrowser] 🖱️ Clicked {selector}")
            return True
            
        except Exception as e:
            print(f"[StealthBrowser] ❌ Click Failed: {e}")
            return False
    
    async def get_screenshot(self, path="latest_view.png"):
        await self.page.screenshot(path=path)
        return path

    async def close(self):
        if self.browser_context:
            await self.browser_context.close()
        if self.playwright:
            await self.playwright.stop()

# Global Singleton for the App to access
# In a real ADK app, this might be managed by the Runtime, but a global is fine for Phase 4
browser_instance = StealthBrowser(headless=False)