import tkinter as tk
from tkinter import messagebox
from tkcalendar import Calendar
import sqlite3
from datetime import date, datetime

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

def save_to_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        today = str(date.today())
        cursor.execute('''
            INSERT INTO logs (entry_date, chats, emails)
            VALUES (?, ?, ?)
            ON CONFLICT(entry_date) DO UPDATE SET
                chats=excluded.chats,
                emails=excluded.emails
        ''', (today, chats_count.get(), emails_count.get()))
        conn.commit()
    update_monthly_total()

def calculate_rollover_goal():
    """Calculates goal based on work days only (chats != -1)."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        today = str(date.today())
        
        # Count days that have data and are NOT marked as -1 (day off)
        cursor.execute("SELECT COUNT(*), SUM(chats + emails) FROM logs WHERE entry_date != ? AND chats != -1", (today,))
        days_count, total_past_work = cursor.fetchone()
        
        # Check if today is a day off
        cursor.execute("SELECT chats FROM logs WHERE entry_date = ?", (today,))
        today_row = cursor.fetchone()
        if today_row and today_row[0] == -1:
            return 0
        
        if not days_count or days_count == 0:
            return DAILY_GOAL_VALUE
        
        total_past_work = total_past_work if total_past_work else 0
        expected_past_total = days_count * DAILY_GOAL_VALUE
        debt_or_bonus = expected_past_total - total_past_work
        
        return DAILY_GOAL_VALUE + debt_or_bonus

# --- Logic ---
def update_ui_and_totals(*args):
    """Refreshes the math and the color logic."""
    # 1. Update Remaining Goal
    goal = calculate_rollover_goal()
    current_done = chats_count.get() + emails_count.get()
    
    # Handle Day Off View
    if goal == 0 and chats_count.get() == -1:
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

def toggle_selected_day_off():
    """Marks the date selected on the CALENDAR as a day off or work day."""
    selected_date = str(cal.selection_get())
    today = str(date.today())
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chats FROM logs WHERE entry_date = ?", (selected_date,))
        row = cursor.fetchone()
        
        if row and row[0] == -1:
            # It's currently a day off, change to work day (0)
            cursor.execute("UPDATE logs SET chats=0, emails=0 WHERE entry_date=?", (selected_date,))
        else:
            # Change to day off (-1)
            cursor.execute('''
                INSERT INTO logs (entry_date, chats, emails) VALUES (?, -1, -1)
                ON CONFLICT(entry_date) DO UPDATE SET chats=-1, emails=-1
            ''', (selected_date,))
            
    # If the date we just changed is "Today", update the live counters
    if selected_date == today:
        load_today_data()
    
    show_history_for_date() # Refresh history label
    update_ui_and_totals()  # Refresh rollover math

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

def show_history_for_date(event=None):
    formatted_date = str(cal.selection_get())
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chats, emails FROM logs WHERE entry_date = ?", (formatted_date,))
        row = cursor.fetchone()
    
    if row:
        if row[0] == -1:
            history_label.config(text=f"{formatted_date}: REST DAY", fg="blue")
            day_off_btn.config(text="Unmark Day Off")
        else:
            history_label.config(text=f"{formatted_date}: {row[0]} Chats | {row[1]} Emails", fg="black")
            day_off_btn.config(text="Mark Selected as Day Off")
    else:
        history_label.config(text=f"No data for {formatted_date}", fg="gray")
        day_off_btn.config(text="Mark Selected as Day Off")

# --- UI Setup ---
init_db()
root = tk.Tk()
root.title("Shift Tracker")
root.geometry("340x530")
root.attributes("-topmost", True)

chats_count = tk.IntVar()
emails_count = tk.IntVar()
total_count = tk.Variable()
remaining_count = tk.IntVar()
monthly_total = tk.IntVar()

load_today_data()

# Layout
cal_frame = tk.LabelFrame(root, text="Calendar & History", padx=10, pady=10)
cal_frame.pack(pady=10, fill="x", padx=10)

cal = Calendar(cal_frame, selectmode='day', date_pattern='y-mm-dd')
cal.pack(pady=5)
cal.bind("<<CalendarSelected>>", show_history_for_date)

history_label = tk.Label(cal_frame, text="Select a date", font=("Arial", 9, "bold"))
history_label.pack()

day_off_btn = tk.Button(cal_frame, text="Mark Selected as Day Off", command=toggle_selected_day_off)
day_off_btn.pack(pady=5)

month_name = datetime.now().strftime('%B')
tk.Label(root, text=f"{month_name} Monthly Total:").pack()
tk.Label(root, textvariable=monthly_total, font=("Arial", 12, "bold"), fg="#6f42c1").pack()

counter_frame = tk.LabelFrame(root, text="Live Progress (Today)", padx=10, pady=10)
counter_frame.pack(pady=10, fill="x", padx=10)

tk.Label(counter_frame, text="REMAINING GOAL:").grid(row=0, column=0)
goal_display_label = tk.Label(counter_frame, textvariable=remaining_count, font=("Arial", 24, "bold"))
goal_display_label.grid(row=0, column=1)

tk.Button(counter_frame, text="Chat +1", command=increment_chats, width=10).grid(row=1, column=0, pady=5)
tk.Button(counter_frame, text="Email +1", command=increment_emails, width=10).grid(row=1, column=1, pady=5)

tk.Label(counter_frame, text="TODAY'S TOTAL:").grid(row=2, column=0)
tk.Label(counter_frame, textvariable=total_count, font=("Arial", 12, "bold")).grid(row=2, column=1)

# Initialize
chats_count.trace_add("write", update_ui_and_totals)
emails_count.trace_add("write", update_ui_and_totals)
update_ui_and_totals()

root.mainloop()