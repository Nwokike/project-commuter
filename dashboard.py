import streamlit as st
import pandas as pd
import os
import time
import json
import pdfplumber
from modules.db import get_connection, save_config, get_config

st.set_page_config(page_title="Project Commuter", layout="wide", page_icon="🐜")

# --- Helper Functions ---
def load_cv_text(uploaded_file):
    """Extracts text from PDF."""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = "".join([p.extract_text() or "" for p in pdf.pages])
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {e}"

def get_status():
    return get_config("system_status") or "IDLE"

def resolve_sos():
    """Resumes the bot."""
    save_config("system_status", "RUNNING")
    save_config("sos_message", "")
    st.success("✅ System Resumed!")
    time.sleep(1)
    st.rerun()

# --- HEADER & STATUS ---
st.title("🐜 Project Commuter: Command Center")

status = get_status()

# 🔴 SOS STATE
if status == "SOS":
    st.error("🚨 SOS TRIGGERED! The Agent has paused.")
    
    msg = get_config("sos_message")
    st.info(f"**Reason:** {msg}")
    
    st.markdown("""
    **How to fix:**
    1. Open the Bot's Chrome window.
    2. Perform the action manually (e.g., Log in, solve Captcha, click the button).
    3. Click the button below to give control back to the AI.
    """)
    
    if st.button("✅ I have fixed it (Resume Agent)", type="primary", use_container_width=True):
        resolve_sos()

# 🟡 WAITING STATE
elif status == "IDLE" or not get_config("cv_text"):
    st.warning("⏳ System Waiting: Please Configure in 'Mission Control' below.")

# 🟢 RUNNING STATE
elif status == "RUNNING":
    st.success("🟢 System is Autonomous. Watching for jobs...")
    if st.button("🛑 EMERGENCY STOP"):
        save_config("system_status", "STOPPED")
        st.rerun()

st.divider()

# --- TABS ---
tab1, tab2 = st.tabs(["🎛️ Mission Control", "🧠 Neural Feed"])

# ==============================================================================
# TAB 1: MISSION CONTROL (Inputs)
# ==============================================================================
with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Targeting")
        
        # Load existing
        curr_query = get_config("search_query") or "Software Engineer"
        curr_loc = get_config("job_location") or "Remote"
        
        new_query = st.text_input("Job Search Query", value=curr_query)
        new_loc = st.text_input("Location", value=curr_loc)
        
        st.caption("Note: 'Easy Apply' filter is enforced automatically by the Scout.")

    with col2:
        st.subheader("👤 Identity (CV)")
        
        # CV Status Indicator
        cv_text = get_config("cv_text")
        if cv_text:
            st.success(f"✅ CV Loaded ({len(cv_text)} chars)")
            with st.expander("View Loaded CV Text"):
                st.text(cv_text[:500] + "...")
        else:
            st.error("❌ No CV Loaded. Bot cannot apply.")
            
        # Uploader
        uploaded_file = st.file_uploader("Upload New CV (PDF)", type=["pdf"])
        if uploaded_file:
            if st.button("📄 Process & Ingest CV"):
                with st.spinner("Reading PDF..."):
                    text = load_cv_text(uploaded_file)
                    if len(text) > 100:
                        save_config("cv_text", text)
                        st.toast("CV Ingested Successfully!", icon="✅")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Could not extract text. Is this a scanned image?")

    st.divider()
    if st.button("💾 Save Configuration & Open Gate", type="primary", use_container_width=True):
        save_config("search_query", new_query)
        save_config("job_location", new_loc)
        # If paused, start it
        if status != "RUNNING":
            save_config("system_status", "RUNNING")
        st.toast("Configuration Saved. Orchestrator Notified.", icon="📡")
        time.sleep(1)
        st.rerun()

# ==============================================================================
# TAB 2: NEURAL FEED (Live Logs)
# ==============================================================================
with tab2:
    c1, c2 = st.columns([4, 1])
    with c1:
        st.caption("Live stream of Agent decisions and internal monologue.")
    with c2:
        if st.button("🔄 Refresh"):
            st.rerun()

    # Auto-refresh loop using empty container
    placeholder = st.empty()
    
    # Fetch Data
    conn = get_connection()
    try:
        # Get last 20 thoughts
        df = pd.read_sql("SELECT * FROM agent_thoughts ORDER BY id DESC LIMIT 20", conn)
    except Exception as e:
        st.error(f"Database Error: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()

    if not df.empty:
        for _, row in df.iterrows():
            with st.container(border=True):
                # Header
                col_a, col_b = st.columns([1, 5])
                col_a.caption(row['timestamp'])
                
                # Color code agents
                agent = row['agent_name']
                if "Orchestrator" in agent: icon = "🤖"
                elif "Vision" in agent: icon = "👁️"
                elif "Navigator" in agent: icon = "🧭"
                elif "Scout" in agent: icon = "📡"
                else: icon = "👻"
                
                col_a.markdown(f"**{icon} {agent}**")
                
                # Content
                content = row['thought_content']
                
                # Attempt JSON Pretty Print
                try:
                    if "{" in content and "}" in content:
                        parsed = json.loads(content)
                        # Special handling for Vision decisions
                        if "page_type" in parsed:
                            action = parsed.get('action', 'unknown').upper()
                            reason = parsed.get('reasoning', '')
                            
                            if action == "SOS":
                                st.error(f"**DECISION: {action}**")
                            else:
                                st.success(f"**DECISION: {action}**")
                            
                            st.write(f"_{reason}_")
                            with st.expander("Raw JSON"):
                                st.json(parsed)
                        else:
                            st.json(parsed)
                    else:
                        st.write(content)
                except:
                    st.write(content)

                # Image
                img_path = row['visual_context_path']
                if img_path and os.path.exists(img_path):
                    st.image(img_path, width=400)
    else:
        st.info("No thoughts recorded yet. Start the bot!")