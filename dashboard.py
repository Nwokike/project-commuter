import streamlit as st
import sqlite3
import pandas as pd
import os
import time
import hashlib

# Ensure we point to the correct DB path relative to execution
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "bot_memory.db")
SCREENSHOT_PATH = "latest_view.png"

def get_con():
    # Helper to connect to DB
    return sqlite3.connect(DB_PATH)

st.set_page_config(page_title="Project Commuter", layout="wide", page_icon="🐜")

st.title("🐜 Project Commuter: Flight Deck")

# --- Metric Bar ---
conn = get_con()
try:
    # Quick sanity checks for table existence
    queue_count = pd.read_sql("SELECT COUNT(*) FROM job_queue WHERE status='PENDING'", conn).iloc[0,0]
    applied_count = pd.read_sql("SELECT COUNT(*) FROM job_queue WHERE status='APPLIED'", conn).iloc[0,0]
    # Check for active SOS events (last 5 minutes)
    sos_events = pd.read_sql("SELECT * FROM application_logs WHERE action='SOS_TRIGGERED' ORDER BY timestamp DESC LIMIT 1", conn)
except Exception as e:
    queue_count = 0
    applied_count = 0
    sos_events = pd.DataFrame()
conn.close()

col1, col2, col3 = st.columns(3)
col1.metric("Pending Jobs", queue_count)
col2.metric("Applied", applied_count)

sos_active = False
latest_sos_q = ""
latest_sos_hash = ""

if not sos_events.empty:
    last_event = sos_events.iloc[0]
    # Parse "HASH::Question Text"
    try:
        details = last_event['details']
        latest_sos_hash, latest_sos_q = details.split("::", 1)
        col3.metric("SOS Status", "ACTIVE 🚨", delta_color="inverse")
        sos_active = True
    except:
        col3.metric("SOS Status", "Standby 🟢")
else:
    col3.metric("SOS Status", "Standby 🟢")

# --- Tabs ---
tab1, tab2 = st.tabs(["🔴 Live Mission", "🆘 SOS Resolution Center"])

with tab1:
    st.subheader("Bot's Eye View")
    if os.path.exists(SCREENSHOT_PATH):
        # Auto-refreshing image mechanism could be added, for now static load
        st.image(SCREENSHOT_PATH, caption=f"Snapshot at {time.ctime(os.path.getmtime(SCREENSHOT_PATH))}", use_container_width=True)
    else:
        st.info("No screenshot available. Bot might be sleeping or scouting.")

    st.subheader("Mission Logs")
    conn = get_con()
    try:
        logs = pd.read_sql("SELECT timestamp, action, details FROM application_logs ORDER BY timestamp DESC LIMIT 10", conn)
        st.dataframe(logs, use_container_width=True)
    except:
        st.write("No logs yet.")
    conn.close()

with tab2:
    st.header("Human Intervention Required")
    
    if sos_active:
        st.error(f"The Bot is STUCK on this question:")
        st.markdown(f"### ❓ `{latest_sos_q}`")
        
        with st.form("sos_response_form"):
            user_answer = st.text_input("Type the answer the bot should use:", placeholder="e.g., 5 years, Yes, No...")
            submitted = st.form_submit_button("🚀 Send Answer & Resume Bot")
            
            if submitted and user_answer:
                conn = get_con()
                cursor = conn.cursor()
                try:
                    # Save to Answer Bank with the EXACT hash the bot is polling for
                    cursor.execute(
                        "INSERT OR REPLACE INTO answer_bank (question_hash, question_text, answer_text, source, created_at) VALUES (?, ?, ?, 'USER_OVERRIDE', CURRENT_TIMESTAMP)", 
                        (latest_sos_hash, latest_sos_q, user_answer)
                    )
                    conn.commit()
                    st.success("Answer sent! The bot should pick it up in < 2 seconds.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Database Error: {e}")
                finally:
                    conn.close()
    else:
        st.success("No active SOS alerts. The bot is running autonomously.")
        st.write("You can still manually add answers to the bank below to train it for the future.")
        
        # Manual Training Interface
        with st.expander("➕ Add Training Data Manually"):
            t_q = st.text_input("Question Text")
            t_a = st.text_input("Answer")
            if st.button("Add to Brain"):
                if t_q and t_a:
                    h = hashlib.md5(t_q.encode()).hexdigest()
                    c = get_con()
                    c.execute("INSERT OR REPLACE INTO answer_bank (question_hash, question_text, answer_text, source) VALUES (?, ?, ?, 'USER_OVERRIDE')", (h, t_q, t_a))
                    c.commit()
                    c.close()
                    st.success("Added.")

# Auto-refresh for polling UI (Basic implementation)
if sos_active:
    time.sleep(2)
    st.rerun()