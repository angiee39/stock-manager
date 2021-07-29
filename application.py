import os
# from dotenv import load_dotenv
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # if request.method == "POST":
    transactions = db.execute("SELECT *, SUM(shares) FROM transactions WHERE user_id = (?) GROUP BY symbol", session["user_id"])
    balancee = db.execute("SELECT cash FROM users WHERE id = (?)", session['user_id'])
    total = balancee[0]["cash"]
    for stock in transactions:
        total += float(lookup(stock["symbol"])["price"]) * stock["SUM(shares)"]
    return render_template("index.html", transactions=transactions, balancee=balancee, lookup=lookup, total=total)
    # else:
    # return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol or not lookup(symbol):
            return apology("please enter a valid stock symbol")
        # Amount of shares to buy
        shares = int(request.form.get("shares"))
        if not shares > 0:
            return apology("please enter a positive integer")
            
        # Current price of a share, current time, total price, user balance
        stock = lookup(symbol)
        name = stock["name"]
        price = float(stock["price"])
        date = datetime.now()
        total = price * shares
        balance = db.execute("SELECT cash FROM users WHERE id = (?)", session["user_id"])
        
        if total > balance[0]["cash"]:
            return apology("not enough cash to buy this stock")
        # Insert into transactions and update user cash balance
        db.execute("INSERT INTO transactions (symbol, name, shares, price, date, user_id, type) VALUES(?, ?, ?, ?, ?, ?, ?)", symbol.upper(), name, shares, price, date, session["user_id"], "buy")
        new_balance = balance[0]["cash"]-total
        db.execute("UPDATE users SET cash = (?) WHERE id = (?)", new_balance, session["user_id"])
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = (?)", session["user_id"])
    return render_template("history.html", transactions=transactions)
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("enter a stock symbol")
        stock = lookup(symbol)
        return render_template("quoted.html", stock=stock)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        if not username:
            return apology("username missing")
        password = request.form.get("password")
        if not password:
            return apology("password missing")
        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)
        return redirect("/")

    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("select a stock")
        input_shares = int(request.form.get("shares"))
        if not input_shares > 0:
            return apology("input a positive integer")
        shares_in_stock = db.execute("SELECT shares FROM transactions WHERE user_id = (?) AND symbol = (?)", session["user_id"], symbol)
        print(shares_in_stock)
        stock_count = 0
        for item in shares_in_stock:
            stock_count += item["shares"]
        if input_shares > stock_count:
            return apology("not enough shares to sell")
            
        # Current price of a share, current time, total price, user balance
        stock = lookup(symbol)
        name = stock["name"]
        price = float(stock["price"])
        date = datetime.now()
        total = price * input_shares
        balance = db.execute("SELECT cash FROM users WHERE id = (?)", session["user_id"])
        
         # Insert into transactions and update user cash balance
        db.execute("INSERT INTO transactions (symbol, name, shares, price, date, user_id, type) VALUES(?, ?, ?, ?, ?, ?, ?)", symbol.upper(), name, -abs(input_shares), price, date, session["user_id"], "sell")
        new_balance = balance[0]["cash"]+total
        db.execute("UPDATE users SET cash = (?) WHERE id = (?)", new_balance, session["user_id"])
        return redirect("/")

    else:
        transactions = db.execute("SELECT DISTINCT symbol FROM transactions WHERE user_id = (?)", session["user_id"])
        return render_template("sell.html", transactions=transactions)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
