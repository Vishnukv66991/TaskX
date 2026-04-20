from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.db import supabase

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def splash():
    return render_template('splash.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash("All fields are required!", "danger")
            return redirect(url_for('auth.signup'))

        hashed_password = generate_password_hash(password)

        try:
            existing_user = supabase.table("users").select("email").eq("email", email).execute()
            if existing_user.data:
                flash("Email already exists!", "danger")
                return redirect(url_for('auth.signup'))

            supabase.table("users").insert({
                "username": username,
                "email": email,
                "password": hashed_password
            }).execute()

            flash("Signup successful! Please login.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash("Something went wrong!", "danger")
            return redirect(url_for('auth.signup'))

    return render_template('signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Email and password are required.", "danger")
            return redirect(url_for('auth.login'))

        try:
            response = supabase.table("users").select("*").eq("email", email).execute()
            user = response.data

            if user and check_password_hash(user[0]['password'], password):
                session['user_id'] = user[0]['id']
                session['username'] = user[0]['username']
                flash("Login successful!", "success")
                return redirect(url_for('main.dashboard'))
            else:
                flash("Invalid email or password", "danger")
        except Exception as e:
            flash("Login failed due to an internal error.", "danger")

        return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
