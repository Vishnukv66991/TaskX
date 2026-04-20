from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from app.utils.db import supabase
from app.utils.decorators import login_required, admin_required

users_bp = Blueprint('users', __name__)

@users_bp.route('/add-user', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not username or not email or not password or not role:
            flash("All fields are required!", "danger")
            return redirect(url_for('users.add_user'))

        hashed_password = generate_password_hash(password)

        try:
            supabase.table("users").insert({
                "username": username,
                "email": email,
                "password": hashed_password,
                "role": role
            }).execute()
            flash("User added successfully!", "success")
        except Exception as e:
            flash("Error adding user. Email may already exist.", "danger")

        return redirect(url_for('users.add_user'))

    return render_template('add_user.html')

@users_bp.route('/users')
@login_required
def list_users():
    try:
        response = supabase.table("users").select("id, username, email, role").execute()
        users = response.data if response.data else []
    except Exception as e:
        users = []
        flash("Error fetching users.", "danger")
    return render_template("users.html", users=users)


@users_bp.route('/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    try:
        supabase.table("users").delete().eq("id", user_id).execute()
        flash("User deleted successfully!", "success")
    except Exception as e:
        flash("Error deleting user.", "danger")
    return redirect(url_for('users.list_users'))


@users_bp.route('/edit-user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        
        if not username or not email or not role:
            flash("All fields are required.", "danger")
            return redirect(url_for('users.edit_user', user_id=user_id))

        try:
            supabase.table("users").update({
                "username": username,
                "email": email,
                "role": role
            }).eq("id", user_id).execute()
            flash("User updated successfully!", "success")
            return redirect(url_for('users.list_users'))
        except Exception as e:
            flash("Error updating user.", "danger")

    try:
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        if not response.data:
            flash("User not found.", "danger")
            return redirect(url_for('users.list_users'))
        user = response.data[0]
    except Exception as e:
        flash("Server error.", "danger")
        return redirect(url_for('users.list_users'))

    return render_template("user.html", user=user)
