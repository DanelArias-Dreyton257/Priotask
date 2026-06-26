/*
 * Wires ApiClient + TokenStore + Views together and holds the small bit of
 * app state (the logged-in username, the fetched tasks/plan, and the
 * current filter/sort/edit selections). Analogous to a server-side Manager:
 * it coordinates the lower layers but has no rendering or transport logic
 * of its own.
 */
import { ApiClient, ApiError } from "./api.js";
import { TokenStore } from "./session.js";
import { Views } from "./views.js";

const api = new ApiClient(window.PRIOTASK_API_BASE_URL);

let allTasks = [];
let scoreByTaskId = new Map();
let editingTaskId = null;
let showingWeekPlan = false;

async function refreshTasksAndPlan() {
    const hours = document.getElementById("hours-input").value || undefined;
    const [tasks, plan] = await Promise.all([api.listTasks(), api.getTodayPlan(hours)]);
    allTasks = tasks;
    scoreByTaskId = new Map(plan.map((entry) => [entry.task.task_id, entry.score]));
    refreshCategoryOptions();
    renderTaskList();
    Views.renderPlan(plan);
    if (showingWeekPlan) await refreshWeekPlan();
}

async function refreshWeekPlan() {
    const hours = document.getElementById("week-hours-input").value || undefined;
    const days = await api.getWeekPlan(hours, 7);
    Views.renderWeekPlan(days);
}

async function refreshPrioritizerStatus() {
    const status = await api.getPrioritizerStatus();
    Views.renderPrioritizerStatus(status);
}

async function refreshAccount() {
    const me = await api.getMe();
    Views.renderAccount(me);
}

function distinctValues(field) {
    return [...new Set(allTasks.map((task) => task[field]).filter(Boolean))].sort();
}

function refreshCategoryOptions() {
    const types = distinctValues("task_type");
    const subtypes = distinctValues("task_subtype");

    Views.wireCategoryField(
        document.getElementById("new-task-type-select"),
        document.getElementById("new-task-type-new"),
        types,
        "",
    );
    Views.wireCategoryField(
        document.getElementById("new-task-subtype-select"),
        document.getElementById("new-task-subtype-new"),
        subtypes,
        "",
    );
    Views.populateFilterSelect(document.getElementById("task-type-filter"), types, "All types");
    Views.populateFilterSelect(document.getElementById("task-subtype-filter"), subtypes, "All sub-types");
}

function filteredSortedTasks() {
    const search = document.getElementById("task-search").value.trim().toLowerCase();
    const typeFilter = document.getElementById("task-type-filter").value;
    const subtypeFilter = document.getElementById("task-subtype-filter").value;
    const showDone = document.getElementById("show-done-checkbox").checked;
    const sortBy = document.getElementById("task-sort").value;

    const tasks = allTasks.filter((task) => {
        if (!showDone && task.done) return false;
        if (search && !task.name.toLowerCase().includes(search)) return false;
        if (typeFilter && task.task_type !== typeFilter) return false;
        if (subtypeFilter && task.task_subtype !== subtypeFilter) return false;
        return true;
    });

    tasks.sort((a, b) => {
        if (sortBy === "deadline") return a.deadline.localeCompare(b.deadline);
        if (sortBy === "type") {
            return (a.task_type || "").localeCompare(b.task_type || "")
                || (a.task_subtype || "").localeCompare(b.task_subtype || "")
                || a.name.localeCompare(b.name);
        }
        const scoreA = scoreByTaskId.get(a.task_id);
        const scoreB = scoreByTaskId.get(b.task_id);
        if (scoreA === undefined && scoreB === undefined) return a.name.localeCompare(b.name);
        if (scoreA === undefined) return 1;
        if (scoreB === undefined) return -1;
        return scoreB - scoreA;
    });

    return tasks;
}

function renderTaskList() {
    Views.renderTasks(filteredSortedTasks(), {
        onComplete: completeTask,
        onDelete: deleteTask,
        onLogHours: logHours,
        onEdit: startEditTask,
        onCancelEdit: cancelEditTask,
        onSaveEdit: saveEditTask,
        editingTaskId,
        categories: { types: distinctValues("task_type"), subtypes: distinctValues("task_subtype") },
    });
}

function startEditTask(taskId) {
    editingTaskId = taskId;
    renderTaskList();
}

function cancelEditTask() {
    editingTaskId = null;
    renderTaskList();
}

async function saveEditTask(taskId, fields) {
    await runOrReportError(async () => {
        await api.updateTask(taskId, fields);
        editingTaskId = null;
        await refreshTasksAndPlan();
    });
}

async function completeTask(taskId) {
    await runOrReportError(async () => {
        await api.completeTask(taskId);
        await refreshTasksAndPlan();
    });
}

async function logHours(taskId, hours) {
    await runOrReportError(async () => {
        await api.logHours(taskId, hours);
        await refreshTasksAndPlan();
    });
}

async function deleteTask(taskId) {
    await runOrReportError(async () => {
        await api.deleteTask(taskId);
        await refreshTasksAndPlan();
    });
}

async function runOrReportError(action, { treatAuthErrorAsSessionExpiry = true } = {}) {
    try {
        Views.clearMessage();
        await action();
    } catch (error) {
        // A 401 from login/register itself means "wrong credentials", not "your
        // session expired" - there was no session yet, so don't relabel it and
        // don't log out a user who was never logged in for this attempt.
        if (treatAuthErrorAsSessionExpiry && error instanceof ApiError && error.status === 401) {
            logout();
            Views.showMessage("Session expired, please log in again.", true);
            return;
        }
        Views.showMessage(error.message, true);
    }
}

function reportEnterAppError(error) {
    // A stored token can outlive the server's in-memory AuthService (e.g. a
    // restart) - resuming with it should drop back to the login screen with
    // the same wording as any other expired session, not leave the app
    // looking authenticated while every request fails.
    if (error instanceof ApiError && error.status === 401) {
        logout();
        Views.showMessage("Session expired, please log in again.", true);
        return;
    }
    Views.showMessage(error.message, true);
}

function enterApp(username) {
    TokenStore.setUsername(username);
    Views.showAuthenticated(username);
    refreshTasksAndPlan().catch(reportEnterAppError);
    refreshPrioritizerStatus().catch(reportEnterAppError);
    refreshAccount().catch(reportEnterAppError);
}

function logout() {
    TokenStore.clearToken();
    editingTaskId = null;
    Views.showAnonymous();
}

document.getElementById("login-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    runOrReportError(async () => {
        await api.login(form.get("username"), form.get("password"));
        enterApp(form.get("username"));
        Views.resetForm(event.target);
    }, { treatAuthErrorAsSessionExpiry: false });
});

document.getElementById("register-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    runOrReportError(async () => {
        await api.register(form.get("username"), form.get("password"), form.get("email"));
        await api.login(form.get("username"), form.get("password"));
        enterApp(form.get("username"));
        Views.resetForm(event.target);
    }, { treatAuthErrorAsSessionExpiry: false });
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
            task_type: Views.readCategoryField(
                document.getElementById("new-task-type-select"),
                document.getElementById("new-task-type-new"),
            ),
            task_subtype: Views.readCategoryField(
                document.getElementById("new-task-subtype-select"),
                document.getElementById("new-task-subtype-new"),
            ),
        });
        Views.resetForm(event.target);
        await refreshTasksAndPlan();
    });
});

document.getElementById("plan-form").addEventListener("submit", (event) => {
    event.preventDefault();
    runOrReportError(refreshTasksAndPlan);
});

document.getElementById("week-plan-form").addEventListener("submit", (event) => {
    event.preventDefault();
    runOrReportError(refreshWeekPlan);
});

document.getElementById("plan-tab-today").addEventListener("click", () => {
    showingWeekPlan = false;
    document.getElementById("plan-tab-today").classList.add("active");
    document.getElementById("plan-tab-week").classList.remove("active");
    document.getElementById("plan-today-view").classList.remove("hidden");
    document.getElementById("plan-week-view").classList.add("hidden");
});

document.getElementById("plan-tab-week").addEventListener("click", () => {
    showingWeekPlan = true;
    document.getElementById("plan-tab-week").classList.add("active");
    document.getElementById("plan-tab-today").classList.remove("active");
    document.getElementById("plan-week-view").classList.remove("hidden");
    document.getElementById("plan-today-view").classList.add("hidden");
    runOrReportError(refreshWeekPlan);
});

document.getElementById("train-button").addEventListener("click", () => {
    runOrReportError(async () => {
        const { trained } = await api.trainPrioritizer();
        Views.showMessage(trained
            ? "Priority model trained on your task history."
            : "Not enough task history yet to train the priority model.");
        await refreshTasksAndPlan();
        await refreshPrioritizerStatus();
    });
});

document.getElementById("reset-model-button").addEventListener("click", () => {
    runOrReportError(async () => {
        await api.resetPrioritizerModel();
        Views.showMessage("Priority model reset; back to formula-only scoring.");
        await refreshTasksAndPlan();
        await refreshPrioritizerStatus();
    });
});

for (const id of ["task-search", "task-type-filter", "task-subtype-filter", "task-sort", "show-done-checkbox"]) {
    document.getElementById(id).addEventListener("input", renderTaskList);
    document.getElementById(id).addEventListener("change", renderTaskList);
}

for (const link of document.querySelectorAll(".nav-link")) {
    link.addEventListener("click", () => Views.showWindow(link.dataset.window));
}

document.getElementById("update-email-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    runOrReportError(async () => {
        await api.updateEmail(form.get("email"));
        Views.showMessage("Email updated.");
        await refreshAccount();
        Views.resetForm(event.target);
    });
});

document.getElementById("change-password-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    runOrReportError(async () => {
        await api.changePassword(form.get("current_password"), form.get("new_password"));
        Views.showMessage("Password changed.");
        Views.resetForm(event.target);
    });
});

// Resume an existing session (token survives page reloads via localStorage).
const existingToken = TokenStore.getToken();
const existingUsername = TokenStore.getUsername();
if (existingToken && existingUsername) {
    enterApp(existingUsername);
} else {
    Views.showAnonymous();
}
