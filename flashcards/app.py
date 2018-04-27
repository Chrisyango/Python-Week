from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'flashcards'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MySQL
mysql = MySQL(app)

# Index
@app.route('/')
def index():
  return render_template('home.html')

# About
@app.route('/about')
def about():
  return render_template('about.html')

# Register From Class
class RegisterForm(Form):
  name = StringField('Name', [validators.Length(min=1, max=50)])
  username = StringField('Username', [validators.Length(min=4, max=25)])
  email = StringField('Email', [validators.Length(min=6, max=50)])
  password = PasswordField('Password', [
    validators.DataRequired(),
    validators.EqualTo('confirm', message='Password do not match')
  ])
  confirm = PasswordField('Confirm Password')

# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
  form = RegisterForm(request.form)
  if request.method == 'POST' and form.validate():
    name = form.name.data
    email = form.email.data
    username = form.username.data
    password = sha256_crypt.encrypt(str(form.password.data))
    # Create Cursor
    cur = mysql.connection.cursor()
    # Execute query
    cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))
    # Commit to DB
    mysql.connection.commit()
    # Close connection
    cur.close()
    flash('You are now registered and can log in', 'success')
    redirect(url_for('login'))

  return render_template('register.html', form=form)

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    # Get Form Fields
    username = request.form['username']
    password_candidate = request.form['password']
    # Create cursor
    cur = mysql.connection.cursor()
    # Get user by username
    result = cur.execute("SELECT * FROM users WHERE username = %s", [username])
    if result > 0:

      # Get stored hash
      data = cur.fetchone()
      password = data['password']

      # Compare passwords
      if sha256_crypt.verify(password_candidate, password):
        session['logged_in'] = True
        session['username'] = username
        session['question'] = 0
        session['correct'] = 0
        flash('You are now logged in', 'success')
        return redirect(url_for('dashboard'))

      else:
        error = 'Invalid login'
        return render_template('login.html', error=error)

      cur.close()

    else:
      error = 'Username not found'
      return render_template('login.html', error=error)
  return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
  @wraps(f)
  def wrap(*args, **kwargs):
    if 'logged_in' in session:
      return f(*args, **kwargs)
    else:
      flash('Unauthorized, please login', 'danger')
      return redirect(url_for('login'))
  return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
  session.clear()
  flash('You are now logged out', 'success')
  return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
  author = session['username']
  # Create cursor
  cur = mysql.connection.cursor()

  #Get cards
  result = cur.execute("SELECT * FROM cards WHERE author = %s", [author])
  cards = cur.fetchall()

  if result > 0:
    return render_template('dashboard.html', cards=cards)
  else:
    msg = 'No Cards Found'
    return render_template('dashboard.html', msg=msg)
  # Close connections
  cur.close()

# # Cards
# @app.route('/cards')
# def cards():
#   # Create cursor
#   cur = mysql.connection.cursor()

#   #Get cards
#   result = cur.execute("SELECT * FROM cards")
#   cards = cur.fetchall()

#   if result > 0:
#     return render_template('cards.html', cards=cards)
#   else:
#     msg = 'No Cards Found'
#     return render_template('cards.html', msg=msg)
#   # Close connections
#   cur.close()

# Cards
@app.route('/cards')
@is_logged_in
def cards():
  # Create cursor
  cur = mysql.connection.cursor()

  #Get cards
  result = cur.execute("SELECT * FROM cards")
  cards = cur.fetchall()

  if result > 0:
    return render_template('cards.html', cards=cards)
  else:
    msg = 'No Cards Found'
    return render_template('cards.html', msg=msg)
  # Close connections
  cur.close()

# Single Card
@app.route('/card/<string:id>/')
def card(id):
  # Create cursor
  cur = mysql.connection.cursor()

  #Get articles
  result = cur.execute("SELECT * FROM cards WHERE id = %s", [id])
  card = cur.fetchone()

  return render_template('card.html', card=card)

# Card Form Class
class CardForm(Form):
  question = StringField('Question', [validators.Length(min=1)])
  answer = TextAreaField('Answer', [validators.Length(min=1)])

# Add Card
@app.route('/add_card', methods=['GET', 'POST'])
@is_logged_in
def add_card():
  form = CardForm(request.form)
  if request.method == 'POST' and form.validate():
    question = form.question.data
    answer = form.answer.data
    # Create cursor
    cur = mysql.connection.cursor()
    # Execute
    cur.execute("INSERT INTO cards(question, answer, author) VALUES(%s, %s, %s)", (question, answer, session['username']))
    # Commit to DB
    mysql.connection.commit()
    # Close connection
    cur.close()
    flash('Card Created', 'success')
    return redirect(url_for('dashboard'))
  return render_template('add_card.html', form=form)

# Edit Card
@app.route('/edit_card/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_card(id):
  # Create cursor
  cur = mysql.connection.cursor()

  # Get card by id
  result = cur.execute("SELECT * FROM cards WHERE id=%s", [id])

  card = cur.fetchone()

  # Get form
  form = CardForm(request.form)

  # Populate card form fields
  form.question.data = card['question']
  form.answer.data = card['answer']

  if request.method == 'POST' and form.validate():
    question = request.form['question']
    answer = request.form['answer']
    # Create cursor
    cur = mysql.connection.cursor()
    # Execute
    cur.execute("UPDATE cards SET question=%s, answer=%s WHERE id = %s", (question, answer, id))
    # Commit to DB
    mysql.connection.commit()
    # Close connection
    cur.close()
    flash('Question Updated', 'success')
    return redirect(url_for('dashboard'))
  return render_template('edit_card.html', form=form)

# Delete Card
@app.route('/delete_card/<string:id>', methods=['POST'])
@is_logged_in
def delete_card(id):
  # Create cursor
  cur = mysql.connection.cursor()
  # Execute
  cur.execute("DELETE FROM cards WHERE id= %s", [id])
  # Commit to DB
  mysql.connection.commit()
  # Close connection
  cur.close()
  flash('Card Deleted', 'success')
  return redirect(url_for('dashboard'))

# Quiz
@app.route('/quiz')
def quiz():
  session['question'] = 0
  session['correct'] = 0
  return render_template('quiz.html')

# Answer Form Class
class AnswerForm(Form):
  answer = TextAreaField('Answer', [validators.Length(min=1)])

# Answer Cards
@app.route('/answer_cards', methods=['GET', 'POST'])
@is_logged_in
def answer_cards():
  author = session['username']
  # Create cursor
  cur = mysql.connection.cursor()
  #Get cards
  result = cur.execute("SELECT * FROM cards WHERE author = %s", [author])
  cards = cur.fetchall()
  if session['question'] == len(cards):
    return redirect(url_for('results'))
  card = cards[session['question']]
  # Close connections
  cur.close()
  if request.method == 'POST':
    # Get Form Fields
    answer = request.form['answer']
    session['question'] = session['question'] + 1
    if answer == card['answer']:
      session['correct'] = session['correct'] + 1
      # flash('You are correct', 'success') 
    # else:
    #   flash('You are incorrect', 'success')
    return redirect(url_for('answer_cards'))
  if result > 0:
    return render_template('answer_cards.html', card=card)
  else:
    msg = 'No Cards Found'
    return render_template('answer_cards.html', msg=msg)

# Results
@app.route('/results')
def results():
  return render_template('results.html')

if __name__ == '__main__':
  app.secret_key='secret123'
  app.run(debug=True)