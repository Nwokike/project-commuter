import sys
import os
import time

def main():
    print("-" * 50)
    print("🚀 PROEJCT COMMUTER: MISSION CONTROL LAUNCHER")
    print("-" * 50)
    print("Initializing System...")
    
    try:
        ret = os.system(f'"{sys.executable}" api_server.py')
        
        if ret != 0:
            print(f"\n[Launcher] ⚠️ System exited with code {ret}")
            
    except KeyboardInterrupt:
        print("\n\n[Launcher] 🛑 Shutdown Sequence Complete.")
    except Exception as e:
        print(f"\n[Launcher] 💥 Error: {e}")

if __name__ == "__main__":
    main()
