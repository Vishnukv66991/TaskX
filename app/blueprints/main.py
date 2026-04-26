from flask import Blueprint, jsonify, render_template, session
from app.utils.decorators import login_required
from app.utils.db import supabase

main_bp = Blueprint('main', __name__)


def _status_counts(tasks):
    total = len(tasks)
    completed = len([t for t in tasks if (t.get('status') or '').lower() in {'completed', 'complete'}])
    pending = len([t for t in tasks if (t.get('status') or '').lower() in {'pending', 'hold', 'in progress'}])
    return total, completed, pending


def _safe_unread_chat_count(user_id):
    try:
        # Preferred when schema has read tracking.
        unread_res = (
            supabase.table("messages")
            .select("id", count="exact")
            .eq("receiver_id", user_id)
            .eq("is_read", False)
            .execute()
        )
        return unread_res.count or 0
    except Exception:
        return 0


@main_bp.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role', 'member')
    user_id = session['user_id']

    try:
        users_res = supabase.table("users").select("id, username").execute()
        users = users_res.data or []
        user_map = {u["id"]: u["username"] for u in users}

        if role == 'admin':
            response = supabase.table("tasks").select("*", count="exact").order("id", desc=True).execute()
        else:
            response = (
                supabase.table("tasks")
                .select("*", count="exact")
                .eq("assigned_to", user_id)
                .order("id", desc=True)
                .execute()
            )
        tasks = response.data or []
        total_tasks, completed, pending = _status_counts(tasks)

        for task in tasks:
            task["assigned_name"] = user_map.get(task.get("assigned_to"), "Unassigned")

        assignee_counts = {}
        if role == 'admin':
            for task in tasks:
                assignee = task.get("assigned_to")
                assignee_name = user_map.get(assignee, "Unassigned")
                assignee_counts[assignee_name] = assignee_counts.get(assignee_name, 0) + 1

    except Exception:
        tasks = []
        total_tasks = completed = pending = 0
        assignee_counts = {}

    return render_template(
        "dashboard.html",
        tasks=tasks[:10],
        total=total_tasks,
        completed=completed,
        pending=pending,
        is_admin=(role == 'admin'),
        assignee_counts=assignee_counts,
    )


@main_bp.route('/api/notifications/summary')
@login_required
def notifications_summary():
    user_id = session['user_id']
    role = session.get('role', 'member')
    try:
        if role == 'admin':
            task_res = supabase.table("tasks").select("id", count="exact").execute()
        else:
            task_res = (
                supabase.table("tasks")
                .select("id", count="exact")
                .eq("assigned_to", user_id)
                .neq("status", "complete")
                .neq("status", "completed")
                .execute()
            )
        task_count = task_res.count or 0
    except Exception:
        task_count = 0

    return jsonify(
        {
            "task_notifications": task_count,
            "chat_unread": _safe_unread_chat_count(user_id),
        }
    )
