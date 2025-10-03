from flask import Flask, request, redirect, url_for, session
import sqlite3
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # for server use
import matplotlib.pyplot as plt
import io, base64

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change this in production
DB_PATH = "lockscreen.db"

# --- LOGIN PAGE ---
@app.route("/", methods=["GET", "POST"]) 
def login():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]
        if user == "admin" and pw == "bizmatech":  # simple admin login
            session["admin"] = True
            return redirect(url_for("dashboard"))
    return """
    <html>
    <head>
        <style>
            body {
                margin:0;
                padding:0;
                height:100vh;
                display:flex;
                justify-content:center;
                align-items:center;
                font-family:Arial;
                background: url('/static/BACKGROUND.jpg') no-repeat center center fixed;
                background-size:cover;
            }
            .login-box {
                background: rgba(0,0,0,0.7);
                padding:30px;
                border-radius:10px;
                text-align:center;
                color:white;
                width:300px;
                box-shadow:0 4px 15px rgba(0,0,0,0.4);
            }
            .login-box input {
                width:90%;
                padding:10px;
                margin:10px 0;
                border:none;
                border-radius:5px;
            }
            .login-box button {
                width:100%;
                padding:10px;
                background:#b30000;
                border:none;
                border-radius:5px;
                color:white;
                font-size:16px;
                cursor:pointer;
                transition:0.3s;
            }
            .login-box button:hover {
                background:#ff4b4b;
            }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2>Admin Login</h2>
            <form method="post">
                <input type="text" name="username" placeholder="Username"><br>
                <input type="password" name="password" placeholder="Password"><br>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    """

# --- SIDEBAR TEMPLATE ---
def sidebar():
    return """
    <div class="sidebar">
        <h2>Menu</h2>
        <a href="/dashboard">Dashboard</a>
        <a href="/logs">View Logs</a>
        <a href="/users">Users</a>
        <a href="/logout">Logout</a>
    </div>
    <style>
        body { margin:0; padding:0; display:flex; font-family:Arial; }

        /* Sidebar Styling */
        .sidebar {
            width:200px;
            background: linear-gradient(180deg, #ff4b4b, #b30000); /* 🔴 Red gradient */
            color:white;
            padding:20px;
            height:100vh;
            box-shadow: 2px 0 10px rgba(0,0,0,0.5);
        }

        .sidebar h2 {
            margin-bottom:20px;
            font-size:22px;
            font-weight:bold;
            text-shadow:1px 1px 4px rgba(0,0,0,0.6);
        }

        .sidebar a {
            display:block;
            color:white;
            text-decoration:none;
            padding:12px 15px;
            margin:10px 0;
            background: rgba(255,255,255,0.15);
            border-radius:8px;
            transition:0.3s ease;
            font-weight:500;
        }

        .sidebar a:hover {
            background:black;
            color:#b30000;
            transform: translateX(5px);
            box-shadow:0 4px 8px rgba(0,0,0,0.3);
        }

        /* Content Styling */
        .content {
            flex:1;
            padding:20px;
            background:url('/static/BACKGROUND.jpg') no-repeat center center fixed;
            background-size:cover;
            color:black;
            overflow:auto;
        }
    </style>
    """

# --- DASHBOARD PAGE ---
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Total stats
    cur.execute("SELECT SUM(coins), SUM(added_time) FROM logs")
    total_coins, total_time = cur.fetchone()

    # Today’s stats
    today = datetime.now().strftime("%Y-%m-%d")
    cur.execute("SELECT SUM(coins), SUM(added_time) FROM logs WHERE date(timestamp)=?", (today,))
    today_coins, today_time = cur.fetchone()

    # Chart data
    cur.execute("SELECT date(timestamp), SUM(coins) FROM logs GROUP BY date(timestamp)")
    data = cur.fetchall()
    conn.close()

    if data:
        dates, sums = zip(*data)
        plt.figure(figsize=(6,3))
        plt.plot(dates, sums, marker="o")
        plt.title("Coins Inserted per Day")
        plt.xticks(rotation=45)
        plt.tight_layout()
        img = io.BytesIO()
        plt.savefig(img, format="png")
        img.seek(0)
        chart_url = base64.b64encode(img.getvalue()).decode()
        plt.close()
    else:
        chart_url = ""

    return f"""
    <html><body>
    {sidebar()}
    <div class="content">
        <h1>Dashboard</h1>
        <div style='background:rgba(0,0,0,0.7); padding:15px; border-radius:10px; display:inline-block; margin:10px;'>
            <h3>Total Coins</h3><p>{total_coins or 0}</p>
        </div>
        <div style='background:rgba(0,0,0,0.7); padding:15px; border-radius:10px; display:inline-block; margin:10px;'>
            <h3>Total Time Added</h3><p>{(total_time or 0)//60} mins</p>
        </div>
        <div style='background:rgba(0,0,0,0.7); padding:15px; border-radius:10px; display:inline-block; margin:10px;'>
            <h3>Today Coins</h3><p>{today_coins or 0}</p>
        </div>
        <div style='background:rgba(0,0,0,0.7); padding:15px; border-radius:10px; display:inline-block; margin:10px;'>
            <h3>Today Time</h3><p>{(today_time or 0)//60} mins</p>
        </div>
        {f"<h2>Usage Chart</h2><img src='data:image/png;base64,{chart_url}'/>" if chart_url else ""}
    </div>
    </body></html>
    """

# --- LOGS PAGE ---
@app.route("/logs")
def logs():
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT coins, added_time, timestamp FROM logs ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()

    # ✅ Table HTML with CSS
    table = """
    <style>
        .log-table {
            border-collapse: collapse;
            width: 90%;
            margin: 20px auto;
            font-family: Arial, sans-serif;
            font-size: 14px;
            background: #fff;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .log-table th {
            background: #b30000;
            color: white;
            padding: 12px;
            text-align: center;
        }
        .log-table td {
            padding: 10px;
            text-align: center;
            border-bottom: 1px solid #ddd;
        }
        .log-table tr:nth-child(even) {
            background: #f9f9f9;
        }
        .log-table tr:hover {
            background: #ffe5e5;
        }
    </style>

    <table class="log-table">
        <tr><th>Coins</th><th>Added Time</th><th>Timestamp</th></tr>
    """

    for c, t, ts in rows:
        table += f"<tr><td>{c}</td><td>{t//60} min</td><td>{ts}</td></tr>"

    table += "</table>"

    return f"""
    <html><body>
    {sidebar()}
    <div class="content">
        <h1>View Logs</h1>
        {table}
    </div>
    </body></html>
    """
   # --- USERS PAGE ---
@app.route("/users")
def users():
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, username, password FROM users ORDER BY id ASC")
    user_rows = cur.fetchall()
    conn.close()

    table = """
    <style>
        .styled-table {
            border-collapse: collapse;
            width: 80%;
            margin: 20px auto;
            font-family: Arial, sans-serif;
            font-size: 14px;
            background: #fff;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .styled-table th {
            background: #b30000;
            color: white;
            padding: 12px;
            text-align: center;
        }
        .styled-table td {
            padding: 10px;
            text-align: center;
            border-bottom: 1px solid #ddd;
        }
        .styled-table tr:nth-child(even) {
            background: #f9f9f9;
        }
        .styled-table tr:hover {
            background: #ffe5e5;
        }
        .action-btn {
            padding: 5px 10px;
            margin: 2px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 13px;
        }
        .btn-add { background: #28a745; color: white; }
        .btn-edit { background: #007bff; color: white; }
        .btn-delete { background: #dc3545; color: white; }
        .btn-add:hover { background: #218838; }
        .btn-edit:hover { background: #0069d9; }
        .btn-delete:hover { background: #c82333; }
    </style>

    <div style='text-align:center; margin:20px;'>
        <a href='/users/add'><button class='action-btn btn-add'>+ Add User</button></a>
    </div>

    <table class="styled-table">
        <tr><th>ID</th><th>Username</th><th>Password</th><th>Actions</th></tr>
    """

    for uid, uname, pw in user_rows:
        table += f"""
        <tr>
            <td>{uid}</td>
            <td>{uname}</td>
            <td>{pw}</td>
            <td>
                <a href='/users/edit/{uid}'><button class='action-btn btn-edit'>Edit</button></a>
                <a href='/users/delete/{uid}' onclick="return confirm('Delete user {uname}?');">
                    <button class='action-btn btn-delete'>Delete</button>
                </a>
            </td>
        </tr>
        """

    table += "</table>"

    return f"""
    <html><body>
    {sidebar()}
    <div class="content">
        <div style='text-align:center; margin-bottom:20px;'>
            <img src='/static/Bizmatech.jpg' alt='ADMIN' style='height:60px;'>
            <h1>Manage Users</h1>
        </div>
        {table}
    </div>
    </body></html>
    """
# --- ADD USER ---
@app.route("/users/add", methods=["GET", "POST"])
def add_user():
    if not session.get("admin"):
        return redirect(url_for("login"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return redirect(url_for("users"))

    return f"""
    <html><body style='text-align:center; font-family:Arial;'>
        <h2>Add User</h2>
        <form method="post">
            <input type="text" name="username" placeholder="Username" required><br><br>
            <input type="password" name="password" placeholder="Password" required><br><br>
            <button type="submit">Save</button>
        </form>
        <br>
        <a href='/users'>Back</a>
    </body></html>
    """

# --- EDIT USER ---
@app.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        cur.execute("UPDATE users SET username=?, password=? WHERE id=?", (username, password, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for("users"))

    cur.execute("SELECT username, password FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()
    conn.close()

    if not user:
        return "User not found!"

    return f"""
    <html><body style='text-align:center; font-family:Arial;'>
        <h2>Edit User</h2>
        <form method="post">
            <input type="text" name="username" value="{user[0]}" required><br><br>
            <input type="password" name="password" value="{user[1]}" required><br><br>
            <button type="submit">Update</button>
        </form>
        <br>
        <a href='/users'>Back</a>
    </body></html>
    """
    
# --- DELETE USER ---
@app.route("/users/delete/<int:user_id>")
def delete_user(user_id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("users"))

# --- LOGOUT ---
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
