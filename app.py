from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime
from time import time

# 🔥 FIREWALL IMPORT
from firewall import block_all_outbound, allow_all_outbound

app = Flask(__name__)

child_start_time = None


# ---------------- DATABASE ----------------
def connect_db():
    return sqlite3.connect("database.db")


def create_db():
    con = connect_db()
    cur = con.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS parent(username TEXT, password TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS child(username TEXT, password TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS whitelist(site TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS time_limit(minutes INTEGER)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs(
            user_type TEXT,
            username TEXT,
            activity TEXT,
            time TEXT
        )
    """)

    cur.execute("INSERT OR IGNORE INTO parent VALUES('parent','1234')")
    cur.execute("INSERT OR IGNORE INTO child VALUES('child','1234')")
    cur.execute("INSERT OR IGNORE INTO time_limit VALUES(60)")

    con.commit()
    con.close()


create_db()

# ---------------- PARENT LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def parent_login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        con = connect_db()
        cur = con.cursor()
        cur.execute("SELECT * FROM parent WHERE username=? AND password=?", (u, p))

        if cur.fetchone():
            return redirect("/parent_dashboard")

        con.close()

    return render_template("parent_login.html")


# ---------------- PARENT DASHBOARD ----------------
@app.route("/parent_dashboard", methods=["GET", "POST"])
def parent_dashboard():
    con = connect_db()
    cur = con.cursor()

    if request.method == "POST":

        if "site" in request.form:
            site = request.form["site"]
            cur.execute("INSERT INTO whitelist VALUES(?)", (site,))
            con.commit()

        if "minutes" in request.form:
            minutes = request.form["minutes"]
            cur.execute("DELETE FROM time_limit")
            cur.execute("INSERT INTO time_limit VALUES(?)", (minutes,))
            con.commit()

    cur.execute("SELECT minutes FROM time_limit")
    row = cur.fetchone()
    limit = row[0] if row else 60

    cur.execute("SELECT * FROM activity_logs ORDER BY time DESC")
    logs = cur.fetchall()

    con.close()
    return render_template("parent_dashboard.html", logs=logs, limit=limit)


# ---------------- CHILD LOGIN ----------------
@app.route("/child_login", methods=["GET", "POST"])
def child_login():
    global child_start_time

    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        con = connect_db()
        cur = con.cursor()
        cur.execute("SELECT * FROM child WHERE username=? AND password=?", (u, p))

        if cur.fetchone():
            child_start_time = time()
            allow_all_outbound()  # 🟢 Allow internet at start
            return redirect("/child_browser")

        con.close()

    return render_template("child_login.html")


# ---------------- CHILD BROWSER ----------------
@app.route("/child_browser", methods=["GET", "POST"])
def child_browser():
    global child_start_time

    con = connect_db()
    cur = con.cursor()

    cur.execute("SELECT minutes FROM time_limit")
    row = cur.fetchone()
    limit_minutes = row[0] if row else 60

    remaining_time = None

    if child_start_time:
        elapsed_minutes = (time() - child_start_time) / 60
        remaining_time = max(0, int(limit_minutes - elapsed_minutes))

        if elapsed_minutes > int(limit_minutes):
            block_all_outbound()   # 🔴 Block internet after limit
            return "⏰ Time Limit Exceeded. Internet Blocked."

    if request.method == "POST":
        url = request.form["url"]

        cur.execute("SELECT site FROM whitelist WHERE site=?", (url,))
        allowed = cur.fetchone()

        if allowed:
            return redirect("http://" + url)
        else:
            message = "❌ Website Blocked"
            return render_template("child_browser.html",
                                   message=message,
                                   remaining_time=remaining_time)

    con.close()
    return render_template("child_browser.html",
                           remaining_time=remaining_time)


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
