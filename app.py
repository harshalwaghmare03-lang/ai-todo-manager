import sqlite3
from datetime import datetime, timedelta
import google.generativeai as genai
import pandas as pd
import streamlit as st

# Configure Gemini API with your provided key
genai.configure(api_key="AQ.Ab8RN6JFCw6YBFy806H0IpmxjoQnYXOQ2s78scNObCyZWk78tQ")
model = genai.GenerativeModel("gemini-3.6-flash")

# Database Initialization with Timestamp tracking
def init_db():
    conn = sqlite3.connect("todos.db")
    c = conn.cursor()
    # Added created_at column to support historical analysis
    c.execute(
        """CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    due_date TEXT,
                    priority TEXT,
                    est_time TEXT,
                    done INTEGER,
                    created_at TEXT
                )"""
    )
    # Check if column exists (migration helper if database already exists)
    c.execute("PRAGMA table_info(tasks)")
    columns = [col[1] for col in c.fetchall()]
    if "created_at" not in columns:
        c.execute("ALTER TABLE tasks ADD COLUMN created_at TEXT")
    conn.commit()
    conn.close()

def load_tasks():
    conn = sqlite3.connect("todos.db")
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

def add_task_db(title, due_date, priority, est_time):
    conn = sqlite3.connect("todos.db")
    c = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO tasks (title, due_date, priority, est_time, done, created_at) VALUES (?, ?, ?, ?, 0, ?)",
        (title, due_date, priority, est_time, current_time),
    )
    conn.commit()
    conn.close()

def update_task_status(task_id, done):
    conn = sqlite3.connect("todos.db")
    c = conn.cursor()
    c.execute("UPDATE tasks SET done = ? WHERE id = ?", (1 if done else 0, task_id))
    conn.commit()
    conn.close()

def clear_completed_db():
    conn = sqlite3.connect("todos.db")
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE done = 1")
    conn.commit()
    conn.close()

init_db()

# Initialize session state for AI caching
if "ai_breakdown" not in st.session_state:
    st.session_state.ai_breakdown = ""
if "ai_schedule" not in st.session_state:
    st.session_state.ai_schedule = ""
if "ai_coach_advice" not in st.session_state:
    st.session_state.ai_coach_advice = ""

st.title("🚀 All-in-One AI To-Do Manager")

# --- SIDEBAR: DAILY SCORE & EXCITING THOUGHT ---
st.sidebar.header("📊 Today's Progress Score")
df_score = load_tasks()
if not df_score.empty:
    total_tasks = len(df_score)
    completed_tasks = len(df_score[df_score["done"] == 1])
    score = int((completed_tasks / total_tasks) * 100)
    
    st.sidebar.metric(label="Productivity Score", value=f"{score}/100", delta=f"{completed_tasks} completed")
    st.sidebar.progress(score / 100)
    
    if score == 100:
        st.sidebar.info("🌟 Perfect day! You smashed every single target out of the park!")
    elif score >= 50:
        st.sidebar.info("⚡ You're in the flow zone! Momentum is building, keep pushing!")
    else:
        st.sidebar.info("💡 A journey of a thousand miles begins with a single task. Take it one step at a time!")
else:
    st.sidebar.metric(label="Productivity Score", value="0/100")
    st.sidebar.info("🎯 Your board is clean. Add a task to kickstart your day!")


# App Navigation Tabs (Added Progress Analytics tab)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Tasks & NLP Input", 
    "AI Goal Breakdown", 
    "Schedule Optimizer", 
    "AI Coach",
    "📊 Progress Analytics"
])

# --- TAB 1: Tasks & NLP Input ---
with tab1:
    st.subheader("Add Task via Natural Language")
    nl_input = st.text_input("Type naturally (e.g., 'Finish project report by Friday high priority')", key="nl_in")
    
    if st.button("Parse & Add Task"):
        if nl_input:
            with st.spinner("AI is parsing your task..."):
                prompt = (
                    f"Extract the following details from this text: '{nl_input}'. "
                    "Return output strictly in this pipe-separated format: Task Title | Due Date (YYYY-MM-DD or 'Today/Tomorrow') | Priority (High/Medium/Low) | Estimated Time (e.g., '30 mins')"
                )
                try:
                    res = model.generate_content(prompt).text.strip()
                    parts = res.split("|")
                    title = parts[0].strip()
                    due = parts[1].strip()
                    prio = parts[2].strip()
                    time_est = parts[3].strip()
                    add_task_db(title, due, prio, time_est)
                    st.success(f"Added: {title}")
                    st.rerun()
                except Exception as e:
                    add_task_db(nl_input, "Anytime", "Medium", "30 mins")
                    st.success("Added with default attributes!")
                    st.rerun()

    st.subheader("Your Task Board")
    df_tasks = load_tasks()
    if not df_tasks.empty:
        for index, row in df_tasks.iterrows():
            col1, col2, col3, col4 = st.columns([0.5, 0.2, 0.15, 0.15])
            with col1:
                is_done = st.checkbox(row["title"], value=bool(row["done"]), key=f"task_{row['id']}")
                if is_done != bool(row["done"]):
                    update_task_status(row["id"], is_done)
                    st.rerun()
            with col2:
                st.text(f"Due: {row['due_date']}")
            with col3:
                st.text(f"Prio: {row['priority']}")
            with col4:
                st.text(f"⏱️ {row['est_time']}")
                
        if st.button("Clear Completed Tasks"):
            clear_completed_db()
            st.rerun()
    else:
        st.info("No tasks recorded yet.")

# --- TAB 2: AI Goal Breakdown ---
with tab2:
    st.subheader("Decompose Big Goals")
    big_goal = st.text_input("Enter a complex goal:", placeholder="e.g., Build a personal portfolio website")
    if st.button("Decompose Goal"):
        if big_goal:
            with st.spinner("Breaking down your goal..."):
                prompt = f"Break down this goal into 4 concrete subtasks: {big_goal}"
                st.session_state.ai_breakdown = model.generate_content(prompt).text
                
    if st.session_state.ai_breakdown:
        st.markdown(st.session_state.ai_breakdown)

# --- TAB 3: Schedule Optimizer ---
with tab3:
    st.subheader("Daily Time-Block Planner")
    if st.button("Generate Optimized Schedule"):
        df = load_tasks()
        pending = df[df["done"] == 0]["title"].tolist()
        if pending:
            with st.spinner("AI is organizing your daily schedule..."):
                prompt = f"Create an optimized chronological hourly time-block schedule for today based on these pending tasks: {pending}"
                st.session_state.ai_schedule = model.generate_content(prompt).text
        else:
            st.warning("No pending tasks to schedule!")
            
    if st.session_state.ai_schedule:
        st.markdown(st.session_state.ai_schedule)

# --- TAB 4: AI Coach ---
with tab4:
    st.subheader("Your Productivity Coach")
    if st.button("Get Daily Advice"):
        df = load_tasks()
        completed_count = len(df[df["done"] == 1])
        pending_count = len(df[df["done"] == 0])
        with st.spinner("Analyzing progress..."):
            prompt = f"I have completed {completed_count} tasks and have {pending_count} pending tasks. Give a short, encouraging productivity coaching summary and actionable advice."
            st.session_state.ai_coach_advice = model.generate_content(prompt).text
            
    if st.session_state.ai_coach_advice:
        st.markdown(st.session_state.ai_coach_advice)

# --- NEW TAB 5: PROGRESS ANALYTICS ---
with tab5:
    st.subheader("📊 Performance Analytics")
    
    df_analytics = load_tasks()
    
    if not df_analytics.empty:
        # Fill missing timestamps with current time for historical fallback stability
        df_analytics["created_at"] = df_analytics["created_at"].fillna(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        df_analytics["date_only"] = df_analytics["created_at"].apply(lambda x: x.split(" ")[0])
        
        # User Selection for Time Frames
        time_frame = st.selectbox("Select Analytics Range:", ["Past Day (Hourly View)", "Past Week", "Past Month"])
        
        now = datetime.now()
        
        if time_frame == "Past Day (Hourly View)":
            st.write("### Tasks Logged Today")
            # Grouping item count by today's date
            today_str = now.strftime("%Y-%m-%d")
            today_df = df_analytics[df_analytics["date_only"] == today_str]
            
            if not today_df.empty:
                chart_data = today_df.groupby("priority").size().reset_index(name="Task Count")
                st.bar_chart(data=chart_data, x="priority", y="Task Count")
            else:
                st.info("No tasks recorded today yet. Add some to populate the chart!")
                
        elif time_frame == "Past Week":
            st.write("### Weekly Complete vs Pending Distribution")
            start_week = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            filtered_df = df_analytics[df_analytics["date_only"] >= start_week]
            
            if not filtered_df.empty:
                # Create pivot structure of dates vs status counts
                weekly_data = filtered_df.groupby(["date_only", "done"]).size().unstack(fill_value=0)
                weekly_data = weekly_data.rename(columns={0: "Pending Tasks", 1: "Completed Tasks"})
                st.bar_chart(weekly_data)
            else:
                st.info("No task logging trends found for this week.")
                
        elif time_frame == "Past Month":
            st.write("### Monthly Trendline Matrix")
            start_month = (now - timedelta(days=30)).strftime("%Y-%m-%d")
