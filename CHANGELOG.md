# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versioning
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]
### Docs
- Link to the [GitHub Pages deployment history](https://github.com/DanelArias-Dreyton257/Priotask/deployments/github-pages) from the README's Deployment section.

## [1.0.1] - 2026-07-01
### Added
- Auto-seeded demo account on the deployed instance: `server/src/services/DemoSeeder.py`
  creates the `admin` / `adminadmin` user with a varied set of tasks whenever the Render
  service boots against an empty database (its free tier has no persistent disk, so this
  covers every redeploy/spin-up reset). All deadlines are computed relative to "now" and
  kept at least a day out, so the demo never shows stale or overdue tasks.

## [1.0.0] - 2026-07-01
First public release, deployed via GitHub Actions: the static client on
GitHub Pages, the Flask API on Render. Covers everything built across
Phases 1-15:

- Client-server task manager with authentication (register/login/logout,
  bearer-token sessions with sliding expiry and multi-device support).
- Full task CRUD: search/filter/sort, type/sub-type categorisation,
  recurring tasks (daily/weekly/monthly with an "every N" interval and
  optional end date), partial-hours logging, and account management
  (email/password update, account deletion).
- Prioritization engine: a closed-form `FormulaPrioritizer` derived from the
  project's technical spec, plus an optional per-user `PrioritizerNetwork`
  (small Keras model) that learns a correction on top of it, auto-retraining
  every 5th completed task.
- Timetable views: Today / This week / This month plans, each turning
  ranked priority scores into a concrete hours-to-spend recommendation per
  task via water-filling against the available daily hours budget.
- 144 server-side tests and 42 client-side (Playwright-driven) tests.

[Unreleased]: https://github.com/DanelArias-Dreyton257/Priotask/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/DanelArias-Dreyton257/Priotask/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/DanelArias-Dreyton257/Priotask/releases/tag/v1.0.0
