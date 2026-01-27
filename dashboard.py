import streamlit as st
import pandas as pd
import os
import json
import time
import pdfplumber
from modules.db import get_connection, save_config, get_config, log_thought

st.set_page_config(page_title="Commuter AI Core", layout="wide", page_icon="🐜")

# --- CSS: Immersive Dark Mode & Chat Styling ---
st.markdown("""
    <style>
    /* Global Clean Up */
    .main .block-container { padding-top: 2rem; }
    
    /* Chat Styling */
    .stChatMessage { background-color: #1e1e1e; border: 1px solid #333; border-radius: 10px; margin-bottom: 10px; }
    .stChatMessage p { color: #E0E0E0 !important; font-family: 'Segoe UI', sans-serif; }
    
    /* User Message distinct color */
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #2b2b2b; }
    
    /* Status Badges */
    .status-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
    .status-running { background-color: #1b5e20; color: #fff; }
    .status-stopped { background-color: #b71c1c; color: #fff; }
    .status-idle { background-color: #f57f17; color: #000; }
    
    /* Hide Deploy Button */
    .stDeployButton { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- Logic: Command Processor ---
def process_user_command(command: str):
    """
    Translates natural language chat into system actions.
    """
    cmd = command.lower().strip()
    
    # 1. Stop / Pause
    if any(x in cmd for x in ["stop", "pause", "halt", "kill"]):
        save_config("system_status", "STOPPED")
        return "🛑 **SYSTEM HALTED.** The bot will finish its current step and stop."
    
    # 2. Start / Resume
    elif any(x in cmd for x in ["start", "resume", "go", "run"]):
        if not get_config("cv_text"):
            return "⚠️ **Cannot Start:** No CV loaded. Please upload one in the Sidebar."
        save_config("system_status", "RUNNING")
        return "🚀 **SYSTEM ENGAGED.** Orchestrator is now live."
    
    # 3. Search / Find
    elif any(x in cmd for x in ["search", "find", "look for", "hunt"]):
        # Extract query: "search for python developer" -> "python developer"
        # Simple heuristic: take everything after the keyword
        for trigger in ["search for ", "find ", "look for ", "hunt "]:
            if trigger in cmd:
                new_query = command.split(trigger)[1].strip()
                save_config("search_query", new_query)
                return f"🎯 **Target Updated:** Now hunting for `{new_query}`. Scout dispatched."
        return "❓ I didn't catch the job title. Try 'Search for [Job Title]'."
    
    # 4. Clear Memory / Reset (Optional safety)
    elif "reset" in cmd or "clear" in cmd:
        return "🧹 Reset command received (Functionality masked for safety)."

    # Default
    return f"🤖 I heard: '{command}'. \n\n**Available Commands:**\n- 'Start' / 'Stop'\n- 'Find [Job Title]'"

# --- Logic: Data Fetching ---
def get_system_state():
    status = get_config("system_status") or "IDLE"
    feeds = 0
    jobs = 0
    applied = 0
    
    conn = get_connection()
    try:
        feeds = pd.read_sql("SELECT COUNT(*) FROM job_queue WHERE status='PENDING' AND company='LinkedIn Search'", conn).iloc[0,0]
        jobs = pd.read_sql("SELECT COUNT(*) FROM job_queue WHERE status='PENDING' AND company!='LinkedIn Search'", conn).iloc[0,0]
        applied = pd.read_sql("SELECT COUNT(*) FROM job_queue WHERE status='APPLIED'", conn).iloc[0,0]
    except:
        pass
    finally:
        conn.close()
        
    return status, feeds, jobs, applied

def load_cv_text(uploaded_file):
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            return "".join([p.extract_text() or "" for p in pdf.pages]).strip()
    except Exception as e:
        return ""

# --- UI: Sidebar (Configuration) ---
with st.sidebar:
    st.header("🎛️ Mission Control")
    
    # Live Status Indicator
    status, feeds, jobs, applied = get_system_state()
    
    if status == "RUNNING":
        st.markdown('<div class="status-badge status-running">🟢 ONLINE</div>', unsafe_allow_html=True)
    elif status == "STOPPED" or status == "SOS":
        st.markdown(f'<div class="status-badge status-stopped">🔴 {status}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge status-idle">🟡 IDLE</div>', unsafe_allow_html=True)

    st.divider()
    
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Feeds", feeds)
    c2.metric("Jobs", jobs)
    c3.metric("Sent", applied)
    
    st.divider()

    # Manual Overrides
    st.caption("🔧 Manual Configuration")
    curr_query = get_config("search_query") or "Not Set"
    st.text_input("Current Target", value=curr_query, disabled=True)
    
    uploaded_file = st.file_uploader("Update CV (PDF)", type=["pdf"])
    if uploaded_file and st.button("📄 Ingest CV"):
        text = load_cv_text(uploaded_file)
        if len(text) > 50:
            save_config("cv_text", text)
            st.toast("CV Ingested Successfully!")

    # Live Mode Toggle
    st.divider()
    live_mode = st.toggle("⚡ Real-Time Uplink", value=True, help="Auto-refreshes the feed every 2 seconds.")

# --- UI: Main Chat Interface ---
st.title("🧠 Neural Core Uplink")

# 1. SOS Banner (High Priority)
if status == "SOS":
    sos_msg = get_config("sos_message")
    st.error(f"🚨 **INTERVENTION REQUIRED**\n\n{sos_msg}\n\n1. Check the Bot Window.\n2. Fix the issue (e.g. solve CAPTCHA).\n3. Type 'Resume' below or click Resolve.")
    if st.button("✅ Resolved"):
        save_config("system_status", "RUNNING")
        save_config("sos_message", "")
        st.rerun()

# 2. Chat History / Neural Feed
# We use a container to hold the feed so it can be refreshed
chat_container = st.container()

with chat_container:
    conn = get_connection()
    try:
        # Fetch last 50 thoughts/messages
        history = pd.read_sql("SELECT * FROM agent_thoughts ORDER BY id DESC LIMIT 50", conn)
        # Reverse to show oldest at top (standard chat feel) - actually, for a "Feed" usually newest is top. 
        # Let's keep newest at top for "System Log" feel, or newest at bottom for "Chat" feel?
        # User wants "Chat Bot". Chat bots have newest at bottom.
        history = history.iloc[::-1] 
    except:
        history = pd.DataFrame()
    conn.close()

    if not history.empty:
        for _, row in history.iterrows():
            agent = row['agent_name']
            content = row['thought_content']
            
            # Icon & Role Mapping
            avatar = "🤖"
            role = "assistant"
            
            if agent == "User":
                avatar = "👤"
                role = "user"
            elif agent == "System":
                avatar = "🖥️"
            elif "Vision" in agent: 
                avatar = "👁️"
            elif "Navigator" in agent: 
                avatar = "🧭"
            elif "Scout" in agent: 
                avatar = "📡"
                
            with st.chat_message(role, avatar=avatar):
                # Bold the Agent Name
                st.markdown(f"**{agent}**")
                
                # Check for JSON (Vision Data)
                try:
                    if "{" in content and "}" in content and ("action" in content or "page_type" in content):
                        data = json.loads(content)
                        if "page_type" in data:
                            action = data.get('action', 'UNKNOWN').upper()
                            target = data.get('target_som_id', 'N/A')
                            reason = data.get('reasoning', '')
                            
                            st.markdown(f"**Decision:** `{action}` on Element `{target}`")
                            st.caption(f"Reasoning: {reason}")
                        else:
                            st.json(data)
                    else:
                        st.write(content)
                except:
                    st.write(content)
                
                # Show screenshot if available
                if row['visual_context_path'] and os.path.exists(row['visual_context_path']):
                    with st.expander("Visual Context"):
                        st.image(row['visual_context_path'])

# 3. Chat Input (The Interruption Mechanism)
if prompt := st.chat_input("Command the Swarm (e.g., 'Stop', 'Find Java Jobs')..."):
    # A. Log User Input
    log_thought("User", prompt)
    
    # B. Process Command
    response = process_user_command(prompt)
    
    # C. Log System Response
    log_thought("System", response)
    
    # D. Force Update
    st.rerun()

# 4. Real-Time Loop
if live_mode:
    time.sleep(2)
    st.rerun()
