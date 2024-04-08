from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for, json, jsonify, flash
from flask_pymongo import pymongo
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Connect to MongoDB Atlas
CONNECTION_STRING = os.getenv("MONGODB_URI") 
# Access the MongoDB connection string using os.getenv()

client = pymongo.MongoClient(CONNECTION_STRING)
db = client.get_database('expense_info')
expenses_collection = db.get_collection('expenses')  
users_collection = db.get_collection('users')


class User:
    def signup(self, username, password):
        user = {
            "_id": uuid.uuid4().hex,
            "username": username,
            "password": generate_password_hash(password),
        }

        users_collection.insert_one(user)

        return {"Message": "Signup successful!"}, 200

class Expense:
    def add_expense(self, amount, category, description, user_name):
        # Ensure user is authenticated
        expense = {
                "_id": uuid.uuid4().hex,
                "user_name": user_name,
                "amount": amount,
                "category": category,
                "description": description,
                "timestamp": datetime.now()
            }
        if user_name:    
            expenses_collection.insert_one(expense)
            return {"Message": "Added successful!"}, 200
        else:
            return {"Message": "Failed to add!"}, 400
    
    def get_expense_by_id(self, expense_id):
        return expenses_collection.find_one({"_id": expense_id})

    def update_expense(self, expense_id, amount, category, description):
        expenses_collection.update_one(
            {"_id": expense_id},
            {"$set": {"amount": amount, "category": category, "description": description}}
        )

    def delete_expense(self, expense_id):
        expenses_collection.delete_one({"_id": expense_id})

# Routes
@app.route('/')
def index():
    return render_template('home.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        
        # Check if username exists
        user_data = users_collection.find_one({"username": username})
        if user_data:
            # Check if password matches
            stored_password = user_data['password']
            if check_password_hash(stored_password, password):
                print(f"Logged in.")

                # Set up session for the user
                session['username'] = username
                # print(f"{session[username]}.")
                return redirect(url_for('dashboard'))  # Redirect to dashboard on successful login
            else:
                flash('Incorrect password. Please try again.', 'error')
        else:
            flash('Username does not exist. Please sign up.', 'error')

    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    print(f"{username} and {password} and {confirm_password}.")
    # Check if username already exists
    if users_collection.find_one({"username": username}):
        return jsonify({"Error": "Username already taken!"}), 400
     
    # Check if passwords match
    if password != confirm_password:
        return jsonify({"Error": "Passwords don't match!"}), 400

    # Signup successful, create a User instance and call the signup method
    user_instance = User()
    response, status_code = user_instance.signup(username, password)
    
    # Redirect to the login page after successful signup
    if status_code == 200:
        return redirect(url_for('login'))

    return jsonify(response), status_code

@app.route('/signup', methods=['GET'])
def signup1():    
    return render_template('signup.html')

# Routes for expense management
@app.route('/edit/<expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense_instance = Expense()
    expense_data = expense_instance.get_expense_by_id(expense_id)
    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']
        expense_instance.update_expense(expense_id, amount, category, description)
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    else:
        return render_template('edit_expense.html', expense=expense_data)

@app.route('/expenses/<expense_id>/update', methods=['POST'])
def update_expense(expense_id):
    # Retrieve the expense document from the database based on the expense_id
    expense_data = expenses_collection.find_one({"_id": expense_id})
    if expense_data:
        # Get the new data from the form
        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']
        
        # Update the expense document with the new data
        expenses_collection.update_one(
            {"_id": expense_id},
            {"$set": {"amount": amount, "category": category, "description": description}}
        )

        flash('Expense updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Expense not found!', 'error')
        return redirect(url_for('dashboard'))


@app.route('/delete/<expense_id>', methods=['POST'])
def delete_expense(expense_id):
    expense_instance = Expense()
    expense_instance.delete_expense(expense_id)
    flash('Expense deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/save', methods=['POST'])
def save_transaction():
    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']
        
        # Get the user ID from the session
        user_name = session.get('username')
        print(f"{user_name} and {amount} and {description}.")
        # Ensure user is authenticated
        if user_name:
            # Create the expense document
            expense_instance = Expense()
            response, status_code = expense_instance.add_expense(amount, category, description, user_name)
            if status_code == 200:
                return redirect(url_for('dashboard'))
            return jsonify(response), status_code
        else:
            # Redirect to the login page if user is not authenticated
            flash('You must be logged in to save expenses', 'error')
            return redirect(url_for('login'))


@app.route('/test')
def display_users():
    users = list(users_collection.find({}))
    return render_template('users.html', users=users)

@app.route('/expenses')
def display_expenses():
    # Get the category filter from the query parameters
    category_filter = request.args.get('category')

    # If a category filter is provided, query expenses with that category
    if category_filter:
        expenses = list(expenses_collection.find({"category": category_filter}))
    else:
        # Otherwise, fetch all expenses
        expenses = list(expenses_collection.find({}))

    # Fetch all unique categories for the category dropdown in the frontend
    categories = set(expense['category'] for expense in expenses)

    return render_template('expenses.html', expenses=expenses, categories=categories)

@app.route('/dashboard', methods=['GET'])
def dashboard():
    # Retrieve expenses from the database
    expenses = list(expenses_collection.find({}))
    categories = set(expense['category'] for expense in expenses)
    return render_template('dashboard.html', expenses=expenses, categories=categories)


@app.route('/logout')
def logout():
    # Remove user's session data
    session.pop('username', None)
    flash('Logged out successfuly!', 'successful')
    # Redirect the user to the login page
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
