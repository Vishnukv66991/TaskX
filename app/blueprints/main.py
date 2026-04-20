from flask import Blueprint, render_template, session
from app.utils.decorators import login_required
from app.utils.db import supabase

main_bp = Blueprint('main', __name__)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        response = supabase.table("tasks").select("*", count="exact").eq("user_id", session['user_id']).execute()
        tasks = response.data if response.data else []

        total_tasks = len(tasks)
        completed = len([t for t in tasks if t.get('status') == 'completed'])
        pending = len([t for t in tasks if t.get('status') == 'pending'])

    except Exception as e:
        tasks = []
        total_tasks = completed = pending = 0

    return render_template(
        "dashboard.html",
        tasks=tasks,
        total=total_tasks,
        completed=completed,
        pending=pending
    )
