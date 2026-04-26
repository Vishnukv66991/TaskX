import re
from collections import Counter
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.utils.db import supabase
from app.utils.decorators import login_required

tasks_bp = Blueprint('tasks', __name__)
UPDATE_MARKER = "[PROGRESS_UPDATE]"


def extract_parent_id(task):
    parent_id = task.get("parent_id")
    if parent_id:
        return parent_id

    details = task.get("task_details") or ""
    match = re.search(r"\[PARENT_TASK_ID:(\d+)\]", details)
    if match:
        return int(match.group(1))
    return None


def normalize_status(raw_status):
    status = (raw_status or "pending").strip().lower()
    if status == "complete":
        return "completed"
    return status


def _split_task_details_and_updates(task):
    raw_details = (task.get("task_details") or "").strip()
    if not raw_details:
        task["task_details_clean"] = None
        task["progress_updates"] = []
        return

    clean_lines = []
    updates = []

    for line in raw_details.splitlines():
        line = line.strip()
        if line.startswith(f"{UPDATE_MARKER}|"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                _, ts, author, message = parts
                updates.append(
                    {
                        "timestamp": ts,
                        "author": author or "Unknown",
                        "message": message.strip(),
                    }
                )
        else:
            clean_lines.append(line)

    task["task_details_clean"] = "\n".join([l for l in clean_lines if l]).strip() or None
    task["progress_updates"] = updates


def task_matches(task, status_filter, assignee_filter, query):
    if status_filter != "all" and normalize_status(task.get("status")) != status_filter:
        return False

    if assignee_filter != "all":
        assignee_value = str(task.get("assigned_to") or "")
        if assignee_value != assignee_filter:
            return False

    if query:
        text = " ".join(
            [
                str(task.get("task_name") or ""),
                str(task.get("task_description") or ""),
                str(task.get("task_details") or ""),
            ]
        ).lower()
        if query not in text:
            return False

    return True


def filter_tree(task, status_filter, assignee_filter, query):
    filtered_children = []
    for child in task.get("subtasks", []):
        kept_child = filter_tree(child, status_filter, assignee_filter, query)
        if kept_child:
            filtered_children.append(kept_child)

    include_self = task_matches(task, status_filter, assignee_filter, query)
    if include_self or filtered_children:
        task["subtasks"] = filtered_children
        task["subtask_count"] = len(filtered_children)
        return task
    return None


@tasks_bp.route('/tasks')
@login_required
def tasks_page():
    status_filter = normalize_status(request.args.get("status", "all"))
    assignee_filter = request.args.get("assignee", "all")
    query = (request.args.get("q", "") or "").strip().lower()

    try:
        # Fetch tasks
        tasks_res = supabase.table("tasks") \
            .select("*") \
            .order("id", desc=True) \
            .execute()

        tasks = tasks_res.data or []

        # Fetch users
        users_res = supabase.table("users") \
            .select("id, username") \
            .execute()

        users = users_res.data or []

        # Map user_id → username
        user_map = {u["id"]: u["username"] for u in users}

        # Attach username to each task
        status_counter = Counter()
        for task in tasks:
            task["assigned_name"] = user_map.get(task.get("assigned_to"), "Unassigned")
            status_counter[normalize_status(task.get("status"))] += 1
            _split_task_details_and_updates(task)

        task_map = {task["id"]: task for task in tasks}

        for task in tasks:
            task["subtasks"] = []

        root_tasks = []

        for task in tasks:
            parent_id = extract_parent_id(task)
            if parent_id and parent_id in task_map:
                task_map[parent_id]["subtasks"].append(task)
            else:
                root_tasks.append(task)

        filtered_tasks = []
        for root in root_tasks:
            kept = filter_tree(root, status_filter, assignee_filter, query)
            if kept:
                filtered_tasks.append(kept)

    except Exception as e:
        print("Error:", e)
        users = []
        status_counter = Counter()
        filtered_tasks = []
        root_tasks = []

    summary = {
        "total": sum(status_counter.values()),
        "pending": status_counter.get("pending", 0),
        "in_progress": status_counter.get("in progress", 0),
        "complete": status_counter.get("complete", 0) + status_counter.get("completed", 0),
        "hold": status_counter.get("hold", 0),
    }

    return render_template(
        "tasks.html",
        tasks=filtered_tasks,
        users=users,
        summary=summary,
        selected_status=status_filter,
        selected_assignee=assignee_filter,
        query=request.args.get("q", ""),
    )


@tasks_bp.route('/tasks/<int:task_id>/update', methods=['POST'])
@login_required
def add_task_update(task_id):
    update_text = (request.form.get("progress_comment") or "").strip()
    redirect_to = request.form.get("next") or request.referrer or url_for("tasks.tasks_page")

    if not update_text:
        flash("Progress comment cannot be empty.", "warning")
        return redirect(redirect_to)

    author = session.get("username", "Unknown")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    safe_text = " ".join(update_text.splitlines()).strip()
    update_line = f"{UPDATE_MARKER}|{timestamp}|{author}|{safe_text}"

    try:
        task_res = (
            supabase.table("tasks")
            .select("id, task_details")
            .eq("id", task_id)
            .single()
            .execute()
        )
        task = task_res.data
        if not task:
            flash("Task not found.", "danger")
            return redirect(redirect_to)

        current_details = (task.get("task_details") or "").strip()
        new_details = f"{current_details}\n{update_line}".strip() if current_details else update_line

        supabase.table("tasks").update({"task_details": new_details}).eq("id", task_id).execute()
        flash("Progress update added.", "success")
    except Exception as e:
        print("Task update error:", e)
        flash("Failed to add progress update.", "danger")

    return redirect(redirect_to)


@tasks_bp.route('/subtasks/new/<int:parent_id>', methods=['GET'])
@login_required
def new_subtask(parent_id):
    try:
        parent_res = supabase.table("tasks").select("id, task_name").eq("id", parent_id).single().execute()
        parent_task = parent_res.data
    except Exception as e:
        print("Parent task fetch error:", e)
        parent_task = None

    if not parent_task:
        flash("Parent task not found.", "danger")
        return redirect(url_for('tasks.tasks_page'))

    try:
        users_res = supabase.table("users").select("id, username").execute()
        users = users_res.data or []
    except Exception as e:
        print("User fetch error:", e)
        users = []

    return render_template("subtask_form.html", parent_task=parent_task, users=users)
