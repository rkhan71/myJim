from email import message
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