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
    │   ├── Server.py        # Entry point (stub, future API)
    │   ├── data/
    │   │   ├── db/           # DB access: DB.py (sqlite3), TaskDAO/UserDAO, TempDB (mock store)
    │   │   ├── domain/       # Domain models: Task, User
    │   │   └── dto/          # Data-transfer objects: TaskDTO, UserDTO
    │   ├── remote/           # Client-server link: RemoteFacade, TokenManager (stubs)
    │   └── services/
    │       ├── TaskManager.py       # Task CRUD (stub)
    │       ├── UserManager.py       # User CRUD (stub)
    │       └── Prioritizer/         # See "The Prioritization Model" below
    │           ├── PrioritizerModel.py      # Common interface: score(task, reference_date)
    │           ├── FormulaPrioritizer.py    # Closed-form model from tareas_spec.pdf (done)
    │           ├── PrioritizerNetwork.py    # Per-user neural network (stub, future)
    │           └── PrioritizerService.py    # Ranking (rank) + diagnostics, model-agnostic
    └── test/
        ├── Prioritizer_test.py      # Unit tests for FormulaPrioritizer/PrioritizerService
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
Phase 3 of the roadmap below still needs to turn into a "hours to spend on this today" number.

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

### Phase 2 — Persistence
- Replace the inconsistent `DB`/`TempDB`/DAO layer with one real sqlite3-backed
  implementation, fixing the current broken imports (`server.data...` vs `server.src.data...`).
- Flesh out `TaskManager`/`UserManager` as the CRUD layer between DAOs and domain objects
  (including domain ↔ DTO mapping).
- Marking a task "done" persists the completion (needed later as training signal for Phase 6).

### Phase 3 — Daily time budget (turns `v_i` into an actual recommendation)
This is where "the score" becomes the feature the user actually sees. Rough approach
(normalization details still open, as noted above):
- Only tasks with remaining effort `h_i > 0` and not done are eligible for today.
- The user has a configurable daily capacity `available_hours_today` (sensible default, e.g. 6h).
- Each eligible task gets a share of that capacity proportional to its score:
  `share_i = v_i / sum(v_j for j in today's candidates)`,
  `recommended_hours_i = min(remaining_effort_i, available_hours_today * share_i)`.
- Tasks capped by `remaining_effort_i` free up unused budget, which gets redistributed among
  the remaining tasks (water-filling) until the budget is exhausted or every task is fully covered.
- Overdue tasks (`d_i <= 0`) are never starved by this redistribution — they're guaranteed a
  minimum slot before the remaining budget is shared out.
- Output per task: rank, `v_i`, `recommended_hours_today`. Diagnostics already built in Phase 1
  (`mean`, `std`, `V/4`, `V/8`) are meant to help calibrate `available_hours_today` itself.

### Phase 4 — Server API
- Endpoints to list/create/update/complete tasks and to fetch "today's plan" (ranked tasks +
  `recommended_hours_today` from Phase 3).
- Wire up the already-stubbed `RemoteFacade`/`TokenManager` on the client side against it.

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
- [ ] Create the server storage system through a sqlite3 database
- [x] Create the server prioritizer based on the closed-form spec (`FormulaPrioritizer`)
- [ ] Create the server prioritizer as a neural network (`PrioritizerNetwork`, stubbed)
- [ ] Create the server user management system
- [ ] Create the server task management system
- [ ] Create the server API
### Client
- [ ] Create the client user interface
- [ ] Create the client task management system
- [ ] Create the client connection to the server
### Tests
- [ ] Create the tests for the server
- [ ] Create the tests for the client
### Documentation
- [ ] Create the documentation for the server
- [ ] Create the documentation for the client
### Other
- [ ] Create the installation script
- [ ] Create the uninstallation script
- [ ] Create the update script

 
