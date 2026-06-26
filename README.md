# Priotask
Priotask helps manage and prioritize tasks for effective time management, allowing users to quickly focus on important tasks and meet deadlines. It streamlines manual workload management.

## Getting Started
Everything needed to run Phases 1-10 and 13 locally and try the app end to end.

### 1. Set up the environment
```
conda env create -f environment.yml
conda activate priotask
```
If the environment already exists and `environment.yml` changed since you created it:
```
conda env update -f environment.yml --prune
```
Phase 6 pins `python<3.13` (TensorFlow/Keras don't ship wheels past 3.12 yet). `conda env
update` won't downgrade an already-created env's Python version — if yours predates this pin,
recreate it instead: `conda env remove -n priotask && conda env create -f environment.yml`.

### 2. Run the server (API)
From the repo root:
```
python -m server.src.Server
```
Starts the Flask API on `http://localhost:5000`, backed by a `priotask.db` SQLite file created
in the repo root on first run.

### 3. Run the client (web UI)
In a second terminal, from the repo root:
```
python -m client.src.Client
```
Starts the web client on `http://localhost:5500`. It points at `http://localhost:5000` by
default; override with `PRIOTASK_API_BASE_URL` if the server runs elsewhere, e.g.:
```
PRIOTASK_API_BASE_URL=http://localhost:5000 python -m client.src.Client
```

Steps 2 and 3 can be replaced with one command/terminal, `./scripts/run.sh` (see
[Scripts](#scripts) below).

### 4. Try it
Open `http://localhost:5500` in a browser:
1. **Register** a user (or **Log in** if you already have one) — registering logs you in
   automatically.
2. Once logged in, a **Tasks** / **Timetable** / **Prioritizer** / **Account** nav bar (Phase 13)
   switches between four windows client-side with no page reload; it always opens on
   **Timetable**, so you land on "what to work on" rather than the raw task list.
3. In the **Tasks** window, add a task with the **New task** form (name, deadline, effort in
   hours, importance 1-10). It shows up under **Your tasks**, and the **Timetable** window's
   "Today's plan" shows the recommended hours to spend on it today (`DailyPlanner`, Phase 3)
   alongside its priority rank.
4. **Done** marks a task complete, **Delete** removes it, **Edit** turns the task into an inline
   form to change any of its fields, and **Log hours** logs partial progress (subtracting from the
   task's remaining effort, auto-completing it once none is left); all of these refresh **Today's
   plan** automatically. The **Refresh plan** button re-fetches the plan with a different hours
   budget.
5. Above the task list: **search by name**, **filter by type/sub-type**, **sort** by priority/
   deadline/type, and a **Show completed** checkbox to reveal done tasks (hidden by default).
   Overdue tasks are highlighted. Type/sub-type on the task form (and the edit form) are dropdowns
   of categories you've already used, with a "+ Add new..." option for a new one.
6. The **Timetable** window has a **Today** / **This week** toggle (Phase 9). "This week" shows a
   7-day grid: each day's planned tasks and hours, a load bar (planned hours vs. that day's
   capacity), and any task deadlines falling on that day even if no hours were scheduled for it
   ("Due: ..."). "Hours available per day" + **Refresh week** re-fetches it with a different daily
   budget.
7. The **Prioritizer** window's **Train priority model** fits the user's `PrioritizerNetwork`
   (Phase 6) on their task history so far — it reports whether there was enough completion history
   to actually train on. The status line next to it (Phase 10) shows whether a trained model is
   currently active and when it was last trained, without itself triggering training; **Reset
   model** (shown once a model is active) discards it and reverts to formula-only scoring.
8. The **Account** window (Phase 13) shows the logged-in user's username/email, and lets them
   update their email or change their password (the current password is verified server-side
   before the change is accepted).

### 5. Run the tests
```
python -m unittest discover -s server/test -p "*_test.py"
python -m unittest discover -s client/test -p "*_test.py"
```
These cover the server and the client's app shell, but there's no JS unit test runner yet (Phase
11). Phase 8's client UI was verified manually with a Playwright-driven browser session against
the running app instead — `playwright` is in `environment.yml` for that purpose; run
`python -m playwright install chromium` once after creating/updating the env if you want to do
the same.

## Scripts
Bash scripts in `scripts/` (run from the repo root, or anywhere — they `cd` to the repo root
themselves):
- `./scripts/run.sh` — starts the server and the client together in one terminal; `Ctrl+C` stops
  both.
- `./scripts/reset_db.sh [path]` — deletes the SQLite file (`priotask.db` by default), wiping
  every user, task and trained `PrioritizerNetwork` weight; the server recreates an empty one with
  the current schema next time it starts. Prompts for confirmation unless run with `FORCE=1`.
- `./scripts/seed_demo_data.sh [path]` — registers an `admin`/`admin` user (if it doesn't exist
  yet) and seeds it with a varied set of demo tasks (overdue, due today/this week/this month,
  different efforts/importances/types, a couple already completed, one partially logged) for
  manually trying out the UI. No-op if `admin` already has tasks.

## The Behaviour
Priotask is supposed to let a user register the tasks they need to do and help them schedule them. The user can also prioritize tasks, and the application will help them focus on the most important tasks. The user can also mark tasks as done, and the application will adapt to the user's preferences. 
## The Code Behind
The project is a client-server application. The server is suppose to store user and task data, while the client is the user interface for the aplication. All the code is written in Python. The server includes a database, which is a SQLite database. The server also includes a 'Prioritizer'. There are two prioritization models behind a common interface (`PrioritizerModel`): `FormulaPrioritizer`, a closed-form scoring model derived directly from the project's technical spec (urgency from effort/deadline, scaled by importance), and `PrioritizerNetwork`, a small per-user neural network (Phase 6) that learns a correction on top of `FormulaPrioritizer`'s score instead of replacing it outright. Each time a user marks a task done, that's training signal — the prioritizer learns to weigh that kind of task higher. Each user gets their own model, persisted through `ModelStore` (a thin, model-agnostic key-value store keyed by `user_id` + `model_type`), so a future model (an XGBoost booster, say) can be added alongside the neural network without changing how weights are stored.
## Repo Structure
```
Priotask/
├── tareas_spec.pdf          # Technical spec: the formulas behind FormulaPrioritizer
├── environment.yml          # Conda environment (Python, lint/format/type-check tools)
│
├── client/                  # Phase 5: minimal web client
│   ├── src/
│   │   ├── Client.py         # Entry point: tiny Flask app serving the page (port 5500)
│   │   └── webapp/
│   │       ├── templates/
│   │       │   └── index.html   # App shell: login/register, task list, today's plan
│   │       └── static/
│   │           ├── css/style.css
│   │           └── js/
│   │               ├── api.js       # ApiClient: fetch wrapper over the server REST API
│   │               ├── session.js   # TokenStore: localStorage-backed bearer token
│   │               ├── views.js     # DOM rendering, no app state or fetch calls
│   │               └── app.js       # Controller: wires api.js + session.js + views.js
│   └── test/
│       └── Client_test.py    # Smoke test: index page + static JS are served
│
└── server/                  # Storage, business logic, prioritization
    ├── src/
    │   ├── Server.py        # Entry point: runs the Flask app (create_app)
    │   ├── api/              # Phase 4 REST API (Flask)
    │   │   ├── app.py        # create_app(): wires DB/managers/services, registers blueprints, CORS
    │   │   ├── auth.py       # require_auth decorator (Bearer token -> g.user_id)
    │   │   ├── user_routes.py        # POST /users, /auth/login, /auth/logout, GET|PUT /users/me,
    │   │   │                         # POST /users/me/password (Phase 13)
    │   │   ├── task_routes.py        # CRUD for /tasks (+ /complete, /log-hours, Phase 7)
    │   │   ├── plan_routes.py        # GET /plan/today (Phase 3), GET /plan/week (Phase 9)
    │   │   └── prioritizer_routes.py # POST /prioritizer/train (PrioritizerTrainer, Phase 6)
    │   ├── data/
    │   │   ├── db/           # DB access: DB.py (sqlite3, schema for users/tasks/model_weights/
    │   │   │                 # completion_snapshots), TaskDAO/UserDAO/ModelWeightsDAO/
    │   │   │                 # CompletionSnapshotDAO (Phase 7)
    │   │   ├── domain/       # Domain models: Task, User (now carry persistence fields)
    │   │   └── dto/          # Wire-format dataclasses: TaskDTO, UserDTO
    │   ├── remote/           # Client-server link: RemoteFacade, TokenManager (stubs)
    │   └── services/
    │       ├── TaskManager.py       # Task CRUD + domain<->DTO mapping, completion snapshots
    │       │                       # and partial-hours logging (Phase 7)
    │       ├── UserManager.py       # User CRUD + password hashing (done)
    │       ├── AuthService.py       # Bearer token issuing/lookup, in-memory (Phase 4, done)
    │       └── Prioritizer/         # See "The Prioritization Model" below
    │           ├── PrioritizerModel.py      # Common interface: score(task, reference_date)
    │           ├── FormulaPrioritizer.py    # Closed-form model from tareas_spec.pdf (done)
    │           ├── FeatureExtractor.py      # Task -> fixed-order feature vector (Phase 6)
    │           ├── ModelStore.py            # Per-user weight persistence, model-agnostic (Phase 6)
    │           ├── PrioritizerNetwork.py    # Per-user Keras NN: correction on v_i (Phase 6)
    │           ├── PrioritizerTrainer.py    # Builds training set from task history, fits/saves (Phase 6)
    │           ├── PrioritizerService.py    # Ranking (rank) + diagnostics, model-agnostic
    │           └── DailyPlanner.py          # v_i -> recommended_hours_today (Phase 3); plan_week
    │                                        # carries remaining effort across N simulated days
    │                                        # (Phase 9)
    └── test/
        ├── Prioritizer_test.py        # Unit tests for FormulaPrioritizer/PrioritizerService
        ├── PrioritizerNetwork_test.py # Unit tests for FeatureExtractor/ModelStore/PrioritizerNetwork/Trainer
        ├── DailyPlanner_test.py       # Unit tests for DailyPlanner (water-filling budget)
        ├── TaskManager_test.py        # Unit tests for TaskManager (in-memory sqlite)
        ├── UserManager_test.py        # Unit tests for UserManager (in-memory sqlite)
        ├── Api_test.py                # Unit tests for the Flask API (in-memory sqlite)
        └── Server_test.py
```

## The Prioritization Model
This is the math behind `FormulaPrioritizer` (`server/src/services/Prioritizer/FormulaPrioritizer.py`),
taken directly from the project's technical spec ([tareas_spec.pdf](tareas_spec.pdf)). Given the
active tasks `T = {1, ..., N}` and a reference date `t` (today, recalculated daily), each task `i`
has three inputs:

| Symbol | Meaning | Field on `Task` |
|---|---|---|
| `f_i` | deadline | `deadline` |
| `n_i` | estimated effort, in hours | `expected_duration_h` |
| `alpha_i` | importance, manually set in `[1, 10]` | `importance` |

**1. Effort, converted to days** (`FormulaPrioritizer.effort_days`) — hours are turned into the
same unit as the date arithmetic below:
```
h_i = n_i / 24
```

**2. Days remaining until the deadline** (`FormulaPrioritizer.days_remaining`) — the `-0.49`
offset makes a task count as overdue (`d_i < 0`) from the start of its due day, not just after
midnight:
```
d_i = f_i - t - 0.49
```

**3. Urgency** (`FormulaPrioritizer.urgency`) — split into two regimes depending on the sign of `d_i`:
```
        h_i / d_i           if d_i > 0   (current: minimum daily effort to still make it)
r_i =
        (2 + |d_i|) * h_i   if d_i <= 0  (overdue: grows linearly with the delay)
```
The jump between regimes is intentional: `r_i -> +inf` as `d_i -> 0+`, while `r_i = 2*h_i`
exactly at `d_i = 0`. Crossing the deadline resets urgency to a finite base value
(`2 * h_i`) instead of leaving it at infinity, and the overdue regime then grows from there
so a late task never gets buried again as time passes.

**4. Priority score** (`FormulaPrioritizer.score`) — importance scales urgency linearly:
```
v_i = alpha_i * r_i
```

**5. Ordering** (`PrioritizerService.rank`) — tasks are sorted by score, descending, with ties
broken lexicographically by type, sub-type and name (ascending):
```
pi = argsort(v, desc; task_type, task_subtype, name, asc)
```

**6. Diagnostics panel** (`PrioritizerService.diagnostics`) — summary stats over `{v_i}` meant to
help gauge how loaded a session is, plus two reference thresholds (a quarter and an eighth of the
total score) for deciding how many tasks to take on:
```
v_mean = mean(v_i)
v_std  = stdev(v_i)          # population standard deviation
V      = sum(v_i)
threshold_quarter = V / 4
threshold_eighth  = V / 8
```

`v_i` itself is not meant to be shown to the user as-is — it's the internal ranking signal that
Phase 3 of the roadmap below turns into a "hours to spend on this today" number
(`DailyPlanner.plan`, see below).

## The Future
The first version of Priotask will be fully Python based, but this does not necessarilly be the case later on. The idea is to support mobile devices with a client application (at least on Android). 
## The Team
The project is developed by Danel Arias, a student at the University of Deusto, in Bilbao, Spain.

## The Roadmap
This section tracks the path from the current state (a scoring formula with no persistence,
no API and no client) to the end goal described below, in phases. Each phase should be
shippable and testable on its own before moving to the next.

### End goal
A user opens the app and sees their active tasks ordered by priority, and for the tasks they
should focus on, a recommended **number of hours to spend on it today**, derived from the
priority score `v_i`. The score itself was never meant to be a user-facing number — it is an
internal ranking signal that still needs to be normalized into a time budget.

### Phase 1 — Domain & scoring (done)
- `Task` domain model with the spec's input variables (`deadline`, `expected_duration_h`,
  `importance`, plus `task_type`/`task_subtype` for tie-breaks).
- `FormulaPrioritizer`: closed-form urgency/score model (`h_i`, `d_i`, `r_i`, `v_i`).
- `PrioritizerService.rank()` (eq. 5 ordering) and `.diagnostics()` (eq. 6: mean/std/sum and
  the `V/4`, `V/8` session-load thresholds).
- `PrioritizerNetwork`: interface-compatible stub, not trained yet.

### Phase 2 — Persistence (done)
- Replaced the inconsistent `DB`/`TempDB`/DAO layer with one real sqlite3-backed
  `DB` (schema for `users`/`tasks`, row access by column name via `sqlite3.Row`), fixing the
  previously broken imports (`server.data...` vs `server.src.data...`).
- `TaskDAO`/`UserDAO` now run real parameterized SQL against that schema, with the `DB` instance
  injectable for tests (`DB(":memory:")`).
- `TaskManager`/`UserManager` are the CRUD layer between DAOs and domain objects, including
  domain ↔ DTO mapping (`TaskDTO`/`UserDTO`, wire-format dataclasses with ISO-8601 dates).
- `Task`/`User` domain models gained persistence fields (`task_id`/`user_id`, `done`,
  `completed_at`; `User` stores a salted `password_hash` via PBKDF2-HMAC-SHA256 instead of
  plaintext).
- Marking a task "done" persists the completion (needed later as training signal for Phase 6).

### Phase 3 — Daily time budget (done)
This is where "the score" becomes the feature the user actually sees, implemented in
`server/src/services/Prioritizer/DailyPlanner.py` (`DailyPlanner.plan`):
- Only tasks with remaining effort `expected_duration_h > 0` and not done are eligible for today.
- The caller passes a daily capacity `available_hours_today` (default `6.0h`,
  `DEFAULT_AVAILABLE_HOURS_TODAY`).
- Eligible tasks are ranked via `PrioritizerService.rank` (score `v_i`, eq. 5 tie-breaks), then
  each gets a share of the capacity proportional to its score:
  `share_i = v_i / sum(v_j for j in today's candidates)`,
  `recommended_hours_i = min(remaining_effort_i, available_hours_today * share_i)`.
- Tasks capped by `remaining_effort_i` free up unused budget, which gets redistributed among
  the remaining tasks (water-filling, `DailyPlanner._water_fill`) until the budget is exhausted
  or every task is fully covered.
- Overdue tasks (deadline at/before the reference date) are never starved by this
  redistribution: they are water-filled first against the *full* budget; only what's left over
  afterwards is water-filled among the current (not-yet-due) tasks.
- Output per task (`PlanEntry`): `rank`, `task`, `score` (`v_i`), `recommended_hours_today`.
  Diagnostics already built in Phase 1 (`mean`, `std`, `V/4`, `V/8`) are meant to help calibrate
  `available_hours_today` itself.

### Phase 4 — Server API (done)
A Flask app (`server/src/api/app.py`, `create_app`) exposing the persistence and prioritization
layers from Phases 1-3 over HTTP, run via `python -m server.src.Server`:
- `POST /api/users` — register a user.
- `POST /api/auth/login` / `POST /api/auth/logout` — issue/revoke a bearer token
  (`AuthService`, in-memory token store, no expiry yet — restarting the server logs everyone out).
- `GET /api/tasks`, `POST /api/tasks`, `GET|PUT|DELETE /api/tasks/<id>`,
  `POST /api/tasks/<id>/complete`, `POST /api/tasks/<id>/log-hours` — task CRUD plus completion
  and partial-progress logging (Phase 7), scoped to the authenticated user
  (`Authorization: Bearer <token>`); tasks belonging to another user 404.
- `GET /api/plan/today?hours=<n>` — today's plan: ranked tasks + `recommended_hours_today`
  from `DailyPlanner` (Phase 3), `hours` overrides the default daily budget.
- `POST /api/prioritizer/train` — (Phase 6) fits the authenticated user's `PrioritizerNetwork`
  on their task history and persists it; `{"trained": false}` if there isn't enough signal yet
  (see Phase 6 below).
- `_enable_cors` (`app.py`) adds permissive CORS headers and handles `OPTIONS` preflight
  requests, needed once Phase 5's client started calling this API from a different origin/port.

### Phase 5 — Minimal client (done)
A browser-based client (`client/`) talking to the Phase 4 API end to end: register/log in,
list tasks ordered by priority, add/complete/delete tasks, and see today's recommended hours
per task. Plain HTML/CSS/JS (no framework, no build step), served by a second, much smaller
Flask app (`client/src/Client.py`, `python -m client.src.Client`, port `5500` by default) that
just renders the page shell and points it at the API (`PRIOTASK_API_BASE_URL` env var, default
`http://localhost:5000`); all app logic runs client-side in the browser.

The JS layering mirrors the server's DAO/DTO/Manager split:
- `api.js` (`ApiClient`) — the only place that calls `fetch`; knows the routes and JSON shapes
  (`TaskDTO`/`UserDTO`), analogous to the server-side `RemoteFacade` stub.
- `session.js` (`TokenStore`) — persists the bearer token (and username) in `localStorage` so a
  page refresh doesn't log the user out; analogous to `TokenManager`.
- `views.js` (`Views`) — pure DOM rendering from plain data, no fetch calls and no app state.
- `app.js` — the controller: wires DOM events to `ApiClient` calls and `Views` updates, the only
  place that holds app state (which view is showing, the current task/plan data).

The server-side `RemoteFacade`/`TokenManager` stubs (`server/src/remote/`) are left as-is for a
possible future native client (e.g. the Android client mentioned under "The Future") — the web
client below talks to the API directly over HTTP and doesn't need them.

### Phase 6 — Personalization (`PrioritizerNetwork`) (in progress)
A per-user model that learns a *correction* on top of `FormulaPrioritizer`'s score `v_i` rather
than replacing it, built so the storage/training plumbing isn't tied to any one ML library:

- **`FeatureExtractor`** (`server/src/services/Prioritizer/FeatureExtractor.py`) turns a `Task`
  into a fixed-order numeric vector — `effort_days`, `days_remaining`, `importance`, `urgency`,
  `formula_score` — reusing `FormulaPrioritizer`'s own building blocks so the formula and the
  learned correction never drift apart. Any model that learns (the network today, others later)
  trains and predicts on this same vector.
- **`ModelStore`** (`server/src/services/Prioritizer/ModelStore.py`) persists opaque per-user
  weights keyed by `user_id` + an arbitrary `model_type` string, backed by a new `model_weights`
  table (`server/src/data/db/DB.py`, `ModelWeightsDAO`). It never looks inside the bytes — each
  model owns its own serialization — so a future model (an XGBoost booster, say) can reuse the
  same store under its own `model_type` without touching this class.
- **`PrioritizerNetwork`** (`server/src/services/Prioritizer/PrioritizerNetwork.py`) is a small
  Keras model — 3 layers total: the 5-feature input, one hidden `Dense(8, relu)`, and a
  `Dense(1, sigmoid)` output — registered under `model_type = "keras_nn_v1"`. Its output is read
  as a `[0, 1]` correction and blended as `v_i * (2 * correction)`: an untrained (or never-stored)
  network defaults to `correction ≈ 0.5`, i.e. multiplier `≈ 1`, so plugging it in is a no-op
  until a user actually has a trained model. With no stored weights for a user (or no `user_id`
  at all, e.g. an unpersisted `Task`), `score()` falls straight back to `FormulaPrioritizer`.
- **`PrioritizerTrainer`** (`server/src/services/Prioritizer/PrioritizerTrainer.py`) builds the
  training set from a user's task history: done tasks are positive examples (scored as of their
  `completed_at`), still-open tasks are negative examples (scored as of now). This is a coarse
  proxy for "the task the user picked" — Phase 2's schema doesn't snapshot which tasks were on
  the table at each completion — good enough to start training on, revisit if it's not enough.
  Training only runs once there's a minimum number of examples with both labels present
  (`PrioritizerTrainer.MIN_EXAMPLES`); otherwise `train()` is a no-op.
- **`POST /api/prioritizer/train`** (`prioritizer_routes.py`) triggers training for the
  authenticated user; `create_app` wires the same `PrioritizerNetwork`/`ModelStore` into
  `DailyPlanner` via `PrioritizerService`, so a freshly trained model is picked up by
  `/api/plan/today` immediately, with no redeploy.

**Known gaps**, split by where they get addressed:

User-visible, closed by Phase 10 (Personalization visibility) below:
- No client UI to trigger training or show whether a user's network is active — the only signal
  was the one-shot `{"trained": bool}` response from `POST /api/prioritizer/train`. Closed by the
  status indicator + `GET /api/prioritizer/status`.
- No way to read a user's model status without retraining, even though `ModelWeightsDAO.upsert`
  already stored an `updated_at` timestamp per save (`server/src/data/db/ModelWeightsDAO.py`).
  Closed by `GET /api/prioritizer/status`, a side-effect-free read of that same row.
- No way to discard a trained model and fall back to formula-only scoring — `ModelStore.delete`
  existed and was unit-tested, but no route called it. Closed by `DELETE /api/prioritizer/model`
  (`PrioritizerNetwork.forget`, which also evicts the in-memory `_cache` entry so the very next
  score for that user re-checks the store instead of serving the just-deleted model).
- The negative-example heuristic (Phase 7's completion snapshots, plus all currently-open tasks)
  is a reasonable first cut but still unvalidated against real usage — showing the formula score
  and the learned-correction score side by side remains optional future work, not done here.

Internal/robustness, tracked under Phase 11 (Hardening & polish):
- `FeatureExtractor`'s five features (`effort_days`, `days_remaining`, `importance`, `urgency`,
  `formula_score`) are fed into the network unnormalized despite spanning very different numeric
  ranges — `urgency`/`formula_score` can grow large (even unbounded near a deadline, see the
  `r_i -> +inf` note above), and an unscaled large-magnitude feature can dominate gradient updates
  on the tiny per-user datasets this trains on.
- `score()` calls `model.predict()` once per task, so ranking a user's full list means one Keras
  call per task instead of one batched call across all of them.
- `fit()` always runs a fixed 50 epochs with no train/validation split, early stopping, or
  regularization — on a small single-user dataset this risks memorizing noise with no way to
  detect it.
- Persisted weights are tied to today's `FEATURE_ORDER` and architecture (`HIDDEN_UNITS`); any
  future change to `FeatureExtractor` breaks loading existing users' stored weights with a
  shape-mismatch exception instead of a graceful fallback to formula-only scoring.
- `PrioritizerNetwork._cache` is an in-memory, per-process dict — fine for today's single-process
  dev server, but would serve stale models across workers in a multi-process deployment, with no
  invalidation path.
- No lock/guard around training: two concurrent `POST /api/prioritizer/train` calls for the same
  user race on `ModelStore.save`, last write wins.
- Weight (de)serialization uses `pickle` (`PrioritizerNetwork._serialize`/`_deserialize`) — safe
  today since it only ever reads back what this same code wrote, but worth flagging now so it
  isn't missed if model weights are ever exposed via an import/export feature later
  (`pickle.loads` on untrusted bytes is a remote-code-execution risk).

### Phase 7 — Task lifecycle completeness (done)
Closes the two functional gaps left over from Phase 6, both about how task completion data is
captured, plus the client UI that was deferred when Phase 6 shipped:
- **Partial completion**: `POST /api/tasks/<id>/log-hours` (`TaskManager.log_hours`) logs `n`
  hours worked, subtracting from `expected_duration_h` instead of only supporting an all-or-nothing
  `complete`. Only the running total is kept (no per-entry log) — `expected_duration_h` itself is
  the record. If logging hours brings the remaining effort to zero, the task is marked done
  automatically, through the same path (and the same completion snapshot, see below) as
  `complete`.
- **Real per-completion snapshots**: `TaskManager.mark_done` now records a `CompletionSnapshot`
  (new `completion_snapshots` table, `CompletionSnapshotDAO`) — the completed task's ID, the
  completion timestamp, and the IDs of every other task that was still open *at that exact
  moment*. `PrioritizerTrainer._build_examples` (Phase 6) uses these snapshots as its primary
  signal: the completed task is a positive example, the snapshot's open tasks are negatives, both
  scored as of that completion's timestamp — replacing the old proxy that only ever compared
  *all-time-done* tasks against *currently-open* tasks. Tasks still open right now are still added
  as a supplementary negative signal scored as of now (valid even before any completion history
  exists, e.g. a brand-new account), so training doesn't regress for accounts with little history.
- **Client UI for both**: an inline "Log hours" form next to "Done"/"Delete" on each task
  (`views.js`/`app.js`/`api.js:logHours`), and a "Train priority model" button that calls
  `POST /api/prioritizer/train` and reports whether training actually ran
  (`api.js:trainPrioritizer`); a persistent trained/untrained status indicator is Phase 10.

### Phase 8 — Task organization & editing (client usability) (done)
The task list was flat, ordered only by creation order, and uneditable from the UI even though
the server already supported more — this phase is pure client work against existing APIs
(`client/src/webapp/static/js/views.js`, `app.js`, `index.html`):
- **Edit-in-place**: an "Edit" button (alongside Log/Done/Delete) swaps a task's display row for
  an inline form (`Views`'s `buildEditItem`) prefilled with its current fields; Save calls the
  already-working `PUT /api/tasks/<id>` (`task_routes.py:update_task`, `api.js:updateTask`), Cancel
  reverts without a server round-trip. `app.js` tracks which task (if any) is being edited
  (`editingTaskId`) and re-renders the list around it.
- **Sorting**: a "Sort" dropdown over the fetched task list — by priority score (read from the
  same `/api/plan/today` response already fetched for "Today's plan", via a `task_id -> score`
  map; tasks outside today's plan, e.g. done ones, sort last), by deadline, or by
  `task_type`/`task_subtype`/name (mirroring `PrioritizerService.rank`'s own tie-break order).
- **Managed type/subtype categories**: `task_type`/`task_subtype` are no longer free-text inputs.
  Both the "New task" form and the edit-in-place form use a `<select>` populated from the distinct
  categories already used across the user's tasks (computed client-side in `app.js`), plus a
  "+ Add new..." option that reveals a text input — so picking an existing category is one
  selection, and typos no longer silently fragment grouping/filtering (`Views.wireCategoryField`/
  `readCategoryField`).
- **Filtering**: a "Show completed" checkbox (off by default, hiding done tasks), `task_type`/
  `task_subtype` filter dropdowns (populated the same way, via `Views.populateFilterSelect`), and
  a name search box — all combine (AND) over the client-side task list, no new endpoints needed.
- **Visual urgency cues**: overdue tasks (deadline at/before today, not done) get a distinct
  pastel-red style (`.task-item.overdue`), surfacing in the UI the same overdue/not-yet-due split
  `FormulaPrioritizer.urgency` already makes internally (`d_i <= 0`), instead of that distinction
  only showing up as a score difference.

Verified end to end with a Playwright-driven browser run (register/login, create overdue and
upcoming tasks across categories, exercise every filter/sort/edit control, confirm the rendered
DOM and styling) on top of the existing `client/test/Client_test.py` smoke coverage.

### Phase 9 — Time visualization (weekly/calendar view) (done)
The main missing user-facing capability: previously the user only ever saw a single day's plan,
never a forward-looking view of their week.
- **`DailyPlanner.plan_week`** (`server/src/services/Prioritizer/DailyPlanner.py`) generalizes
  `plan()` across `days` simulated days: each day calls the existing `plan()` (eligibility +
  ranking + water-filling, unchanged), then subtracts that day's `recommended_hours_today` from
  each task's remaining effort (on a per-call clone, never mutating the caller's tasks) before
  ranking the next day — a task fully covered on one day stops competing for budget on the next.
  Each day's `PlanEntry`s are snapshotted (cloned) before that mutation, so an earlier day never
  retroactively shows a task as `done` once a later day finishes covering it.
- **`GET /api/plan/week?days=7&hours=6`** (`plan_routes.py`) returns one entry per day: ranked
  tasks + hours (as `/plan/today` does), `planned_hours_total` and `available_hours` (the load
  indicator), the day's `diagnostics` (`PrioritizerService.diagnostics()`'s mean/std/`V`/`V/4`/`V/8`,
  computed server-side since Phase 1 but never surfaced via the API until now), and `deadlines` —
  tasks due that day even if they got no hours that day (e.g. already fully scheduled earlier in
  the week). `days` is bounded to `[1, 31]`.
- Client: a **Today** / **This week** toggle in the `plan-section` ("Timetable"), wired in `app.js`
  (`showingWeekPlan`) — "This week" renders a 7-day grid (`Views.renderWeekPlan`, `views.js`), one
  card per day with a load bar (planned hours vs. that day's capacity, redder past 100%), the
  day's planned tasks/hours, and a "Due: ..." line for that day's deadlines. A second "Hours
  available per day" + "Refresh week" form (`#week-plan-form`) re-fetches it with a different
  daily budget, independent of the Today tab's own hours input.

Verified end to end with a Playwright-driven browser run (login, create a multi-day task, switch
to the week tab, confirm hours carry forward across days and the deadline marker appears on the
due day) on top of new server-side unit/API test coverage (`DailyPlanner_test.py`, `Api_test.py`).

### Phase 10 — Personalization visibility (done)
Surfaces the Phase 6 `PrioritizerNetwork` model, which already trained and scored server-side but
was invisible to the user — closes the user-visible gaps listed under Phase 6 above:
- `GET /api/prioritizer/status` (`prioritizer_routes.py`) — whether the authenticated user has a
  trained model and, if so, its `updated_at`, read straight from `ModelWeightsDAO.get` (the
  timestamp `ModelWeightsDAO.upsert` already stored, just never read back) without itself
  triggering training.
- `DELETE /api/prioritizer/model` (`prioritizer_routes.py`) discards a user's trained model and
  reverts them to formula-only scoring, via the new `PrioritizerNetwork.forget` (wraps the
  already-implemented `ModelStore.delete` and also evicts the matching `_cache` entry, so the
  model is gone from the very next score call, not just the next process restart).
- Client: a status indicator next to "Train priority model" ("active (trained <when>)" / "not
  enough data yet"), driven by `GET /api/prioritizer/status` (`api.js:getPrioritizerStatus`,
  `views.js:renderPrioritizerStatus`) — refreshed on login and after every train/reset action, not
  just shown as a one-shot toast — plus a "Reset model" button (only shown once a model is
  active) calling the new delete endpoint (`api.js:resetPrioritizerModel`).
- Manual retrain is the existing "Train priority model" button; an automatic trigger after N
  completions is left as future work (Phase 6's negative-example heuristic is still unvalidated
  against real usage, so auto-retraining on a heuristic that isn't trusted yet would just compound
  the uncertainty).
- Not done: showing the formula score and the learned-correction score side by side was listed as
  optional and is left for a future phase.

### Phase 11 — Hardening & polish
- JS unit tests for `views.js`/`app.js`/`api.js` — today only `client/test/Client_test.py` exists
  (a smoke test that the page and static assets are served), so the JS modules are untested beyond
  manual browser checks.
- Documentation for the server and client (module-level docs beyond this README).
- Installation, uninstallation and update scripts, reusing/extending the existing
  `scripts/run.sh` and `scripts/reset_db.sh` rather than duplicating them.
- `PrioritizerNetwork`/`PrioritizerTrainer` robustness (see the "Internal/robustness" gaps listed
  under Phase 6 above for the reasoning behind each):
  - Normalize `FeatureExtractor`'s feature vector before it reaches the network instead of feeding
    in raw, differently-scaled values.
  - Batch `model.predict()` across a user's tasks for one ranking pass instead of one call per task.
  - Add a train/validation split (or at least early stopping) to `fit()` instead of always running
    a fixed 50 epochs on whatever data is available.
  - Version the stored weights against `FEATURE_ORDER`/`HIDDEN_UNITS` so a future architecture
    change falls back to formula-only scoring for existing users instead of crashing on load.
  - Guard against concurrent `POST /api/prioritizer/train` calls for the same user racing on
    `ModelStore.save`.
  - Invalidate/refresh `PrioritizerNetwork._cache` correctly if the server ever runs as more than
    one process/worker.

### Phase 12 — Recurring (cyclic) tasks
Today every task is a one-off: a chore that comes back every week has to be re-created by hand
each time. This phase lets a task declare a recurrence rule so it regenerates itself instead:
- Server: a recurrence rule on the task (e.g. `recurrence_interval` + `recurrence_unit` -
  daily/weekly/monthly - plus an optional end date), stored either as new columns on `tasks` or a
  small `task_recurrences` table keyed by a template task. When a recurring task is completed
  (`TaskManager.mark_done`/`log_hours`), instead of just marking it done, the next occurrence is
  created automatically with the deadline advanced by the rule's interval and the same effort/
  importance/type/subtype - so the board always has exactly one open instance of a recurring task,
  never zero and never a pile-up of duplicates.
- Completion history for a recurring task's past occurrences is preserved (each instance still has
  its own `task_id`/`completed_at`), so `PrioritizerTrainer`'s completion snapshots (Phase 7) keep
  working unchanged - a recurring task is just a task that happens to spawn its successor.
- Client: a "Repeats" control on the task form (none / daily / weekly / monthly, optional end
  date), and a small recurring-task indicator in the task list so it's visually distinct from a
  one-off task.

### Phase 13 — Top-level navigation & account settings (done)
Phases 8-10 each added their own chunk of UI (editing/filtering, a week view, training status) on
top of what used to be a single screen (`app-section`'s `.board` of `tasks-section` +
`plan-section`) - that stopped scaling once all of them existed at once. This phase turned the
client into a small set of focused windows behind a top-level nav, instead of one ever-growing
page:
- A top nav bar (`#app-nav` in `index.html`, wired in `app.js`) listing one entry per window,
  switched client-side with no page reload via `Views.showWindow` - the same `.hidden`-toggling
  pattern `Views.showAuthenticated`/`showAnonymous` already used for `auth-section`/`app-section`,
  just generalized to more than two panes (`.app-window` sections, one nav `.nav-link` per
  `data-window` id):
  - **Tasks** (`#tasks-window`) - the task list, editing, sorting/filtering/categories (Phase 8).
  - **Timetable** (`#timetable-window`) - today's plan and the week view (Phase 9); the
    today/week toggle from that phase lives here, nested inside `plan-section`.
  - **Prioritizer** (`#prioritizer-window`) - training status and retrain controls (Phase 10),
    pulled out of `plan-section` into its own window with a short explanation of what the model
    does, instead of being squeezed in below the week-plan form.
  - **Account** (`#account-window`) - new, see below.
  Logging in (`Views.showAuthenticated`) always resets to the same window - **Timetable**, not
  Tasks - so a returning user lands straight on "what should I work on today/this week" instead of
  the raw task list, and never on whatever tab they happened to leave open in a previous session.
- **Account window**: view username/email, change password, and update email (log out already
  existed in the header). This needed server support that didn't exist yet - `UserDAO`/
  `UserManager` previously only had `add_user`/`get_user_by_username`/`delete_user`, no read-by-id
  or update path - so this phase added `UserDAO.get_user_by_id`/`update_email`/`update_password`,
  `UserManager.get_user_by_id`/`update_email`/`change_password` (the latter re-verifies the
  current password via the existing PBKDF2 hash before accepting a new one), and three routes:
  `GET /api/users/me`, `PUT /api/users/me` (body: `{"email": ...}`), and
  `POST /api/users/me/password` (body: `{"current_password": ..., "new_password": ...}`, 400 if
  the current password doesn't match) - all behind `require_auth` and scoped to `g.user_id`.
  Client-side: `api.js:getMe/updateEmail/changePassword`, `views.js:renderAccount`, and two forms
  in `app.js` (`#update-email-form`, `#change-password-form`) that refresh the displayed
  username/email on login and after every successful update.

Verified end to end with a Playwright-driven browser run (register, switch through all four nav
tabs, update email, change password, confirm the wrong-current-password case is rejected, log out
and back in with the new password) on top of new server unit/API test coverage
(`UserManager_test.py`, `Api_test.py`).

## The TODO List
This section presents all the tasks that need to be done to complete the project, grouped by the
roadmap phase that owns them (see above for full descriptions).
### Phase 7 — Task lifecycle completeness (done)
- [x] Let a task be marked as partially done by logging `n` hours worked, subtracting that from
  `expected_duration_h` instead of only supporting an all-or-nothing `complete`
- [x] Capture a real per-completion snapshot of "tasks on the table" instead of
  `PrioritizerTrainer`'s current proxy (done tasks vs. currently-open tasks)
- [x] Client UI to trigger `/api/prioritizer/train`
- [x] Client UI for logging partial hours worked ("Log hours" action)
### Phase 8 — Task organization & editing (done)
- [x] Edit-in-place for a task in the client (`PUT /api/tasks/<id>` already exists server-side)
- [x] Sort tasks by score, deadline, or type/subtype in the client
- [x] Replace the free-text type/subtype inputs with dropdowns populated from the user's
  existing categories
- [x] Filter the task list by type and/or subtype (via the dropdowns above)
- [x] Filter/search tasks (hide done, search by name)
- [x] Visual styling for overdue tasks in the task list
### Phase 9 — Time visualization (done)
- [x] `GET /api/plan/week` multi-day plan endpoint (server)
- [x] Week-view grid in the client (7-day plan + hours per day)
- [x] Per-day load indicator using `PrioritizerService.diagnostics()` thresholds
- [x] Deadline markers on the week view
### Phase 10 — Personalization visibility (done)
- [x] `GET /api/prioritizer/status` (trained?/`updated_at`) — server, reads `ModelWeightsDAO`
  without retraining
- [x] `DELETE /api/prioritizer/model` (or similar) to reset a user's model to formula-only scoring
  — server, wires up the already-implemented `ModelStore.delete`
- [x] Client UI showing whether a user has a trained `PrioritizerNetwork` ("active" /
  "not enough data yet"), driven by the status endpoint above
- [x] Client "reset model" control calling the delete endpoint above
- [x] Manual retrain action in the client (existing "Train priority model" button); auto-triggered
  retrain after N completions left as future work, see Phase 10 notes above
- [ ] Optional: show formula score vs. learned-correction score side by side
### Phase 11 — Hardening & polish
- [ ] JS unit tests for `views.js`/`app.js`/`api.js`
- [ ] Create the documentation for the server
- [ ] Create the documentation for the client
- [ ] Create the installation script
- [ ] Create the uninstallation script
- [ ] Create the update script
- [ ] Normalize `FeatureExtractor`'s feature vector before it reaches `PrioritizerNetwork`
- [ ] Batch `PrioritizerNetwork.score`'s `model.predict()` calls across a user's task list
- [ ] Add a train/validation split or early stopping to `PrioritizerNetwork.fit`
- [ ] Version persisted model weights against `FEATURE_ORDER`/`HIDDEN_UNITS` so architecture
  changes fall back to formula-only scoring instead of crashing on load
- [ ] Guard against concurrent `POST /api/prioritizer/train` calls for the same user
- [ ] Make `PrioritizerNetwork._cache` safe for a multi-process/worker deployment
### Phase 12 — Recurring (cyclic) tasks
- [ ] Recurrence rule on a task (interval/unit, optional end date) - server schema + storage
- [ ] Completing a recurring task spawns its next occurrence instead of just marking it done
- [ ] "Repeats" control on the client task form, plus a recurring-task indicator in the task list
### Phase 13 — Top-level navigation & account settings (done)
- [x] Top nav bar switching between Tasks/Timetable/Prioritizer/Account windows client-side
- [x] Move the task list + editing/filtering (Phase 8) behind the Tasks window
- [x] Move today's plan + week view (Phase 9) behind the Timetable window
- [x] Move training status/retrain controls (Phase 10) behind the Prioritizer window
- [x] `GET /api/users/me`, `PUT /api/users/me` (update email) and `POST /api/users/me/password`
  (change password)
- [x] Account window: view username/email, change password, update email
### Done (Phases 1-6)
- [x] Create the server storage system through a sqlite3 database
- [x] Create the server prioritizer based on the closed-form spec (`FormulaPrioritizer`)
- [x] Create the server prioritizer as a neural network (`PrioritizerNetwork`, Phase 6: 3-layer
  Keras model, blended as a correction on top of `FormulaPrioritizer`)
- [x] Create the server user management system
- [x] Create the server task management system
- [x] Turn the priority score into a daily time budget (`DailyPlanner`, Phase 3)
- [x] Create the server API (Flask, `server/src/api/`, Phase 4)
- [x] Persist per-user model weights in a model-agnostic way (`ModelStore`/`model_weights` table,
  Phase 6) so a future model (e.g. XGBoost) can be added without changing the storage layer
- [x] Create the client user interface (`client/src/webapp/`, Phase 5)
- [x] Create the client task management system (`api.js` + `app.js`: create/list/complete/delete)
- [x] Create the client connection to the server (`api.js`, CORS-enabled, Phase 5)
- [x] Create the tests for the server (Prioritizer, DailyPlanner, TaskManager, UserManager,
  Api — `server/test/`)
- [x] Create the tests for the client (`client/test/Client_test.py`: page + static assets served;
  no JS unit tests yet, see Phase 11)
- [x] Create a script that launches the server and the client together (`scripts/run.sh`, one
  command instead of two separate `python -m server.src.Server` /
  `python -m client.src.Client` terminals)
- [x] Create a script that flushes the database (`scripts/reset_db.sh`)

 
