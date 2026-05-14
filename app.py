from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import json
from reportlab.pdfgen import canvas

app = Flask(__name__)

app.secret_key = "expense_secret_key"

conn = sqlite3.connect('expenses.db', check_same_thread=False)

cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    expense_name TEXT,
    category TEXT,
    amount REAL
)
''')

conn.commit()

monthly_budget = 10000


@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        cursor.execute(
            'INSERT INTO users (username, password) VALUES (?, ?)',
            (username, password)
        )

        conn.commit()

        return redirect('/login')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        cursor.execute(
            'SELECT * FROM users WHERE username = ? AND password = ?',
            (username, password)
        )

        user = cursor.fetchone()

        if user:

            session['username'] = username

            return redirect('/')

    return render_template('login.html')


@app.route('/logout')
def logout():

    session.pop('username', None)

    return redirect('/login')


@app.route('/', methods=['GET', 'POST'])
def home():

    global monthly_budget

    if 'username' not in session:
        return redirect('/login')

    username = session['username']

    if request.method == 'POST':

        if 'set_budget' in request.form:

            monthly_budget = float(request.form['budget'])

        else:

            expense_name = request.form['expense_name']
            category = request.form['category']
            amount = float(request.form['amount'])

            cursor.execute(
                'INSERT INTO expenses (username, expense_name, category, amount) VALUES (?, ?, ?, ?)',
                (username, expense_name, category, amount)
            )

            conn.commit()

    search_query = request.args.get('search', '')

    if search_query:

        cursor.execute(
            '''
            SELECT * FROM expenses
            WHERE username = ?
            AND category LIKE ?
            ''',
            (username, f'%{search_query}%')
        )

    else:

        cursor.execute(
            'SELECT * FROM expenses WHERE username = ?',
            (username,)
        )

    expenses = cursor.fetchall()

    cursor.execute(
        'SELECT SUM(amount) FROM expenses WHERE username = ?',
        (username,)
    )

    total_expense = cursor.fetchone()[0]

    if total_expense is None:
        total_expense = 0

    remaining_balance = monthly_budget - total_expense

    progress_percentage = (total_expense / monthly_budget) * 100

    if progress_percentage > 100:
        progress_percentage = 100

    total_entries = len(expenses)

    expense_names = []
    expense_amounts = []

    category_totals = {}

    for expense in expenses:

        expense_names.append(expense[2])

        expense_amounts.append(expense[4])

        category = expense[3]

        if category not in category_totals:
            category_totals[category] = 0

        category_totals[category] += expense[4]

    ai_message = "Your spending looks balanced."

    if category_totals:

        highest_category = max(category_totals, key=category_totals.get)

        ai_message = f"You spend most on {highest_category}."

    return render_template(
        'index.html',
        expenses=expenses,
        total_expense=total_expense,
        total_entries=total_entries,
        remaining_balance=remaining_balance,
        monthly_budget=monthly_budget,
        progress_percentage=progress_percentage,
        ai_message=ai_message,
        expense_names=json.dumps(expense_names),
        expense_amounts=json.dumps(expense_amounts),
        username=username
    )


@app.route('/download_report')
def download_report():

    if 'username' not in session:
        return redirect('/login')

    username = session['username']

    cursor.execute(
        'SELECT * FROM expenses WHERE username = ?',
        (username,)
    )

    expenses = cursor.fetchall()

    pdf_file = f"{username}_expense_report.pdf"

    c = canvas.Canvas(pdf_file)

    c.setFont("Helvetica-Bold", 18)

    c.drawString(180, 800, "Expense Report")

    y = 750

    total = 0

    for expense in expenses:

        line = f"{expense[2]} | {expense[3]} | ₹ {expense[4]}"

        c.drawString(50, y, line)

        total += expense[4]

        y -= 25

    c.drawString(50, y - 20, f"Total Expense: ₹ {total}")

    c.save()

    return send_file(pdf_file, as_attachment=True)


@app.route('/delete/<int:id>')
def delete(id):

    cursor.execute('DELETE FROM expenses WHERE id = ?', (id,))

    conn.commit()

    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)