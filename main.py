import tkinter as tk
from tkinter import messagebox
from tkcalendar import Calendar
import sqlite3
from datetime import date, datetime, timedelta

# --- Configuration & Database ---
DB_FILE = "productivity.db"
DAILY_GOAL_VALUE = 75 

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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                month_year TEXT PRIMARY KEY,
                target INTEGER
            )
        ''')
        conn.commit()

def reset_database():
    if messagebox.askyesno("Reset Data", "Are you sure you want to delete ALL logged history? This cannot be undone."):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM logs")
            conn.commit()
        load_today_data()
        update_ui_and_totals()
        messagebox.showinfo("Success", "Database cleared.")

def get_shift_date():
    now = datetime.now()
    if now.hour < 8:
        return str((now - timedelta(days=1)).date())
    return str(now.date())

# --- Monthly Goal Logic ---

def set_monthly_goal():
    try:
        val = int(goal_input_var.get())
        month_key = get_shift_date()[:7] # YYYY-MM
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO goals (month_year, target) VALUES (?, ?) ON CONFLICT(month_year) DO UPDATE SET target=excluded.target", (month_key, val))
            conn.commit()
        update_monthly_total()
    except ValueError:
        messagebox.showerror("Error", "Enter a valid number")

def get_monthly_target():
    month_key = get_shift_date()[:7] # YYYY-MM
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT target FROM goals WHERE month_year = ?", (month_key,))
        row = cursor.fetchone()
        return row[0] if row else 0

# --- Productivity Logic ---

def calculate_rollover_goal():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        today_shift = get_shift_date()
        current_month = today_shift[:7] # YYYY-MM
        
        cursor.execute("SELECT chats FROM logs WHERE entry_date = ?", (today_shift,))
        today_row = cursor.fetchone()
        if today_row and today_row[0] == -1:
            return 0

        # Logic: Count work days in current month only
        cursor.execute("SELECT COUNT(*) FROM logs WHERE chats != -1 AND entry_date LIKE ?", (f"{current_month}%",))
        tracked_days = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT 1 FROM logs WHERE entry_date = ?", (today_shift,))
        if not cursor.fetchone():
            tracked_days += 1
            
        # Logic: Sum past work in current month only
        cursor.execute("""
            SELECT SUM(chats + emails) FROM logs 
            WHERE entry_date != ? 
            AND chats != -1 
            AND entry_date LIKE ?
        """, (today_shift, f"{current_month}%"))
        
        total_past_work = cursor.fetchone()[0] or 0
        
        return (tracked_days * DAILY_GOAL_VALUE) - total_past_work

# --- Timer Variables ---
start_time = None
accumulated_time = timedelta(0)
running = False

def toggle_shift():
    global start_time, running, accumulated_time
    if not running:
        start_time = datetime.now()
        running = True
        start_btn.config(text="Pause Shift", bg="#fff3cd")
        update_live_stats()
    else:
        if start_time:
            accumulated_time += (datetime.now() - start_time)
        running = False
        start_btn.config(text="Resume Shift", bg="#d4edda")

def update_live_stats():
    if running or accumulated_time.total_seconds() > 0:
        if running and start_time:
            current_session = datetime.now() - start_time
            total_elapsed = accumulated_time + current_session
        else:
            total_elapsed = accumulated_time
            
        total_seconds = int(total_elapsed.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        elapsed_str.set(f"{hours:02}:{minutes:02}:{seconds:02}")
        
        if total_seconds > 10:
            total_tasks = (0 if chats_count.get() == -1 else chats_count.get()) + \
                          (0 if emails_count.get() == -1 else emails_count.get())
            hours_decimal = total_seconds / 3600
            avg = total_tasks / hours_decimal
            avg_per_hour.set(f"{avg:.2f}/hr")
        else:
            avg_per_hour.set("---")
            
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

def save_to_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        shift_date = get_shift_date()
        cursor.execute('''
            INSERT INTO logs (entry_date, chats, emails)
            VALUES (?, ?, ?)
            ON CONFLICT(entry_date) DO UPDATE SET
                chats=excluded.chats, emails=excluded.emails
        ''', (shift_date, chats_count.get(), emails_count.get()))
        conn.commit()
    update_monthly_total()

def load_today_data():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        shift_date = get_shift_date()
        cursor.execute("SELECT chats, emails FROM logs WHERE entry_date = ?", (shift_date,))
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
        current_month = get_shift_date()[:7] # YYYY-MM
        cursor.execute("""
            SELECT SUM(CASE WHEN chats < 0 THEN 0 ELSE chats END + 
                       CASE WHEN emails < 0 THEN 0 ELSE emails END) 
            FROM logs WHERE entry_date LIKE ?""", (f"{current_month}%",))
        done = cursor.fetchone()[0] or 0
        monthly_total.set(done)
        
        target = get_monthly_target()
        monthly_left.set(max(0, target - done))

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
    today_shift = get_shift_date()
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chats FROM logs WHERE entry_date = ?", (selected_date,))
        row = cursor.fetchone()
        if row and row[0] == -1:
            cursor.execute("UPDATE logs SET chats=0, emails=0 WHERE entry_date=?", (selected_date,))
        else:
            cursor.execute("INSERT INTO logs (entry_date, chats, emails) VALUES (?, -1, -1) ON CONFLICT(entry_date) DO UPDATE SET chats=-1, emails=-1", (selected_date,))
        conn.commit()
    
    if selected_date == today_shift: 
        load_today_data()
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
root.title("Onecom Tracker")
root.geometry("340x700") # Slightly taller to fit reset button
root.attributes("-topmost", True)

chats_count = tk.IntVar()
emails_count = tk.IntVar()
total_count = tk.Variable()
remaining_count = tk.IntVar()
monthly_total = tk.IntVar()
monthly_left = tk.IntVar()
goal_input_var = tk.StringVar()
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

# Stats Row
stats_row = tk.Frame(root)
stats_row.pack(fill="x", padx=10, pady=5)

m_total_frame = tk.Frame(stats_row)
m_total_frame.pack(side="left", expand=True)
tk.Label(m_total_frame, text=f"{datetime.strptime(get_shift_date(), '%Y-%m-%d').strftime('%b')} Done", font=("Arial", 8)).pack()
tk.Label(m_total_frame, textvariable=monthly_total, font=("Arial", 12, "bold"), fg="#6f42c1").pack()

m_left_frame = tk.Frame(stats_row)
m_left_frame.pack(side="left", expand=True)
tk.Label(m_left_frame, text="Month Left", font=("Arial", 8)).pack()
tk.Label(m_left_frame, textvariable=monthly_left, font=("Arial", 12, "bold"), fg="#28a745").pack()

a_frame = tk.Frame(stats_row)
a_frame.pack(side="left", expand=True)
tk.Label(a_frame, text="Live Avg/Hr", font=("Arial", 8)).pack()
tk.Label(a_frame, textvariable=avg_per_hour, font=("Arial", 12, "bold"), fg="#007bff").pack()

# Live Shift Frame
live_frame = tk.LabelFrame(root, text="Live Shift Session", padx=10, pady=5, fg="blue")
live_frame.pack(pady=5, fill="x", padx=10)
start_btn = tk.Button(live_frame, text="Start Shift", command=toggle_shift, bg="#e1f5fe", font=("Arial", 10, "bold"))
break_btn = tk.Button(live_frame, text="Break", bg="#e1f5fe", font=("Arial", 10, "bold"))
break_btn.pack(fill="x", pady=2)
start_btn.pack(fill="x", pady=2)
timer_label = tk.Label(live_frame, textvariable=elapsed_str, font=("Courier", 18, "bold"), fg="#333")
timer_label.pack()

# Today's Progress
counter_frame = tk.LabelFrame(root, text="Today's Progress", padx=10, pady=10)
counter_frame.pack(pady=5, fill="x", padx=10)
tk.Label(counter_frame, text="REMAINING:").grid(row=0, column=0)
goal_display_label = tk.Label(counter_frame, textvariable=remaining_count, font=("Arial", 22, "bold"))
goal_display_label.grid(row=0, column=1)

tk.Button(counter_frame, text="Chat +1", command=increment_chats, width=9, height=2).grid(row=1, column=0, pady=5)
tk.Button(counter_frame, text="Email +1", command=increment_emails, width=9, height=2).grid(row=1, column=1, pady=5)

tk.Label(counter_frame, text="TOTAL:").grid(row=2, column=0)
tk.Label(counter_frame, textvariable=total_count, font=("Arial", 12, "bold")).grid(row=2, column=1)

# Footer Utilities
footer = tk.Frame(root)
footer.pack(fill="x", side="bottom", pady=10)
tk.Button(footer, text="Reset Database", command=reset_database, fg="gray", font=("Arial", 7)).pack()

chats_count.trace_add("write", update_ui_and_totals)
emails_count.trace_add("write", update_ui_and_totals)
update_ui_and_totals()

root.mainloop()