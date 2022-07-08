from flask import Flask, render_template, redirect, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username") or not request.form.get("password") or not request.form.get("confirm"):
            return render_template("error.html", message="Required field not filled out.")
        if request.form.get("password") != request.form.get("confirm"):
            return render_template("error.html", message="Passwords do not match.")
        connect = sqlite3.connect("myJim.db")
        cursor = connect.cursor()
        cursor.execute("SELECT username FROM users")
        uname = request.form.get("username")
        unames = cursor.fetchall()
        for i in unames:
            if i == uname:
                return render_template("error.html", message="Username is already taken.")
        pword = generate_password_hash(request.form.get("password"))
        cursor.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (uname, pword))
        connect.commit()
        connect.close()
        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        if not request.form.get("username") or not request.form.get("password"):
            return render_template("error.html", message="Required field not filled out.")
        connect = sqlite3.connect("myJim.db")
        cursor = connect.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        userdata = cursor.fetchone()
        if not userdata or not check_password_hash(userdata[2], request.form.get("password")):
            return render_template("error.html", message="Invalid username and/or password.")
        session["user_id"] = userdata[0]
        connect.close()
        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/diary", methods=["GET", "POST"])
def diary():
    if request.method == "POST":
        if request.form.get("exercise"):
            exercise = request.form.get("exercise")
            connect = sqlite3.connect("myJim.db")
            cursor = connect.cursor()
            cursor.execute("INSERT INTO exercise_list VALUES (?, ?)", (session["user_id"], exercise))
            cursor.execute("SELECT * FROM exercise_list WHERE user_id = ?", (session["user_id"],))
            exercises = cursor.fetchall()
            cursor.execute("SELECT * FROM diary WHERE user_id = ? AND day = ?", (session["user_id"], session["date"]))
            entries = cursor.fetchall()
            connect.commit()
            connect.close()
            return render_template("diary.html", exercises=exercises, entries=entries)
        elif request.form.get("exercise-select"):
            exercise = request.form.get("exercise-select")
            weight = request.form.get("weight")
            units = request.form.get("units")
            reps = request.form.get("reps")
            connect = sqlite3.connect("myJim.db")
            cursor = connect.cursor()
            data = (session["user_id"], exercise, weight, units, reps, session["date"])
            cursor.execute("INSERT INTO diary VALUES (?, ?, ?, ?, ?, ?)", data)
            cursor.execute("SELECT * FROM exercise_list WHERE user_id = ?", (session["user_id"],))
            exercises = cursor.fetchall()
            cursor.execute("SELECT * FROM diary WHERE user_id = ? AND day = ?", (session["user_id"], session["date"]))
            entries = cursor.fetchall()
            connect.commit()
            connect.close()
            return render_template("diary.html", exercises=exercises, entries=entries)
        else:
            return render_template("error.html", message="Required field not filled out.")
    else: 
        url = request.url
        temp = url.split("?")
        if len(temp) > 1:
            date = temp[1].split("=")
            session["date"] = date[1]
            connect = sqlite3.connect("myJim.db")
            cursor = connect.cursor()
            cursor.execute("SELECT * FROM exercise_list WHERE user_id = ?", (session["user_id"],))
            exercises = cursor.fetchall()
            cursor.execute("SELECT * FROM diary WHERE user_id = ? AND day = ?", (session["user_id"], session["date"]))
            entries = cursor.fetchall()
            connect.close()
            return render_template("diary.html", exercises=exercises, entries=entries)
        elif session["date"]:
            connect = sqlite3.connect("myJim.db")
            cursor = connect.cursor()
            cursor.execute("SELECT * FROM exercise_list WHERE user_id = ?", (session["user_id"],))
            exercises = cursor.fetchall()
            cursor.execute("SELECT * FROM diary WHERE user_id = ? AND day = ?", (session["user_id"], session["date"]))
            entries = cursor.fetchall()
            connect.close()
            return render_template("diary.html", exercises=exercises, entries=entries)
        else:
            return render_template("diary.html")

