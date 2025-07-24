from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from datetime import timedelta

from datetime import datetime, timedelta

import sqlite3

app = Flask(__name__)
app.secret_key = 'lms_secret' 


ADMIN_USER = "admin"
ADMIN_PASS = "admin123"



@app.route('/')
def home():  # instead of home()
    return render_template("home.html")

@app.route('/admin')
def admin_redirect():
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid credentials. Please try again."
    return render_template('login.html', error=error)


@app.route('/admin/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('dashboard.html')

@app.route('/admin/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))
def init_db():
    with sqlite3.connect("library.db") as conn:
        conn.execute('''
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        isbn TEXT,
        quantity INTEGER NOT NULL
    )
''')

        conn.execute("DELETE FROM sqlite_sequence WHERE name='books'")
        conn.execute("UPDATE sqlite_sequence SET seq = 100 WHERE name='books'")

        conn.execute('''CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            password TEXT NOT NULL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            book_id INTEGER,
            issue_date TEXT,
            return_date TEXT,
            status TEXT DEFAULT 'Issued',
            FOREIGN KEY(member_id) REFERENCES members(id),
            FOREIGN KEY(book_id) REFERENCES books(id)
        )''')



# ---------------- BOOK MANAGEMENT ------------------

@app.route('/admin/books')
def manage_books():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    with sqlite3.connect("library.db") as conn:
        books = conn.execute("SELECT * FROM books").fetchall()
    return render_template("manage_books.html", books=books)

@app.route('/admin/book/add', methods=["POST"])
def add_book():
    title = request.form['title']
    author = request.form['author']
    isbn = request.form['isbn']
    quantity = request.form['quantity']
    with sqlite3.connect("library.db") as conn:
        conn.execute("INSERT INTO books (title, author, isbn, quantity) VALUES (?, ?, ?, ?)",
                     (title, author, isbn, quantity))
    return redirect(url_for('manage_books'))

@app.route('/admin/book/delete/<int:book_id>')
def delete_book(book_id):
    with sqlite3.connect("library.db") as conn:
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return redirect(url_for('manage_books'))

@app.route('/admin/book/update/<int:book_id>', methods=["POST"])
def update_book(book_id):
    title = request.form['title']
    author = request.form['author']
    isbn = request.form['isbn']
    quantity = request.form['quantity']
    with sqlite3.connect("library.db") as conn:
        conn.execute("UPDATE books SET title=?, author=?, isbn=?, quantity=? WHERE id=?",
                     (title, author, isbn, quantity, book_id))
    return redirect(url_for('manage_books'))

# ----------- MEMBER SIGNUP & LOGIN ----------

@app.route('/member/signup', methods=["GET", "POST"])
def member_signup():
    error = None
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        try:
            with sqlite3.connect("library.db") as conn:
                conn.execute("INSERT INTO members (name, email, phone, password) VALUES (?, ?, ?, ?)",
                             (name, email, phone, password))
            return redirect(url_for('member_login'))
        except sqlite3.IntegrityError:
            error = "Email already registered!"
    
    return render_template("member_signup.html", error=error)


@app.route('/member/login', methods=["GET", "POST"])
def member_login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with sqlite3.connect("library.db") as conn:
            user = conn.execute("SELECT * FROM members WHERE email = ? AND password = ?", 
                                (email, password)).fetchone()
        if user:
            session['member_logged_in'] = True
            session['member_id'] = user[0]
            session['member_name'] = user[1]
            return redirect(url_for('member_dashboard'))
        else:
            error = "Invalid credentials!"
    return render_template("member_login.html", error=error)


@app.route('/member/dashboard')
def member_dashboard():
    if not session.get('member_logged_in'):
        return redirect(url_for('member_login'))
    
    member_id = session['member_id']
    
    with sqlite3.connect("library.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
    SELECT books.title, issues.issue_date, issues.return_date, issues.status, issues.id
    FROM issues
    JOIN books ON issues.book_id = books.id
    WHERE issues.member_id = ?
''', (member_id,))

        issued_books = cursor.fetchall()
    
    return render_template("member_dashboard.html", 
                           name=session['member_name'], 
                           issued_books=issued_books)




@app.route('/admin/issue', methods=["GET", "POST"])
def issue_book():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    success = session.pop('issue_success', None)
 

    with sqlite3.connect("library.db") as conn:
        members = conn.execute("SELECT id, name FROM members").fetchall()
        books = conn.execute("SELECT id, title, quantity FROM books WHERE quantity > 0").fetchall()

    if request.method == "POST":
        member_id = request.form['member_id']
        book_id = request.form['book_id']
        issue_date = datetime.now().strftime("%Y-%m-%d")

        with sqlite3.connect("library.db") as conn:
            conn.execute("INSERT INTO issues (member_id, book_id, issue_date) VALUES (?, ?, ?)",
                         (member_id, book_id, issue_date))
            # Decrease book quantity
            conn.execute("UPDATE books SET quantity = quantity - 1 WHERE id = ?", (book_id,))
        
        session['issue_success'] = "Book issued successfully!"
        return redirect(url_for('issue_book'))

        # Reload updated list
        with sqlite3.connect("library.db") as conn:
            members = conn.execute("SELECT id, name FROM members").fetchall()
            books = conn.execute("SELECT id, title, quantity FROM books WHERE quantity > 0").fetchall()

    return render_template("admin_issue_book.html", members=members, books=books, success=success)





@app.template_filter('to_datetime')
def to_datetime_filter(value):
    return datetime.strptime(value, "%Y-%m-%d")



@app.route('/admin/return', methods=["GET", "POST"])
def return_book():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    success = session.pop('return_success', None)

    with sqlite3.connect("library.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT issues.id, members.name, books.title, issues.issue_date
                          FROM issues
                          JOIN members ON issues.member_id = members.id
                          JOIN books ON issues.book_id = books.id
                          WHERE issues.status = 'Issued' ''')
        issued = cursor.fetchall()

    if request.method == "POST":
        issue_id = request.form['issue_id']
        return_date = datetime.today().strftime("%Y-%m-%d")

        with sqlite3.connect("library.db") as conn:
            conn.execute("UPDATE issues SET return_date = ?, status = 'Returned' WHERE id = ?",
                         (return_date, issue_id))

        session['return_success'] = "Book returned successfully!"
        return redirect(url_for('return_book'))

    return render_template("admin_return_book.html", issued=issued, success=success)







@app.template_filter('to_datetime')
def to_datetime_filter(value):
    return datetime.strptime(value, "%Y-%m-%d")




@app.route('/admin/reports')
def reports():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    today = datetime.today().strftime('%Y-%m-%d')
    week_ago = (datetime.today() - timedelta(days=7)).strftime('%Y-%m-%d')
    month_start = datetime.today().replace(day=1).strftime('%Y-%m-%d')

    with sqlite3.connect("library.db") as conn:
        cursor = conn.cursor()

        daily = cursor.execute('''
            SELECT books.title, members.name, issues.issue_date, issues.status
            FROM issues
            JOIN books ON books.id = issues.book_id
            JOIN members ON members.id = issues.member_id
            WHERE issue_date = ?''', (today,)).fetchall()

        weekly = cursor.execute('''
            SELECT books.title, members.name, issues.issue_date, issues.status
            FROM issues
            JOIN books ON books.id = issues.book_id
            JOIN members ON members.id = issues.member_id
            WHERE issue_date BETWEEN ? AND ?''', (week_ago, today)).fetchall()

        monthly = cursor.execute('''
            SELECT books.title, members.name, issues.issue_date, issues.status
            FROM issues
            JOIN books ON books.id = issues.book_id
            JOIN members ON members.id = issues.member_id
            WHERE issue_date >= ?''', (month_start,)).fetchall()

    return render_template("admin_reports.html",
                           daily=daily, weekly=weekly, monthly=monthly)




@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

@app.route('/member/logout')
def member_logout():
    session.pop('member_logged_in', None)
    session.pop('member_id', None)
    session.pop('member_name', None)
    return redirect(url_for('home'))


@app.route('/admin/members')
def manage_members():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    with sqlite3.connect("library.db") as conn:
        members = conn.execute("SELECT * FROM members").fetchall()
    
    return render_template("admin_manage_members.html", members=members)

@app.route('/admin/member/delete/<int:member_id>')
def delete_member(member_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    with sqlite3.connect("library.db") as conn:
        conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    return redirect(url_for('manage_members'))


@app.route('/admin/transactions')
def view_transactions():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    with sqlite3.connect("library.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT members.name, books.title, issues.issue_date, issues.return_date, issues.status
            FROM issues
            JOIN members ON issues.member_id = members.id
            JOIN books ON issues.book_id = books.id
        ''')
        transactions = cursor.fetchall()

    return render_template("admin_transactions.html", transactions=transactions)


@app.route('/member/return/<int:issue_id>')
def member_return(issue_id):
    if not session.get('member_logged_in'):
        return redirect(url_for('member_login'))

    return_date = datetime.today().strftime("%Y-%m-%d")
    with sqlite3.connect("library.db") as conn:
        conn.execute("UPDATE issues SET return_date = ?, status = 'Returned' WHERE id = ?", 
                     (return_date, issue_id))

    return redirect(url_for('member_dashboard'))







@app.context_processor
def inject_globals():
    return {
        'now': datetime.now(),
        'timedelta': timedelta
    }












if __name__ == '__main__':
    init_db()
    app.run(debug=True)
