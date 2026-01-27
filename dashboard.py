import streamlit as st
import pandas as pd
import os
import json
import time
import pdfplumber
from modules.db import get_connection, save_config, get_config

st.set_page_config(page_title="Commuter Mission Control", layout="wide", page_icon="🐜")

# --- CSS FIX: High Contrast Text & Responsive Buttons ---
st.markdown("""
    <style>
    /* Make buttons full width */
    .stButton>button { width: 100%; border-radius: 5px; }
    
    /* Force chat message text to be white for visibility */
    .stChatMessage p { color: #FFFFFF !important; }
    .stChatMessage { background-color: #2e2e2e; border: 1px solid #444; }
    
    /* Status banners */
    .success-box { padding: 10px; background-color: #1b5e20; border-radius: 5px; color: white; }
    .error-box { padding: 10px; background-color: #b71c1c; border-radius: 5px; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def load_cv_text(uploaded_file):
    """Safely extracts text from PDF."""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            return "".join([p.extract_text() or "" for p in pdf.pages]).strip()
    except Exception as e:
        return ""

def get_status():
    """Reads the global system status flag."""
    return get_config("system_status") or "IDLE"

def resolve_sos():
    """Unblocks the bot and resumes operation."""
    save_config("system_status", "RUNNING")
    save_config("sos_message", "")
    st.success("✅ System Resumed! The bot will retry in the next loop.")
    time.sleep(1)
    st.rerun()

# --- SIDEBAR: Configuration & Controls ---
with st.sidebar:
    st.header("🎛️ Mission Control")
    
    # 1. Status Indicator
    status = get_status()
    if status == "RUNNING":
        st.markdown('<div class="success-box">🟢 SYSTEM ONLINE</div>', unsafe_allow_html=True)
        if st.button("🛑 STOP SYSTEM"):
            save_config("system_status", "STOPPED")
            st.rerun()
    elif status == "SOS":
        st.markdown('<div class="error-box">🚨 SOS TRIGGERED</div>', unsafe_allow_html=True)
    else:
        st.warning("🟡 System Idle")

    st.divider()

    # 2. Targeting
    st.subheader("🎯 Targeting")
    curr_query = get_config("search_query") or "Software Engineer"
    new_query = st.text_input("Job Query", value=curr_query)
    st.caption("Note: 'Easy Apply' is automatically enforced.")
    
    # 3. Identity
    st.subheader("👤 Identity")
    cv_text = get_config("cv_text")
    if cv_text:
        st.info(f"✅ CV Loaded ({len(cv_text)} chars)")
    else:
        st.error("❌ No CV Loaded")
        
    uploaded_file = st.file_uploader("Upload CV (PDF)", type=["pdf"])
    if uploaded_file and st.button("📄 Ingest CV"):
        text = load_cv_text(uploaded_file)
        if len(text) > 50:
            save_config("cv_text", text)
            st.toast("CV Saved Successfully!", icon="✅")
            time.sleep(1)
            st.rerun()

    st.divider()
    
    # 4. Master Start Button
    if st.button("💾 Save Config & START", type="primary"):
        save_config("search_query", new_query)
        save_config("system_status", "RUNNING")
        st.toast("Configuration Saved. Orchestrator Notified!", icon="🚀")
        time.sleep(1)
        st.rerun()

# --- MAIN AREA: Neural Feed ---
st.title("🧠 Neural Feed")

# 🚨 SOS ALERT SECTION
if status == "SOS":
    with st.container(border=True):
        st.error("🚨 **ACTION REQUIRED: The Bot is stuck.**")
        st.write(f"**Reason:** {get_config('sos_message')}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.info("👉 Please open the Chrome window, perform the required action (e.g., Log In), then click Resolve.")
        with c2:
            if st.button("✅ I Have Fixed It (Resume)"):
                resolve_sos()

# 📡 LIVE LOGS CONTROLS
col_feed, col_refresh = st.columns([5, 1])
with col_feed:
    st.caption("Real-time decision logs from the Agent Swarm.")
with col_refresh:
    if st.button("🔄 Refresh Feed"):
        st.rerun()

# Fetch latest thoughts from DB
conn = get_connection()
try:
    thoughts = pd.read_sql("SELECT * FROM agent_thoughts ORDER BY id DESC LIMIT 20", conn)
except:
    thoughts = pd.DataFrame()
conn.close()

if not thoughts.empty:
    for _, row in thoughts.iterrows():
        agent = row['agent_name']
        content = row['thought_content']
        ts = row['timestamp'].split(" ")[1] # Just time
        
        # Icon mapping
        avatar = "🤖"
        if "Vision" in agent: avatar = "👁️"
        elif "Navigator" in agent: avatar = "🧭"
        elif "Scout" in agent: avatar = "📡"
        
        with st.chat_message(name=agent, avatar=avatar):
            st.markdown(f"**{agent}** ({ts})")
            
            # Try to parse JSON for cleaner display
            try:
                if "{" in content and "}" in content:
                    parsed = json.loads(content)
                    if "page_type" in parsed:
                        # Pretty print Vision decisions
                        action = parsed.get('action', 'UNKNOWN').upper()
                        target = parsed.get('target_som_id', 'N/A')
                        reason = parsed.get('reasoning', '')
                        
                        st.markdown(f"**Action:** `{action}` on ID `{target}`")
                        st.text(f"Reason: {reason}")
                    else:
                        st.json(parsed)
                else:
                    st.write(content)
            except:
                st.write(content)
            
            # Display Screenshot if available
            if row['visual_context_path'] and os.path.exists(row['visual_context_path']):
                with st.expander("View Vision Context"):
                    st.image(row['visual_context_path'])
else:
    st.info("No logs found. Please Configure and Start the system via the Sidebar.")
