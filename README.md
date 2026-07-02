# Priotask
[![CI](https://github.com/DanelArias-Dreyton257/Priotask/actions/workflows/ci.yml/badge.svg)](https://github.com/DanelArias-Dreyton257/Priotask/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/DanelArias-Dreyton257/Priotask)](https://github.com/DanelArias-Dreyton257/Priotask/releases/latest)

Priotask helps you manage and prioritize tasks for effective time management. Register your tasks and the app figures out what to work on today — not just ranked by importance, but converted into a concrete **hours-to-spend** recommendation per task that fits within your available time budget.

## Getting Started
Everything needed to run Priotask locally and try it end to end.

### 1. Set up the environment
The easiest path is the install script (requires conda on `$PATH`):
```
./scripts/install.sh
```
This creates the `priotask` conda environment, downloads the Playwright Chromium browser (used by the JS test suite), and initialises `priotask.db`. Run once after cloning the repo.

Or manually, if you prefer step-by-step control:
```
conda env create -f environment.yml
conda activate priotask
python -m playwright install chromium
```
If the environment already exists and `environment.yml` changed since you created it, use
`./scripts/update.sh` (or `conda env update -f environment.yml --prune` manually). Python is
pinned to `<3.13` (TensorFlow/Keras don't ship wheels past 3.12 yet) — `conda env update`
won't downgrade an existing env's Python version, so if yours predates this pin recreate it:
`conda env remove -n priotask && conda env create -f environment.yml`.

### 2. Run the server (API)
From the repo root:
```
python -m server.src.Server
```
Starts the Flask API on `http://localhost:5000`, backed by a `priotask.db` SQLite file created in the repo root on first run.

### 3. Run the client (web UI)
In a second terminal, from the repo root:
```
python -m client.src.Client
```
Starts the web client on `http://localhost:5500`. It points at `http://localhost:5000` by
default; override with `PRIOTASK_API_BASE_URL` if the server runs elsewhere:
```
PRIOTASK_API_BASE_URL=http://localhost:5000 python -m client.src.Client
```
Steps 2 and 3 can be replaced with one command: `./scripts/run.sh` (see [Scripts](#scripts) below).

### 4. Try it
Open `http://localhost:5500` in a browser:
1. **Register** a user (or **Log in** if you already have one) — registering logs you in automatically.
   If `PRIOTASK_GOOGLE_CLIENT_ID` is configured (see [One-time environment setup](#one-time-environment-setup)), a **Sign in with Google** button appears above the forms — it creates an account automatically on first use (or links Google to an existing account with the same, verified email) and needs no password.
2. Once logged in, a **Tasks / Timetable / Prioritizer / Account** nav bar switches between four windows client-side with no page reload; it always opens on **Timetable**, so you land on "what to work on" rather than the raw task list.
3. The **Timetable** window has three plan tabs: **Today**, **This week**, and **This month**. "This week" shows a weekday-aligned 7-column grid (Mon–Sun headers; today lands in its real weekday column; columns before today show the following week's days as muted full-content cards — a "next week preview"). "This month" shows the same day-cards wrapped into 5–6 rows covering the rest of the current calendar month. Both range views share the "Hours available per day" + **Refresh** form; the "Today" tab has its own separate hours + **Refresh plan** form. Each day card shows planned tasks/hours, a load bar, and any deadlines falling on that day.
4. In the **Tasks** window, add a task with the **New task** form (name, deadline, effort in hours, importance 1–10). It shows up under **Your tasks**, and the **Timetable** window's "Today's plan" shows the recommended hours to spend on it today alongside its priority rank. The **Repeats** dropdown lets it recur daily/weekly/monthly (with an "every N" interval and an optional end date) — completing a recurring task automatically spawns its next occurrence with the deadline advanced by the rule instead of just marking it done.
5. **Done** marks a task complete, **Delete** removes it, **Edit** turns the task into an inline form to change any of its fields (including its recurrence rule), and **Log hours** logs partial progress (subtracting from the task's remaining effort, auto-completing it once none is left); all of these refresh **Today's plan** automatically.
6. Above the task list: **search by name**, **filter by type/sub-type**, **sort** by priority/deadline/type, and a **Show completed** checkbox to reveal done tasks (hidden by default). Overdue tasks are highlighted in red, and recurring tasks show a "🔁 repeats ..." badge. Type/sub-type on the task form (and the edit form) are dropdowns of categories you've already used, with a "+ Add new..." option for a new one.
7. The **Prioritizer** window's **Train priority model** fits the user's neural network on their task history — the button is disabled and shows a spinner while training is in flight. It reports whether there was enough completion history to train on once it finishes. The status line shows whether a trained model is currently active and when it was last trained; **Reset model** (shown once a model is active) discards it and reverts to formula-only scoring. The model also re-fits automatically in the background every 5th task completion — no manual "Train" click needed once you have enough history.
8. The **Account** window shows the logged-in user's username/email, and lets them update their email or change their password (the current password is verified server-side before the change is accepted). An account created via Google sign-in has no local password, so the window shows a "Signed in with Google" badge and hides the change-password form instead (it can still update its email). **Delete account** permanently removes the account and all its data — type "DELETE" in the confirmation box to unlock the button; on success the app logs out automatically.

### 5. Run the tests
```
python -m unittest discover -s server/test -p "*_test.py"
python -m unittest discover -s client/test -p "*_test.py"
```
The first command covers the server (Prioritizer, DailyPlanner, TaskManager, UserManager,
AuthService, API — 170 tests). The second covers the client: `Client_test.py` (smoke test
that the page and static assets are served) and `Js_test.py` (43 Playwright-driven tests for
`views.js` and `api.js`). The Playwright tests spin up the Flask client on a local ephemeral
port and exercise the JS modules in a headless Chromium browser; they require
`python -m playwright install chromium` once (the install scripts do this automatically).

## Scripts
Bash scripts in `scripts/` (run from the repo root, or anywhere — they `cd` to the repo root themselves):
- `./scripts/install.sh` — first-time setup: creates the `priotask` conda environment from
  `environment.yml`, downloads the Playwright Chromium browser, and initialises `priotask.db`.
  Run once after cloning the repo.
- `./scripts/update.sh` — updates the conda environment after a `git pull`: runs `conda env
  update --prune`, re-downloads Playwright Chromium if the pinned version changed, and applies
  any pending DB column migrations by starting the server briefly.
- `./scripts/uninstall.sh [path]` — removes the `priotask` conda environment and (optionally,
  after a prompt) deletes the database. The repo directory itself is not removed. `FORCE=1`
  skips all prompts.
- `./scripts/run.sh` — starts the server and the client together in one terminal; `Ctrl+C` stops both.
- `./scripts/reset_db.sh [path]` — deletes the SQLite file (`priotask.db` by default), wiping
  every user, task and trained model weight; the server recreates an empty one with the current
  schema next time it starts. Prompts for confirmation unless run with `FORCE=1`.
- `./scripts/seed_demo_data.sh [path]` — registers an `admin`/`adminadmin` user (if it doesn't
  exist yet) and seeds it with a varied set of demo tasks (overdue, due today/this week/this
  month, different efforts/importances/types, a couple already completed, one partially logged)
  for manually trying out the UI. No-op if `admin` already has tasks.

## Deployment
`main` is the deployed branch. Every push and pull request runs the CI workflow
(`.github/workflows/ci.yml`): sets up the `priotask` conda environment exactly as
described above, then runs both test suites. Pushing a tag matching `vX.Y.Z` runs
the release workflow (`.github/workflows/release.yml`), which re-runs CI as a
gate and, only if it's green:
- **Client**: builds `client/src/webapp/{templates,static}` into a static
  `dist/` folder via `scripts/build_static_site.py` (relative asset paths, and
  `PRIOTASK_API_BASE_URL` baked in from the `PROD_API_BASE_URL` repo variable)
  and publishes it to **GitHub Pages**.
- **Server**: calls Render's deploy hook (`RENDER_DEPLOY_HOOK_URL` repo secret)
  to redeploy the Flask API — described by `render.yaml` — on **Render.com**.
- Creates a GitHub Release for the tag with auto-generated notes.

See the [GitHub Pages deployment history](https://github.com/DanelArias-Dreyton257/Priotask/deployments/github-pages) for past deploys of the client.

### Releasing a new version
1. Merge `development` into `main` via a pull request.
2. Update [`CHANGELOG.md`](CHANGELOG.md) (move `[Unreleased]` items under a new
   version heading).
3. Tag `main` and push the tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.

### One-time environment setup
These are one-off steps in the GitHub/Render UIs, not run by any workflow:
1. **GitHub Pages** requires GitHub Pro/Team/Enterprise on a private repo (Free
   plan can't publish Pages from a private repo). Repo Settings → Pages →
   Source = "GitHub Actions".
2. Create a Render web service from this repo (branch `main`); it reads
   `render.yaml`. Turn off Render's own auto-deploy-on-push in its dashboard —
   deploys are meant to happen only through the tag-triggered workflow above.
3. Add the Render service's public URL as the repo variable `PROD_API_BASE_URL`
   (Settings → Secrets and variables → Actions → Variables).
4. Add the Render service's Deploy Hook URL as the repo secret
   `RENDER_DEPLOY_HOOK_URL` (Settings → Secrets and variables → Actions →
   Secrets).
5. (Optional) To enable **Sign in with Google**: create an OAuth 2.0 Client
   ID in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   (Application type: "Web application"). Under Authorized JavaScript
   origins, add the GitHub Pages origin (and `http://localhost:5500` for
   local dev) — no redirect URI is needed, since the client only ever
   receives an ID token via Google Identity Services, never a redirect. Add
   the resulting Client ID as the repo variable `GOOGLE_CLIENT_ID` (baked into
   the built static site by `scripts/build_static_site.py`), and set the same
   value as `PRIOTASK_GOOGLE_CLIENT_ID` on the Render service (already present
   in `render.yaml` with `sync: false`, so it's entered once in Render's
   dashboard). Leaving this unset disables the feature everywhere — no button
   on the client, and the server's `/api/auth/google` returns 503.

### Known limitation
Render's free tier has an ephemeral filesystem (no persistent disk without a
paid instance type), so `priotask.db` resets on every redeploy and likely on
every spin-down/spin-up cycle after 15 minutes of inactivity. Fine for
demoing v1.0.0; not a place to keep real data yet — see
[Planned Improvements](#technical--operational).

To keep the deployed instance demoable through those resets, the Render
service runs with `PRIOTASK_SEED_DEMO=true`, which auto-seeds an
`admin` / `adminadmin` account with a varied set of tasks
(`server/src/services/DemoSeeder.py`) on every boot of an empty database.
Every deadline is computed relative to "now" and kept at least a day out, so
the demo always looks like an active, ongoing project rather than showing
stale or overdue tasks.

## Versioning
Priotask follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).
Releases are git tags (`vX.Y.Z`); see [`CHANGELOG.md`](CHANGELOG.md) for what
changed in each one, and [Releases](https://github.com/DanelArias-Dreyton257/Priotask/releases)
for the published artifacts.

## Architecture

### Overview
Priotask is a client-server application written entirely in Python (no Node.js, no build step). The **server** (port 5000) handles persistence, business logic, and the prioritization engine. The **client** (port 5500) is a Flask app that serves a static HTML/CSS/JS shell; all app logic runs client-side in the browser, talking to the server API over HTTP.

The JS layering mirrors the server's DAO/service split:
- **`api.js`** (`ApiClient`) — the only place that calls `fetch`; knows the routes and JSON shapes (`TaskDTO`/`UserDTO`).
- **`session.js`** (`TokenStore`) — persists the bearer token (and username) in `localStorage` so a page refresh doesn't log the user out.
- **`views.js`** (`Views`) — pure DOM rendering from plain data, no fetch calls and no app state.
- **`app.js`** — the controller: wires DOM events to `ApiClient` calls and `Views` updates; the only place that holds app state.

The server-side `RemoteFacade`/`TokenManager` stubs (`server/src/remote/`) are kept as scaffolding for a possible future native client (e.g. Android) — the web client talks to the API directly over HTTP and doesn't use them.

### Prioritization Engine
Two models sit behind a common `PrioritizerModel` interface:
- **`FormulaPrioritizer`** — a closed-form scoring model derived directly from the project's technical spec (`tareas_spec.pdf`): urgency from effort/deadline, scaled by importance.
- **`PrioritizerNetwork`** — a small per-user Keras neural network that learns a *correction* on top of `FormulaPrioritizer`'s score rather than replacing it. An untrained network defaults to correction ≈ 1×, so it's a no-op until the user has enough completion history to train on.

Each user gets their own model, persisted through `ModelStore` (a model-agnostic key-value store keyed by `user_id` + `model_type`). The storage layer is designed to be model-agnostic: an XGBoost booster or any other learner can be added under its own `model_type` without changing how weights are stored.

### Repository Layout
```
Priotask/
├── tareas_spec.pdf          # Technical spec: the formulas behind FormulaPrioritizer
├── environment.yml          # Conda environment (Python, lint/format/type-check tools)
├── render.yaml              # Render Blueprint: how the API is deployed
├── CHANGELOG.md             # Keep a Changelog + SemVer release notes
├── .github/workflows/
│   ├── ci.yml               # Tests on every push/PR; reused by release.yml
│   └── release.yml          # On `vX.Y.Z` tag push: test, deploy, GitHub Release
├── scripts/build_static_site.py  # Builds client/ into dist/ for GitHub Pages
│
├── client/
│   ├── src/
│   │   ├── Client.py        # Entry point: Flask app serving the page (port 5500)
│   │   └── webapp/
│   │       ├── templates/
│   │       │   └── index.html
│   │       └── static/
│   │           ├── css/style.css
│   │           └── js/
│   │               ├── api.js       # ApiClient: fetch wrapper over the server REST API
│   │               ├── session.js   # TokenStore: localStorage-backed bearer token
│   │               ├── views.js     # DOM rendering, no app state or fetch calls
│   │               └── app.js       # Controller: wires api.js + session.js + views.js
│   └── test/
│       ├── Client_test.py   # Smoke test: index page + static JS are served
│       └── Js_test.py       # 42 Playwright-driven JS unit tests
│
└── server/
    ├── wsgi.py              # gunicorn entry point for production (server.wsgi:app)
    ├── requirements-prod.txt  # Lean runtime deps for the Render deploy
    ├── src/
    │   ├── Server.py        # Entry point: runs the Flask app (create_app)
    │   ├── api/
    │   │   ├── app.py             # create_app(): wires DB/managers/services, registers blueprints, CORS
    │   │   ├── auth.py            # require_auth decorator (Bearer token → g.user_id)
    │   │   ├── user_routes.py     # POST /users, /auth/login, /auth/google, /auth/logout,
    │   │   │                      # GET|PUT /users/me, POST /users/me/password, DELETE /users/me
    │   │   ├── task_routes.py     # CRUD for /tasks (+ /complete, /log-hours)
    │   │   ├── plan_routes.py     # GET /plan/today, GET /plan/week
    │   │   └── prioritizer_routes.py  # POST /prioritizer/train, GET /prioritizer/status,
    │   │                              # DELETE /prioritizer/model
    │   ├── data/
    │   │   ├── db/          # DB.py (sqlite3 schema + migrations), DAOs (Task/User/
    │   │   │                # ModelWeights/CompletionSnapshot/Session)
    │   │   ├── domain/      # Domain models: Task, User
    │   │   └── dto/         # Wire-format dataclasses: TaskDTO, UserDTO
    │   ├── remote/          # Client-server link stubs: RemoteFacade, TokenManager
    │   └── services/
    │       ├── TaskManager.py      # Task CRUD, completion snapshots, partial-hours logging,
    │       │                       # recurrence spawning, auto-retrain callback
    │       ├── Recurrence.py       # next_deadline(): day/week/month date arithmetic
    │       ├── UserManager.py      # User CRUD + password hashing (PBKDF2-HMAC-SHA256);
    │       │                       # Google account creation/linking
    │       ├── AuthService.py      # Bearer token issuing/lookup; DB-persisted sessions with
    │       │                       # sliding expiry, multi-device support, Google ID token login
    │       └── Prioritizer/
    │           ├── PrioritizerModel.py     # Common interface: score(task, reference_date)
    │           ├── FormulaPrioritizer.py   # Closed-form model from tareas_spec.pdf
    │           ├── FeatureExtractor.py     # Task → normalized fixed-order feature vector
    │           ├── ModelStore.py           # Per-user weight persistence, model-agnostic
    │           ├── PrioritizerNetwork.py   # Per-user Keras NN: correction on v_i
    │           ├── PrioritizerTrainer.py   # Builds training set from task history, fits/saves
    │           ├── PrioritizerService.py   # Ranking + diagnostics, model-agnostic
    │           └── DailyPlanner.py         # v_i → recommended_hours_today; plan_week
    └── test/
        ├── Prioritizer_test.py
        ├── PrioritizerNetwork_test.py
        ├── DailyPlanner_test.py
        ├── TaskManager_test.py
        ├── UserManager_test.py
        ├── AuthService_test.py
        ├── Api_test.py
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

**6. Diagnostics** (`PrioritizerService.diagnostics`) — summary stats over `{v_i}` meant to
help gauge how loaded a session is, plus two reference thresholds (a quarter and an eighth of the
total score) for deciding how many tasks to take on:
```
v_mean = mean(v_i)
v_std  = stdev(v_i)          # population standard deviation
V      = sum(v_i)
threshold_quarter = V / 4
threshold_eighth  = V / 8
```

`v_i` itself is not shown to the user directly — it is the internal ranking signal that
`DailyPlanner.plan` turns into a "hours to spend on this today" number. Eligible tasks are ranked
by score, then each gets a share of the daily capacity proportional to its score
(`share_i = v_i / sum(v_j)`). Tasks capped by their remaining effort free up unused budget, which
is redistributed among the remaining tasks (water-filling) until the budget is exhausted or every
task is fully covered. Overdue tasks are water-filled first against the full budget; only what's
left over goes to not-yet-due tasks.

## Planned Improvements
Possible next steps, roughly ordered from lowest to highest complexity.

### User Experience
- **Diagnostics panel** — surface the urgency statistics (`v_mean`, `v_std`, `V/4`, `V/8` session-load thresholds) already computed server-side, to help the user calibrate their daily available-hours budget.
- **Formula vs. neural net comparison** — show the formula-only score alongside the learned correction in the Prioritizer window so the model's influence is transparent.
- **Keyboard shortcuts** — hotkeys for common actions (new task, mark done, switch tabs).
- **Configurable week start** — Sunday as an alternative first day of week (ISO Monday is the current default).
- **Dark mode** — a system-preference-respecting color scheme toggle.
- **Accessibility** — ARIA labels, keyboard-navigable task list, screen-reader-friendly status announcements.

### Task Management
- **Task dependencies** — mark a task as blocked until a prerequisite is done; the planner skips blocked tasks automatically.
- **Actual time log** — record individual work sessions (duration + timestamp) rather than only subtracting from the remaining estimate, so the full history is visible.
- **iCal export** — export deadlines as calendar events (`.ics`) for import into Google Calendar, Outlook, etc.
- **CSV / JSON export & import** — data portability and backup without touching the database directly.

### Timetable
- **Deadline notifications** — browser push notifications or email alerts as a deadline approaches.
- **Drag-and-drop reordering** — manually adjust a day's planned task order as a one-off override without editing priorities.

### Prioritization Model
- **Model diagnostics** — show training history and validation loss curve in the Prioritizer window after fitting.
- **Alternative models** — plug in an XGBoost booster or a rule-based model alongside the neural network; `ModelStore` and `PrioritizerModel` already support multiple models per user under different `model_type` keys.
- **Better training signal** — richer negative-example heuristics beyond the current "open tasks at completion time" proxy; for example, weighting by how close a skipped task was to its own deadline.

### Technical / Operational
- **Persistent/managed database** — the deployed Render API currently uses the free tier's ephemeral filesystem (see [Known limitation](#known-limitation)); move `priotask.db` to a persistent disk or a managed Postgres once the app holds real user data.
- **CI lint/type-check gate** — `black`/`isort`/`pylint`/`mypy` are already dev dependencies in `environment.yml` but aren't yet enforced in CI; the codebase needs a formatting pass before that gate can be added without immediately going red.
- **Docker / docker-compose** — container-based setup so conda isn't required; simplifies deployment on a remote server.
- **OpenAPI / Swagger documentation** — auto-generated, browsable API docs for the REST endpoints.
- **Rate limiting** — protect the Flask API from abuse on a public deployment.
- **Progressive Web App (PWA)** — make the client installable on mobile and capable of offline task viewing.
- **Android client** — native Android app using the existing REST API; the `RemoteFacade` stub in `server/src/remote/` already anticipates this.

## The Team
The project is developed by Danel Arias, a student at the University of Deusto, in Bilbao, Spain.
