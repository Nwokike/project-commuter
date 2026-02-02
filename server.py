"""
Project Commuter - Main Server
FastAPI + WebSocket for real-time agent communication and intervention mode
"""

import os
import asyncio
import json
import base64
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents import root_agent
from tools.browser_tools import (
    set_screenshot_callback,
    set_intervention_mode,
    is_intervention_mode,
    click_element,
    type_text,
    take_screenshot,
    close_browser,
)

APP_NAME = "project_commuter"
session_service = InMemorySessionService()
runner: Optional[Runner] = None
active_websockets: list[WebSocket] = []
current_session_id: Optional[str] = None
current_user_id: str = "default_user"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    
    async def broadcast_screenshot(screenshot_base64: str):
        for ws in active_websockets:
            try:
                await ws.send_json({
                    "type": "screenshot",
                    "data": screenshot_base64
                })
            except:
                pass
    
    set_screenshot_callback(broadcast_screenshot)
    
    yield
    
    await close_browser()


app = FastAPI(title="Project Commuter", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class UserProfile(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = ""
    location: Optional[str] = ""
    job_titles: Optional[list[str]] = []
    skills: Optional[list[str]] = []
    experience_summary: Optional[str] = ""


class InterventionAction(BaseModel):
    action: str
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    selector: Optional[str] = None


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/api/session/create")
async def create_session():
    """Create a new session."""
    global current_session_id
    import uuid
    session_id = str(uuid.uuid4())[:8]
    
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=current_user_id,
        session_id=session_id,
        state={}
    )
    
    current_session_id = session_id
    return {"session_id": session_id, "status": "created"}


@app.post("/api/profile")
async def update_profile(profile: UserProfile):
    """Update user profile stored in session state."""
    global current_session_id
    
    if not current_session_id:
        await create_session()
    
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=current_user_id,
        session_id=current_session_id
    )
    
    if session:
        session.state["user:full_name"] = profile.full_name
        session.state["user:email"] = profile.email
        session.state["user:phone"] = profile.phone
        session.state["user:location"] = profile.location
        session.state["user:job_titles"] = profile.job_titles
        session.state["user:skills"] = profile.skills
        session.state["user:experience_summary"] = profile.experience_summary
    
    return {"status": "updated", "profile": profile.model_dump()}


@app.post("/api/chat")
async def chat(message: ChatMessage):
    """Send a message to the agent and get a response."""
    global current_session_id
    
    if not current_session_id:
        await create_session()
    
    try:
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=message.message)]
        )
        
        response_text = ""
        async for event in runner.run_async(
            user_id=current_user_id,
            session_id=current_session_id,
            new_message=content
        ):
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        response_text += part.text
        
        return {
            "status": "success",
            "response": response_text,
            "intervention_mode": is_intervention_mode()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/intervention/action")
async def intervention_action(action: InterventionAction):
    """Handle user actions during intervention mode."""
    try:
        if action.action == "click":
            result = await click_element(x=action.x, y=action.y, selector=action.selector)
        elif action.action == "type":
            result = await type_text(selector=action.selector, text=action.text or "")
        elif action.action == "screenshot":
            result = await take_screenshot()
        elif action.action == "resume":
            set_intervention_mode(False)
            result = {"status": "success", "message": "Automation resumed"}
        elif action.action == "pause":
            set_intervention_mode(True)
            result = {"status": "success", "message": "Automation paused"}
        else:
            result = {"status": "error", "error": f"Unknown action: {action.action}"}
        
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/intervention/status")
async def intervention_status():
    """Get current intervention mode status."""
    return {"intervention_mode": is_intervention_mode()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await websocket.accept()
    active_websockets.append(websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Project Commuter"
        })
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "chat":
                message = data.get("message", "")
                
                await websocket.send_json({
                    "type": "thinking",
                    "message": "Processing your request..."
                })
                
                try:
                    global current_session_id
                    if not current_session_id:
                        await create_session()
                    
                    content = types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=message)]
                    )
                    
                    async for event in runner.run_async(
                        user_id=current_user_id,
                        session_id=current_session_id,
                        new_message=content
                    ):
                        if hasattr(event, 'content') and event.content:
                            for part in event.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    await websocket.send_json({
                                        "type": "agent_response",
                                        "message": part.text
                                    })
                        
                        if hasattr(event, 'actions'):
                            await websocket.send_json({
                                "type": "agent_action",
                                "actions": str(event.actions)
                            })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
            
            elif data.get("type") == "intervention":
                action_data = data.get("action", {})
                action = InterventionAction(**action_data)
                result = await intervention_action(action)
                await websocket.send_json({
                    "type": "intervention_result",
                    "result": result
                })
    
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
    except Exception as e:
        if websocket in active_websockets:
            active_websockets.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    # Use PORT environment variable for Render, default to 5000 for local
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
