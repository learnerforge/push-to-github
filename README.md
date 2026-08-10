# URGithub

**Universal Git repository operations manager.** Scan, discover, synchronize, commit, push, verify, schedule, quarantine, and report on your Git repositories — automatically and safely, on your own machine.

No cloud. No daemon installs. Python standard library only. Every trigger enters exactly one pipeline, and nothing destructive ever happens.

---

## Why URGithub

- **One pipeline, every trigger.** Startup, shutdown, a timer, a file change, a manual click, a launcher `.bat` — all call the same engine (`runner.run_trigger`). There is never a second implementation of synchronization.
- **Safety first.** Never `reset`, never `--force`, never `rebase`, never `clean`. Pulls are fast-forward only. Secrets stop a repo cold. Divergence blocks a repo instead of clobbering it. GitHub-repo *authorization* is checked separately from *authentication*.
- **Fully automatic.** Windows Task Scheduler keeps everything running after you close the terminal: logon startup, a repeating timer, and an EventID-1074 shutdown task that quick-pushes before Windows goes down.
- **Transparent.** Every action is journaled (append-only JSONL), and every run writes a human-readable `report.html` (dark GitHub theme).

---

## The four rules

| Rule | Meaning |
|------|---------|
| **Rule 0** | No registration → no operations. Only `--setup` runs first. |
| **Rule 1** | No scan → no sync. The sync engine only touches repos scanned in the current run. |
| **Rule 2** | Every run produces `report.html` — success, failure, and nothing-changed alike. |
| **Rule 3** | Trigger type does not matter. `startup`, `every 3h`, `manual`, and future triggers all call the same entry point. |

---

## Requirements

- **Windows 10/11**
- **Git** — on `PATH` (`git --version`), with a configured identity:
  ```
  git config --global user.name  "Your Name"
  git config --global user.email "you@example.com"
  ```
- **GitHub CLI (`gh`)** — installed and authenticated with the `repo` (push) scope:
  ```
  gh auth login
  gh auth status      # must show "Token scopes: ... 'repo' ..."
  ```
- **Python 3.10+** — any recent Python works; nothing beyond the standard library is needed. [Download Python](https://www.python.org/downloads/)

## Installing the tools (from scratch)

```powershell
# 1. Git
winget install Git.Git            # or https://git-scm.com/download/win

# 2. GitHub CLI
winget install GitHub.cli         # or https://cli.github.com/

# 3. Restart the terminal so PATH updates, then verify both are visible
git --version                     # → git version 2.xx
gh --version                      # → gh version 2.xx

# 4. Authenticate gh (browser / device flow). Pick "GitHub.com" → "HTTPS"
gh auth login
gh auth status                    # ✓ Logged in ... Token scopes: ... 'repo' ...
```

**Official download pages** (when you prefer manual installs):

| Software | Windows | Linux | macOS |
|---|---|---|---|
| Python 3.10+ | [python.org/downloads/windows](https://www.python.org/downloads/windows/) | [python.org/downloads/source](https://www.python.org/downloads/source/) | [python.org/downloads/macos](https://www.python.org/downloads/macos/) |
| Git | [git-scm.com/download/win](https://git-scm.com/download/win) | [git-scm.com/download/linux](https://git-scm.com/download/linux) | [git-scm.com/download/mac](https://git-scm.com/download/mac) |
| GitHub CLI | [cli.github.com](https://cli.github.com/) | [cli.github.com](https://cli.github.com/) | [cli.github.com](https://cli.github.com/) |
| GitHub account | [github.com/signup](https://github.com/signup) | [github.com/signup](https://github.com/signup) | [github.com/signup](https://github.com/signup) |

The registration wizard (`--setup`) re-checks all of this for you — Git · version · username · email · gh CLI · authentication · `repo` push scope · live GitHub connection · base writable — with one-click fix buttons.

---

## Quick start

```powershell
cd E:\Project-1

# One command: register (GUI wizard) → install scheduled tasks
# (startup, timer, shutdown-with-UAC) → first run → schedule status
python urgithub.py --setup-all

# Or step by step:
python urgithub.py --setup       # register one time
python urgithub.py --sync        # run the full pipeline once
python urgithub.py --schedule install   # install scheduled tasks
python urgithub.py --tray        # open the control panel
```

That's it. After setup you can also use the launchers in `<base>\urgithub\Run\` or the project's `Run\` folder.

---

## Registration (`--setup`)

Registration is a one-time wizard that creates the base structure and writes `~/.urgithub/base.txt` (the locator that points at your `config.json`).

1. Run `python urgithub.py --setup`.
2. Pick a **base location** (a parent folder; URGithub creates `urgithub\` inside it).
3. The environment check verifies ten items: Python, Git installed, Git version, Git username, Git email, GitHub CLI, GitHub authentication, `repo` push scope, live GitHub connection, base writable.
4. Use the built-in fix buttons (**Install Git**, **Configure identity**, **Install GitHub CLI**, **Authenticate GitHub**) if anything is red.
5. **Register** stays disabled until every check passes. Optionally tick "install scheduled tasks". Click it — done.

Falls back to a console prompt automatically if the GUI cannot open.

> Where does the data live? In your base location, e.g. `D:\Data\urgithub\` — not in this project folder. The project is just the engine. The only thing written outside the base location is `~\.urgithub\base.txt`.

---

## Usage

```
python urgithub.py [options]
```

| Command | What it does |
|---------|--------------|
| `--setup` | One-time registration wizard |
| `--setup-all` | Full setup in one command: register (if needed) + install schedule (UAC for shutdown task) + first run + status |
| `--startup` | Startup trigger — full pipeline (discover → scan → validate → sync → report) |
| `--scan` | Manual scan only — never syncs |
| `--sync` | Manual full sync — always discovers, scans and validates first |
| `--shutdown` | Quick push of existing local commits (hard 30 s timeout, never opens the report) |
| `--status` | Registration + managed-repo status |
| `--verify` | Verify every registry entry (folder + git + origin) |
| `--repos` | List managed repositories |
| `--report` | Regenerate `report.html` from a fresh scan |
| `--run <trigger>` | Run any trigger by name (see **Triggers**) |
| `--config [KEY [VALUE]]` | Get/set a config value by dotted key |
| `--schedule [install\|uninstall\|status]` | Manage Windows Task Scheduler tasks |
| `--watch` | Run the file-change watcher (blocks) |
| `--tray` | Open the control panel GUI |
| `--forget NAME` | Remove one repository from the registry (folder left on disk) |
| `--prune` | Remove all stale registry entries (missing / quarantined / deleted) |
| `--yes` | Skip confirmation prompts for `--forget` / `--prune` |
| `--version` | Show version |

### Config quick reference

```powershell
python urgithub.py --config                          # dump full config.json
python urgithub.py --config triggers.every_hours     # read one key
python urgithub.py --config triggers.every_hours 6   # set one key (int/bool/float auto-coerced)
```

After changing trigger settings, re-apply: `python urgithub.py --schedule install`.

---

## Triggers

| Trigger | When it fires | Notes |
|---------|---------------|-------|
| `startup` | Windows logon (scheduled task) or `--startup` | Full pipeline |
| `shutdown` | User-initiated shutdown/restart/logoff (EventID 1074) | Quick push only, never blocks Windows |
| `scheduled` | `every_hours` / `every_minutes` repeating task | Epoch-aligned interval boundaries |
| `at_time` | A specific time daily | Rolls to tomorrow if the time has passed |
| `file_change` | Debounced change under `repos in github\` | Ignores `.git` internals |
| `manual` | `--run manual`, launchers, or control panel | — |
| `manual_scan` / `manual_sync` | Control panel buttons | Interactive → opens the report in the browser |
| `event_hook` | *(roadmap)* webhook/email | Same entry point |

**Rule 3:** every trigger above runs `runner.run_trigger()`, which executes the identical gate chain and pipeline.

---

## How a run works

```
registration gate → lock (stale after 15 s) → journal run-start → light env check
→ DISCOVER   (scan repos in github\, reconcile with `gh repo list`,
              clone missing, adopt renames, staged quarantine)
→ SCAN       (20-point inspection per repo → ScanResult)
→ VALIDATE   (secrets gate · size gate · divergence gate · auth gate —
              stop that repo, continue others)
→ SYNC       (fetch → fast-forward-only pull)
→ COMMIT/PUSH (per auto_commit / push policy)
→ JOURNAL    (every action with before/after SHAs)
→ REPORT     (report.html, atomic write + archive — Rule 2)
→ SHOW       (interactive → browser · background → toast · shutdown → never)
→ journal run-end → release lock
```

### Shutdown is the only deviation

Quick push of already-made commits only — **no discover, no scan, no pull, no commit**. Hard 30 s timeout per repo. Never opens `report.html` (the file is still written). If it fails, the next run's report surfaces it. The local repo is never touched destructively.

### When a repo is not pushed

| Situation | Result |
|-----------|--------|
| Secret files found (`block_on_secrets`) | `blocked: secrets` — by filename pattern **and** file content |
| File larger than `limits.max_file_mb` | `blocked: oversize files` |
| Local ahead **and** remote ahead | `blocked: divergence` |
| Remote unreachable | `blocked: remote unreachable` |
| No push permission on the repo | `blocked: no push permission` |
| No `origin` remote | `blocked: no remote configured` |
| Folder missing / not a git repo / quarantined | `blocked: missing` |
| Dirty tree + `auto_commit` off | `skipped` (never silently commits) |
| Fetch / `git add` / commit / push fails | `failed` (journaled with the reason) |

Every case is journaled and visible in `report.html`. Repos that pass are still pushed — one bad repo never blocks the others.

---

## Configuration

`config.json` lives at `<base>\urgithub\.urgithub\config.json`. Defaults (any omitted key deep-merges over these):

```jsonc
{
  "github_owner": "auto",            // "auto" = your gh login
  "clone_missing_repos": true,       // clone missing repos; also clones ALL repos on the first run
  "skip_forks": false,               // true = exclude forks from the first-run clone-all

  "commit_policy": {
    "auto_commit": false,            // commit working-tree changes automatically?
    "message_prefix": "sync:"
  },

  "push": {
    "push_all_branches": false,
    "timeout_seconds": 60
  },

  "shutdown": {
    "enabled": true,
    "quick_push": true,
    "timeout_seconds": 30,           // hard cap so shutdown is never blocked
    "open_report": false
  },

  "report": {
    "auto_open": true,               // interactive runs open the browser
    "archive": true,                 // keep timestamped report-*.html copies
    "archive_keep_days": 90,
    "show_files": true,              // Files & Last Commit section (per-file commit times)
    "files_max": 500                 // per-repo file cap in that section (0 disables)
  },

  "security": {
    "block_on_secrets": true,
    "patterns": [".env*", "*.pem", "*.key", "credentials.json", "secrets.json", "*.p12"],  // filename matches
    "content_patterns": [            // regex over file content
      "-----BEGIN [A-Z ]*PRIVATE KEY-----",
      "gh[opsur]_[A-Za-z0-9]{20,}",
      "AKIA[0-9A-Z]{16}",
      "AIza[0-9A-Za-z\\-_]{35}",
      "xox[baprs]-[0-9A-Za-z\\-]{10,}",
      "sk_live_[0-9A-Za-z]{20,}",
      "sk-[A-Za-z0-9_\\-]{24,}",
      "(?i)(api[_-]?key|secret|password|passwd|access[_-]?token)\\s*[:=]\\s*['\"][^'\"]{8,}['\"]"
    ],
    "allow_files": [],               // globs excluded from BOTH checks (false-positive escape hatch)
    "max_scan_bytes": 1048576        // per-file content scan cap
  },

  "limits": {
    "max_file_mb": 100,              // GitHub hard limit — above this blocks the repo
    "warn_file_mb": 50,              // above this is flagged "large" in the report (warning only)
    "block_on_oversize": true
  },

  "deleted_repo_policy": {
    "confirm_scans": 3,              // 3 consecutive 404s before quarantine
    "confirm_days": 7,               // and at least 7 days elapsed
    "require_remote_confirmation": true,
    "require_user_confirmation": true
  },

  "notify": {
    "toast_on_failure": true,
    "email": { "enabled": false, "smtp": "", "recipients": [] },
    "webhook": { "discord": "", "slack": "", "github_actions": false }
  },

  "triggers": {
    "startup": true,
    "shutdown": true,
    "every_hours": 3,                // 0 disables
    "every_minutes": 0,              // wins over every_hours when > 0
    "at_time": null,                 // "HH:MM", e.g. "21:15"
    "file_change": true,
    "manual": true
  }
}
```

Edit with `python urgithub.py --config triggers.every_hours 6` or any JSON editor, then re-run `--schedule install`.

---

## Scheduling (Windows Task Scheduler)

`python urgithub.py --schedule install` creates these tasks (all pointing at absolute `python.exe` + script paths):

| Task | Schedule |
|------|----------|
| `URGithub-startup` | At user logon |
| `URGithub-scheduled` | Every N hours / minutes, or daily at `at_time` |
| `URGithub-shutdown` | Event-triggered on shutdown/restart/logoff (EventID 1074, provider User32), 10 s delay, runs as SYSTEM, network-only, 2-minute execution cap |

It also **deploys the full launcher set** (`start/scan/sync/shutdown/schedule/manual.bat`) into `<base>\urgithub\Run\`.

```powershell
python urgithub.py --schedule install
python urgithub.py --schedule status    # query task state
python urgithub.py --schedule uninstall # remove all URGithub tasks
```

> Creating the SYSTEM-level shutdown task may require an elevated (admin) prompt. `--setup-all` and the wizard retry it with a UAC prompt automatically.

---

## Control panel (`--tray`)

`python urgithub.py --tray` opens a small window with:

- **Scan Now** / **Sync Now** — run `manual_scan` / `manual_sync` in the background
- **Open Report** — opens the latest `report.html`
- **Schedule Status** / **Install Schedule** — query or install Task Scheduler tasks
- **Quit** — closes the panel
- A live log area, a **resident timer** that fires `scheduled` / `at_time` (checked every 20 s), and an optional **file watcher** thread

Everything runs in background threads so the UI never freezes.

---

## File watcher (`--watch`)

`python urgithub.py --watch` polls `repos in github\` every 10 s. When files change it waits 30 s of quiet (debounce), then fires the `file_change` trigger — one full pipeline run. `.git` internals and all dot-folders are ignored, so git bookkeeping never triggers spurious runs.

---

## Reports

Each run writes `report.html` to `<base>\urgithub\.urgithub\reports\` (atomic write + timestamped archive, pruned after `archive_keep_days`). Dark GitHub theme:

- **Header** — run time · trigger · duration · run ID · outcome
- **7 stat cards** — Pushed · Cloned · Renamed · Initialized · Removed · Failed · Events, each with its own accent color
- **Activity timeline** — icon-chip rows (P/C/I/R/D/X/B/-) with mono timestamps, repo names, details, and `↗` links to GitHub
- **Details** — per-repo blocks with action badge, `before → after` SHAs, A/M/D/R changed-file chips, and "Open on GitHub ↗"
- **All repositories** — a **live re-scan** showing registry status, **branch**, and CLEAN/DIRTY/UNINIT
- **Security & Size** and **Environment Drift** — only when findings exist

---

## Deployed layout

```
<base location>\urgithub\
├── logs\                 ← application.log + error.log (rotating)
├── repos in github\      ← ACTIVE managed repositories
├── deleted repos\        ← quarantined archives (never auto-deleted)
├── Run\                  ← deployed .bat launchers + NOTES.md
└── .urgithub\            ← hidden data
    ├── config.json       ← all settings
    ├── shutdown-task.xml ← generated Task Scheduler XML
    ├── database\
    │   ├── registry.json ← repo registry (status, SHAs, quarantine state)
    │   └── journal.jsonl ← append-only event journal
    ├── reports\          ← report.html + archive\
    ├── locks\            ← run.lock (stale after 15 s)
    └── cache\ credentials\
```

---

## Project layout

```
E:\Project-1\
├── urgithub.py            ← entry point (thin: cli.main)
├── urgithub_core\
│   ├── cli.py             ← argument handling + config/schedule/watch/tray/status commands
│   ├── runner.py          ← universal run_trigger() pipeline + gates
│   ├── discovery.py       ← registry, reconciliation, adoption, clone, quarantine, rename
│   ├── scan.py            ← 20-point inspection + validation gates
│   ├── sync.py            ← safe pull/commit/push + shutdown quick-push
│   ├── report.py          ← report.html (dark theme) + archiving + show rules + toasts
│   ├── scheduler.py       ← Task Scheduler integration + launcher deploy + next-run math
│   ├── watch.py           ← debounced file watcher
│   ├── tray.py            ← control panel GUI
│   ├── wizard.py          ← registration wizard (GUI + console fallback)
│   ├── envcheck.py        ← registration environment checks
│   ├── config.py          ← defaults, deep-merge, locator, load/save
│   ├── paths.py           ← path derivation + ensure_all
│   ├── registry.py        ← JSON repo registry
│   ├── journal.py         ← append-only JSONL journal
│   ├── lock.py            ← PID-based run lock
│   ├── logs.py            ← rotating logging
│   └── gitops.py          ← non-interactive git/gh wrappers
├── Run\                   ← dev launchers (start/scan/sync/shutdown/schedule/manual.bat)
├── docs\                  ← README + REPORT-REDESIGN-NOTE + spec/00..05
└── .gitignore
```

No third-party dependencies. No build step. `python urgithub.py` is all there is.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `not registered. Run: python urgithub.py --setup` | Register once with `--setup` |
| Env check fails on GitHub auth | `gh auth login` (ensure the `repo` scope), then re-run `--setup` |
| Repo shows `blocked: divergence` | Someone else pushed; `git pull` manually and review — URGithub never force-pushes |
| Repo shows `blocked: secrets` | Remove the secret file, gitignore it, or add it to `security.allow_files`; keys inside code files are caught by `security.content_patterns` |
| Repo shows `blocked: oversize files` | Remove the big file, move it to LFS, or raise `limits.max_file_mb` (GitHub rejects files > 100 MB) |
| `--schedule status` empty | Run `--schedule install` first (needs registration) |
| Shutdown task not created | Run `--schedule install` from an **elevated** prompt (the wizard retries with UAC) |
| A run says `skipped — lock held` | Another run is active; the lock expires after 15 s stale |
| Two runs fire at once | Impossible by design — the global lock serializes them; the second one exits |

### Keep repo names in sync with GitHub

GitHub is the source of truth for names.

- **Renamed on GitHub only** → URGithub detects it via `gh api` returning the new name and renames the local folder + registry entry automatically.
- **Renamed locally only** → URGithub adopts it: on the next run it reads the folder's `origin`, matches it to the existing registry entry (whose path is gone), and reuses that entry — updating the path, no duplicate clone, no quarantine. Then just `gh repo rename NewName --repo owner/OldName` on GitHub to match.
- Leftover ghost entries (from manual moves) can be dropped with `--forget NAME` or bulk-cleaned with `--prune`.

---

## Development & verification

Each phase has a standalone test harness in the temp workspace:

```powershell
python p2_test.py  # discovery / registry
python p3_test.py  # scan engine
python p4_test.py  # sync engine
python p5_test.py  # report engine
python p6_test.py  # triggers / scheduler / watcher / tray wiring
python p7_test.py  # rename adoption + registry cleanup
python p8_test.py  # content-based secrets + file-size gate
python smoke_harness.py  # end-to-end scan → push → idempotent second run
```

All harnesses create throwaway bases under a temp dir and patch the locator; they never touch your real registration.

---

## Roadmap

- **Done (Phases 1–6 + report redesign):** registration wizard · discovery/registry · 20-point scan · validation gates · safe sync/commit/push · dark-theme report.html + journal · quarantine workflow · Windows Task Scheduler (startup/timer/shutdown) · file watcher · control panel · config CLI.
- **Future:** `event_hook` trigger (webhook/email), email/webhook notifications, real system-tray icon (via a `pystray`-based optional extra), report header avatar + outcome badge + footer polish.
