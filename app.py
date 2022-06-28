from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    message = "Wagwan! Welcome to myJim."
    return render_template("index.html", message = message)