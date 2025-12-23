import tkinter as tk
from tkcalendar import Calendar
import sqlite3
from datetime import date

# --- Database Management ---
DB_FILE = "productivity.db"

def init_db():
    """Create the table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # We store chats and emails separately so history is more detailed
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            entry_date TEXT PRIMARY KEY,
            chats INTEGER,
            emails INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db():
    """Save or Update today's counts in the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    today = str(date.today())
    
    # "UPSERT" logic: If date exists, update it. If not, insert it.
    cursor.execute('''
        INSERT INTO logs (entry_date, chats, emails)
        VALUES (?, ?, ?)
        ON CONFLICT(entry_date) DO UPDATE SET
            chats=excluded.chats,
            emails=excluded.emails
    ''', (today, chats_count.get(), emails_count.get()))
    
    conn.commit()
    conn.close()

def load_today_data():
    """Load today's saved progress from the database on startup."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    today = str(date.today())
    cursor.execute("SELECT chats, emails FROM logs WHERE entry_date = ?", (today,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        chats_count.set(row[0])
        emails_count.set(row[1])

# --- Logic ---
def update_total(*args):
    new_total = chats_count.get() + emails_count.get()
    total_count.set(new_total)
    save_to_db() # Saves to SQLite file every time a button is clicked

def increment_chats():
    chats_count.set(chats_count.get() + 1)

def increment_emails():
    emails_count.set(emails_count.get() + 1)

def reset_counts():
    chats_count.set(0)
    emails_count.set(0)

def show_history_for_date(event=None):
    formatted_date = str(cal.selection_get())
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT chats, emails FROM logs WHERE entry_date = ?", (formatted_date,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        history_label.config(text=f"{formatted_date}\nChats: {row[0]} | Emails: {row[1]} | Total: {row[0]+row[1]}")
    else:
        history_label.config(text=f"No data for {formatted_date}")

# --- UI Setup ---
init_db() # Ensure DB exists before UI starts

root = tk.Tk()
root.title("Productivity Tracker")
root.geometry("300x520") 
root.attributes("-topmost", True)

chats_count = tk.IntVar(value=0)
emails_count = tk.IntVar(value=0)
total_count = tk.IntVar(value=0)

# Load data BEFORE adding traces to avoid saving blank data over existing data
load_today_data()

# Add traces AFTER loading data
chats_count.trace_add("write", update_total)
emails_count.trace_add("write", update_total)

# --- Layout ---
# Calendar Section (Moved to top for better flow)
cal_frame = tk.LabelFrame(root, text="History Log", padx=10, pady=10)
cal_frame.pack(pady=10, fill="both", expand=True, padx=10)

cal = Calendar(cal_frame, selectmode='day', date_pattern='y-mm-dd')
cal.pack(pady=5)
cal.bind("<<CalendarSelected>>", show_history_for_date)

history_label = tk.Label(cal_frame, text="Select a date to see stats", font=("Arial", 8, "italic"))
history_label.pack(pady=5)

# Counter Section
counter_frame = tk.LabelFrame(root, text="Daily Counter", padx=10, pady=10)
counter_frame.pack(pady=10, fill="x", padx=10)

tk.Label(counter_frame, text="Chats").grid(row=0, column=0, sticky="w")
tk.Label(counter_frame, textvariable=chats_count, font=("Arial", 10, "bold")).grid(row=0, column=1, padx=20)
tk.Button(counter_frame, text="+1", command=increment_chats).grid(row=0, column=2)

tk.Label(counter_frame, text="Emails").grid(row=1, column=0, sticky="w")
tk.Label(counter_frame, textvariable=emails_count, font=("Arial", 10, "bold")).grid(row=1, column=1, padx=20)
tk.Button(counter_frame, text="+1", command=increment_emails).grid(row=1, column=2)

tk.Label(counter_frame, text="TODAY'S TOTAL:", font=("Arial", 9, "bold")).grid(row=2, column=0, pady=10)
tk.Label(counter_frame, textvariable=total_count, font=("Arial", 12, "bold"), fg="blue").grid(row=2, column=1)

tk.Button(root, text="Reset Today", command=reset_counts, fg="red", relief="flat").pack(pady=5)

root.mainloop()