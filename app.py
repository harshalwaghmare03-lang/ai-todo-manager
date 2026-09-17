from datetime import datetime, timedelta
import os
import sqlite3
from google import genai
import pandas as pd
import streamlit as st

# --- DATABASE SETUP ---
def init_db():
  conn = sqlite3.connect("todos.db")
  c = conn.cursor()
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
      "INSERT INTO tasks (title, due_date, priority, est_time, done, created_at)"
      " VALUES (?, ?, ?, ?, 0, ?)",
      (title, due_date, priority, est_time, current_time),
  )
  conn.commit()
  conn.close()


def update_task_status(task_id, done):
  conn = sqlite3.connect("todos.db")
  c = conn.cursor()
  c.execute(
      "UPDATE tasks SET done = ? WHERE id = ?", (1 if done else 0, task_id)
  )
  conn.commit()
  conn.close()


def clear_completed_db():
  conn = sqlite3.connect("todos.db")
  c = conn.cursor()
  c.execute("DELETE FROM tasks WHERE done = 1")
  conn.commit()
  conn.close()


init_db()

# --- STREAMLIT UI & CLIENT INITIALIZATION ---
st.set_page_config(
    page_title="AI To-Do Manager", page_icon="🚀", layout="wide"
)
st.title("🚀 All-in-One AI To-Do Manager")

# Retrieve API key: 1. Streamlit Secrets -> 2. OS Environment -> 3. Sidebar Manual Input
API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
MODEL_NAME = "gemini-2.5-flash"

if not API_KEY or not API_KEY.startswith("AIzaSy"):
  with st.sidebar.expander("🔑 API Key Settings", expanded=True):
    API_KEY = st.text_input(
        "Enter Gemini API Key (starts with AIzaSy):",
        value=API_KEY if API_KEY.startswith("AIzaSy") else "",
        type="password",
        help="Generate at https://aistudio.google.com/app/apikey",
    )

client = None
if API_KEY and API_KEY.startswith("AIzaSy"):
  try:
    client = genai.Client(api_key=API_KEY.strip())
  except Exception as e:
    st.sidebar.error(f"Client init failed: {e}")

# Session state initialization
if "ai_breakdown" not in st.session_state:
  st.session_state.ai_breakdown = ""
if "ai_schedule" not in st.session_state:
  st.session_state.ai_schedule = ""
if "ai_coach_advice" not in st.session_state:
  st.session_state.ai_coach_advice = ""

# --- SIDEBAR: DAILY SCORE ---
st.sidebar.header("📊 Today's Progress Score")
df_score = load_tasks()
if not df_score.empty:
  total_tasks = len(df_score)
  completed_tasks = len(df_score[df_score["done"] == 1])
  score = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

  st.sidebar.metric(
      label="Productivity Score",
      value=f"{score}/100",
      delta=f"{completed_tasks} completed",
  )
  st.sidebar.progress(score / 100)

  if score == 100:
    st.sidebar.info("🌟 Perfect score! Everything completed.")
  elif score >= 50:
    st.sidebar.info("⚡ Strong momentum! Keep pushing.")
  else:
    st.sidebar.info("💡 Begin with the highest priority task.")
else:
  st.sidebar.metric(label="Productivity Score", value="0/100")
  st.sidebar.info("🎯 Add your first task to kick off the day.")

# --- NAVIGATION TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Tasks & NLP Input",
    "AI Goal Breakdown",
    "Schedule Optimizer",
    "AI Coach",
    "📊 Progress Analytics",
])

# --- TAB 1: Tasks & NLP Input ---
with tab1:
  st.subheader("Add Task via Natural Language")
  nl_input = st.text_input(
      "Type naturally (e.g., 'Finish project report by Friday high priority')",
      key="nl_in",
  )

  if st.button("Parse & Add Task"):
    if not nl_input.strip():
      st.warning("Please enter task details first.")
    elif not client:
      st.error(
          "Valid API key starting with 'AIzaSy' is required. Enter it in the"
          " sidebar."
      )
    else:
      with st.spinner("Parsing task..."):
        prompt = (
            f"Extract details from this text: '{nl_input}'. "
            "Output strictly in format: Title | Due Date (YYYY-MM-DD or"
            " 'Today/Tomorrow') | Priority (High/Medium/Low) | Estimated Time"
            " (e.g., '30 mins')"
        )
        try:
          response = client.models.generate_content(
              model=MODEL_NAME, contents=prompt
          )
          parts = [p.strip() for p in response.text.strip().split("|")]
          title = parts[0] if len(parts) > 0 else nl_input
          due = parts[1] if len(parts) > 1 else "Today"
          prio = parts[2] if len(parts) > 2 else "Medium"
          est = parts[3] if len(parts) > 3 else "30 mins"
          add_task_db(title, due, prio, est)
          st.success(f"Added: {title}")
          st.rerun()
        except Exception:
          add_task_db(nl_input, "Today", "Medium", "30 mins")
          st.success("Added with default attributes.")
          st.rerun()

  st.subheader("Your Task Board")
  df_tasks = load_tasks()
  if not df_tasks.empty:
    for _, row in df_tasks.iterrows():
      col1, col2, col3, col4 = st.columns([0.5, 0.2, 0.15, 0.15])
      with col1:
        is_done = st.checkbox(
            row["title"], value=bool(row["done"]), key=f"task_{row['id']}"
        )
        if is_done != bool(row["done"]):
          update_task_status(row["id"], is_done)
          st.rerun()
      with col2:
        st.text(f"📅 {row['due_date']}")
      with col3:
        st.text(f"⚡ {row['priority']}")
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
  big_goal = st.text_input(
      "Enter a complex goal:",
      placeholder="e.g., Build a personal portfolio website",
  )
  if st.button("Decompose Goal"):
    if not big_goal.strip():
      st.warning("Please enter a goal statement.")
    elif not client:
      st.error("Valid Gemini API key required in the sidebar.")
    else:
      with st.spinner("Breaking down goal..."):
        prompt = (
            f"Break down this goal into 4 actionable subtasks with short"
            f" descriptions: {big_goal}"
        )
        try:
          res = client.models.generate_content(
              model=MODEL_NAME, contents=prompt
          )
          st.session_state.ai_breakdown = res.text
        except Exception as e:
          st.error(f"Error calling model: {e}")

  if st.session_state.ai_breakdown:
    st.markdown(st.session_state.ai_breakdown)

# --- TAB 3: Schedule Optimizer ---
with tab3:
  st.subheader("Daily Time-Block Planner")
  if st.button("Generate Optimized Schedule"):
    df = load_tasks()
    pending = df[df["done"] == 0]["title"].tolist()
    if not pending:
      st.warning("No pending tasks to schedule.")
    elif not client:
      st.error("Valid Gemini API key required in the sidebar.")
    else:
      with st.spinner("Structuring schedule..."):
        prompt = (
            "Create an optimized chronological hourly time-block schedule for"
            f" today for these tasks: {pending}"
        )
        try:
          res = client.models.generate_content(
              model=MODEL_NAME, contents=prompt
          )
          st.session_state.ai_schedule = res.text
        except Exception as e:
          st.error(f"Error calling model: {e}")

  if st.session_state.ai_schedule:
    st.markdown(st.session_state.ai_schedule)

# --- TAB 4: AI Coach ---
with tab4:
  st.subheader("Productivity Coaching")
  if st.button("Get Daily Advice"):
    df = load_tasks()
    completed = len(df[df["done"] == 1])
    pending = len(df[df["done"] == 0])
    if not client:
      st.error("Valid Gemini API key required in the sidebar.")
    else:
      with st.spinner("Consulting coach..."):
        prompt = (
            f"I completed {completed} tasks and have {pending} remaining. Give"
            " a 2-paragraph direct, energizing productivity critique and next"
            " focus."
        )
        try:
          res = client.models.generate_content(
              model=MODEL_NAME, contents=prompt
          )
          st.session_state.ai_coach_advice = res.text
        except Exception as e:
          st.error(f"Error calling model: {e}")

  if st.session_state.ai_coach_advice:
    st.markdown(st.session_state.ai_coach_advice)

# --- TAB 5: Progress Analytics ---
with tab5:
  st.subheader("📊 Performance Analytics")
  df_analytics = load_tasks()

  if not df_analytics.empty:
    df_analytics["created_at"] = df_analytics["created_at"].fillna(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    df_analytics["date_only"] = df_analytics["created_at"].apply(
        lambda x: x.split(" ")[0]
    )

    time_frame = st.selectbox(
        "Select Analytics Range:", ["Past Day", "Past Week", "Past Month"]
    )
    now = datetime.now()

    if time_frame == "Past Day":
      today_str = now.strftime("%Y-%m-%d")
      filtered_df = df_analytics[df_analytics["date_only"] == today_str]
    elif time_frame == "Past Week":
      start_week = (now - timedelta(days=7)).strftime("%Y-%m-%d")
      filtered_df = df_analytics[df_analytics["date_only"] >= start_week]
    else:
      start_month = (now - timedelta(days=30)).strftime("%Y-%m-%d")
      filtered_df = df_analytics[df_analytics["date_only"] >= start_month]

    if not filtered_df.empty:
      chart_data = (
          filtered_df.groupby("priority").size().reset_index(name="Task Count")
      )
      st.bar_chart(data=chart_data, x="priority", y="Task Count")
      st.write(
          f"Total tasks in selected period: **{len(filtered_df)}** (Done:"
          f" {len(filtered_df[filtered_df['done'] == 1])}, Pending:"
          f" {len(filtered_df[filtered_df['done'] == 0])})"
      )
    else:
      st.info("No task records found for the selected time range.")
  else:
    st.info("No task data recorded yet.")
