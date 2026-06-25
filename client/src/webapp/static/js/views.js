/*
 * DOM rendering only - takes plain data (the same shapes the server hands
 * back: TaskDTO-like objects, plan entries) and updates the page. No fetch
 * calls and no app state live here, that belongs to the controller (app.js).
 */

export const Views = {
    showAuthenticated(username) {
        document.getElementById("auth-section").classList.add("hidden");
        document.getElementById("app-section").classList.remove("hidden");
        document.getElementById("user-bar").classList.remove("hidden");
        document.getElementById("username-display").textContent = username;
    },

    showAnonymous() {
        document.getElementById("auth-section").classList.remove("hidden");
        document.getElementById("app-section").classList.add("hidden");
        document.getElementById("user-bar").classList.add("hidden");
    },

    showMessage(text, isError = false) {
        const banner = document.getElementById("message-banner");
        banner.textContent = text;
        banner.classList.remove("hidden", "error", "info");
        banner.classList.add(isError ? "error" : "info");
    },

    clearMessage() {
        document.getElementById("message-banner").classList.add("hidden");
    },

    renderTasks(tasks, { onComplete, onDelete }) {
        const list = document.getElementById("task-list");
        list.innerHTML = "";

        if (tasks.length === 0) {
            list.innerHTML = "<li class='empty'>No tasks yet.</li>";
            return;
        }

        for (const task of tasks) {
            const item = document.createElement("li");
            item.className = "task-item" + (task.done ? " done" : "");

            const info = document.createElement("div");
            info.className = "task-info";
            info.innerHTML = `
                <strong>${escapeHtml(task.name)}</strong>
                <span>deadline: ${task.deadline.slice(0, 10)}</span>
                <span>effort: ${task.expected_duration_h}h</span>
                <span>importance: ${task.importance}</span>
            `;
            item.appendChild(info);

            if (!task.done) {
                const actions = document.createElement("div");
                actions.className = "task-actions";

                const completeButton = document.createElement("button");
                completeButton.textContent = "Done";
                completeButton.addEventListener("click", () => onComplete(task.task_id));
                actions.appendChild(completeButton);

                const deleteButton = document.createElement("button");
                deleteButton.textContent = "Delete";
                deleteButton.addEventListener("click", () => onDelete(task.task_id));
                actions.appendChild(deleteButton);

                item.appendChild(actions);
            }

            list.appendChild(item);
        }
    },

    renderPlan(entries) {
        const list = document.getElementById("plan-list");
        list.innerHTML = "";

        if (entries.length === 0) {
            list.innerHTML = "<li class='empty'>Nothing scheduled for today.</li>";
            return;
        }

        for (const entry of entries) {
            const item = document.createElement("li");
            item.className = "plan-item";
            item.innerHTML = `
                <strong>#${entry.rank} ${escapeHtml(entry.task.name)}</strong>
                <span>${entry.recommended_hours_today.toFixed(1)}h today</span>
                <span class="score">score ${entry.score.toFixed(2)}</span>
            `;
            list.appendChild(item);
        }
    },

    resetForm(form) {
        form.reset();
    },
};

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}
