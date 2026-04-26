import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from app.utils.db import supabase
from app.utils.decorators import login_required

spaces_bp = Blueprint('spaces', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
UPDATE_MARKER = "[PROGRESS_UPDATE]"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_status(raw_status):
    status = (raw_status or "pending").strip().lower()
    return "completed" if status == "complete" else status


def split_task_details_and_updates(task):
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


def _ensure_admin_access():
    if session.get("role") != "admin":
        flash("Only admins can access spaces.", "danger")
        return False
    return True

# =========================
# CREATE SPACE
# =========================
@spaces_bp.route('/create-space', methods=['GET', 'POST'])
@login_required
def create_space():
    if not _ensure_admin_access():
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        space_type = request.form.get('type')
        user_id = session['user_id']

        if not name or not space_type:
            flash("Name and Type are required", "danger")
            return redirect(url_for('spaces.create_space'))

        try:
            supabase.table("spaces").insert({
                "name": name,
                "description": description,
                "type": space_type,
                "created_by": user_id
            }).execute()

            flash("Space created successfully!", "success")
            return redirect(url_for('spaces.list_spaces'))

        except Exception as e:
            print(e)
            flash("Failed to create space", "danger")

    return render_template("create_space.html")


# =========================
# LIST SPACES
# =========================
@spaces_bp.route('/spaces')
@login_required
def list_spaces():
    if not _ensure_admin_access():
        return redirect(url_for('main.dashboard'))

    try:
        res = supabase.table("spaces").select("*").order("id", desc=True).execute()
        spaces = res.data if res.data else []

        # Get users for name mapping
        users_res = supabase.table("users").select("id, username").execute()
        users = users_res.data if users_res.data else []

        user_map = {u["id"]: u["username"] for u in users}

        for s in spaces:
            s["created_by_name"] = user_map.get(s.get("created_by"), "Unknown")

    except Exception as e:
        print(e)
        spaces = []

    return render_template("spaces.html", spaces=spaces)


# =========================
# SPACE DETAILS + TASKS
# =========================
@spaces_bp.route('/space/<int:space_id>', methods=['GET', 'POST'])
@login_required
def space_detail(space_id):
    if not _ensure_admin_access():
        return redirect(url_for('main.dashboard'))

    # CREATE TASK
    if request.method == 'POST':
        task_name = request.form.get('task_name')
        task_description = request.form.get('task_description')
        task_details = request.form.get('task_details')
        attachment_file = request.files.get('attachment')
        assigned_to = request.form.get('assigned_to')
        status = normalize_status(request.form.get('status'))

        if not task_name or not task_description:
            flash("Task name and description are required.", "danger")
            return redirect(url_for('spaces.space_detail', space_id=space_id))

        if not assigned_to:
            assigned_to = None

        attachment_path = None
        if attachment_file and attachment_file.filename:
            filename = secure_filename(attachment_file.filename)
            if allowed_file(filename):
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                saved_path = os.path.join(upload_folder, unique_filename)
                attachment_file.save(saved_path)
                attachment_path = f'uploads/{unique_filename}'
            else:
                flash('Allowed file types: png, jpg, jpeg, gif, pdf', 'danger')
                return redirect(url_for('spaces.space_detail', space_id=space_id))

        try:
            supabase.table("tasks").insert({
                "space_id": space_id,
                "task_name": task_name.strip(),
                "task_description": task_description.strip(),
                "task_details": (task_details or "").strip() or None,
                "attachment": attachment_path,
                "assigned_to": assigned_to,
                "status": status
            }).execute()

            flash("Task created successfully!", "success")

        except Exception as e:
            print(f"Error creating task: {e}")
            flash("Failed to create task", "danger")

        return redirect(url_for('spaces.space_detail', space_id=space_id))

    try:
        # SPACE DATA
        space_res = supabase.table("spaces").select("*").eq("id", space_id).single().execute()
        space = space_res.data

        # TASKS
        task_res = supabase.table("tasks") \
            .select("*") \
            .eq("space_id", space_id) \
            .order("id", desc=True) \
            .execute()
        tasks = task_res.data if task_res.data else []

        # USERS (for dropdown + mapping)
        user_res = supabase.table("users").select("id, username").execute()
        users = user_res.data if user_res.data else []

    except Exception as e:
        print(f"Error fetching space data: {e}")
        space = {"name": "Unknown Space", "description": ""}
        tasks = []
        users = []
        flash("Error loading space details or tasks table may be missing.", "danger")

    user_map = {u["id"]: u["username"] for u in users}

    for t in tasks:
        t["assigned_name"] = user_map.get(t.get("assigned_to"), "Unassigned")
        split_task_details_and_updates(t)

    return render_template(
        "space_detail.html",
        space=space,
        tasks=tasks,
        users=users
    )