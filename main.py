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

from enum import Enum

class State(Enum):
    SCOUTING = "SCOUTING"
    NAVIGATING = "NAVIGATING"
    APPLYING = "APPLYING"
    SOS = "SOS"
    IDLE = "IDLE"

async def main():
    print("[Orchestrator] System Starting v2.0 (State Machine)...")
    init_db()
    load_dotenv()
    
    browser = StealthBrowser(headless=False)
    page = await browser.launch()
    apps_submitted = 0
    current_state = State.SCOUTING
    
    try:
        while True:
            # 1. State: IDLE (Schedule Check)
            now = datetime.now()
            if not (WORK_START_HOUR <= now.hour < WORK_END_HOUR):
                current_state = State.IDLE
                await asyncio.sleep(3600)
                continue
            
            # 2. State: SCOUTING
            if current_state == State.SCOUTING:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT job_hash, url FROM job_queue WHERE status='PENDING' LIMIT 1")
                job = cursor.fetchone()
                conn.close()
                
                if job:
                    current_state = State.NAVIGATING
                else:
                    print("[Orchestrator] No jobs in queue. Scouting...")
                    search_url = await job_search_agent.run_async("Python Developer Remote")
                    await page.goto(search_url)
                    await asyncio.sleep(5)
                    cards = await page.locator(".job-card-container").all()
                    for card in cards[:5]:
                        html = await card.inner_html()
                        parsed_str = await listing_parser_agent.run_async(html)
                        parsed = json.loads(parsed_str)
                        if parsed.get("Easy Apply"):
                            add_to_queue(parsed["url"], parsed["company"], parsed["title"])
                    await asyncio.sleep(10)
                    continue

            # 3. State: NAVIGATING / APPLYING
            if current_state in [State.NAVIGATING, State.APPLYING]:
                job_hash, url = job
                if current_state == State.NAVIGATING:
                    await page.goto(url)
                    await asyncio.sleep(5)
                    current_state = State.APPLYING
                
                # Application Loop (Internal State)
                for attempt in range(20):
                    # Use SoM Vision
                    vision_data_str = await vision_agent.run_async(page, "latest_view.png")
                    vision_data = json.loads(vision_data_str)
                    
                    cmd_str = await navigation_agent.run_async(f"UI Map: {vision_data}. Goal: Apply.")
                    cmd = json.loads(cmd_str)
                    
                    if cmd["action"] == "type":
                        prompt = f"Field: {cmd.get('label', 'unknown')}. ID: {cmd['som_id']}"
                        mem_val = await memory_agent.run_async(prompt)
                        ctx_val = await context_agent.run_async(prompt)
                        val = await decision_agent.run_async(f"Memory: {mem_val} Context: {ctx_val}")
                        
                        if "SOS" in val:
                            current_state = State.SOS
                            await sos_agent.run_async(f"Job: {url}, Field: {cmd.get('label')}")
                            break
                        
                        # Click by SoM ID
                        selector = f"[data-som-id='{cmd['som_id']}']"
                        await browser.human_type(selector, val)
                    
                    elif cmd["action"] == "click":
                        selector = f"[data-som-id='{cmd['som_id']}']"
                        await browser.human_click(selector)
                    
                    elif cmd["action"] == "success":
                        conn = get_connection()
                        conn.execute("UPDATE job_queue SET status='APPLIED' WHERE job_hash=?", (job_hash,))
                        conn.commit()
                        conn.close()
                        apps_submitted += 1
                        current_state = State.SCOUTING
                        break
                    
                    await asyncio.sleep(2)
                
                if current_state == State.SOS:
                    print("[Orchestrator] SOS Triggered. Waiting for human...")
                    # In v2, this would poll the DB/Liaison, for now we sleep
                    await asyncio.sleep(60) 

    except Exception as e:
        print(f"[Orchestrator] CRITICAL FAILURE: {e}. State was {current_state}")
        # Persistence: In a full DB impl, we'd save state here
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
