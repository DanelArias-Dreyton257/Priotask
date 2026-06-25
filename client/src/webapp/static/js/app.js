/*
 * Wires ApiClient + TokenStore + Views together and holds the small bit of
 * app state (the logged-in username). Analogous to a server-side Manager:
 * it coordinates the lower layers but has no rendering or transport logic
 * of its own.
 */
import { ApiClient, ApiError } from "./api.js";
import { TokenStore } from "./session.js";
import { Views } from "./views.js";

const api = new ApiClient(window.PRIOTASK_API_BASE_URL);

async function refreshTasksAndPlan() {
    const hours = document.getElementById("hours-input").value || undefined;
    const [tasks, plan] = await Promise.all([api.listTasks(), api.getTodayPlan(hours)]);
    Views.renderTasks(tasks, { onComplete: completeTask, onDelete: deleteTask });
    Views.renderPlan(plan);
}

async function completeTask(taskId) {
    await runOrReportError(async () => {
        await api.completeTask(taskId);
        await refreshTasksAndPlan();
    });
}

async function deleteTask(taskId) {
    await runOrReportError(async () => {
        await api.deleteTask(taskId);
        await refreshTasksAndPlan();
    });
}

async function runOrReportError(action) {
    try {
        Views.clearMessage();
        await action();
    } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
            logout();
            Views.showMessage("Session expired, please log in again.", true);
            return;
        }
        Views.showMessage(error.message, true);
    }
}

function enterApp(username) {
    TokenStore.setUsername(username);
    Views.showAuthenticated(username);
    refreshTasksAndPlan().catch((error) => Views.showMessage(error.message, true));
}

function logout() {
    TokenStore.clearToken();
    Views.showAnonymous();
}

document.getElementById("login-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    runOrReportError(async () => {
        await api.login(form.get("username"), form.get("password"));
        enterApp(form.get("username"));
        Views.resetForm(event.target);
    });
});

document.getElementById("register-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    runOrReportError(async () => {
        await api.register(form.get("username"), form.get("password"), form.get("email"));
        await api.login(form.get("username"), form.get("password"));
        enterApp(form.get("username"));
        Views.resetForm(event.target);
    });
});

document.getElementById("logout-button").addEventListener("click", () => {
    runOrReportError(async () => {
        await api.logout();
        logout();
    });
});

document.getElementById("task-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    runOrReportError(async () => {
        await api.createTask({
            name: form.get("name"),
            deadline: form.get("deadline"),
            expected_duration_h: Number(form.get("expected_duration_h")),
            importance: Number(form.get("importance")),
            task_type: form.get("task_type") || "",
            task_subtype: form.get("task_subtype") || "",
        });
        Views.resetForm(event.target);
        await refreshTasksAndPlan();
    });
});

document.getElementById("plan-form").addEventListener("submit", (event) => {
    event.preventDefault();
    runOrReportError(refreshTasksAndPlan);
});

// Resume an existing session (token survives page reloads via localStorage).
const existingToken = TokenStore.getToken();
const existingUsername = TokenStore.getUsername();
if (existingToken && existingUsername) {
    enterApp(existingUsername);
} else {
    Views.showAnonymous();
}
