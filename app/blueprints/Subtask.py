import os
import re
import uuid
from flask import Blueprint, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from app.utils.db import supabase
from app.utils.decorators import login_required

subtask_bp = Blueprint("subtask", __name__)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_status(raw_status):
    status = (raw_status or "pending").strip().lower()
    return "completed" if status == "complete" else status


def is_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def build_parent_marker(parent_id):
    return f"[PARENT_TASK_ID:{parent_id}]"


def add_parent_marker(task_details, parent_id):
    marker = build_parent_marker(parent_id)
    if not task_details:
        return marker
    if marker in task_details:
        return task_details
    return f"{marker}\n{task_details}"


@subtask_bp.route("/create-subtask", methods=["POST"])
@login_required
def create_subtask():
    task_name = request.form.get("task_name")
    task_description = request.form.get("task_description")
    task_details = request.form.get("task_details")
    parent_id_raw = request.form.get("parent_id")
    assigned_to = request.form.get("assigned_to") or None
    status = normalize_status(request.form.get("status"))
    attachment_file = request.files.get("attachment")

    if not task_name or not task_description:
        flash("Task name and description are required.", "danger")
        return redirect(url_for("tasks.new_subtask", parent_id=parent_id_raw))

    try:
        parent_id = int(parent_id_raw)
    except (TypeError, ValueError):
        flash("Invalid parent task.", "danger")
        return redirect(url_for("tasks.tasks_page"))

    try:
        parent_res = (
            supabase.table("tasks")
            .select("*")
            .eq("id", parent_id)
            .single()
            .execute()
        )
        parent_task = parent_res.data
    except Exception as e:
        print("Parent lookup error:", e)
        parent_task = None

    if not parent_task:
        flash("Parent task not found.", "danger")
        return redirect(url_for("tasks.tasks_page"))

    attachment_path = None
    if attachment_file and attachment_file.filename:
        filename = secure_filename(attachment_file.filename)
        if allowed_file(filename):
            upload_folder = os.path.join(current_app.root_path, "static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            saved_path = os.path.join(upload_folder, unique_filename)
            attachment_file.save(saved_path)
            attachment_path = f"uploads/{unique_filename}"
        else:
            flash("Allowed file types: png, jpg, jpeg, gif, pdf", "danger")
            return redirect(url_for("tasks.new_subtask", parent_id=parent_id))

    try:
        full_details = add_parent_marker(task_details, parent_id)

        base_data = {
            "task_name": task_name,
            "task_description": task_description,
            "task_details": full_details,
            "parent_id": parent_id,
            "attachment": attachment_path,
            "status": status,
        }

        if parent_task.get("space_id") is not None:
            base_data["space_id"] = parent_task.get("space_id")

        if assigned_to and is_uuid(assigned_to):
            base_data["assigned_to"] = assigned_to

        payload_attempts = [
            dict(base_data),
            {k: v for k, v in base_data.items() if k != "assigned_to"},
            {k: v for k, v in base_data.items() if k != "space_id"},
            {
                k: v
                for k, v in base_data.items()
                if k not in {"assigned_to", "space_id"}
            },
            {k: v for k, v in base_data.items() if k != "parent_id"},
            {
                k: v
                for k, v in base_data.items()
                if k not in {"parent_id", "assigned_to", "space_id"}
            },
        ]
        payload_attempts[-1]["status"] = "pending"

        last_error = None
        created = False
        for payload in payload_attempts:
            try:
                supabase.table("tasks").insert(payload).execute()
                created = True
                break
            except Exception as insert_error:
                last_error = insert_error
                print("Subtask insert attempt failed:", insert_error)

        if created:
            flash("Subtask created successfully!", "success")
        else:
            print("Subtask Error:", last_error)
            flash("Failed to create subtask.", "danger")
    except Exception as e:
        print("Subtask Error:", e)
        flash("Failed to create subtask.", "danger")

    return redirect(url_for("tasks.tasks_page"))
