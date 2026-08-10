# URGithub — `Run\` Folder Notes

> This folder holds **Windows trigger launchers only**. The `.bat` files are thin entry points — all logic lives in the Python application. At `--setup` / `--schedule install`, the full launcher set is deployed (with absolute `python.exe` + `urgithub.py` paths) to `<base location>\urgithub\Run\`.

## 1. What this folder is

- Thin launchers that call the Python engine with a trigger flag.
- **No Git logic** (no `git add`, `git commit`, `git push`, scanning, or report generation) lives in `.bat` files.

```
BAT
  ↓
Python application (urgithub_core)
  ↓
Discovery → Scanner → Validation gates → Sync Engine → Report Engine
```

## 2. Files

| File | Python call | Purpose |
|------|-------------|---------|
| `start.bat` | `python urgithub.py --startup` | Windows startup trigger — full pipeline (DISCOVER → SCAN → VALIDATE → SYNC → REPORT) |
| `scan.bat` | `python urgithub.py --scan` | Manual **SCAN ONLY** (never syncs by itself) |
| `sync.bat` | `python urgithub.py --sync` | Manual full operation — always runs DISCOVER → SCAN → VALIDATE → SYNC → REPORT first |
| `shutdown.bat` | `python urgithub.py --shutdown` | Before-shutdown trigger — **quick push only, timeout-bounded, never blocks shutdown** |
| `schedule.bat` | `python urgithub.py --run scheduled` | Scheduled-trigger entry — used by Windows Task Scheduler |
| `manual.bat` | `python urgithub.py --tray` | Main GUI launcher — control panel with Scan/Sync/Report/Schedule buttons |

When you run `--schedule install`, `scheduler.deploy_launchers()` rewrites all six launchers into `<base location>\urgithub\Run\` with absolute paths to the current `python.exe` and `urgithub.py`.

## 3. The non-negotiable pipeline

```
ANY TRIGGER → DISCOVER → SCAN → VALIDATE → SYNC → REPORT.HTML → SHOW REPORT
```

- `--scan` = SCAN only (plus discovery).
- `--sync` = a *sync request* — it must never directly synchronize; it always scans and validates first (Rule 1).
- `--shutdown` = quick push with a hard 30 s timeout; if GitHub is unreachable it must **not** block Windows from shutting down; it never launches `report.html` (the file is still written — Rule 2).
- `.bat` files must **never** bypass this pipeline. They only pass a trigger flag.

## 4. Folder core rules

```
repos in github   = ACTIVE MANAGED REPOSITORIES
deleted repos     = ARCHIVED / QUARANTINED REPOSITORIES (never auto-delete)
logs              = OPERATION HISTORY
Run               = WINDOWS TRIGGERS ONLY
```

## 5. `repos in github` — belongs here only if

1. It is a valid Git repository.
2. It has a `.git` directory.
3. It has a configured remote, where required.
4. The application recognizes it as a managed repository (registry entry).
5. It has not been intentionally archived/deleted.

The scanner must **not** assume every ordinary folder is a repository.

## 6. Deletion safety (never accidental)

Deletion is **NOT** suspected when: GitHub unreachable, internet disconnected, auth fails, GitHub API error, remote cannot be contacted, local repo errors, or repo temporarily unavailable — those are connection/operation failures.

Staged flow (see `docs\spec\00-…` for the full detail): FIRST DETECTION → mark `deletion suspected` (`pending`, `deletion_hits=1`) → verify again on later runs → still confirmed after `confirm_scans` scans / `confirm_days` days and remote 404 → **ask the user** (confirmation required on interactive runs) → archive/move to `deleted repos\`.

- **Case A — GitHub deleted, local exists:** do NOT delete the local repository. User chooses to keep the local copy or move it to `deleted repos\`.
- **Case B — Local deleted, remote alive:** status `missing`; the repo is re-cloned per `clone_missing_repos` (default on).
- **First-run clone-all:** a fresh registration starts with an empty registry, so every GitHub repo not yet registered is seeded and cloned on the first run (private + forks, unless `skip_forks`).
- `deleted repos\` is an **archive**, not a trash bin. Permanent deletion is never done automatically.

## 7. Four-layer environment model

`Git installed` ≠ `Git configured` ≠ `GitHub authenticated` ≠ `repo authorized`. All four are checked separately (registration wizard + scan permission check per repo).

## 8. The absolute rules

- Rule 0: No registration → no operations.
- Rule 1: No scan → no sync.
- Rule 2: Every run produces `report.html`.
- Rule 3: Trigger type does not matter — everything enters the same pipeline.

## 9. Active working files — no other files

These are the **only** files in the working set. Do not create or edit any other files without going through the phase plan.

Working set:

```
Run\NOTES.md                      ← this file
Run\start.bat                     ← --startup
Run\scan.bat                      ← --scan
Run\sync.bat                      ← --sync
Run\shutdown.bat                  ← --shutdown
Run\schedule.bat                  ← --run scheduled
Run\manual.bat                    ← --tray
README.md                         ← project overview
docs\README.md                    ← spec index + flow diagram
docs\REPORT-REDESIGN-NOTE.md      ← report.html dark-theme redesign note
docs\spec\00-environment-detection-and-registration.md
docs\spec\01-universal-trigger-pipeline.md
docs\spec\02-base-location-and-folder-structure.md
docs\spec\03-scan-engine.md
docs\spec\04-sync-commit-push-engine.md
docs\spec\05-report-and-history-system.md
urgithub.py                       ← entry point (thin: cli.main)
urgithub_core\*                   ← the engine package
```

## 10. Phase delivery status

- **Phase 1 — Registration:** `--setup` GUI wizard (tkinter + console fallback) with the four-layer environment check and one-click fix buttons; `--setup-all` (register → schedule install with UAC-elevated shutdown task → first run → status); full folder structure + `config.json` + locator; Rule 0 gate.
- **Phase 2 — Discovery & Registry:** `discovery.py` — scans `repos in github\`, reconciles with `gh repo list`, clones missing repos, staged quarantine workflow (`pending` → confirm → `deleted repos\`), rename handling + local-rename adoption; registry statuses `active|missing|LOCAL_MISSING|pending|quarantined|deleted`.
- **Phase 3 — Scan Engine:** `scan.py` — 20-point inspection → `ScanResult`; secrets by filename patterns **and** content regexes (binary-skip, 1 MB cap, `allow_files`), file-size gate (100 MB block / 50 MB warn), divergence/auth gates; `validate_result` gate order.
- **Phase 4 — Sync/Commit/Push:** `sync.py` — safe pull (`fetch` + `merge --ff-only`), commit per `auto_commit`, push per policy, shutdown quick-push; never force/reset/clean/rebase.
- **Phase 5 — Report & History:** `report.py` — dark-theme `report.html` (atomic write + archive), 7 stat cards, icon-chip timeline with ↗ links, per-repo detail blocks with A/M/D/R file chips, live All-Repos re-scan (branch + CLEAN/DIRTY/UNINIT), Security & Size + Environment Drift sections; show rules (interactive→browser, background→toast, shutdown→never).
- **Phase 6 — Triggers / Tray / Installer:** `scheduler.py` (Task Scheduler: logon startup, repeating every-hours/minutes or at-time, EventID-1074 shutdown task via XML; launcher deployment; `compute_next_runs`), `watch.py` (debounced file-change watcher ignoring `.git`), `tray.py` (control panel + resident timer + watcher thread), CLI `--config`, `--run`, `--schedule install|uninstall|status`, `--watch`, `--tray`, `--forget`, `--prune`. Every trigger enters the one universal pipeline — Rule 3.
