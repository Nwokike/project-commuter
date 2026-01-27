import streamlit as st
import sqlite3
import pandas as pd
import os
import time
import json
from modules.db import get_connection, save_config, get_config
# We import ingest_cv dynamically or assume it's available via path
# For simplicity in this phase, we'll implement a lightweight ingest helper here 
# to avoid complex import paths until the next phase refactor.
import pdfplumber

st.set_page_config(page_title="Project Commuter", layout="wide", page_icon="🐜")

# --- Helper Functions ---
def load_cv_text(uploaded_file):
    """Extracts text from the uploaded PDF."""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {e}"

# --- Header ---
st.title("🐜 Project Commuter: Command Center")

# --- Tabs ---
tab1, tab2 = st.tabs(["🎛️ Mission Control", "🧠 Neural Feed"])

# ==============================================================================
# TAB 1: MISSION CONTROL (Configuration)
# ==============================================================================
with tab1:
    st.header("Job Search Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Load existing config if available
        current_query = get_config("search_query") or "Software Engineer Remote"
        current_location = get_config("job_location") or "United States"
        
        new_query = st.text_input("Job Search Query", value=current_query)
        new_location = st.text_input("Location / Region", value=current_location)
        
        browser_mode = st.radio("Browser Mode", ["Headless (Invisible)", "Headed (Visible)"], index=1)
        
    with col2:
        st.subheader("Context Injection")
        uploaded_cv = st.file_uploader("Upload your CV (PDF)", type=["pdf"])
        
        if uploaded_cv:
            if st.button("📄 Process & Ingest CV"):
                with st.spinner("Extracting text from CV..."):
                    cv_text = load_cv_text(uploaded_cv)
                    if len(cv_text) > 50:
                        save_config("cv_text", cv_text)
                        st.success(f"CV Ingested! ({len(cv_text)} characters)")
                        with st.expander("View Extracted Text"):
                            st.text(cv_text[:1000] + "...")
                    else:
                        st.error("Could not extract text. Is the PDF scanned?")

    # Save Button
    if st.button("💾 Save Mission Configuration", type="primary"):
        save_config("search_query", new_query)
        save_config("job_location", new_location)
        save_config("headless_mode", "true" if "Headless" in browser_mode else "false")
        st.toast("Configuration Saved!", icon="✅")

# ==============================================================================
# TAB 2: NEURAL FEED (Live Agent Thoughts)
# ==============================================================================
with tab2:
    st.header("Live Agent Telemetry")
    
    # Auto-refresh mechanism
    if st.toggle("Auto-Refresh Feed", value=True):
        time.sleep(2)
        st.rerun()
        
    conn = get_connection()
    try:
        # Fetch latest thoughts
        thoughts = pd.read_sql(
            "SELECT * FROM agent_thoughts ORDER BY timestamp DESC LIMIT 10", 
            conn
        )
    except:
        thoughts = pd.DataFrame()
    conn.close()

    if not thoughts.empty:
        for index, row in thoughts.iterrows():
            with st.container(border=True):
                # Header: Agent Name & Time
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.caption(row['timestamp'])
                    st.markdown(f"**🤖 {row['agent_name']}**")
                
                with c2:
                    # Content Parsing
                    content = row['thought_content']
                    
                    # Try to parse JSON for pretty printing
                    try:
                        json_content = json.loads(content)
                        
                        # Special formatting for Visionary decisions
                        if "page_type" in json_content:
                            color = "green" if json_content['page_type'] == 'success' else "blue"
                            st.markdown(f":{color}[**Decision:** {json_content.get('action', 'unknown').upper()}]")
                            st.write(f"Reasoning: {json_content.get('reasoning', 'No reasoning provided.')}")
                            st.json(json_content, expanded=False)
                        else:
                            st.code(content, language="json")
                            
                    except:
                        # Fallback for plain text thoughts
                        st.write(content)
                        
                    # Show Image if available
                    if row['visual_context_path'] and os.path.exists(row['visual_context_path']):
                        with st.expander("View Visual Context"):
                            st.image(row['visual_context_path'])
    else:
        st.info("No agent activity recorded yet. Start the bot to see thoughts here.")