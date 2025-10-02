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
        if user == "admin" and pw == "1234":  # simple admin login
            session["admin"] = True
            return redirect(url_for("dashboard"))
    return """
    <html><body style="text-align:center; font-family:Arial;">
        <h2>Admin Login</h2>
        <form method="post">
            <input type="text" name="username" placeholder="Username"><br><br>
            <input type="password" name="password" placeholder="Password"><br><br>
            <button type="submit">Login</button>
        </form>
    </body></html>
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
        .sidebar {
            width:200px;
            background:#222;
            color:white;
            padding:20px;
            height:100vh;
        }
        .sidebar a {
            display:block;
            color:white;
            text-decoration:none;
            padding:10px;
            margin:5px 0;
            background:#444;
            border-radius:5px;
        }
        .sidebar a:hover { background:#666; }
        .content {
            flex:1;
            padding:20px;
            background:url('/static/BACKGROUND.jpg') no-repeat center center fixed;
            background-size:cover;
            color:white;
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

    table = "<table border=1 style='background:rgba(0,0,0,0.7); margin:10px;'><tr><th>Coins</th><th>Added Time</th><th>Timestamp</th></tr>"
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

    # You can later connect to a "users" table in SQLite if needed
    dummy_users = [("admin", "1234"), ("guest", "password")]

    table = "<table border=1 style='background:rgba(0,0,0,0.7); margin:10px;'><tr><th>Username</th><th>Password</th></tr>"
    for u, p in dummy_users:
        table += f"<tr><td>{u}</td><td>{p}</td></tr>"
    table += "</table>"

    return f"""
    <html><body>
    {sidebar()}
    <div class="content">
        <h1>Users</h1>
        {table}
    </div>
    </body></html>
    """

# --- LOGOUT ---
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
