import tkinter as tk
from tkinter import messagebox
from tkcalendar import Calendar
import sqlite3
from datetime import date, datetime, timedelta

# --- Configuration & Database ---
DB_FILE = "productivity.db"
DAILY_GOAL_VALUE = 54 

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                entry_date TEXT PRIMARY KEY,
                chats INTEGER,
                emails INTEGER
            )
        ''')
        conn.commit()

# --- Productivity Logic ---

def calculate_rollover_goal():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        today = str(date.today())
        cursor.execute("SELECT COUNT(*), SUM(chats + emails) FROM logs WHERE entry_date != ? AND chats != -1", (today,))
        days_count, total_past_work = cursor.fetchone()
        
        cursor.execute("SELECT chats FROM logs WHERE entry_date = ?", (today,))
        today_row = cursor.fetchone()
        if today_row and today_row[0] == -1:
            return 0
        
        days_count = days_count if days_count else 0
        total_past_work = total_past_work if total_past_work else 0
        expected_past_total = days_count * DAILY_GOAL_VALUE
        debt_or_bonus = expected_past_total - total_past_work
        return DAILY_GOAL_VALUE + debt_or_bonus

# --- Timer Variables ---
start_time = None
accumulated_time = timedelta(0)
running = False

def toggle_shift():
    global start_time, running, accumulated_time
    
    if not running:
        # START or RESUME
        start_time = datetime.now()
        running = True
        start_btn.config(text="⏸ Pause Shift", bg="#fff3cd") # Yellow tint
        update_live_stats()
    else:
        # PAUSE
        if start_time:
            accumulated_time += (datetime.now() - start_time)
        running = False
        start_btn.config(text="▶ Resume Shift", bg="#d4edda") # Green tint

def update_live_stats():
    """Background loop for timer and productivity averages"""
    if running or accumulated_time.total_seconds() > 0:
        # Calculate current total elapsed time
        if running and start_time:
            current_session = datetime.now() - start_time
            total_elapsed = accumulated_time + current_session
        else:
            total_elapsed = accumulated_time
            
        # Update Elapsed Time Display
        total_seconds = int(total_elapsed.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        elapsed_str.set(f"{hours:02}:{minutes:02}:{seconds:02}")
        
        # Calculate Productivity Per Hour
        # Only calculate if we've been working for at least 10 seconds to avoid huge spikes
        if total_seconds > 10:
            total_tasks = (0 if chats_count.get() == -1 else chats_count.get()) + \
                          (0 if emails_count.get() == -1 else emails_count.get())
            
            hours_decimal = total_seconds / 3600
            avg = total_tasks / hours_decimal
            avg_per_hour.set(f"{avg:.2f}/hr")
        else:
            avg_per_hour.set("---")
            
    # Always keep the loop alive if the window is open
    if running:
        root.after(1000, update_live_stats)

def update_ui_and_totals(*args):
    goal = calculate_rollover_goal()
    current_done = (0 if chats_count.get() == -1 else chats_count.get()) + \
                   (0 if emails_count.get() == -1 else emails_count.get())
    
    if chats_count.get() == -1:
        total_count.set("REST DAY")
        remaining_count.set(0)
        goal_display_label.config(fg="blue")
    else:
        total_count.set(current_done)
        remaining = goal - current_done
        remaining_count.set(remaining)
        
        if remaining >= 20: goal_display_label.config(fg="red")
        elif 0 < remaining < 20: goal_display_label.config(fg="orange")
        else: goal_display_label.config(fg="green")
    
    update_monthly_total()

# --- Standard Database Functions ---

def save_to_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        today = str(date.today())
        cursor.execute('''
            INSERT INTO logs (entry_date, chats, emails)
            VALUES (?, ?, ?)
            ON CONFLICT(entry_date) DO UPDATE SET
                chats=excluded.chats, emails=excluded.emails
        ''', (today, chats_count.get(), emails_count.get()))
        conn.commit()
    update_monthly_total()

def load_today_data():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        today = str(date.today())
        cursor.execute("SELECT chats, emails FROM logs WHERE entry_date = ?", (today,))
        row = cursor.fetchone()
        if row:
            chats_count.set(row[0])
            emails_count.set(row[1])
        else:
            chats_count.set(0)
            emails_count.set(0)

def update_monthly_total():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute("""
            SELECT SUM(CASE WHEN chats < 0 THEN 0 ELSE chats END + 
                       CASE WHEN emails < 0 THEN 0 ELSE emails END) 
            FROM logs WHERE entry_date LIKE ?""", (f"{current_month}%",))
        result = cursor.fetchone()[0]
        monthly_total.set(result if result else 0)

def increment_chats():
    if chats_count.get() != -1:
        chats_count.set(chats_count.get() + 1)
        save_to_db()

def increment_emails():
    if emails_count.get() != -1:
        emails_count.set(emails_count.get() + 1)
        save_to_db()

def toggle_selected_day_off():
    selected_date = str(cal.selection_get())
    today = str(date.today())
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chats FROM logs WHERE entry_date = ?", (selected_date,))
        row = cursor.fetchone()
        if row and row[0] == -1:
            cursor.execute("UPDATE logs SET chats=0, emails=0 WHERE entry_date=?", (selected_date,))
        else:
            cursor.execute("INSERT INTO logs (entry_date, chats, emails) VALUES (?, -1, -1) ON CONFLICT(entry_date) DO UPDATE SET chats=-1, emails=-1", (selected_date,))
    if selected_date == today: load_today_data()
    show_history_for_date()
    update_ui_and_totals()

def show_history_for_date(event=None):
    formatted_date = str(cal.selection_get())
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chats, emails FROM logs WHERE entry_date = ?", (formatted_date,))
        row = cursor.fetchone()
    if row:
        if row[0] == -1:
            history_label.config(text=f"{formatted_date}: REST DAY", fg="blue")
        else:
            history_label.config(text=f"{formatted_date}: {row[0]} Ch | {row[1]} Em", fg="black")
    else:
        history_label.config(text=f"No data for {formatted_date}", fg="gray")

# --- UI Setup ---
init_db()
root = tk.Tk()
root.title("Shift Tracker Pro")
root.geometry("340x620")
root.attributes("-topmost", True)

chats_count = tk.IntVar()
emails_count = tk.IntVar()
total_count = tk.Variable()
remaining_count = tk.IntVar()
monthly_total = tk.IntVar()
elapsed_str = tk.StringVar(value="00:00:00")
avg_per_hour = tk.StringVar(value="0.00/hr")

load_today_data()

# Calendar Frame
cal_frame = tk.LabelFrame(root, text="Calendar & History", padx=5, pady=5)
cal_frame.pack(pady=5, fill="x", padx=10)
cal = Calendar(cal_frame, selectmode='day', date_pattern='y-mm-dd')
cal.pack()
cal.bind("<<CalendarSelected>>", show_history_for_date)
history_label = tk.Label(cal_frame, text="Select a date", font=("Arial", 9, "bold"))
history_label.pack()
day_off_btn = tk.Button(cal_frame, text="Toggle Day Off", command=toggle_selected_day_off, font=("Arial", 8))
day_off_btn.pack(pady=2)

# Live Real-Time Stats Frame
live_frame = tk.LabelFrame(root, text="Live Shift Session", padx=10, pady=10, fg="blue")
live_frame.pack(pady=5, fill="x", padx=10)

start_btn = tk.Button(live_frame, text="▶ Start Shift", command=toggle_shift, bg="#e1f5fe", font=("Arial", 10, "bold"))
start_btn.pack(fill="x", pady=2)

timer_label = tk.Label(live_frame, textvariable=elapsed_str, font=("Courier", 18, "bold"), fg="#333")
timer_label.pack()

# Bottom Stats Row
stats_row = tk.Frame(root)
stats_row.pack(fill="x", padx=15, pady=5)

# Monthly Total
m_frame = tk.Frame(stats_row)
m_frame.pack(side="left", expand=True)
tk.Label(m_frame, text=f"{datetime.now().strftime('%b')} Total", font=("Arial", 8)).pack()
tk.Label(m_frame, textvariable=monthly_total, font=("Arial", 14, "bold"), fg="#6f42c1").pack()

# Live Average
a_frame = tk.Frame(stats_row)
a_frame.pack(side="right", expand=True)
tk.Label(a_frame, text="Live Avg/Hr", font=("Arial", 8)).pack()
tk.Label(a_frame, textvariable=avg_per_hour, font=("Arial", 14, "bold"), fg="#007bff").pack()

# Live Progress Frame
counter_frame = tk.LabelFrame(root, text="Today's Progress", padx=10, pady=10)
counter_frame.pack(pady=5, fill="x", padx=10)

tk.Label(counter_frame, text="REMAINING:").grid(row=0, column=0)
goal_display_label = tk.Label(counter_frame, textvariable=remaining_count, font=("Arial", 22, "bold"))
goal_display_label.grid(row=0, column=1)

tk.Button(counter_frame, text="Chat +1", command=increment_chats, width=9, height=2).grid(row=1, column=0, pady=5)
tk.Button(counter_frame, text="Email +1", command=increment_emails, width=9, height=2).grid(row=1, column=1, pady=5)

tk.Label(counter_frame, text="TOTAL:").grid(row=2, column=0)
tk.Label(counter_frame, textvariable=total_count, font=("Arial", 12, "bold")).grid(row=2, column=1)

chats_count.trace_add("write", update_ui_and_totals)
emails_count.trace_add("write", update_ui_and_totals)
update_ui_and_totals()

root.mainloop()