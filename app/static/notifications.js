async function refreshNotificationBatches() {
  try {
    const response = await fetch("/api/notifications/summary", {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!response.ok) return;

    const payload = await response.json();
    const taskCount = Number(payload.task_notifications || 0);
    const chatCount = Number(payload.chat_unread || 0);

    const taskBadge = document.getElementById("task-notif-badge");
    const chatBadge = document.getElementById("chat-notif-badge");

    if (taskBadge) {
      taskBadge.textContent = taskCount > 99 ? "99+" : String(taskCount);
      taskBadge.style.display = taskCount > 0 ? "inline-flex" : "none";
    }
    if (chatBadge) {
      chatBadge.textContent = chatCount > 99 ? "99+" : String(chatCount);
      chatBadge.style.display = chatCount > 0 ? "inline-flex" : "none";
    }
  } catch (error) {
    // Notification polling should never break UI interactions.
    console.debug("Notification polling unavailable", error);
  }
}

refreshNotificationBatches();
setInterval(refreshNotificationBatches, 15000);
