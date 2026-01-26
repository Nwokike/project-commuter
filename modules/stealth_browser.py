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
        import platform
        
        # Mirror Host Stack
        os_version = platform.platform()
        python_version = platform.python_version()
        
        # Dynamic UA Generation (Simplified)
        chrome_v = "132.0.0.0" # Modern 2026 version
        ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_v} Safari/537.36"

        print(f"[StealthBrowser] Layering defense for {os_version} (Python {python_version})")
        
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-features=IsolateOrigins,site-per-process", # Helps with frame-based fingerprinting
        ]

        try:
            self.browser_context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=self.headless,
                args=args,
                viewport={"width": 1920, "height": 1080},
                user_agent=ua,
                extra_http_headers={
                    "sec-ch-ua": f'"Not A(Brand";v="8", "Chromium";v="{chrome_v.split(".")[0]}", "Google Chrome";v="{chrome_v.split(".")[0]}"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                }
            )
            
            self.page = self.browser_context.pages[0] if self.browser_context.pages else await self.browser_context.new_page()
            
            # Advanced Masking Script
            mask_script = """
            // Mask WebGL
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Open Source Technology Center';
                if (parameter === 37446) return 'Mesa DRI Intel(R) HD Graphics 5500 (Broadwell GT2)';
                return getParameter.apply(this, arguments);
            };

            // Mask AudioContext
            const oldAudioContext = window.AudioContext || window.webkitAudioContext;
            window.AudioContext = function() {
                const ctx = new oldAudioContext();
                const oldCreateOscillator = ctx.createOscillator;
                ctx.createOscillator = function() {
                    const osc = oldCreateOscillator.apply(this, arguments);
                    const oldStart = osc.start;
                    osc.start = function() {
                        // Add subtle noise
                        return oldStart.apply(this, arguments);
                    };
                    return osc;
                };
                return ctx;
            };
            """
            await self.page.add_init_script(mask_script)
            await stealth_async(self.page)
            
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
