"""
Project Commuter - Main Server
FastAPI + WebSocket for real-time agent communication and intervention mode
"""

import os
import asyncio
import json
import base64
import io
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import litellm 
from pypdf import PdfReader

from agents import root_agent
from models.groq_config import GROQ_MODELS
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
    """Create a new session with DEFAULT context to prevent crashes."""
    global current_session_id
    import uuid
    session_id = str(uuid.uuid4())[:8]
    
    # Initialize with placeholder data so the AI doesn't crash on {user:full_name}
    initial_state = {
        "user:full_name": "Candidate",
        "user:email": "Not specified",
        "user:phone": "",
        "user:location": "Not specified",
        "user:job_titles": [],
        "user:skills": [],
        "user:experience_summary": "No CV uploaded yet.",
        "user:education": "",
        "discovered_jobs": []
    }
    
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=current_user_id,
        session_id=session_id,
        state=initial_state
    )
    
    current_session_id = session_id
    return {"session_id": session_id, "status": "created", "state": initial_state}


@app.post("/api/upload_cv")
async def upload_cv(file: UploadFile = File(...)):
    """
    Parse a PDF CV and inject the data directly into the session state.
    Uses Llama 8B (via LiteLLM) to extract structured data.
    """
    global current_session_id
    
    if not current_session_id:
        await create_session()
        
    try:
        # 1. Extract Text from PDF
        contents = await file.read()
        pdf_file = io.BytesIO(contents)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
            
        # 2. Parse with LLM
        prompt = f"""
        Extract the following details from this CV text into a JSON object:
        - full_name
        - email
        - phone
        - location
        - job_titles (list of roles they can apply for)
        - skills (list of top technical skills)
        - experience_summary (a 3-sentence summary of their career)
        - education (latest degree)

        CV TEXT:
        {text[:4000]}
        
        Return ONLY valid JSON.
        """
        
        response = litellm.completion(
            model=GROQ_MODELS["parser"]["primary"],
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        extracted_data = json.loads(response.choices[0].message.content)
        
        # 3. Update Session State
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=current_user_id,
            session_id=current_session_id
        )
        
        if session:
            session.state["user:full_name"] = extracted_data.get("full_name", "Candidate")
            session.state["user:email"] = extracted_data.get("email", "")
            session.state["user:phone"] = extracted_data.get("phone", "")
            session.state["user:location"] = extracted_data.get("location", "")
            session.state["user:job_titles"] = extracted_data.get("job_titles", [])
            session.state["user:skills"] = extracted_data.get("skills", [])
            session.state["user:experience_summary"] = extracted_data.get("experience_summary", "")
            session.state["user:education"] = extracted_data.get("education", "")
            
        return {"status": "success", "profile": extracted_data}
        
    except Exception as e:
        print(f"Error parsing CV: {str(e)}")
        return {"status": "error", "error": str(e)}


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
                        # Handle Text Response
                        if hasattr(event, 'content') and event.content:
                            for part in event.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    await websocket.send_json({
                                        "type": "agent_response",
                                        "message": part.text
                                    })
                        
                        # Handle Actions (Tools) - Clean up the log output
                        if hasattr(event, 'actions') and event.actions:
                            actions_desc = []
                            try:
                                for action in event.actions:
                                    if hasattr(action, 'tool_name'):
                                        name = action.tool_name
                                        args = getattr(action, 'tool_args', '')
                                        desc = f"Use tool: {name}"
                                        if args:
                                            args_str = str(args)
                                            if len(args_str) > 50:
                                                args_str = args_str[:47] + "..."
                                            desc += f"({args_str})"
                                        actions_desc.append(desc)
                                    elif hasattr(action, 'name'):
                                        actions_desc.append(f"Calling: {action.name}")
                                    else:
                                        s = str(action)
                                        if "skip_summarization" not in s: 
                                            actions_desc.append(s[:50] + "..." if len(s) > 50 else s)
                            except:
                                actions_desc.append("Thinking...")

                            if actions_desc:
                                await websocket.send_json({
                                    "type": "agent_action",
                                    "actions": " | ".join(actions_desc)
                                })
                        
                        # Handle Agent Transfers (Reasoning steps)
                        if hasattr(event, 'transfer_to_agent') and event.transfer_to_agent:
                            await websocket.send_json({
                                "type": "agent_action",
                                "actions": f"Delegating to {event.transfer_to_agent}"
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
