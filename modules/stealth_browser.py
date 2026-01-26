import asyncio
import random
import os
import shutil
import time
import json
from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import Stealth

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
        
        # Files needed for cookies and login state
        files_to_copy = [
            "Cookies",
            "Login Data",
            "Preferences",
            "Web Data",
            "Local State"
        ]
        
        # Chrome profiles are often in 'Default' or 'Profile X'
        # We'll try to find 'Default' first
        source_profile = os.path.join(DEFAULT_USER_DATA_DIR, "Default")
        if not os.path.exists(source_profile):
            source_profile = DEFAULT_USER_DATA_DIR # Fallback to root or user should specify
            
        target_profile = os.path.join(TEMP_PROFILE_DIR, "Default")
        os.makedirs(target_profile, exist_ok=True)
        
        # Copy Local State to the root of temp dir
        local_state_src = os.path.join(DEFAULT_USER_DATA_DIR, "Local State")
        if os.path.exists(local_state_src):
            try:
                shutil.copy2(local_state_src, os.path.join(TEMP_PROFILE_DIR, "Local State"))
            except Exception as e:
                print(f"[StealthBrowser] Warning: Could not copy Local State: {e}")

        for f in files_to_copy:
            src = os.path.join(source_profile, f)
            dst = os.path.join(target_profile, f)
            
            if os.path.exists(src):
                try:
                    # Use copy2 to preserve metadata
                    shutil.copy2(src, dst)
                    print(f"[StealthBrowser] Copied {f}")
                except Exception as e:
                    print(f"[StealthBrowser] Warning: Could not copy {f}: {e}")
                    # If it's locked, we might still be able to run but without cookies
            else:
                # Some files might be in subfolders like 'Network' in newer Chrome versions
                network_src = os.path.join(source_profile, "Network", f)
                network_dst = os.path.join(target_profile, "Network")
                if os.path.exists(network_src):
                    os.makedirs(network_dst, exist_ok=True)
                    try:
                        shutil.copy2(network_src, os.path.join(network_dst, f))
                        print(f"[StealthBrowser] Copied {f} from Network folder")
                    except Exception as e:
                        print(f"[StealthBrowser] Warning: Could not copy {f} from Network: {e}")

    async def launch(self):
        """
        Launches Chrome with persistent context.
        """
        self.playwright = await async_playwright().start()
        
        # Clone profile before launch
        self._clone_profile()
        
        # Dynamic UA Generation (Simplified)
        chrome_v = "132.0.0.0" # Modern 2026 version
        ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_v} Safari/537.36"

        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-features=IsolateOrigins,site-per-process",
        ]

        print(f"[StealthBrowser] 🚀 Launching Browser from {TEMP_PROFILE_DIR}...")
        
        try:
            # Use the cloned profile
            self.browser_context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=TEMP_PROFILE_DIR,
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
            # Fallback for non-clickable inputs
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
                await asyncio.sleep(random.uniform(0.2, 0.4))
                await self.page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.1, 0.3))
                # Now type the correct one
            
            # Base latency
            latency = random.uniform(0.08, 0.22) # Slightly slower and more varied
            
            # Add micro-hesitations for spaces or special chars
            if char in [' ', '.', '@']:
                latency += random.uniform(0.15, 0.35)
                
            await self.page.keyboard.type(char)
            await asyncio.sleep(latency)
            i += 1
            
        # Post-typing hesitation (checking work)
        await asyncio.sleep(random.uniform(0.5, 1.2))


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

# Global Singleton for the App to access
# In a real ADK app, this might be managed by the Runtime, but a global is fine for Phase 4
browser_instance = StealthBrowser(headless=False)