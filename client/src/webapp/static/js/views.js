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

    // Phase 11: wires a "Repeats" select (none/day/week/month) plus an
    // interval number input and an optional end-date input, showing the
    // latter two only once a recurrence unit is actually chosen. Used by
    // both the new-task form and the edit-in-place form.
    wireRecurrenceField(selectEl, intervalEl, endEl, task = {}) {
        selectEl.value = task.recurrence_unit || "";
        intervalEl.value = task.recurrence_interval || 1;
        endEl.value = task.recurrence_end_date ? task.recurrence_end_date.slice(0, 10) : "";

        const sync = () => {
            const repeats = selectEl.value !== "";
            intervalEl.classList.toggle("hidden", !repeats);
            endEl.classList.toggle("hidden", !repeats);
        };
        sync();
        selectEl.onchange = sync;
    },

    readRecurrenceField(selectEl, intervalEl, endEl) {
        const recurrenceUnit = selectEl.value || null;
        return {
            recurrence_unit: recurrenceUnit,
            recurrence_interval: recurrenceUnit ? Number(intervalEl.value) || 1 : null,
            recurrence_end_date: recurrenceUnit && endEl.value ? endEl.value : null,
        };
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
            item.className = "plan-item" + (isDueToday(entry.task) ? " due-today" : "");
            item.innerHTML = `
                <strong>#${entry.rank} ${escapeHtml(entry.task.name)}</strong>
                <span>${entry.recommended_hours_today.toFixed(1)}h today</span>
                <span class="score">score ${entry.score.toFixed(2)}</span>
                ${isDueToday(entry.task) ? "<span class='due-today-badge'>Due today</span>" : ""}
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

    renderAccount({ username, email, has_password, google_linked }) {
        document.getElementById("account-username").textContent = username;
        document.getElementById("account-email").textContent = email;
        document.getElementById("account-google-badge").classList.toggle("hidden", !google_linked);
        // A Google-only account (no local password set) has nothing for
        // "change password" to verify against - hide the form instead of
        // letting it fail on every submit.
        document.getElementById("change-password-form").classList.toggle("hidden", !has_password);
        document.getElementById("account-no-password-hint").classList.toggle("hidden", !!has_password);
        // v1.2: Drive backup/restore only makes sense for accounts that can
        // re-authenticate with Google to grant Drive access later.
        document.getElementById("google-backup-section").classList.toggle("hidden", !google_linked);
    },

    // v1.2: disables the backup/restore buttons and shows a spinner on
    // whichever one was clicked while the Drive round-trip is in flight.
    setDriveButtonLoading(buttonId, loading, loadingText) {
        const button = document.getElementById(buttonId);
        const other = document.getElementById(
            buttonId === "backup-to-drive-button" ? "restore-from-drive-button" : "backup-to-drive-button",
        );
        other.disabled = loading;
        button.disabled = loading;
        if (loading) {
            button.dataset.originalText = button.textContent;
            button.innerHTML = `<span class='spinner'></span> ${loadingText}`;
        } else {
            button.textContent = button.dataset.originalText || button.textContent;
        }
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

    // Phase 12: shown while GET /api/plan/today is in-flight; replaced by
    // renderPlan() once the response arrives.
    showTodayPlanLoading() {
        const list = document.getElementById("plan-list");
        list.innerHTML = "";
        const item = document.createElement("li");
        item.className = "loading-state";
        item.innerHTML = "<span class='spinner'></span> Loading today's plan...";
        list.appendChild(item);
    },

    // Phase 12: shown while GET /api/plan/week is in-flight; replaced by
    // renderWeekPlan() once the response arrives.
    showWeekPlanLoading() {
        const grid = document.getElementById("week-grid");
        grid.innerHTML = "<div class='loading-state'><span class='spinner'></span> Loading week plan...</div>";
    },

    // Phase 12: disables the Train button and shows a spinner while
    // POST /api/prioritizer/train is in-flight (training can take several
    // seconds on 50 Keras epochs); re-enables it when `loading` is false.
    setTrainButtonLoading(loading) {
        const btn = document.getElementById("train-button");
        btn.disabled = loading;
        if (loading) {
            btn.dataset.originalText = btn.textContent;
            btn.innerHTML = "<span class='spinner'></span> Training...";
        } else {
            btn.innerHTML = btn.dataset.originalText || "Train priority model";
        }
    },

    // Phase 9 / Phase 14: rolling 7-day grid (week mode) or calendar month
    // grid (monthMode).
    //
    // Week mode: Mon–Sun header row, always exactly 7 day cards in one row.
    // The server returns 7 rolling days from today (today→today+6). Days that
    // spill into the next calendar week are placed FIRST (columns Mon→today-1)
    // as muted "next week preview" cards so today always lands in its real
    // weekday column. Example layout for Thursday:
    //   [next Mon muted] [next Tue muted] [next Wed muted] [Thu today] [Fri] [Sat] [Sun]
    //
    // Month mode: Mon–Sun header row, muted synthetic cards for earlier days
    // in the first week (no server data for past days), real day cards for
    // today→end of month, then invisible trailing blanks to complete the last
    // partial row so the grid is always rectangular.
    renderWeekPlan(days, { monthMode = false } = {}) {
        const grid = document.getElementById("week-grid");
        grid.innerHTML = "";

        const todayDate = new Date();
        const todayOffset = (todayDate.getDay() + 6) % 7; // Mon=0, Sun=6
        const today = todayDate.toISOString().slice(0, 10);

        // Mon–Sun headers (both modes)
        for (const label of ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]) {
            const header = document.createElement("div");
            header.className = "week-header-cell";
            header.textContent = label;
            grid.appendChild(header);
        }

        if (monthMode) {
            // Muted prefix cards for Mon–(today-1) in the month's first week.
            for (let i = 0; i < todayOffset; i++) {
                const past = new Date(todayDate);
                past.setDate(past.getDate() - (todayOffset - i));
                grid.appendChild(pastDayCard(past.toISOString().slice(0, 10)));
            }
            for (const day of days) {
                grid.appendChild(buildDayCard(day, day.date === today));
            }
            const totalDataCells = todayOffset + days.length;
            const trailing = (7 - (totalDataCells % 7)) % 7;
            for (let i = 0; i < trailing; i++) {
                grid.appendChild(blankDayCard());
            }
        } else {
            // Sunday of the current calendar week — days beyond it are next week.
            const sundayDate = new Date(todayDate);
            sundayDate.setDate(sundayDate.getDate() + (6 - todayOffset));
            const sundayStr = sundayDate.toISOString().slice(0, 10);

            // Split: this week (today→Sunday) and next week overflow (Mon→Wed_next).
            const thisWeek = days.filter((d) => d.date <= sundayStr);
            const nextWeek = days.filter((d) => d.date > sundayStr);

            // Next-week days go FIRST so they occupy columns 1→todayOffset
            // and today lands in column todayOffset+1 (its real weekday slot).
            for (const day of nextWeek) {
                const card = buildDayCard(day, false);
                card.classList.add("day-card-past");
                grid.appendChild(card);
            }
            for (const day of thisWeek) {
                grid.appendChild(buildDayCard(day, day.date === today));
            }
        }
    },
};

function isOverdue(task) {
    if (task.done) return false;
    const today = new Date().toISOString().slice(0, 10);
    return task.deadline.slice(0, 10) <= today;
}

function isDueToday(task) {
    const today = new Date().toISOString().slice(0, 10);
    return task.deadline.slice(0, 10) === today;
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
        ${task.recurrence_unit ? `<span class="recurrence-badge">\u{1F501} repeats every ${task.recurrence_interval > 1 ? task.recurrence_interval + " " : ""}${task.recurrence_unit}${task.recurrence_interval > 1 ? "s" : ""}</span>` : ""}
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
        <select name="recurrence_unit">
            <option value="">Repeats: none</option>
            <option value="day">Daily</option>
            <option value="week">Weekly</option>
            <option value="month">Monthly</option>
        </select>
        <input type="number" name="recurrence_interval" class="hidden" min="1" step="1" placeholder="Every N">
        <input type="date" name="recurrence_end_date" class="hidden" placeholder="Ends on">
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
    Views.wireRecurrenceField(
        form.querySelector('select[name="recurrence_unit"]'),
        form.querySelector('input[name="recurrence_interval"]'),
        form.querySelector('input[name="recurrence_end_date"]'),
        task,
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
            ...Views.readRecurrenceField(
                form.querySelector('select[name="recurrence_unit"]'),
                form.querySelector('input[name="recurrence_interval"]'),
                form.querySelector('input[name="recurrence_end_date"]'),
            ),
        });
    });
    form.querySelector(".cancel-edit").addEventListener("click", () => onCancelEdit());

    item.appendChild(form);
    return item;
}

// Full-structure muted card for a day with no server data (past days in
// month mode). Uses buildDayCard with synthetic empty data so it looks
// like a real card but greyed out via .day-card-past.
function pastDayCard(isoDate) {
    const card = buildDayCard({
        date: isoDate,
        available_hours: 0,
        planned_hours_total: 0,
        entries: [],
        deadlines: [],
    }, false);
    card.classList.add("day-card-past");
    return card;
}

// Invisible filler used only to complete the last partial row in month mode.
function blankDayCard() {
    const card = document.createElement("div");
    card.className = "day-card day-card-blank";
    return card;
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
