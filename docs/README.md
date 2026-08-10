# URGithub — Specification

A universal Git repository operations manager: scans, synchronizes, commits, pushes, verifies, schedules, quarantines, and reports repository state according to user-configured rules. Runs on your own machine, Python standard library only, nothing destructive ever.

## The absolute rules

- **Rule 0:** No registration → no operations. Only `--setup` / `--setup-all` run first.
- **Rule 1:** No scan → no sync. The sync engine only touches repos scanned in the current run.
- **Rule 2:** Every run produces `report.html` — success, failure, and nothing-changed alike.
- **Rule 3:** Trigger type does not matter — startup, timer, shutdown, file change, manual, and future hooks all enter the same pipeline.

## How the system works — flow diagram

```
                          ┌─────────────────────────────┐
                          │          TRIGGERS           │
                          │  startup · shutdown · every  │
                          │  hours/minutes · at_time ·    │
                          │  file_change · manual · hook  │
                          └──────────────┬──────────────┘
                                         │   Rule 3: every trigger = same entry
                                         ▼
                          ┌─────────────────────────────┐
                          │      runner.run_trigger()   │
                          │                              │
                          │ 0. REGISTRATION GATE (Rule 0)│
                          │    registered? ──no──► exit → "urgithub --setup"
                          │ 1. Acquire global lock       │
                          │    held? ──yes──► journal    │
                          │    "skipped, lock held" → exit│
                          │ 2. Journal run-start {run_id} │
                          │ 3. LIGHT ENV CHECK           │
                          │    git present · gh auth ·   │
                          │    base location exists      │
                          └──────────────┬──────────────┘
                                         ▼
                          ┌─────────────────────────────┐
                          │ 4. DISCOVER                 │
                          │    scan "repos in github\"   │
                          │    + gh repo list reconcile │
                          │    ├─ missing → clone       │
                          │    ├─ renamed → fix folder  │
                          │    │   + registry entry     │
                          │    └─ remote 404 → staged   │
                          │       quarantine (Detail 0) │
                          └──────────────┬──────────────┘
                                         ▼
                          ┌─────────────────────────────┐
                          │ 5. SCAN — 20 checks per repo │
                          │    → ScanResult[]            │
                          │    git state · branch · HEAD │
                          │    remote · reachable · auth │
                          │    dirty · secrets (name +   │
                          │    content) · sizes · ahead/ │
                          │    behind · divergence       │
                          │    Rule 1: no scan → no sync │
                          └──────────────┬──────────────┘
                                         ▼
                          ┌─────────────────────────────┐
                          │ 6. VALIDATE (per repo)       │
                          │    secrets → oversize →      │
                          │    divergence → unreachable  │
                          │    → no permission → no      │
                          │    remote → missing          │
                          │    unsafe → block that repo  │
                          │    only; others continue     │
                          └──────────────┬──────────────┘
                                         ▼
                          ┌─────────────────────────────┐
                          │ 7. SYNC — safe pull          │
                          │    fetch → merge --ff-only   │
                          │ 8. COMMIT / PUSH per policy  │
                          │    auto_commit on/off ·      │
                          │    push_all_branches on/off  │
                          │    → SyncResult[]            │
                          └──────────────┬──────────────┘
                                         ▼
                          ┌─────────────────────────────┐
                          │ 9. JOURNAL   JSONL append    │
                          │    before/after SHAs         │
                          │10. REPORT    report.html     │
                          │    atomic write + archive    │
                          │    Rule 2: EVERY run         │
                          │11. SHOW                      │
                          │    interactive → open browser│
                          │    background  → toast       │
                          │    shutdown    → never       │
                          │12. Journal run-end + outcome │
                          │    + duration                │
                          │13. Release lock              │
                          └─────────────────────────────┘
```

The shutdown trigger is the **only** deviation: discover/scan/pull/commit are skipped and only `git push origin HEAD` runs, with a hard 30 s timeout — it never blocks Windows and never opens the report.

## Report page (one page per run, dark theme)

```
  run events ──► counters ──► 7 stat cards (Pushed · Cloned · Renamed ·
                                              Initialized · Removed · Failed · Events)
      │             │            per-type accent colors
      │             └────► Activity Timeline (icon chips, mono time, repo,
      │                                     detail, ↗ GitHub links)
      ├────────────► Details (per-repo blocks: action badge, before→after SHA,
      │                        changed-file chips, "Open on GitHub ↗")
      ├────────────► All Repos table (LIVE re-scan: branch + CLEAN/DIRTY/UNINIT)
      ├────────────► Security & Size (only when findings exist)
      └────────────► Environment Drift (only when drift exists)
```

## Deployed folder layout

```
<base location>\urgithub\
├── logs\            ← OPERATION HISTORY (application.log + error.log)
├── repos in github\ ← ACTIVE MANAGED REPOSITORIES
├── deleted repos\   ← ARCHIVED / QUARANTINED (never auto-delete)
├── Run\             ← WINDOWS TRIGGERS ONLY (thin launchers + notes)
└── .urgithub\       ← hidden data (config.json, database\, reports\, locks\, …)
```

Full layout, config schema and registry schema: [Detail 2](spec/02-base-location-and-folder-structure.md).

## Details

| File | Content |
|------|---------|
| [Setup Guide (A to Z)](setup.md) | Screen-by-screen setup for Windows / Linux / macOS, every term, all 10 checks, Control Center tabs, troubleshooting |
| [00 — Environment Detection & Registration](spec/00-environment-detection-and-registration.md) | First-launch wizard, four-layer env model, registration gate, light re-check + drift, deleted-repos quarantine workflow |
| [01 — The Universal Trigger Pipeline](spec/01-universal-trigger-pipeline.md) | `run_trigger()`, gate chain + pipeline, all triggers, hard invariants, shutdown exceptions |
| [02 — Base Location & Folder Structure](spec/02-base-location-and-folder-structure.md) | `urgithub\` layout, config.json, registry.json, launchers |
| [03 — The Scan Engine](spec/03-scan-engine.md) | 20-point inspection, `ScanResult`, secrets (name + content), size gates, `validate_result` gate order |
| [04 — The Sync / Commit / Push Engine](spec/04-sync-commit-push-engine.md) | safe pull/commit/push flow, decision table, safety rules, shutdown quick-push |
| [05 — The Report & History System](spec/05-report-and-history-system.md) | report.html (dark theme, cards, timeline, details, live re-scan), atomic write + archive, show rules, JSONL journal, logs |

## Project docs

| File | Content |
|------|---------|
| [Roadmap](ROADMAP.md) | v1.0 → v1.1 (Linux/macOS + notifications) → v1.2 (web dashboard + multi-account) → v2.0 |
| [Release Notes](RELEASE-NOTES.md) | v1.0.0 release notes, requirements, verified deliverables, open limitations |
| [Issue Backlog](ISSUE-BACKLOG.md) | concrete, labeled issues (D/C/P/G) with acceptance criteria |
| [Launch Plan](LAUNCH.md) | install / smoke / real-usage / release phases |
| [Handoff Checklist](URGITHUB-TASKS.md) | pointer docs for each next engineer: where to start, what to read, what to fix |

## Repository map

| Module | Responsibility |
|--------|----------------|
| `urgithub.py` | entry point → `cli.main` |
| `urgithub_core/cli.py` | argument parsing + config/schedule/watch/tray/status/verify/repos/forget/prune commands |
| `urgithub_core/config.py` | defaults, deep-merge, locator, load/save, `register()` |
| `urgithub_core/paths.py` | single-source-of-truth path derivation + `ensure_all()` |
| `urgithub_core/registry.py` | JSON repository registry (load/save/get/set/remove) |
| `urgithub_core/journal.py` | append-only JSONL journal + `open_run`/`close_run` |
| `urgithub_core/lock.py` | PID-based global run lock with stale-steal |
| `urgithub_core/logs.py` | rotating application.log + error.log + console |
| `urgithub_core/gitops.py` | non-interactive `git`/`gh` wrappers with timeouts |
| `urgithub_core/envcheck.py` | the four-layer environment check + snapshot |
| `urgithub_core/wizard.py` | registration wizard (tkinter GUI + console fallback) |
| `urgithub_core/gui.py` | Control Center GUI (`python urgithub.py`): Dashboard / Repositories / Schedule / Settings / Logs / Help, resident timer, file watcher, streaming logs |
| `urgithub_core/discovery.py` | registry discovery, adoption, reconciliation, clone, quarantine, rename |
| `urgithub_core/scan.py` | 20-point inspection + `validate_result` gates |
| `urgithub_core/sync.py` | safe pull/commit/push + shutdown quick-push |
| `urgithub_core/report.py` | report.html (dark theme) + archive + show rules + toasts |
| `urgithub_core/runner.py` | the universal `run_trigger()` pipeline and gates |
| `urgithub_core/scheduler.py` | Task Scheduler tasks (logon/timer/shutdown XML) + launcher deploy + next-run math |
| `urgithub_core/watch.py` | debounced file-change watcher |
| `urgithub_core/tray.py` | legacy tkinter control panel (superseded by `gui.py`; `--tray` now opens the Control Center) |
