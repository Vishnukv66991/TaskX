from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.utils.db import supabase
from app.utils.decorators import login_required

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat')
@login_required
def chat():
    current_user = session['user_id']
    selected_user = request.args.get('user')

    try:
        users_res = supabase.table("users").select("id, username").neq("id", current_user).execute()
        users = users_res.data if users_res.data else []
    except Exception as e:
        users = []
        flash("Failed to load user list.", "danger")

    messages = []
    if selected_user:
        try:
            msg_res = supabase.table("messages").select("*").or_(
                f"and(sender_id.eq.{current_user},receiver_id.eq.{selected_user}),"
                f"and(sender_id.eq.{selected_user},receiver_id.eq.{current_user})"
            ).order("created_at").execute()
            messages = msg_res.data if msg_res.data else []
        except Exception as e:
            flash("Failed to load messages.", "danger")

    return render_template(
        "chat_users.html",
        users=users,
        messages=messages,
        selected_user=selected_user
    )


@chat_bp.route('/send-message', methods=['POST'])
@login_required
def send_message():
    sender = session['user_id']
    receiver = request.form.get('receiver_id')
    message = request.form.get('message')

    if not message:
        flash("Message cannot be empty", "danger")
        return redirect(url_for('chat.chat', user=receiver))

    if not receiver:
        flash("Must select a user to message.", "danger")
        return redirect(url_for('chat.chat'))

    try:
        supabase.table("messages").insert({
            "sender_id": sender,
            "receiver_id": receiver,
            "message": message
        }).execute()
    except Exception as e:
        flash("Failed to send message", "danger")

    return redirect(url_for('chat.chat', user=receiver))
