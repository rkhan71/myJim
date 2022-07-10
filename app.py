from flask import Flask, render_template, redirect, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from datetime import date

app = Flask(__name__)

# Configuring app so that templates auto reload and I can use an SQL database to track sessions
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Home page
@app.route("/")
def index():
    return render_template("index.html")

# Page for users to register new accounts
@app.route("/register", methods=["GET", "POST"])
def register():
    # Checks request method to see whether the form was submitted
    if request.method == "POST":
        # Making sure the required fields are filled out
        if not request.form.get("username") or not request.form.get("password") or not request.form.get("confirm"):
            return render_template("error.html", message="Required field not filled out.")
        if request.form.get("password") != request.form.get("confirm"):
            return render_template("error.html", message="Passwords do not match.")

        connect = sqlite3.connect("myJim.db")
        cursor = connect.cursor()

        # Making sure username is unique
        cursor.execute("SELECT username FROM users")
        uname = request.form.get("username")
        unames = cursor.fetchall()
        for i in unames:
            if i == uname:
                return render_template("error.html", message="Username is already taken.")
        pword = generate_password_hash(request.form.get("password"))

        # Insert username and password hash into database
        cursor.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (uname, pword))
        connect.commit()
        connect.close()

        # Get user back to home screen once they've registered an account
        return redirect("/")
    else:
        # This is for when the page is loaded but the form is not submitted
        return render_template("register.html")

# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    # Making sure that information from other sessions is cleared 
    session.clear()

    if request.method == "POST":
        # Checking that form is properly filled out
        if not request.form.get("username") or not request.form.get("password"):
            return render_template("error.html", message="Required field not filled out.")

        connect = sqlite3.connect("myJim.db")
        cursor = connect.cursor()

        # Checking that the account exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        userdata = cursor.fetchone()
        if not userdata or not check_password_hash(userdata[2], request.form.get("password")):
            return render_template("error.html", message="Invalid username and/or password.")
        
        # Storing the user_id and the current date in the session dictionary
        session["user_id"] = userdata[0]
        session["date"] = date.today().strftime("%Y-%m-%d")

        connect.close()

        # Redirect user to homepage once they've logged in
        return redirect("/")
    else:
        return render_template("login.html")

# Logout route
@app.route("/logout")
def logout():
    # Logging out is simply clearing the information from the current session
    session.clear()
    return redirect("/")

# Page for users to add data to the database
@app.route("/diary", methods=["GET", "POST"])
def diary():
    # Connect to sql database and get the exercises and diary entries that the current user has for the selected date 
    # so that they can be shown on the webpage
    connect = sqlite3.connect("myJim.db")
    cursor = connect.cursor()
    cursor.execute("SELECT * FROM exercise_list WHERE user_id = ?", (session["user_id"],))
    exercises = cursor.fetchall()
    cursor.execute("SELECT * FROM diary WHERE user_id = ? AND day = ?", (session["user_id"], session["date"]))
    entries = cursor.fetchall()

    if request.method == "POST":

        # Checking which form the user submitted by checking if certain inputs were submitted
        if request.form.get("exercise"):
            # Form to add exercise to database
            exercise = request.form.get("exercise")
            cursor.execute("INSERT INTO exercise_list VALUES (?, ?)", (session["user_id"], exercise))

            # Exercises for current user need to be updated
            cursor.execute("SELECT * FROM exercise_list WHERE user_id = ?", (session["user_id"],))
            exercises = cursor.fetchall()
        elif request.form.get("exercise-select"):
            # Form to add a diary entry to database
            if not request.form.get("weight"):
                return render_template("error.html", message="Required field not filled out.")
            if not request.form.get("units"):
                return render_template("error.html", message="Required field not filled out.")
            if not request.form.get("reps"):
                return render_template("error.html", message="Required field not filled out.")
            if not request.form.get("sets"):
                return render_template("error.html", message="Required field not filled out.")
            exercise = request.form.get("exercise-select")
            weight = request.form.get("weight")
            units = request.form.get("units")
            sets = request.form.get("sets")
            reps = request.form.get("reps")

            # Making sure that responses are in correct data types
            try:
                weight = int(weight)
                sets = int(sets)
                reps = int(reps)
            except:
                return render_template("error.html", message="Invalid entry.")
            if units not in ["kg", "lbs"]:
                return render_template("error.html", message="Invalid entry.")
            
            # Adding data entry to database and updating diary entries for current user
            data = (session["user_id"], exercise, weight, units, sets, reps, session["date"])
            cursor.execute("INSERT INTO diary (user_id, exercise, weight, units, sets, reps, day) VALUES (?, ?, ?, ?, ?, ?, ?)", data)
            cursor.execute("SELECT * FROM diary WHERE user_id = ? AND day = ?", (session["user_id"], session["date"]))
            entries = cursor.fetchall()
        elif request.form.get("id"):
            # Form to delete diary entry
            cursor.execute("DELETE FROM diary WHERE id = ?", (request.form.get("id"),))
            cursor.execute("SELECT * FROM diary WHERE user_id = ? AND day = ?", (session["user_id"], session["date"]))
            entries = cursor.fetchall()
        elif request.form.get("exercise-del"):
            # Form to delete exercise
            cursor.execute("DELETE FROM exercise_list WHERE exercise = ?", (request.form.get("exercise-del"),))
            cursor.execute("SELECT * FROM exercise_list WHERE user_id = ?", (session["user_id"],))
            exercises = cursor.fetchall()
        else:
            # If you get here it means that a field in the form you submitted was not filled out
            connect.close()
            return render_template("error.html", message="Required field not filled out.")
    else: 
        # The form to change the date that the user adds/deletes diary entries for uses the GET method so we can get the 
        # responses from the url
        url = request.url
        temp = url.split("?")

        # If the form is submitted the url will be split into two and the date for the session should be changed
        if len(temp) > 1:
            date = temp[1].split("=")
            session["date"] = date[1]

            # If the date is changed we need to update the diary entries shown on the webpage
            cursor.execute("SELECT * FROM diary WHERE user_id = ? AND day = ?", (session["user_id"], session["date"]))
            entries = cursor.fetchall()
    
    # Commit any changes made to the sql database and close the connection. Then render the diary template and pass in the 
    # users exercises and diary entries for their selected date
    connect.commit()
    connect.close()
    return render_template("diary.html", exercises=exercises, entries=entries)

# Page for users to see their progress over longer periods of time in a graphical manner
@app.route("/progress")
def progress():
    return render_template("progress.html")