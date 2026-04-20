from functools import wraps
from flask import session, redirect, url_for, flash, abort
from app.utils.db import supabase

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        
        user_id = session['user_id']
        try:
            response = supabase.table("users").select("role").eq("id", user_id).execute()
            if not response.data or response.data[0].get('role') != 'admin':
                flash("You do not have permission to perform this action.", "danger")
                abort(403)
        except Exception as e:
            abort(500)
            
        return f(*args, **kwargs)
    return decorated_function
