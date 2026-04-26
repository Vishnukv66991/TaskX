from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session
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

    unread_by_user = {}
    try:
        unread_rows = (
            supabase.table("messages")
            .select("sender_id", count="exact")
            .eq("receiver_id", current_user)
            .eq("is_read", False)
            .execute()
        )
        for row in (unread_rows.data or []):
            sender_id = row.get("sender_id")
            unread_by_user[sender_id] = unread_by_user.get(sender_id, 0) + 1
    except Exception:
        unread_by_user = {}

    messages = []
    if selected_user:
        try:
            msg_res = supabase.table("messages").select("*").or_(
                f"and(sender_id.eq.{current_user},receiver_id.eq.{selected_user}),"
                f"and(sender_id.eq.{selected_user},receiver_id.eq.{current_user})"
            ).order("created_at").execute()
            messages = msg_res.data if msg_res.data else []
            try:
                supabase.table("messages").update({"is_read": True}) \
                    .eq("sender_id", selected_user) \
                    .eq("receiver_id", current_user) \
                    .eq("is_read", False) \
                    .execute()
            except Exception:
                pass
        except Exception as e:
            flash("Failed to load messages.", "danger")

    return render_template(
        "chat_users.html",
        users=users,
        messages=messages,
        selected_user=selected_user,
        unread_by_user=unread_by_user,
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


@chat_bp.route('/api/chat/unread')
@login_required
def unread_counts():
    current_user = session['user_id']
    try:
        rows = (
            supabase.table("messages")
            .select("sender_id")
            .eq("receiver_id", current_user)
            .eq("is_read", False)
            .execute()
        ).data or []
    except Exception:
        rows = []

    counts = {}
    for row in rows:
        sender = row.get("sender_id")
        counts[str(sender)] = counts.get(str(sender), 0) + 1

    return jsonify({"counts": counts})
