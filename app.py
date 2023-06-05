from flask import Flask, render_template, request, redirect, url_for,jsonify
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from chatbot import get_answer_gpt3

app = Flask(__name__)
app.debug = True

# MySQL configurations
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Hat00545.1'
app.config['MYSQL_DB'] = 'chatflow_db'   
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route('/')
def index():
    cur = mysql.connection.cursor()
    result = cur.execute('SELECT * FROM users')
    if result > 0:
        users = cur.fetchall()
        print(users)
    return render_template('index.html')


@app.route('/users')
def users():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM users')
    data = cur.fetchall()
    cur.close()
    return render_template('users.html', users=data)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    try:
        if request.method == 'POST':
            # Get form data
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form.get('confirm-password')

            # Check if email already exists
            cur = mysql.connection.cursor()
            result = cur.execute('SELECT * FROM users WHERE email = %s', (email,))
            if result > 0:
                error = 'Email already exists'
                return render_template('singup.html', error=error)

            # Check if confirm password matches
            if password != confirm_password:
                error = 'Passwords do not match'
                return render_template('singup.html', error=error)

            # Hash the password
            hashed_password = sha256_crypt.hash(password)

            # Insert the user into the database
            cur.execute('INSERT INTO users(username, email, password) VALUES(%s, %s, %s)', (username, email, hashed_password))
            mysql.connection.commit()

            return redirect(url_for('login'))

        return render_template('singup.html')

    except mysql.Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return render_template('error.html', error="Could not connect to the database")




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        email = request.form['email']
        password = request.form['password']

        # Check if email exists
        cur = mysql.connection.cursor()
        result = cur.execute('SELECT * FROM users WHERE email = %s', (email,))
        if result == 0:
            error = 'Email not found'
            return render_template('login.html', error=error)

        # Verify the password
        data = cur.fetchone()
        hashed_password = data['password']
        if sha256_crypt.verify(password, hashed_password):
            # Login successful
            return redirect(url_for('chat'))
        else:
            # Incorrect password
            error = 'Incorrect password'
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/answer', methods=['GET'])
def answer():
    try:
        question = request.args['question']
    except KeyError:
        return jsonify({'error': 'No question provided'})

    answer = get_answer_gpt3(question)
    return jsonify({'answer': answer})

if __name__ == '__main__':
    app.run()