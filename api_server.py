import os
import json
import asyncio
import pdfplumber
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List

# Import existing logic (We will refactor this later or import what we need)
from modules.db import get_connection, get_config, save_config

# --- Agent Lifecycle ---
from main import main as bot_main

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Spawn the bot
    asyncio.create_task(bot_main())
    yield
    # Shutdown logic if needed

app = FastAPI(lifespan=lifespan)

# --- Helpers ---
def load_cv_text(file_obj):
    try:
        with pdfplumber.open(file_obj) as pdf:
            return "".join([p.extract_text() or "" for p in pdf.pages]).strip()
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass # Handle dead connections lazily

manager = ConnectionManager()

# --- API Models ---
class CommandRequest(BaseModel):
    command: str

class ConfigRequest(BaseModel):
    key: str
    value: str

# --- API Endpoints ---

@app.get("/api/state")
async def get_state():
    status = get_config("system_status") or "IDLE"
    query = get_config("search_query") or ""
    cv_loaded = bool(get_config("cv_text"))
    
@app.get("/api/state")
async def get_state():
    status = get_config("system_status") or "IDLE"
    query = get_config("search_query") or ""
    cv_loaded = bool(get_config("cv_text"))
    
    # Real DB Metrics
    conn = get_connection()
    try:
        total_jobs = conn.execute("SELECT COUNT(*) FROM job_queue").fetchone()[0]
        applied = conn.execute("SELECT COUNT(*) FROM job_queue WHERE status='APPLIED'").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM job_queue WHERE status='PENDING'").fetchone()[0]
    except Exception as e:
        print(f"[API] DB Error: {e}")
        total_jobs = 0
        applied = 0
        pending = 0
    finally:
        conn.close()

    return {
        "status": status,
        "query": query,
        "cv_loaded": cv_loaded,
        "stats": {
             "total": total_jobs,
             "applied": applied,
             "pending": pending
        }
    }

@app.post("/api/config")
async def update_config(request: ConfigRequest):
    save_config(request.key, request.value)
    return {"status": "updated", "key": request.key, "value": request.value}

@app.post("/api/upload_cv")
async def upload_cv(file: UploadFile = File(...)):
    if file.filename.endswith(".pdf"):
        # We need to save it temporarily or read it directly
        # pdfplumber needs a path or file-like object.
        # file.file is a SpooledTemporaryFile
        text = load_cv_text(file.file)
        print(f"[API] Extracted {len(text)} chars from {file.filename}")
        if len(text) > 50:
            save_config("cv_text", text)
            print("[API] CV Saved to DB.")
            return {"status": "success", "message": "CV Ingested", "length": len(text)}
        
        print("[API] CV text extraction failed (too short).")
        return {"status": "error", "message": "CV text too short"}
    return {"status": "error", "message": "Invalid file type"}

@app.post("/api/command")
async def send_command(request: CommandRequest):
    cmd = request.command.lower()
    if "stop" in cmd:
        save_config("system_status", "STOPPED")
        await manager.broadcast(json.dumps({"type": "status", "payload": "STOPPED"}))
        return {"message": "System Stopping"}
    elif "start" in cmd:
        if not get_config("cv_text"):
             return {"error": "No CV Loaded"}
        save_config("system_status", "RUNNING")
        await manager.broadcast(json.dumps({"type": "status", "payload": "RUNNING"}))
        return {"message": "System Started"}
    return {"message": "Unknown Command"}

@app.websocket("/ws/feed")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive / Ping-Pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- Integration with DB ---
from modules.db import register_broadcast_hook

def broadcast_sync(data):
    """
    Called by modules.db.log_thought (sync).
    We need to bridge this to the async WebSocket manager.
    """
    # Create a task in the running loop
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(manager.broadcast(json.dumps(data)))
    except RuntimeError:
        # No loop running (e.g. script starting up)
        pass

register_broadcast_hook(broadcast_sync)

# --- Static Files ---
# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    import webbrowser
    
    print("[Launcher] 🚀 Mission Control Ready.")
    
    uvicorn.run(app, host="0.0.0.0", port=5000)
