import subprocess
import sys
import time
import signal
import os
import asyncio

# Import the main bot entry point
from main import main as bot_main

# Global process variable for cleanup
streamlit_process = None

def cleanup(signum, frame):
    """Graceful shutdown handler for Ctrl+C."""
    print("\n\n[Launcher] 🛑 Shutdown Sequence Initiated...")
    
    if streamlit_process:
        print("[Launcher] Killing Streamlit Dashboard...")
        if sys.platform == "win32":
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(streamlit_process.pid)])
        else:
            streamlit_process.terminate()
            streamlit_process.wait()
            
    print("[Launcher] System Shutdown Complete. Bye! 👋")
    sys.exit(0)

def run_system():
    global streamlit_process
    
    # 1. Start Streamlit in HEADLESS MODE (Background)
    # This ensures it DOES NOT launch a browser window and lock your profile files.
    print("[Launcher] 🚀 Initiating Launch Sequence...")
    print("[Launcher] Starting Flight Deck (Headless Mode)...")
    
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.py")
    
    streamlit_process = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", dashboard_path,
            "--server.headless", "true",  # CRITICAL FIX: No auto-browser launch
            "--server.port", "8501"
        ],
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(__file__) 
    )
    
    print("[Launcher] ✅ Dashboard active in background at http://localhost:8501")
    print("[Launcher] ⏳ Waiting 2 seconds for server spin-up...")
    time.sleep(2) 
    
    # 2. Start the ADK Bot (Orchestrator) in the foreground
    print("[Launcher] 🤖 Starting Orchestrator (ADK Core)...")
    print("-" * 50)
    
    try:
        # The Bot will now be the ONE to open the browser window
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        cleanup(None, None)
    except Exception as e:
        print(f"\n[Launcher] 💥 CRITICAL ERROR: {e}")
        cleanup(None, None)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    run_system()