# Detail 5 — The Report & History System

## Rule 2

**Every run produces `report.html`** — success, failure, nothing-changed, and even the shutdown quick-push. The report file is always written; only the *showing* differs by trigger.

## Generation (the pipeline tail)

At the end of every `run_trigger()` → `_run_pipeline()` the runner calls:

```python
Reporter(cfg, log, run_id, trigger, interactive=interactive).generate(
    events, sync_results, registry, duration, outcome,
    drift=drift, scan_results=scan_results)
```

- `events` — discovery events + sync events, sorted by `timestamp`.
- `sync_results` — one `SyncResult` per repo.
- `registry` — the live `Registry` (used for per-repo URLs).
- `duration` — wall-clock run time.
- `outcome` — `ok | clean | partial | failed` (Detail 4).
- `drift` — environment drift warnings (Detail 0).
- `scan_results` — security / size findings feed the Security & Size section.

`--setup`, `--status`, `--verify`, `--repos`, `--config`, `--schedule` never generate a report.

## Output location & archiving

- **Latest:** `<base>\urgithub\.urgithub\reports\report.html` — overwritten every run.
- **Archive:** `<base>\urgithub\.urgithub\reports\archive\report-<ISO timestamp>.html`, e.g. `report-2026-08-10T18-45-00.html`.
- **Atomic write:** the body is written to `report.html.tmp` then `replace()`d over `report.html` — a reader never sees a partial file. The archive copy is written from the same body.
- **Pruning:** archived reports older than `report.archive_keep_days` (default 90, `0`/negative disables) are deleted by file mtime at the end of `_write()`.

## Structure (dark GitHub theme)

The report is a single self-contained HTML page (`urgithub_core/report.py`, `CSS` + `generate`). Design tokens: page `#0d1117`, panels `#161b22`, borders `#30363d`, text `#e6edf3`/`#f0f6fc`, muted `#8b949e`/`#484f58`; type accents below.

```
┌──────────────────────────────────────────────────────┐
│ URGithub — Synchronization Report                     │
│ Time: 10 Aug 2026 18:45 · Trigger: manual_sync ·      │
│ Duration: 14.8s · Run: 9f3c2a1b · Outcome: ok         │
├──────────────────────────────────────────────────────┤
│ 7 STAT CARDS (grid)                                   │
│  [2 Pushed] [1 Cloned] [0 Renamed] [3 Initialized]    │
│  [0 Removed] [0 Failed] [6 Events]                    │
│   blue/green/purple/cyan/amber/red/plain numbers      │
├──────────────────────────────────────────────────────┤
│ ACTIVITY TIMELINE                                     │
│  (P) 18:44:58  CampusCart  discovered                 │
│  (C) 18:45:00  Games       cloned              ↗      │
│  (P) 18:45:02  CampusCart  a83f92c..b41c10e (2 files) ↗│
│  (X) 18:45:03  NexaSite    remote unreachable         │
│   icon letter chips · mono time · bold repo · muted   │
│   detail · commit/repo ↗ link when a URL is known     │
├──────────────────────────────────────────────────────┤
│ DETAILS                                              │
│  ┌ CampusCart  [PUSHED]  2 file(s) changed   Open on GitHub ↗
│  │ a83f92c → b41c10e                                │
│  │ A  src/x.py     (green chip)                     │
│  │ M  README.md    (blue chip)                      │
│  └───────────────────────────────────────────────   │
│  ┌ NexaSite  [BLOCKED] — remote unreachable         │
│  └ red-bordered block                                │
├──────────────────────────────────────────────────────┤
│ ALL REPOSITORIES                                     │
│  Repository   Registry  Branch   Working Tree        │
│  CampusCart   active    master   [CLEAN]             │
│  Games        active    main     [CLEAN]             │
│  NexaSite     active    master   [DIRTY]             │
│   (live re-scan: branch + CLEAN/DIRTY/UNINIT)        │
├──────────────────────────────────────────────────────┤
│ SECURITY & SIZE        (only when findings exist)    │
│  Repo  File  Kind  Detail                            │
│  … secret / oversize / large rows                    │
├──────────────────────────────────────────────────────┤
│ FILES & LAST COMMIT  (GitHub file-browser style)     │
│  ┌ Repo  · N file(s)                                 │
│  │ File          Last Commit                         │
│  │ a.txt         2026-08-02T10:14:06Z                │
│  │ new.txt       uncommitted                         │
│  │  newest first · capped at report.files_max        │
├──────────────────────────────────────────────────────┤
│ ENVIRONMENT DRIFT      (only when drift exists)      │
│  • Git version changed: 2.44.0 → 2.45.1             │
└──────────────────────────────────────────────────────┘
```

### 7 stat cards

Counters from `_cards(events)`: `pushed`, `cloned`, `renamed` (renamed + adopted), `initialized` (discovered), `removed`, `failed` (fail + failed), and `events` (total). Each card carries a per-type class that colors its number:

| Card | Color |
|------|-------|
| `card-push` | `#58a6ff` blue |
| `card-clone` | `#3fb950` green |
| `card-rename` | `#d2a8ff` purple |
| `card-init` | `#56d4dd` cyan |
| `card-removed` | `#d29922` amber |
| `card-fail` | `#f85149` red |
| `card-events` | plain `#f0f6fc` |

### Activity timeline

One `.tl-event` row per event, sorted by time. Icon letters and row tint by type: `P` push, `C` clone, `I` init/discovered, `R` rename/adopt, `D` removed, `X` fail, `B` blocked, `-` skipped. Each row: icon chip → mono timestamp → bold repo → muted detail → optional `↗` link.

Timeline events carry a `url` (sync events now get the repo URL from the registry via `runner._sync_events(results, registry)`), so pushed/blocked/failed rows link out to GitHub.

### Details (per-repo blocks)

One `.detail-block` per `SyncResult`:

- Action badge: `PUSHED` / `CLEAN` / `COMMITTED` / `SKIPPED` / `BLOCKED` / `FAILED` (`badge-push/ok/warn/fail`).
- Stats line: `N file(s) changed` plus the reason when present.
- SHA line: `before → after` (mono).
- Changed-file table with status chips: `A` green, `M` blue, `D` red, `R` purple, path in mono.
- `Open on GitHub ↗` link when the registry entry has a `url`.
- Failed repos get a red-tinted border (`detail-fail`).

### All Repositories (live re-scan)

Rendered from the **registry at generation time**, but the branch and working-tree state are freshly re-read from disk per repo (`report._status_for_repo`):

- `git rev-parse --abbrev-ref HEAD` → branch column
- `git status --porcelain` → CLEAN / DIRTY / UNINIT

Columns: Repository (linked) · Registry · Branch · Working Tree (badge). `quarantined`/`deleted` entries and entries without a path are skipped.

### Security & Size

Only rendered when `scan_results` contain findings:

| Row type | Source | Style |
|----------|--------|-------|
| Secret (filename) | `r.secret_findings` kind `name` | `bad` chip |
| Secret (content) | kind `content`, up to 2 patterns + `; …` | `bad` chip |
| Oversized | `r.oversize`, size in MB | `bad` chip |
| Large (warning) | `r.large`, size in MB | `warn` chip |

### Files & Last Commit

A GitHub file-browser-style listing fed by `ScanResult.files` (Detail 3, Check 23 — one `git log` walk per repo, **excluded from the journal**). One `.detail-block` per repo with a `File | Last Commit` table:

- Rows sorted **newest commit first**; untracked files show `uncommitted` and sort last.
- Capped per repo by `report.files_max` (default 500) with a `… and N more (report.files_max)` note.
- Disabled entirely with `report.show_files: false` or `files_max: 0`.
- Section is omitted when no repo produced file data.

### Environment Drift

Only rendered when `drift` warnings exist (git version / identity changes since registration). Bulleted list.

### Empty runs

A run with **zero events still produces a full page** — the timeline shows *"No events this run."* (Rule 2).

## Show rules — `Reporter.show(outcome)`

| Run kind | Behavior |
|----------|----------|
| `shutdown` trigger | **never** opens the report (returns immediately) |
| interactive (`manual_scan`, `manual_sync`) | `webbrowser.open(report_html.as_uri())` |
| background (startup / scheduled / file_change / tray threads) | Windows toast announcing the run outcome (`toast_on_failure` in `notify` must be true) |
| report file missing | warning logged, nothing shown |

The toast is a PowerShell-generated Windows notification (`toast()`, suppressed entirely if `notify.toast_on_failure` is false). All failures that matter also surface in the next run's `report.html`.

## Logs layout (`logs\`)

`setup_logging(paths)` (`urgithub_core/logs.py`) creates:

| File | Level | Rotation |
|------|-------|----------|
| `application.log` | INFO+ | 1 MB, 5 backups |
| `error.log` | ERROR+ | 500 KB, 3 backups |
| console | INFO+ | — |

Log format: `[2026-08-10 18:45:03] [INFO] message`. The console stream is reconfigured to UTF-8/`errors=replace`. `logs\history\` is created for future journal/archive copies. There is no separate `scan.log`/`sync.log` — scan and sync detail goes into `application.log` (journal is the structured record).

## Journal — append-only JSONL

Location: `<base>\urgithub\.urgithub\database\journal.jsonl`. Every line is one event, appended by `Journal.write()`; **never rewritten, never truncated**. Record shape:

```json
{ "ts": "2026-08-10T18:45:00Z", "run_id": "9f3c2a1b", "trigger": "scheduled",
  "phase": "run-start", "outcome": "started" }
```

Optional fields: `repo` (the repository involved), `detail` (dict — scan results, SHA transitions, errors, quarantine target, duration, …).

### Phases written today

| phase | outcomes | example `detail` |
|-------|----------|------------------|
| `run-start` | `started` | — |
| `run-end` | outcome | — |
| `run-skip` | `skipped` | `{"reason": "lock held"}` |
| `env-check` | `env_fail` | `{"git", "github_auth", "base_location"}` |
| `discover` | `started`, `done`, `missing`, `restored`, `adopted` | `{"managed": n}` |
| `clone` | `started`, `failed`, `done` | `{"url"}` / `{"error"}` |
| `scan` | `done`, `failed` | full `ScanResult.to_dict()` |
| `sync` | `skipped`, `committed`, `clean`, `pushed`, `failed`, `blocked` | `{"before","after","files"}` / `{"error"}` / `{"message"}` |
| `quick_push` | `started`, `pushed`, `failed` | `{"before","after"}` / `{"error"}` |
| `quarantine` | `suspected`, `cleared`, `moved`, `kept` | `{"hits"}` / `{"to"}` |
| `rename` | `done` | `{"from","to"}` |
| `drift` | `warning` | `{"items": [...]}` |
| `report` | `failed` | `{"error"}` |
| `engine` | run outcome | `{"duration_s", "scanned", "synced", "blocked", "failed"}` |

### What the journal records

What was scanned, what was detected, what was synchronized, what was pushed, quarantines, errors/conflicts, timestamps, and the affected repository — for every single run, every trigger, forever. Together with the log files it is the complete operation history required for auditing and debugging.
