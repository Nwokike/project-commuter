import asyncio
import random
import os
import shutil
import time
import json
from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import Stealth

# CRITICAL FIX: Use a dedicated, persistent profile directory.
# We do NOT clone the main user profile anymore to avoid file lock crashes.
BOT_PROFILE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chrome_bot_profile")

class StealthBrowser:
    def __init__(self, headless=False):
        self.headless = headless
        self.browser_context: BrowserContext = None
        self.page: Page = None
        self.playwright = None

    async def launch(self):
        """
        Launches Chrome with a persistent Bot Context.
        """
        self.playwright = await async_playwright().start()
        
        # Ensure profile dir exists
        os.makedirs(BOT_PROFILE_DIR, exist_ok=True)
        
        # Dynamic User Agent (Updated for 2026 realism)
        chrome_v = "132.0.0.0" 
        ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_v} Safari/537.36"

        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-features=IsolateOrigins,site-per-process",
            "--start-maximized" # Helps with visibility
        ]

        print(f"[StealthBrowser] 🚀 Launching Browser from {BOT_PROFILE_DIR}...")
        
        try:
            # Launch Persistent Context
            # Note: This will open a window. The user MUST log in here manually the first time.
            self.browser_context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=BOT_PROFILE_DIR,
                channel="chrome",
                headless=self.headless,
                args=args,
                viewport={"width": 1920, "height": 1080},
                user_agent=ua,
                ignore_default_args=["--enable-automation"]
            )
            
            self.page = self.browser_context.pages[0] if self.browser_context.pages else await self.browser_context.new_page()
            
            # Apply Stealth
            await Stealth().apply_stealth_async(self.page)
            
            # Hardware Concurrency Spoofing
            await self.page.evaluate("Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})")
            
            return self.page

        except Exception as e:
            print(f"[StealthBrowser] 💥 CRITICAL: Could not launch. {e}")
            raise e

    async def human_type(self, selector, text):
        """
        Biometric Typing: Varies speed based on key distance and adds occasional mistakes.
        """
        # Focus element
        try:
            await self.page.click(selector)
        except:
            pass
            
        print(f"[StealthBrowser] ⌨️ Typing: '{text}' into {selector}")
        
        chars = list(text)
        i = 0
        while i < len(chars):
            char = chars[i]
            
            # Occasional mistake (1% chance)
            if random.random() < 0.01 and char.isalpha():
                wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                await self.page.keyboard.type(wrong_char)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await self.page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Base latency
            latency = random.uniform(0.05, 0.15) 
            
            if char in [' ', '.', '@']:
                latency += random.uniform(0.1, 0.2)
                
            await self.page.keyboard.type(char)
            await asyncio.sleep(latency)
            i += 1
            
        await asyncio.sleep(random.uniform(0.3, 0.8))


    async def human_click(self, selector):
        """
        Moves mouse in a bezier-like curve then clicks.
        """
        try:
            # Locate element
            loc = self.page.locator(selector).first
            box = await loc.bounding_box()
            if not box:
                print(f"[StealthBrowser] ⚠️ Element {selector} not visible/found.")
                return False

            # Target center with noise
            target_x = box["x"] + (box["width"] / 2) + random.randint(-5, 5)
            target_y = box["y"] + (box["height"] / 2) + random.randint(-5, 5)
            
            await self.page.mouse.move(target_x, target_y, steps=random.randint(5, 15))
            await asyncio.sleep(random.uniform(0.1, 0.2))
            
            await self.page.mouse.click(target_x, target_y)
            print(f"[StealthBrowser] 🖱️ Clicked {selector}")
            return True
            
        except Exception as e:
            print(f"[StealthBrowser] ❌ Click Failed: {e}")
            return False
    
    async def apply_som_tagging(self):
        """
        Injects the SoM tagging script into the current page.
        """
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modules", "scripts", "tag_elements.js")
        if not os.path.exists(script_path):
            print(f"[StealthBrowser] ❌ Tagging script NOT FOUND at {script_path}")
            return
            
        with open(script_path, "r") as f:
            script = f.read()
            
        await self.page.evaluate(script)
        # Wait a tick for DOM update
        await asyncio.sleep(0.5)
        print("[StealthBrowser] 🏷️ SoM Tagging Applied.")

    async def get_screenshot(self, path="latest_view.png"):
        # Ensure tags are fresh before screenshot
        await self.apply_som_tagging()
        await self.page.screenshot(path=path)
        return path

    async def close(self):
        if self.browser_context:
            await self.browser_context.close()
        if self.playwright:
            await self.playwright.stop()

# Global Singleton
browser_instance = StealthBrowser(headless=False)
