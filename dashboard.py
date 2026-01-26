import streamlit as st
import sqlite3
import pandas as pd
import os
import time

ST_DB_PATH = os.path.join("data", "bot_memory.db")
SCREENSHOT_PATH = "latest_view.png"

def get_con():
    return sqlite3.connect(ST_DB_PATH)

st.set_page_config(page_title="Project Commuter", layout="wide")
st.title("🐜 Project Commuter: Flight Deck")

# Sidebar Stats
conn = get_con()
try:
    queue_count = pd.read_sql("SELECT COUNT(*) FROM job_queue WHERE status='PENDING'", conn).iloc[0,0]
    applied_count = pd.read_sql("SELECT COUNT(*) FROM job_queue WHERE status='APPLIED'", conn).iloc[0,0]
    sos_count = pd.read_sql("SELECT COUNT(*) FROM application_logs WHERE action='SOS_TRIGGERED'", conn).iloc[0,0]
except:
    queue_count = 0
    applied_count = 0
    sos_count = 0
conn.close()

col1, col2, col3 = st.columns(3)
col1.metric("Pending Jobs", queue_count)
col2.metric("Applied", applied_count)
col3.metric("SOS Events", sos_count, delta_color="inverse")

# Main View
tab1, tab2 = st.tabs(["🔴 Live View", "🆘 SOS Resolution"])

with tab1:
    st.subheader("Bot Vision")
    if os.path.exists(SCREENSHOT_PATH):
        st.image(SCREENSHOT_PATH, caption="Latest Viewport", use_container_width=True)
        st.caption(f"Last updated: {time.ctime(os.path.getmtime(SCREENSHOT_PATH))}")
    else:
        st.warning("No screenshot available yet.")
    
    st.subheader("Recent Logs")
    conn = get_con()
    logs = pd.read_sql("SELECT * FROM application_logs ORDER BY timestamp DESC LIMIT 10", conn)
    st.dataframe(logs, use_container_width=True)
    conn.close()

with tab2:
    st.subheader("Manual Override")
    user_q = st.text_input("Question Text (copy from logs)")
    user_a = st.text_input("Your Answer")
    if st.button("Save Answer"):
        if user_q and user_a:
            c = get_con()
            # Simple hash for demo
            import hashlib
            q_hash = hashlib.md5(user_q.encode()).hexdigest()
            try:
                c.execute("INSERT OR REPLACE INTO answer_bank (question_hash, question_text, answer_text, source) VALUES (?, ?, ?, 'USER_OVERRIDE')", 
                          (q_hash, user_q, user_a))
                c.commit()
                st.success("Answer saved! Bot will pick this up.")
            except Exception as e:
                st.error(f"Error: {e}")
            c.close()

if st.button("Refresh"):
    st.rerun()
