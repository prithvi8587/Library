from flask import Flask, render_template, request, redirect, session
import os, psycopg2, smtplib
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

USERNAME = os.getenv("LIB_USERNAME")
PASSWORD = os.getenv("LIB_PASSWORD")

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS books(
        id SERIAL PRIMARY KEY,
        title TEXT,
        author TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS students(
        id SERIAL PRIMARY KEY,
        name TEXT,
        email TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS transactions(
        id SERIAL PRIMARY KEY,
        book_id INTEGER,
        student_id INTEGER,
        issue_date TIMESTAMP,
        due_date TIMESTAMP,
        return_date TIMESTAMP
    )""")

    conn.commit()
    cur.close()
    conn.close()

init_db()

def send_email(to_email, book, due):
    try:
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(EMAIL_SENDER, EMAIL_PASSWORD)

        msg = f"Subject: Book Issued\n\nBook: {book}\nReturn by: {due}"
        s.sendmail(EMAIL_SENDER, to_email, msg)
        s.quit()
    except Exception as e:
        print(e)

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["user"] = USERNAME
            return redirect("/dashboard")
        return "Invalid login"
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM books")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM transactions WHERE return_date IS NULL")
    issued = cur.fetchone()[0]

    available = total - issued

    cur.close()
    conn.close()

    return render_template("dashboard.html", total=total, available=available, issued=issued)

@app.route("/add_book", methods=["GET","POST"])
def add_book():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO books(title,author) VALUES(%s,%s)",
                    (request.form["title"], request.form["author"]))
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/dashboard")
    return render_template("add_book.html")

@app.route("/add_student", methods=["GET","POST"])
def add_student():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO students(name,email) VALUES(%s,%s)",
                    (request.form["name"], request.form["email"]))
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/dashboard")
    return render_template("add_student.html")

@app.route("/issue", methods=["GET","POST"])
def issue():
    if request.method == "POST":
        book_id = request.form["book_id"]
        student_id = request.form["student_id"]

        conn = get_db()
        cur = conn.cursor()

        issue_date = datetime.now()
        due = issue_date + timedelta(days=7)

        cur.execute("""
        INSERT INTO transactions(book_id,student_id,issue_date,due_date,return_date)
        VALUES(%s,%s,%s,%s,NULL)
        """, (book_id, student_id, issue_date, due))

        cur.execute("SELECT email FROM students WHERE id=%s", (student_id,))
        student = cur.fetchone()

        cur.execute("SELECT title FROM books WHERE id=%s", (book_id,))
        book = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        if student and book:
            send_email(student[0], book[0], due)

        return redirect("/dashboard")

    return render_template("issue.html")

@app.route("/return", methods=["GET","POST"])
def return_book():
    if request.method == "POST":
        book_id = request.form["book_id"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        UPDATE transactions
        SET return_date=%s
        WHERE book_id=%s AND return_date IS NULL
        """, (datetime.now(), book_id))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/dashboard")

    return render_template("return.html")

if __name__ == "__main__":
    app.run()
