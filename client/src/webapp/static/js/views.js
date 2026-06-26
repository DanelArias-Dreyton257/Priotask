/*
 * DOM rendering only - takes plain data (the same shapes the server hands
 * back: TaskDTO-like objects, plan entries) and updates the page. No fetch
 * calls and no app state live here, that belongs to the controller (app.js).
 */
const NEW_CATEGORY_VALUE = "__new__";

export const Views = {
    showAuthenticated(username) {
        document.getElementById("auth-section").classList.add("hidden");
        document.getElementById("app-section").classList.remove("hidden");
        document.getElementById("user-bar").classList.remove("hidden");
        document.getElementById("username-display").textContent = username;
        Views.showWindow("timetable-window");
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

    // Populates a "<select> + add new" pair: existing categories plus a
    // "+ Add new..." option that reveals a free-text input. Used for both
    // the new-task form and the edit-in-place form, so a category is one
    // selection away instead of free-typed every time.
    wireCategoryField(selectEl, newInputEl, categories, currentValue) {
        selectEl.innerHTML = "";
        selectEl.appendChild(optionEl("", "(none)"));
        for (const category of categories) {
            selectEl.appendChild(optionEl(category, category));
        }
        selectEl.appendChild(optionEl(NEW_CATEGORY_VALUE, "+ Add new..."));

        const isKnown = currentValue && categories.includes(currentValue);
        selectEl.value = isKnown ? currentValue : (currentValue ? NEW_CATEGORY_VALUE : "");
        newInputEl.value = isKnown ? "" : (currentValue || "");
        newInputEl.classList.toggle("hidden", selectEl.value !== NEW_CATEGORY_VALUE);

        selectEl.onchange = () => {
            newInputEl.classList.toggle("hidden", selectEl.value !== NEW_CATEGORY_VALUE);
            if (selectEl.value === NEW_CATEGORY_VALUE) newInputEl.focus();
        };
    },

    readCategoryField(selectEl, newInputEl) {
        return selectEl.value === NEW_CATEGORY_VALUE ? newInputEl.value.trim() : selectEl.value;
    },

    // Populates a plain filter <select> ("All ..." + the distinct values seen).
    populateFilterSelect(selectEl, values, allLabel) {
        const previous = selectEl.value;
        selectEl.innerHTML = "";
        selectEl.appendChild(optionEl("", allLabel));
        for (const value of values) {
            selectEl.appendChild(optionEl(value, value));
        }
        selectEl.value = values.includes(previous) ? previous : "";
    },

    renderTasks(tasks, { onComplete, onDelete, onLogHours, onEdit, onCancelEdit, onSaveEdit, editingTaskId, categories }) {
        const list = document.getElementById("task-list");
        list.innerHTML = "";

        if (tasks.length === 0) {
            list.innerHTML = "<li class='empty'>No tasks match your filters.</li>";
            return;
        }

        for (const task of tasks) {
            const item = task.task_id === editingTaskId
                ? buildEditItem(task, categories, onSaveEdit, onCancelEdit)
                : buildDisplayItem(task, { onComplete, onDelete, onLogHours, onEdit });
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

    // Phase 13: switches between the top-level windows (Tasks/Timetable/
    // Prioritizer/Account) by toggling `.hidden` on `.app-window` sections,
    // the same pattern used for auth-section/app-section.
    showWindow(windowId) {
        for (const link of document.querySelectorAll(".nav-link")) {
            link.classList.toggle("active", link.dataset.window === windowId);
        }
        for (const win of document.querySelectorAll(".app-window")) {
            win.classList.toggle("hidden", win.id !== windowId);
        }
    },

    renderAccount({ username, email }) {
        document.getElementById("account-username").textContent = username;
        document.getElementById("account-email").textContent = email;
    },

    // Phase 10: surfaces whether the user's PrioritizerNetwork is trained
    // (and when), driven by GET /api/prioritizer/status. The "reset" button
    // only makes sense once there's a model to discard.
    renderPrioritizerStatus({ trained, updated_at }) {
        const status = document.getElementById("prioritizer-status");
        const resetButton = document.getElementById("reset-model-button");
        if (trained) {
            const when = updated_at ? new Date(updated_at).toLocaleString() : "unknown time";
            status.textContent = `Priority model: active (trained ${when})`;
            status.className = "prioritizer-status active";
        } else {
            status.textContent = "Priority model: not enough data yet";
            status.className = "prioritizer-status inactive";
        }
        resetButton.classList.toggle("hidden", !trained);
    },

    // Phase 9: a 7(+)-day grid, one card per day - planned tasks/hours, a
    // load bar (planned hours vs. that day's capacity) and any deadlines
    // falling on that day even if no hours were scheduled for them.
    renderWeekPlan(days) {
        const grid = document.getElementById("week-grid");
        grid.innerHTML = "";

        const today = new Date().toISOString().slice(0, 10);
        for (const day of days) {
            grid.appendChild(buildDayCard(day, day.date === today));
        }
    },
};

function isOverdue(task) {
    if (task.done) return false;
    const today = new Date().toISOString().slice(0, 10);
    return task.deadline.slice(0, 10) <= today;
}

function buildDisplayItem(task, { onComplete, onDelete, onLogHours, onEdit }) {
    const item = document.createElement("li");
    item.className = "task-item" + (task.done ? " done" : "") + (isOverdue(task) ? " overdue" : "");

    const info = document.createElement("div");
    info.className = "task-info";
    info.innerHTML = `
        <strong>${escapeHtml(task.name)}</strong>
        <span>deadline: ${task.deadline.slice(0, 10)}</span>
        <span>effort: ${task.expected_duration_h}h</span>
        <span>importance: ${task.importance}</span>
        ${task.task_type ? `<span class="category">${escapeHtml(task.task_type)}${task.task_subtype ? " / " + escapeHtml(task.task_subtype) : ""}</span>` : ""}
    `;
    item.appendChild(info);

    if (!task.done) {
        const actions = document.createElement("div");
        actions.className = "task-actions";

        const logHoursForm = document.createElement("form");
        logHoursForm.className = "log-hours-form";
        logHoursForm.innerHTML = `
            <input type="number" min="0.5" step="0.5" placeholder="Hours" required>
            <button type="submit">Log</button>
        `;
        logHoursForm.addEventListener("submit", (event) => {
            event.preventDefault();
            const input = logHoursForm.querySelector("input");
            onLogHours(task.task_id, Number(input.value));
            input.value = "";
        });
        actions.appendChild(logHoursForm);

        const buttonsRow = document.createElement("div");
        buttonsRow.className = "task-buttons-row";

        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "btn-edit";
        editButton.textContent = "Edit";
        editButton.addEventListener("click", () => onEdit(task.task_id));
        buttonsRow.appendChild(editButton);

        const completeButton = document.createElement("button");
        completeButton.type = "button";
        completeButton.className = "btn-done";
        completeButton.textContent = "Done";
        completeButton.addEventListener("click", () => onComplete(task.task_id));
        buttonsRow.appendChild(completeButton);

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "btn-delete";
        deleteButton.textContent = "Delete";
        deleteButton.addEventListener("click", () => onDelete(task.task_id));
        buttonsRow.appendChild(deleteButton);

        actions.appendChild(buttonsRow);
        item.appendChild(actions);
    }

    return item;
}

function buildEditItem(task, categories, onSaveEdit, onCancelEdit) {
    const item = document.createElement("li");
    item.className = "task-item editing";

    const form = document.createElement("form");
    form.className = "task-edit-form";
    form.innerHTML = `
        <input type="text" name="name" value="${escapeAttr(task.name)}" required>
        <input type="date" name="deadline" value="${task.deadline.slice(0, 10)}" required>
        <input type="number" name="expected_duration_h" value="${task.expected_duration_h}" min="0" step="0.5" required>
        <input type="number" name="importance" value="${task.importance}" min="1" max="10" required>
        <select name="task_type"></select>
        <input type="text" name="task_type_new" class="hidden" placeholder="New type">
        <select name="task_subtype"></select>
        <input type="text" name="task_subtype_new" class="hidden" placeholder="New sub-type">
        <div class="task-buttons-row">
            <button type="submit">Save</button>
            <button type="button" class="cancel-edit">Cancel</button>
        </div>
    `;

    Views.wireCategoryField(
        form.querySelector('select[name="task_type"]'),
        form.querySelector('input[name="task_type_new"]'),
        categories.types,
        task.task_type,
    );
    Views.wireCategoryField(
        form.querySelector('select[name="task_subtype"]'),
        form.querySelector('input[name="task_subtype_new"]'),
        categories.subtypes,
        task.task_subtype,
    );

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const data = new FormData(form);
        onSaveEdit(task.task_id, {
            name: data.get("name"),
            deadline: data.get("deadline"),
            expected_duration_h: Number(data.get("expected_duration_h")),
            importance: Number(data.get("importance")),
            task_type: Views.readCategoryField(
                form.querySelector('select[name="task_type"]'),
                form.querySelector('input[name="task_type_new"]'),
            ),
            task_subtype: Views.readCategoryField(
                form.querySelector('select[name="task_subtype"]'),
                form.querySelector('input[name="task_subtype_new"]'),
            ),
        });
    });
    form.querySelector(".cancel-edit").addEventListener("click", () => onCancelEdit());

    item.appendChild(form);
    return item;
}

function buildDayCard(day, isToday) {
    const card = document.createElement("div");
    card.className = "day-card" + (isToday ? " is-today" : "");

    const capacity = day.available_hours;
    const ratio = capacity > 0 ? Math.min(1, day.planned_hours_total / capacity) : 0;
    const overloaded = day.planned_hours_total > capacity + 1e-9;

    const weekday = new Date(`${day.date}T00:00:00`).toLocaleDateString(undefined, { weekday: "short" });
    card.innerHTML = `
        <span class="day-card-date">${weekday} ${day.date.slice(5)}</span>
        <div class="day-load-bar"><div class="day-load-bar-fill${overloaded ? " overloaded" : ""}" style="width: ${(ratio * 100).toFixed(0)}%"></div></div>
        <span class="day-load-label">${day.planned_hours_total.toFixed(1)}h / ${capacity.toFixed(1)}h</span>
    `;

    // day.entries includes every eligible task even ones the water-filling
    // budget never reached (0h that day) - showing those just pads out the
    // card with rows that have nothing to say, burying the "Due: ..." line
    // below. Only scheduled tasks are worth a row, and only the top ones.
    // Rounded to one decimal for display below, so the threshold matches -
    // otherwise a sliver of an hour survives the filter but still prints "0.0h".
    const scheduled = day.entries.filter((entry) => entry.recommended_hours_today >= 0.05);
    const MAX_VISIBLE_ENTRIES = 5;
    const visible = scheduled.slice(0, MAX_VISIBLE_ENTRIES);
    const hiddenCount = scheduled.length - visible.length;

    const entries = document.createElement("div");
    if (visible.length === 0) {
        entries.innerHTML = "<span class='day-empty'>Nothing scheduled</span>";
    } else {
        for (const entry of visible) {
            const entryEl = document.createElement("div");
            entryEl.className = "day-entry";
            entryEl.innerHTML = `
                <span>#${entry.rank} ${escapeHtml(entry.task.name)}</span>
                <span>${entry.recommended_hours_today.toFixed(1)}h</span>
            `;
            entries.appendChild(entryEl);
        }
        if (hiddenCount > 0) {
            const moreEl = document.createElement("div");
            moreEl.className = "day-entry-more";
            moreEl.textContent = `+${hiddenCount} more`;
            entries.appendChild(moreEl);
        }
    }
    card.appendChild(entries);

    if (day.deadlines.length > 0) {
        const deadlines = document.createElement("div");
        deadlines.className = "day-deadlines";
        deadlines.textContent = `Due: ${day.deadlines.map((task) => task.name).join(", ")}`;
        card.appendChild(deadlines);
    }

    return card;
}

function optionEl(value, label) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    return option;
}

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}

function escapeAttr(value) {
    return escapeHtml(value).replace(/"/g, "&quot;");
}
