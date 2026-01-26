import subprocess
import sys
import time
import signal
import os
import asyncio

# Import the main bot entry point
# Ensure main.py is in the same directory or python path
from main import main as bot_main

# Global process variable for cleanup
streamlit_process = None

def cleanup(signum, frame):
    """Graceful shutdown handler for Ctrl+C."""
    print("\n\n[Launcher] 🛑 Shutdown Sequence Initiated...")
    
    if streamlit_process:
        print("[Launcher] Killing Streamlit Dashboard...")
        # Terminate the subprocess group to ensure child processes die
        if sys.platform == "win32":
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(streamlit_process.pid)])
        else:
            streamlit_process.terminate()
            streamlit_process.wait()
            
    print("[Launcher] System Shutdown Complete. Bye! 👋")
    sys.exit(0)

def run_system():
    global streamlit_process
    
    # 1. Start Streamlit (Dashboard) in the background
    print("[Launcher] 🚀 Initiating Launch Sequence...")
    print("[Launcher] Starting Flight Deck (Dashboard)...")
    
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.py")
    
    # We redirect stdout/stderr to DEVNULL to keep your main terminal clean for Bot logs only
    # If you need to debug Streamlit, remove stdout=subprocess.DEVNULL
    streamlit_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", dashboard_path],
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(__file__) 
    )
    
    print("[Launcher] ✅ Dashboard active at http://localhost:8501")
    print("[Launcher] ⏳ Waiting 3 seconds for UI warmup...")
    time.sleep(3) 
    
    # 2. Start the ADK Bot (Orchestrator) in the foreground
    print("[Launcher] 🤖 Starting Orchestrator (ADK Core)...")
    print("-" * 50)
    
    try:
        # Run the async main loop from main.py
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        # This catches the Ctrl+C before the signal handler if inside asyncio
        cleanup(None, None)
    except Exception as e:
        print(f"\n[Launcher] 💥 CRITICAL ERROR: {e}")
        cleanup(None, None)

if __name__ == "__main__":
    # Register signal handlers for graceful exit
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    run_system()