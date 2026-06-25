# Priotask
Priotask helps manage and prioritize tasks for effective time management, allowing users to quickly focus on important tasks and meet deadlines. It streamlines manual workload management.

## The Behaviour
Priotask is supposed to let a user register the tasks they need to do and help them schedule them. The user can also prioritize tasks, and the application will help them focus on the most important tasks. The user can also mark tasks as done, and the application will adapt to the user's preferences. 
## The Code Behind
The project is a client-server application. The server is suppose to store user and task data, while the client is the user interface for the aplication. All the code is written in Python. The server includes a database, which is a SQLite database. The server also includes a 'Prioritizer'. There are two prioritization models behind a common interface (`PrioritizerModel`): `FormulaPrioritizer`, a closed-form scoring model derived directly from the project's technical spec (urgency from effort/deadline, scaled by importance), and `PrioritizerNetwork`, a small neural network meant to eventually replace it. That network is trained to prioritize tasks based on the user's input: each time a user selects to do a task, that one is flagged to be the priority and the prioritizer is adapted to consider those parameters as important. The idea is that each user will have their own prioritizer, which will be trained to prioritize tasks based on their own preferences. (This means that the neural network's weights will be stored in the database, and will be updated each time the user selects a task to do.)
## Repo Structure
```
Priotask/
├── tareas_spec.pdf          # Technical spec: the formulas behind FormulaPrioritizer
├── environment.yml          # Conda environment (Python, lint/format/type-check tools)
│
├── client/                  # User-facing side (not started yet)
│   ├── src/
│   │   └── Client.py        # Entry point (stub)
│   └── test/
│       └── Client_test.py
│
└── server/                  # Storage, business logic, prioritization
    ├── src/
    │   ├── Server.py        # Entry point: runs the Flask app (create_app)
    │   ├── api/              # Phase 4 REST API (Flask)
    │   │   ├── app.py        # create_app(): wires DB/managers/services, registers blueprints
    │   │   ├── auth.py       # require_auth decorator (Bearer token -> g.user_id)
    │   │   ├── user_routes.py    # POST /users, /auth/login, /auth/logout
    │   │   ├── task_routes.py    # CRUD for /tasks (+ /tasks/<id>/complete)
    │   │   └── plan_routes.py    # GET /plan/today (DailyPlanner, Phase 3)
    │   ├── data/
    │   │   ├── db/           # DB access: DB.py (sqlite3, schema for users/tasks), TaskDAO/UserDAO
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
    │           ├── PrioritizerNetwork.py    # Per-user neural network (stub, future)
    │           ├── PrioritizerService.py    # Ranking (rank) + diagnostics, model-agnostic
    │           └── DailyPlanner.py          # v_i -> recommended_hours_today (Phase 3, done)
    └── test/
        ├── Prioritizer_test.py      # Unit tests for FormulaPrioritizer/PrioritizerService
        ├── DailyPlanner_test.py     # Unit tests for DailyPlanner (water-filling budget)
        ├── TaskManager_test.py      # Unit tests for TaskManager (in-memory sqlite)
        ├── UserManager_test.py      # Unit tests for UserManager (in-memory sqlite)
        ├── Api_test.py              # Unit tests for the Flask API (in-memory sqlite)
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
- Wiring up the already-stubbed `RemoteFacade`/`TokenManager` on the client side against this
  API is left to Phase 5.

### Phase 5 — Minimal client
- Just enough UI (or CLI) to register tasks and show today's plan end to end.

### Phase 6 — Personalization (`PrioritizerNetwork`)
- Train the per-user network from completion signal captured in Phase 2.
- Decide the blending strategy with `FormulaPrioritizer` (e.g. the network learns a correction
  on top of `v_i` rather than replacing it outright until there's enough data per user).

### Phase 7 — Hardening
- Tests for the DB/API/client layers, docs, install/update scripts (see TODO list below).

## The TODO List
This section presents all the tasks that need to be done to complete the project.
### Server
- [x] Create the server storage system through a sqlite3 database
- [x] Create the server prioritizer based on the closed-form spec (`FormulaPrioritizer`)
- [ ] Create the server prioritizer as a neural network (`PrioritizerNetwork`, stubbed)
- [x] Create the server user management system
- [x] Create the server task management system
- [x] Turn the priority score into a daily time budget (`DailyPlanner`, Phase 3)
- [x] Create the server API (Flask, `server/src/api/`, Phase 4)
### Client
- [ ] Create the client user interface
- [ ] Create the client task management system
- [ ] Create the client connection to the server
### Tests
- [x] Create the tests for the server (Prioritizer, DailyPlanner, TaskManager, UserManager,
  Api — `server/test/`)
- [ ] Create the tests for the client
### Documentation
- [ ] Create the documentation for the server
- [ ] Create the documentation for the client
### Other
- [ ] Create the installation script
- [ ] Create the uninstallation script
- [ ] Create the update script

 
