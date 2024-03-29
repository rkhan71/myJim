from flask import Flask, render_template, redirect, request, session, Response
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from datetime import date, timedelta
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
from functools import wraps

app = Flask(__name__)

# Configuring app so that templates auto reload and I can use an SQL database to track sessions
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Decorator that doesn't let users access certain pages if they aren't logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

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
        
        # Storing the user_id, current date, and default unit in the session dictionary
        session["user_id"] = userdata[0]
        session["date"] = date.today().strftime("%Y-%m-%d")
        session["unit"] = "kg"

        connect.close()

        # Redirect user to homepage once they've logged in
        return redirect("/")
    else:
        return render_template("login.html")

# Logout route
@app.route("/logout")
@login_required
def logout():
    # Logging out is simply clearing the information from the current session
    session.clear()
    return redirect("/")

# Page for users to add data to the database
@app.route("/diary", methods=["GET", "POST"])
@login_required
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
            exercise = request.form.get("exercise-select")
            weight = request.form.get("weight")
            units = request.form.get("units")
            reps = request.form.get("reps")

            # Making sure that responses are in correct data types
            try:
                weight = float(weight)
                reps = float(reps)
            except:
                return render_template("error.html", message="Invalid entry.")
            if units not in ["kg", "lbs"]:
                return render_template("error.html", message="Invalid entry.")
            
            # Adding data entry to database and updating diary entries for current user
            data = (session["user_id"], exercise, weight, units, reps, session["date"])
            cursor.execute("INSERT INTO diary (user_id, exercise, weight, units, reps, day) VALUES (?, ?, ?, ?, ?, ?)", data)
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
        elif request.form.get("arrow") == "forward":
            # Button to increase date
            ints = [int(i) for i in session["date"].split("-")]
            session["date"] = (date(ints[0], ints[1], ints[2]) + timedelta(days=1)).strftime("%Y-%m-%d")
        elif request.form.get("arrow") == "back":
            # Button to increase date
            ints = [int(i) for i in session["date"].split("-")]
            session["date"] = (date(ints[0], ints[1], ints[2]) - timedelta(days=1)).strftime("%Y-%m-%d")
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
            d = temp[1].split("=")
            session["date"] = d[1]

            # If the date is changed we need to update the diary entries shown on the webpage
            cursor.execute("SELECT * FROM diary WHERE user_id = ? AND day = ?", (session["user_id"], session["date"]))
            entries = cursor.fetchall()
    
    # Commit any changes made to the sql database and close the connection. Then render the diary template and pass in the 
    # users exercises and diary entries for their selected date
    connect.commit()
    connect.close()
    return render_template("diary.html", exercises=exercises, entries=entries)

# Page where graphs showing users progress is shown
@app.route("/progress", methods=["GET", "POST"])
@login_required
def progress():
    # Get all users exercises to create form so users can choose which graphs to show
    connect = sqlite3.connect("myJim.db")
    cursor = connect.cursor()
    cursor.execute("SELECT * FROM exercise_list WHERE user_id = ? ORDER BY exercise", (session["user_id"],))
    exercises = cursor.fetchall()
    connect.close()
    exercises = [i[1] for i in exercises]
    if request.method == "POST":
        if request.form.get("unit"):
            session["unit"] = request.form.get("unit")
        else:
            # Get list of exercises user wants graphs for
            data = request.form.getlist("exercise")
            session["graph"] = []
            for d in data:
                ind = exercises.index(d)
                session["graph"] += [(ind, d)]
    return render_template("progress.html", exercises=exercises)

# Creating the graph that shows the users progress and making it a path so that when it's reloaded the new data shows up
@app.route("/graph.png")
def make_png():
    # use make_graphs function to create a figure with all the users progress graphs and let the html template access this figure
    # as a png image with the source "/graph.png"
    fig = make_graphs()
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype="image/png")

def make_graphs():
    # Connect to database
    connect = sqlite3.connect("myJim.db")
    cursor = connect.cursor()

    # Creating a figure that will fit all the graphs the user needs (one for each exercise)
    l = len(session["graph"])
    fig, ax = plt.subplots(l, 1, figsize=(6.4, l * 4.8))
    i = 0

    # Conversion between kilograms and pounds
    if session["unit"] == "kg":
        m = 1 / 2.204622621848776
    else:
        m = 2.204622621848776

    for exercise in session["graph"]:
        # Get the first day the exercise was done on
        cursor.execute("SELECT day FROM diary WHERE user_id = ? AND exercise = ? ORDER BY day", (session["user_id"], exercise[1]))
        day1 = cursor.fetchone()
        if day1:
            day1 = day1[0]

        # Get data for graph
        cursor.execute("SELECT * FROM diary WHERE user_id = ? AND exercise = ? ORDER BY day", (session["user_id"], exercise[1]))
        entries = cursor.fetchall()
        y = []
        for entry in entries:
            # Account for different units
            if entry[4] == session["unit"]:
                y += [entry[3] * entry[5]]
            else:
                y += [entry[3] * entry[5] * m]
        cursor.execute("SELECT JULIANDAY(day) - JULIANDAY(?) FROM diary WHERE user_id = ? AND exercise = ? ORDER BY day", (day1, session["user_id"], exercise[1]))
        diffs = cursor.fetchall()
        x = [int(j[0]) for j in diffs]

        # Put graph in a position in the figure
        if l > 1:
            ax[i].plot(x, y, color="red", marker="x", markeredgecolor="blue")
            ax[i].set_title(exercise[1])
            ax[i].set_ylabel("Weight * Total Reps")
            ax[i].set_xlabel(f"Days Since {day1}")
        else:
            ax.plot(x, y, color="red", marker="x", markeredgecolor="blue")
            ax.set_title(exercise[1])
            ax.set_ylabel("Weight * Total Reps")
            ax.set_xlabel(f"Days Since {day1}")

        i += 1
    
    # Returning finished figure with all the graphs in it
    fig.tight_layout(h_pad=5)
    connect.close()
    return fig


