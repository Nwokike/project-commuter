import streamlit as st
import pandas as pd
import os
import json
import time
import pdfplumber
from modules.db import get_connection, save_config, get_config

st.set_page_config(page_title="Commuter Mission Control", layout="wide", page_icon="🐜")

# --- CSS: Make buttons full-width and messages distinct ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; }
    .stChatMessage { background-color: #262730; border-radius: 10px; padding: 10px; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def load_cv_text(uploaded_file):
    """Safely extracts text from PDF."""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = "".join([p.extract_text() or "" for p in pdf.pages])
        return text.strip()
    except Exception as e:
        return ""

def get_status():
    """Reads the global system status flag."""
    return get_config("system_status") or "IDLE"

def resolve_sos():
    """Unblocks the bot."""
    save_config("system_status", "RUNNING")
    save_config("sos_message", "")
    st.success("✅ Resuming Agent...")
    time.sleep(1)
    st.rerun()

# --- SIDEBAR: Configuration & Identity ---
with st.sidebar:
    st.header("🎛️ Mission Control")
    
    # 1. Status Indicator
    status = get_status()
    if status == "RUNNING":
        st.success("🟢 System Online")
        if st.button("🛑 STOP SYSTEM"):
            save_config("system_status", "STOPPED")
            st.rerun()
    elif status == "SOS":
        st.error("🚨 SOS TRIGGERED")
    else:
        st.warning("🟡 System Idle")

    st.divider()

    # 2. Targeting
    st.subheader("🎯 Targeting")
    curr_query = get_config("search_query") or "Software Engineer"
    new_query = st.text_input("Job Query", value=curr_query)
    
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
            st.toast("CV Saved Successfully!")
            time.sleep(1)
            st.rerun()

    st.divider()
    
    # 4. Master Start Button
    if st.button("💾 Save Config & START", type="primary"):
        save_config("search_query", new_query)
        save_config("system_status", "RUNNING")
        st.toast("Orchestrator Notified!", icon="🚀")
        time.sleep(1)
        st.rerun()

# --- MAIN AREA: Neural Feed & SOS ---
st.title("🧠 Neural Feed")

# 🚨 SOS ALERT SECTION
if status == "SOS":
    with st.container(border=True):
        st.error("🚨 **ACTION REQUIRED: The Bot is stuck.**")
        st.write(f"**Reason:** {get_config('sos_message')}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.info("👉 Please open the Chrome window and perform the action manually (e.g., Log In).")
        with c2:
            if st.button("✅ I Have Fixed It (Resume)"):
                resolve_sos()

# 📡 LIVE LOGS SECTION
col_feed, col_refresh = st.columns([5, 1])
with col_feed:
    st.caption("Real-time decision logs from the Agent Swarm.")
with col_refresh:
    if st.button("🔄 Refresh"):
        st.rerun()

# Fetch latest thoughts
conn = get_connection()
try:
    thoughts = pd.read_sql("SELECT * FROM agent_thoughts ORDER BY id DESC LIMIT 15", conn)
except:
    thoughts = pd.DataFrame()
conn.close()

if not thoughts.empty:
    for _, row in thoughts.iterrows():
        agent = row['agent_name']
        content = row['thought_content']
        ts = row['timestamp'].split(" ")[1] # Just time
        
        # Icon mapping
        role = "assistant"
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
                        # Vision Decision pretty print
                        st.markdown(f"**Action:** `{parsed.get('action').upper()}`")
                        st.markdown(f"**Reason:** _{parsed.get('reasoning')}_")
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
    st.info("No logs found. Start the system via the Sidebar.")