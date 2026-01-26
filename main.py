import asyncio
import random
import time
import os
import json
from datetime import datetime
from dotenv import load_dotenv

from modules.stealth_browser import StealthBrowser
from modules.db import get_connection, init_db
from agents.scout_squad import job_search_agent, listing_parser_agent, add_to_queue, duplicate_check_agent
from agents.vision_squad import vision_agent, navigation_agent, scroll_agent, analyze_viewport
from agents.brain_squad import memory_agent, context_agent, decision_agent
from agents.ops_squad import sos_agent, liaison_agent

# Config
APPS_PER_CYCLE = 10
WORK_START_HOUR = 9
WORK_END_HOUR = 18

async def main():
    print("[Orchestrator] System Starting...")
    init_db()
    load_dotenv()
    
    browser = StealthBrowser(headless=False)
    page = await browser.launch()
    apps_submitted = 0
    
    try:
        while True:
            # 1. Logic Check (Time & Breaks)
            now = datetime.now()
            if not (WORK_START_HOUR <= now.hour < WORK_END_HOUR):
                await asyncio.sleep(3600)
                continue
            
            if apps_submitted > 0 and apps_submitted % APPS_PER_CYCLE == 0:
                await asyncio.sleep(random.randint(300, 900))
                apps_submitted += 1

            # 2. Queue & Scout
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT job_hash, url FROM job_queue WHERE status='PENDING' LIMIT 1")
            job = cursor.fetchone()
            conn.close()
            
            if not job:
                search_url = job_search_agent.run("Python Developer Remote")
                await page.goto(search_url)
                await asyncio.sleep(5)
                # Scraping
                cards = await page.locator(".job-card-container").all()
                for card in cards[:5]:
                    html = await card.inner_html()
                    parsed = json.loads(listing_parser_agent.run(html))
                    if parsed.get("Easy Apply"):
                        add_to_queue(parsed["url"], parsed["company"], parsed["title"])
                continue

            # 3. Application Lifecycle
            job_hash, url = job
            await page.goto(url)
            await asyncio.sleep(5)
            
            for _ in range(20):
                await page.screenshot(path="latest_view.png")
                vision_data = vision_agent.run("latest_view.png")
                cmd = json.loads(navigation_agent.run(f"UI Map: {vision_data}. Goal: Apply."))
                
                if cmd["action"] == "type":
                    val = decision_agent.run(f"Question: {cmd['selector']}. Memory: {memory_agent.run(cmd['selector'])} Context: {context_agent.run(cmd['selector'])}")
                    if "SOS" in val:
                        sos_agent.run(f"Job: {url}, Question: {cmd['selector']}")
                        break
                    await browser.human_type(cmd["selector"], val)
                
                elif cmd["action"] == "click":
                    await browser.human_click(cmd["selector"])
                
                elif cmd["action"] == "scroll":
                    await page.mouse.wheel(0, 500)
                
                elif cmd["action"] == "success":
                    conn = get_connection()
                    conn.execute("UPDATE job_queue SET status='APPLIED' WHERE job_hash=?", (job_hash,))
                    conn.commit()
                    conn.close()
                    apps_submitted += 1
                    break
                
                await asyncio.sleep(2)

    except Exception as e:
        print(f"[Orchestrator] Error: {e}")
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
