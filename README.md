# Priotask
Priotask helps manage and prioritize tasks for effective time management, allowing users to quickly focus on important tasks and meet deadlines. It streamlines manual workload management.

## Getting Started
Everything needed to run Phases 1-6 locally and try the app end to end.

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
2. Add a task with the **New task** form (name, deadline, effort in hours, importance 1-10).
3. The task shows up under **Your tasks**, and **Today's plan** shows the recommended hours to
   spend on it today (`DailyPlanner`, Phase 3) alongside its priority rank.
4. **Done** marks a task complete, **Delete** removes it; both refresh **Today's plan**
   automatically. The **Refresh plan** button re-fetches the plan with a different hours budget.

### 5. Run the tests
```
python -m unittest discover -s server/test -p "*_test.py"
python -m unittest discover -s client/test -p "*_test.py"
```

## Scripts
Bash scripts in `scripts/` (run from the repo root, or anywhere — they `cd` to the repo root
themselves):
- `./scripts/run.sh` — starts the server and the client together in one terminal; `Ctrl+C` stops
  both.
- `./scripts/reset_db.sh [path]` — deletes the SQLite file (`priotask.db` by default), wiping
  every user, task and trained `PrioritizerNetwork` weight; the server recreates an empty one with
  the current schema next time it starts. Prompts for confirmation unless run with `FORCE=1`.

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
    │   │   ├── user_routes.py        # POST /users, /auth/login, /auth/logout
    │   │   ├── task_routes.py        # CRUD for /tasks (+ /tasks/<id>/complete)
    │   │   ├── plan_routes.py        # GET /plan/today (DailyPlanner, Phase 3)
    │   │   └── prioritizer_routes.py # POST /prioritizer/train (PrioritizerTrainer, Phase 6)
    │   ├── data/
    │   │   ├── db/           # DB access: DB.py (sqlite3, schema for users/tasks/model_weights),
    │   │   │                 # TaskDAO/UserDAO/ModelWeightsDAO
    │   │   ├── domain/       # Domain models: Task, User (now carry persistence fields)
    │   │   └── dto/          # Wire-format dataclasses: TaskDTO, UserDTO
    │   ├── remote/           # Client-server link: RemoteFacade, TokenManager (stubs)
    │   └── services/
    │       ├── TaskManager.py       # Task CRUD + domain<->DTO mapping (done)
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
    │           └── DailyPlanner.py          # v_i -> recommended_hours_today (Phase 3, done)
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
  `POST /api/tasks/<id>/complete` — task CRUD, scoped to the authenticated user
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

Not yet done: there's no client UI to trigger training or show whether a user's network is
active, and the negative-example heuristic above is a first cut, not validated against real
usage yet.

### Phase 7 — Hardening
- Tests for the DB/API/client layers, docs, install/update scripts (see TODO list below).

## The TODO List
This section presents all the tasks that need to be done to complete the project.
### Server
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
- [ ] Let a task be marked as partially done by logging `n` hours worked, subtracting that from
  `expected_duration_h` instead of only supporting an all-or-nothing `complete`
- [ ] Capture a real per-completion snapshot of "tasks on the table" instead of
  `PrioritizerTrainer`'s current proxy (done tasks vs. currently-open tasks)
- [ ] Client UI to trigger `/api/prioritizer/train` and show whether a user has a trained network
### Client
- [x] Create the client user interface (`client/src/webapp/`, Phase 5)
- [x] Create the client task management system (`api.js` + `app.js`: create/list/complete/delete)
- [x] Create the client connection to the server (`api.js`, CORS-enabled, Phase 5)
### Tests
- [x] Create the tests for the server (Prioritizer, DailyPlanner, TaskManager, UserManager,
  Api — `server/test/`)
- [x] Create the tests for the client (`client/test/Client_test.py`: page + static assets served;
  no JS unit tests yet — the JS modules are untested beyond manual browser checks)
### Documentation
- [ ] Create the documentation for the server
- [ ] Create the documentation for the client
### Other
- [ ] Create the installation script
- [ ] Create the uninstallation script
- [ ] Create the update script
- [x] Create a script that launches the server and the client together (`scripts/run.sh`, one
  command instead of two separate `python -m server.src.Server` /
  `python -m client.src.Client` terminals)
- [x] Create a script that flushes the database (`scripts/reset_db.sh`)

 
