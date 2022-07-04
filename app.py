from flask import Flask, render_template, redirect, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username") or not request.form.get("password") or not request.form.get("confirm"):
            return redirect("error.html")
        if request.form.get("password") != request.form.get("confirm"):
            return redirect("error.html")
        connect = sqlite3.connect("myJim.db")
        cursor = connect.cursor()
        cursor.execute("SELECT username FROM users")
        uname = request.form.get("username")
        unames = cursor.fetchall()
        for i in unames:
            if i == uname:
                return redirect("error.html")
        pword = generate_password_hash(request.form.get("password"))
        cursor.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (uname, pword))
        connect.commit()
        connect.close()
        return redirect("/")
    else:
        return render_template("register.html")