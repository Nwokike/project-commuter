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
            "--start-maximized",
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-session-crashed-bubble" # Prevent 'Restore' popup from blocking
        ]

        # CRITICAL FIX: Use REAL User Profile for persistence (Cookies, LinkedIn Session)
        user_data_path = os.path.join(os.environ["LOCALAPPDATA"], "Google", "Chrome", "User Data")
        
        # Check if dir exists, if not fallback (e.g. non-standard install)
        if not os.path.exists(user_data_path):
            print(f"[StealthBrowser] ⚠️ Standard Chrome Profile not found at {user_data_path}. Using local fallback.")
            user_data_path = os.path.join(os.getcwd(), "data", "chrome_bot_profile")
        
        print(f"[StealthBrowser] 🚀 Launching Browser using Profile: {user_data_path}...")
        
        try:
            # STRATEGY 1: Attach to "Debug Chrome" (Port 9222)
            # This is the "Magic Mode" that uses the ALREADY OPEN browser.
            try:
                print("[StealthBrowser] 📡 Attempting to connect to existing Chrome (Port 9222)...")
                self.browser_context = await self.playwright.chromium.connect_over_cdp("http://localhost:9222")
                print("[StealthBrowser] ✅ Connected to your OPEN Chrome window!")
                
                if self.browser_context.contexts:
                    self.browser_context = self.browser_context.contexts[0]
                
                if self.browser_context.pages:
                    self.page = self.browser_context.pages[0]
                    await self.page.bring_to_front()
                else:
                    self.page = await self.browser_context.new_page()
                
            except Exception:
                print("[StealthBrowser] ℹ️ No Debug Chrome found (Port 9222).")

            # STRATEGY 2: Launch Persistent Context (Standard Mode)
            # This requires Chrome to be closed.
            
            # FAST FAIL CHECK: Is Chrome running?
            # If Chrome is running normaly (no debug port), we CANNOT launch (Lockfile).
            # We must detect this to avoid the "Hang".
            print("[StealthBrowser] 🔍 Checking for existing Chrome processes...")
            tasklist = os.popen('tasklist /FI "IMAGENAME eq chrome.exe"').read()
            if "chrome.exe" in tasklist:
                print("\n" + "!"*60)
                print("🛑 BLOCKING ERROR: CHROME IS OPEN")
                print("1. I cannot use your profile while Chrome is open.")
                print("2. I tried to attach (CDP) but Debug Mode is OFF.")
                print("-" * 30)
                print("👉 SOLUTION A (Easiest): CLOSE Chrome completely, then run launcher.")
                print("👉 SOLUTION B (Advanced): Run 'start chrome --remote-debugging-port=9222'")
                print("!"*60 + "\n")
                raise RuntimeError("Chrome is open. User must close it.")

            print("[StealthBrowser] ⏳ Initializing Playwright Context...")
            print("[StealthBrowser] ⚠️ IF CHROME OPENS BUT HANGS HERE: Please click 'Restore' or close any popups inside Chrome!")
            
            self.browser_context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_path,
                channel="chrome",
                headless=self.headless,
                args=args,
                viewport={"width": 1920, "height": 1080},
                user_agent=ua,
                ignore_default_args=["--enable-automation"],
                timeout=60000 # 60s timeout for heavy profiles
            )
            print("[StealthBrowser] ✅ Context Launched.")
            
            # Handle Tabs
            if self.browser_context.pages:
                print(f"[StealthBrowser] ℹ️ Found {len(self.browser_context.pages)} existing tabs. Using first one.")
                self.page = self.browser_context.pages[0]
            else:
                print("[StealthBrowser] ℹ️ No tabs found. Creating new page.")
                self.page = await self.browser_context.new_page()
            
            # Apply Stealth (Safe Mode)
            try:
                print("[StealthBrowser] 🕵️ Applying Stealth Measures...")
                await asyncio.wait_for(Stealth().apply_stealth_async(self.page), timeout=5.0)
                print("[StealthBrowser] ✅ Stealth Applied.")
            except Exception as e:
                print(f"[StealthBrowser] ⚠️ Stealth Skipped (Not Critical): {e}")

            # Hardware Concurrency Spoofing
            try:
                await self.page.evaluate("Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})")
            except:
                pass
            
            return self.page

        except Exception as e:
            if "SingletonLock" in str(e) or "lock" in str(e).lower():
                print("\n" + "="*60)
                print("🛑 CRITICAL ERROR: CHROME IS ALREADY RUNNING")
                print("To use your real profile (and logins), you MUST close all Chrome windows first.")
                print("The bot cannot attach to a running browser due to file locks.")
                print("="*60 + "\n")
                raise RuntimeError("Chrome is open. Please close it.")
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
