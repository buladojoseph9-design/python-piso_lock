import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel
from PIL import Image, ImageTk
import os
import socket
import sqlite3
import time
from flask import Flask, render_template_string
import threading

# -------- CONFIG ----------
BACKGROUND = "BACKGROUND.jpg"   # Background image
GEAR = "gear.png"               # Gear icon (32x32 PNG)
LOGO = "logo.png"               # Logo image for Insert Coin
LOCK_MESSAGE = "THIS CLIENT PC IS LOCKED.\nPLEASE CLICK LOGO TO INSERT COIN"
TIMER_START = 20
PC_NAME = "DESKTOP-CLIENT01"
ADMIN_NAME = "ADMIN:"
AUTO_SHUTDOWN = False
WARNING_TIME = 1
# --------------------------

# --- DATABASE PATH ---
DB_PATH = r"C:\Users\User\Desktop\myproject\db.sqlite3"
DB_PATH = r"C:\Users\User\Documents\system.db"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lockscreen.db")

# --- DATABASE INIT ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Members table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS members (
         id INTEGER PRIMARY KEY AUTOINCREMENT, 
         username TEXT UNIQUE, password TEXT)
    """)
    # Logs table
    cur.execute ("""
        CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT
        ,coins INTEGER, added_time INTEGER,
         timestamp TEXT )
    """)
    conn.commit()
    conn.close()

# --- ADD MEMBER ---
def add_member(username, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO members (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

# --- VERIFY LOGIN ---
def verify_login(username, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM members WHERE username=? AND password=?", (username, password))
    result = cur.fetchone()
    conn.close()
    return result is not None

# --- LOG COIN INSERT ---
def log_coin(coins, added_time):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO logs (coins, added_time, timestamp) VALUES (?, ?, ?)",
                (coins, added_time, time.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# --- FLASK SETUP ---
app = Flask(__name__)

@app.route("/")
def home():
    return "<h2>Welcome to Admin Panel</h2><p>Go to <a href='/logs'>View Logs</a></p>"

@app.route("/logs")
def logs():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT coins, added_time, timestamp FROM logs ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()

    # Render logs as HTML table
    html = "<h2>Coin Insert Logs</h2><table border='1' cellpadding='5'>"
    html += "<tr><th>Coins</th><th>Added Time</th><th>Timestamp</th></tr>"
    for coins, added_time, ts in rows:
        html += f"<tr><td>{coins}</td><td>{added_time//60} min</td><td>{ts}</td></tr>"
    html += "</table>"
    return html
def run_flask():
    app.run(host="127.0.0.1", port=5000, debug=False)

# Start Flask server in background thread
threading.Thread(target=run_flask, daemon=True).start()
# --- FLASK WEB SERVER ---
app=Flask(__name__)

@app.route("/")
def home():
    return "<h1>Pisonet System</h1><p>Visit <a href='/logs'>/logs</a> to see coin logs.</p>"

@app.route("/logs")
def logs():
    conn=sqlite3.connect(DB_PATH); cur=conn.cursor()
    cur.execute("SELECT id,coins,added_time,timestamp FROM logs ORDER BY id DESC LIMIT 50")
    rows=cur.fetchall(); conn.close()
    html="<h2>Coin Insert Logs</h2><table border=1 cellpadding=5>"
    html+="<tr><th>ID</th><th>Coins</th><th>Added Time (s)</th><th>Timestamp</th></tr>"
    for r in rows: html+=f"<tr><td>{r[0]}</td><td>₱{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>"
    html+="</table>"; return html

class LockScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("BIZMATECH GAMING LOCK")
        self.root.attributes("-fullscreen", True)

        self.total_coins = 0
        self.time_left = TIMER_START
        self.paused = False  # Track pause/resume state

        # Load background 
        self.bg_image = Image.open(BACKGROUND)
        self.bg_image = self.bg_image.resize((self.root.winfo_screenwidth(), self.root.winfo_screenheight()))
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)

        self.canvas = tk.Canvas(root, width=self.root.winfo_screenwidth(),
                                height=self.root.winfo_screenheight(), highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")

        # Header with PC name + Admin
        self.header = tk.Label(root, 
                               text=f"{PC_NAME} | {ADMIN_NAME}", 
                               font=("Arial", 14, "bold"), 
                               fg="white", bg="red", pady=5)
        self.header.place(relx=0.5, rely=0.02, anchor="n")

        # Gear button
        try:
            gear_img = Image.open(GEAR).resize((40, 40))
            self.gear_photo = ImageTk.PhotoImage(gear_img)
            self.gear_btn = tk.Button(root, image=self.gear_photo, bd=0, command=self.open_settings,
                                      bg="black", activebackground="black", cursor="hand2")
            self.gear_btn.place(relx=0.97, rely=0.05, anchor="ne")
        except:
            self.gear_btn = tk.Button(root, text="⚙", font=("Arial", 20), bd=0, command=self.open_settings,
                                      bg="black", fg="white", cursor="hand2")
            self.gear_btn.place(relx=0.97, rely=0.05, anchor="ne")

        # Timer panel
        self.timer_panel = tk.Frame(root, bg="black", bd=3, relief="ridge")
        self.timer_panel.place(relx=0.5, rely=0.25, anchor="center")

        self.timer_label = tk.Label(self.timer_panel, text=self.format_time(),
                                    font=("Consolas", 36, "bold"), fg="red", bg="black", padx=20, pady=10)
        self.timer_label.pack()

        # Insert Coin Button (below timer)
        try:
            logo_img = Image.open(LOGO).resize((200, 200))
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            self.logo_button = tk.Button(root, image=self.logo_photo, bd=0, command=lambda: self.insert_coin(1),
                                         cursor="hand2", bg="black", activebackground="black")
            self.logo_button.place(relx=0.5, rely=0.55, anchor="center")
        except:
            self.logo_button = tk.Button(root, text="INSERT COIN", font=("Arial", 18, "bold"),
                                         bg="black", fg="orange", width=15, height=2,
                                         command=lambda: self.insert_coin(1))
            self.logo_button.place(relx=0.5, rely=0.55, anchor="center")

        # Right side panel
        self.side_panel = tk.Frame(root, bg="#111111", bd=3, relief="ridge")
        self.side_panel.place(relx=0.95, rely=0.3, anchor="ne")

        tk.Label(self.side_panel, text="Total Coins + Time:", font=("Arial", 12, "bold"),
                 fg="white", bg="#111111").pack(anchor="w", padx=10, pady=5)
        self.status_label = tk.Label(self.side_panel,
                                     text=f"₱{self.total_coins} | {self.format_time()}",
                                     font=("Arial", 14, "bold"), fg="cyan", bg="#111111")
        self.status_label.pack(anchor="w", padx=20)

        # Side buttons
        self.make_side_button("₱1 Coin", "blue", lambda: self.insert_coin(1))
        self.make_side_button("₱5 Coin", "green", lambda: self.insert_coin(5))
        self.make_side_button("₱10 Coin", "orange", lambda: self.insert_coin(10))
        self.make_side_button("₱20 Coin", "purple", lambda: self.insert_coin(20))
        self.make_side_button("Pause", "gray", self.pause_time)
        self.make_side_button("Resume", "lightgreen", self.resume_time)
        self.make_side_button("Cancel", "red", self.cancel)
        self.make_side_button("Rates", "yellow", self.show_rates)

        # Footer
        footer = tk.Label(root, text=LOCK_MESSAGE, font=("Arial", 16, "bold"),
                          fg="white", bg="black", pady=10)
        footer.place(relx=0.5, rely=0.95, anchor="s")

        # Start countdown
        self.update_timer()

    def make_side_button(self, text, color, command):
        btn = tk.Button(self.side_panel, text=text, width=15, bg=color,
                        fg="black" if color in ["yellow", "orange", "green", "lightgreen"] else "white",
                        font=("Arial", 11, "bold"), command=command, cursor="hand2")
        btn.pack(pady=4, padx=10)

    def format_time(self, secs=None):
        if secs is None:
            secs = self.time_left
        minutes = secs // 60
        seconds = secs % 60
        return f"{minutes:02d}:{seconds:02d}"

    def update_timer(self):
        if not self.paused:  # Timer only runs if not paused
            if self.time_left > 0:
                self.timer_label.config(text=self.format_time())
                self.status_label.config(text=f"₱{self.total_coins} | {self.format_time()}")

                if self.time_left <= WARNING_TIME:
                    messagebox.showwarning("Warning", f"⚠ PC will lock in {self.time_left} seconds!")

                self.time_left -= 1
            else:
                messagebox.showerror("LOCKED", "Time is up! PC Locked.")
                self.lock_pc()

        self.root.after(1000, self.update_timer)

    def pause_time(self):
        self.paused = True

    def resume_time(self):
        if self.paused:
            self.paused = False

    def insert_coin(self, coin_value):
        added_time = self.rate_mapping().get(coin_value, 0)
        self.total_coins += coin_value
        self.time_left += added_time
        self.status_label.config(text=f"₱{self.total_coins} | {self.format_time()}")

        # ✅ Log coin insert into DB
        log_coin(coin_value, added_time)

    def cancel(self):
        self.root.destroy()

    def lock_pc(self):
        if AUTO_SHUTDOWN:
            os.system("shutdown /s /t 5")
        else:
            try:
                os.system("rundll32.exe user32.dll,LockWorkStation")
            except:
                pass
        self.root.destroy()

    def show_rates(self):
        rates = "\n".join([f"₱{k} = {v//60} Minutes" for k, v in self.rate_mapping().items()])
        messagebox.showinfo("Rates", f"Rates:\n{rates}")

    def rate_mapping(self):
        return {1: 60, 5: 600, 10: 1500, 20: 3600}

    # --- SETTINGS MENU ---
    def open_settings(self):
        win = Toplevel(self.root)
        win.title("Settings")
        win.geometry("500x650")

        # Load same background
        bg_img = Image.open(BACKGROUND)
        bg_img = bg_img.resize((500, 650))
        self.settings_bg_photo = ImageTk.PhotoImage(bg_img)

        canvas = tk.Canvas(win, width=500, height=650, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_image(0, 0, image=self.settings_bg_photo, anchor="nw")

        # Overlay labels
        tk.Label(win, text="ADMIN SETTINGS", font=("Arial", 14, "bold"),
                 fg="white", bg="black").place(relx=0.5, y=30, anchor="center")
        tk.Label(win, text=f"Managed by: {ADMIN_NAME}", font=("Arial", 11, "bold"),
                 fg="yellow", bg="black").place(relx=0.5, y=60, anchor="center")

        y_pos = 120
        btns = [
            ("Edit Rates", self.edit_rates),
            ("Member Login", self.login),
            ("Create Account", self.create_account),
            ("Forgot Password", self.forgot_password),
            ("Show IP Address", self.show_ip),
            ("Set Warning Time", self.set_warning),
            ("Change PC Name", self.change_pc_name),
            ("Toggle Auto Shutdown", self.toggle_shutdown),
            ("View Logs", self.view_logs)   # ✅ NEW BUTTON
        ]
        for text, cmd in btns:
            tk.Button(win, text=text, width=25, command=cmd, bg="black", fg="white",
                      font=("Arial", 11, "bold"), cursor="hand2").place(relx=0.5, y=y_pos, anchor="center")
            y_pos += 50

    # ---- Account Functions ----
    def login(self):
        username = simpledialog.askstring("Login", "Enter username:")
        password = simpledialog.askstring("Login", "Enter password:", show="*")
        if username and password:
            if verify_login(username, password):
                messagebox.showinfo("Welcome", f"Login successful!\nWelcome {username}")
            else:
                messagebox.showerror("Error", "Invalid username or password!")

    def create_account(self):
        username = simpledialog.askstring("Create Account", "Choose a username:")
        password = simpledialog.askstring("Create Account", "Choose a password:", show="*")
        if username and password:
            if add_member(username, password):
                messagebox.showinfo("Account", f"Account created for {username}!")
            else:
                messagebox.showwarning("Account", "Username already exists!")

    def forgot_password(self):
        username = simpledialog.askstring("Forgot Password", "Enter your username:")
        if username:
            messagebox.showinfo("Password Reset", f"Password reset not available.\nAsk admin for help.")
        else:
            messagebox.showwarning("Password Reset", "Username required.")

    def show_ip(self):
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        messagebox.showinfo("IP Address", f"PC Name: {hostname}\nIP: {ip}")

    def set_warning(self):
        global WARNING_TIME
        new_time = simpledialog.askinteger("Warning Time", "Enter warning time (seconds):", minvalue=1, maxvalue=60)
        if new_time:
            WARNING_TIME = new_time
            messagebox.showinfo("Updated", f"Warning time set to {WARNING_TIME} seconds.")

    def change_pc_name(self):
        global PC_NAME
        new_name = simpledialog.askstring("PC Name", "Enter new PC name:")
        if new_name:
            PC_NAME = new_name
            self.header.config(text=f"{PC_NAME} | {ADMIN_NAME}")
            messagebox.showinfo("Updated", f"PC name changed to {PC_NAME}")

    def toggle_shutdown(self):
        global AUTO_SHUTDOWN
        AUTO_SHUTDOWN = not AUTO_SHUTDOWN
        status = "enabled" if AUTO_SHUTDOWN else "disabled"
        messagebox.showinfo("Auto Shutdown", f"Auto shutdown is now {status}.")

    def edit_rates(self):
        messagebox.showinfo("Edit Rates", "Feature to change coin rates coming soon!")

    # --- VIEW LOGS ---
    def view_logs(self):
        logs_win = Toplevel(self.root)
        logs_win.title("Coin Insert Logs")
        logs_win.geometry("500x400")

        tk.Label(logs_win, text="Coin Insert History", font=("Arial", 14, "bold")).pack(pady=10)

        text_area = tk.Text(logs_win, wrap="none", font=("Consolas", 11))
        text_area.pack(fill="both", expand=True, padx=10, pady=10)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT coins, added_time, timestamp FROM logs ORDER BY id DESC LIMIT 50")
        rows = cur.fetchall()
        conn.close()

        if rows:
            for coins, added_time, ts in rows:
                minutes = added_time // 60
                text_area.insert("end", f"[{ts}] ₱{coins} → +{minutes} min\n")
        else:
            text_area.insert("end", "No logs available yet.")

# --- MAIN ---
if __name__=="__main__":
    init_db()
    threading.Thread(target=lambda: app.run(host="127.0.0.1",port=5000,debug=False),daemon=True).start()
    root=tk.Tk(); app_gui=LockScreen(root); root.mainloop()