<div align="center">

# URGithub

### The safe, automatic Git repository manager for your local machine.

Automatically **discover, scan, synchronize, commit, push, verify and monitor** all your Git repositories — with safety gates and a complete HTML activity report after every run.

No cloud. No daemon installs. No third-party Python dependencies. Nothing destructive ever happens.

<!--
  BADGES — add after the CI/security workflows are live (docs/URGITHUB-TASKS.md, item A5):
  ![CI](https://img.shields.io/github/actions/workflow/status/learnerforge/urgithub/tests.yml?label=CI)
  ![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)
  ![License](https://img.shields.io/github/license/learnerforge/urgithub)
  ![Security](https://img.shields.io/badge/security-gated-green)
  ![Release](https://img.shields.io/github/v/release/learnerforge/urgithub)
-->

</div>

---

## The problem

You keep dozens of Git repositories on your own machine — side projects, work repos, AI experiments, scripts. Then you spend hours every week doing the same things by hand:

- forgetting which folders are even Git repos,
- editing a file and leaving it uncommitted for days,
- accidentally pushing a `.env` with real keys in it,
- getting a conflict because someone else pushed while you were working,
- losing track of whether your local copy even matches GitHub.

URGithub exists to make that entire category of work **automatic and safe** — and then show you exactly what it did.

## The solution

**URGithub is the safety layer between your filesystem and GitHub.**

It watches your `repos in github` folder, discovers every repository, scans each one through a **23-point inspection**, blocks anything unsafe, synchronizes the rest, and writes a human-readable HTML report of everything that happened.

```
DISCOVER → SCAN → SECURITY → VALIDATE → SYNC → COMMIT → PUSH → JOURNAL → REPORT
```

Every trigger — startup, shutdown, a timer, a file change, a button click — enters this **one pipeline**. There is never a second, unsafer path.

> **The four rules**
> | Rule | Meaning |
> |------|---------|
> | **Rule 0** | No registration → no operations. Only `--setup` runs first. |
> | **Rule 1** | No scan → no sync. The sync engine only touches repos scanned in the current run. |
> | **Rule 2** | Every run produces `report.html` — success, failure, and nothing-changed alike. |
> | **Rule 3** | Trigger type does not matter. Startup, timer, manual and future triggers all call the same entry point. |

---

<!--
  DEMO GIF — 30–60 seconds, top of the page (docs/URGITHUB-TASKS.md, item A6):
  <img src="docs/screenshots/demo.gif" alt="URGithub demo" width="720">
-->

## Features

| | |
|---|---|
| ◆ **Automatic discovery** | Finds every repo under `repos in github\` and reconciles it against `gh repo list`. On the first run it **clones your entire GitHub account** — private repos and forks included (unless `skip_forks`). |
| ▲ **Secret detection** | Scans file **names and contents** for keys, tokens and passwords. A secret stops that repo cold — nothing with a `.env` or a hard-coded key ever gets pushed. |
| ⟳ **Automatic sync** | Fetch → fast-forward-only pull → commit (per policy) → push. Safe by construction: never `reset`, `--force`, `rebase` or `clean`. |
| ⇉ **Divergence protection** | If the local and remote histories diverged, the repo is **blocked** instead of clobbered. You review, you decide. |
| ▤ **HTML reports** | A dark, GitHub-themed activity report after **every** run — cards, timeline, per-repo details, and per-file last-commit dates. |
| ◷ **Startup / shutdown / scheduled** | Windows Task Scheduler runs it at logon, on a repeating timer, and quick-pushes before shutdown. |
| ✎ **File-change triggering** | A debounced watcher fires a full run when your repos folder changes — edit, save, done. |
| ▣ **Repository quarantine** | Repos confirmed deleted on GitHub are moved to `deleted repos\` — never silently deleted, and only with your confirmation. |
| ◈ **No third-party deps** | Pure Python standard library. No `pip install`, no build step, no daemon. |
| ≣ **Full audit trail** | Every action journaled to an append-only JSONL file with before/after SHAs. |

## How a run works

```
registration gate → lock (stale after 15 s) → journal run-start → light env check
→ DISCOVER   (scan repos in github\, reconcile with `gh repo list`,
              clone missing, adopt renames, staged quarantine)
→ SCAN       (23-point inspection per repo → ScanResult)
→ VALIDATE   (secrets gate · size gate · divergence gate · auth gate —
              stop that repo, continue others)
→ SYNC       (fetch → fast-forward-only pull)
→ COMMIT/PUSH (per auto_commit / push policy)
→ JOURNAL    (every action with before/after SHAs)
→ REPORT     (report.html, atomic write + archive — Rule 2)
→ SHOW       (interactive → browser · background → toast · shutdown → never)
→ journal run-end → release lock
```

### When a repo is **not** pushed

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

## The Git Activity Report

Every run — success, failure, or nothing-changed — writes `report.html` to `<base>\urgithub\.urgithub\reports\` (atomic write, timestamped archive, pruned after 90 days). Dark GitHub theme:

- **Header** — run time · trigger · duration · run ID · outcome
- **7 stat cards** — Pushed · Cloned · Renamed · Initialized · Removed · Failed · Events, each with its own accent color
- **Activity timeline** — icon-chip rows (P/C/I/R/D/X/B/-) with mono timestamps, repo names, details, and `↗` links to GitHub
- **Details** — per-repo blocks with action badge, `before → after` SHAs, A/M/D/R changed-file chips, and "Open on GitHub ↗"
- **All repositories** — a live re-scan showing registry status, **branch**, and CLEAN/DIRTY/UNINIT
- **Files & Last Commit** — per-file "committed at" dates, GitHub file-browser style (newest first, `uncommitted` for untracked)
- **Security & Size** and **Environment Drift** — only when findings exist

<!-- Sample report: <a href="docs/sample-report.html">View a sample report ↗</a> (generate + commit it — docs/URGITHUB-TASKS.md, item A7) -->

---

## Quick Start

### Requirements

URGithub supports **Windows, Linux, and macOS** for its core functionality.

| Requirement        | Version / Details                                    |
| ------------------ | ---------------------------------------------------- |
| Python             | **3.10+**                                            |
| Python GUI         | `tkinter` required for the wizard and Control Center |
| Git                | Installed and available in `PATH`                    |
| GitHub CLI         | `gh` installed and authenticated                     |
| GitHub permissions | Authentication with the required repository access   |

> **Windows users:** Windows 10 or Windows 11 is required for Windows-specific integrations such as Task Scheduler, shutdown quick-push, and Windows notifications.

### Platform Support

| Feature                     | Windows 10/11 |     Linux    |     macOS    |
| --------------------------- | :-----------: | :----------: | :----------: |
| Repository engine           |       ✓       |       ✓      |       ✓      |
| Registration wizard         |       ✓       |       ✓      |       ✓      |
| Control Center GUI          |       ✓       |       ✓      |       ✓      |
| File watcher                |       ✓       |       ✓      |       ✓      |
| Resident scheduler          |       ✓       |       ✓      |       ✓      |
| Task Scheduler integration  |       ✓       |       —      |       —      |
| Startup scheduling          |       ✓       | cron/systemd | launchd/cron |
| Scheduled synchronization   |       ✓       | cron/systemd | launchd/cron |
| Shutdown quick-push         |       ✓       |       —      |       —      |
| Windows toast notifications |       ✓       |       —      |       —      |

### 1. Install the prerequisites

Install:

* **Python 3.10 or newer**
* **Git**
* **GitHub CLI (`gh`)**

Then verify that they are available from your terminal:

```bash
python --version
git --version
gh --version
```

### 2. Authenticate with GitHub

Authenticate GitHub CLI:

```bash
gh auth login
```

Verify your authentication:

```bash
gh auth status
```

URGithub uses the authenticated GitHub CLI session for repository operations.

### 3. Start URGithub

From the project directory:

**Windows**

```powershell
python urgithub.py
```

**Linux / macOS**

```bash
python3 urgithub.py
```

The setup wizard will guide you through repository discovery, configuration, authentication checks, and automatic synchronization settings.

> **Windows only:** register, install the scheduled tasks and run the first sync in one command with `python urgithub.py --setup-all`. Step by step: `--setup`, `--sync`, `--schedule install`, `--tray`. The setup wizard re-checks everything for you — Git · version · username · email · gh CLI · authentication · `repo` push scope · live GitHub connection · base writable — with one-click fix buttons, and falls back to a console prompt if the GUI can't open.

> The first run **downloads all your GitHub repositories** — private and forks included, unless `skip_forks` — into `repos in github\` automatically. No manual cloning.

### 4. Run a synchronization manually

To execute the synchronization workflow:

```bash
python urgithub.py --run manual
```

The workflow follows the safety pipeline:

```text
Discover
   ↓
Scan
   ↓
Validate
   ↓
Sync
   ↓
Commit
   ↓
Push
   ↓
Verify
   ↓
Generate Report
```

### 5. Schedule automatic synchronization

On **Windows**, URGithub can integrate with Windows Task Scheduler for:

* System startup
* Scheduled synchronization
* Shutdown quick-push

On **Linux**, use `cron` or `systemd`:

```bash
python3 urgithub.py --run scheduled
```

On **macOS**, use `launchd` or `cron`:

```bash
python3 urgithub.py --run scheduled
```

### Important

URGithub's **core engine, GUI, wizard, and file watcher are cross-platform**. Only integrations that depend on operating-system-specific functionality are platform-specific.

If you are using Linux or macOS, you can still use the complete repository management engine; you simply configure scheduling through the operating system's native scheduling mechanism.

The complete screen-by-screen guide lives in **[`setup.md`](setup.md)**.

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

## Control panel & file watcher

- `python urgithub.py` (no arguments) — the **Control Center**: Dashboard / Repositories / Schedule / Settings / Logs / Help, with **Scan now** / **Sync now**, schedule status, a resident timer and a streaming log. Everything runs in background threads so the UI never freezes.
- `python urgithub.py --watch` — polls `repos in github\` every 10 s, waits 30 s of quiet (debounce), then fires the `file_change` trigger. `.git` internals are ignored so git bookkeeping never triggers spurious runs.

---

## Performance

Measured on a real 12-repository account (one repo with **3,608 tracked files**):

- Full manual scan of all 12 repos: **~42 seconds**.
- Per-file last-commit history is a **single `git log` walk** per repo (~230 KB for the 3,600-file repo) — not one process per file.
- Idempotent: a second run with nothing to do clones nothing and pushes nothing.

---

## FAQ

**Does it ever push something I didn't want pushed?**
No. Secrets, oversized files, divergence, unreachable remotes, missing permissions and missing remotes all **block** that repo. It never force-pushes and never does destructive `reset`/`rebase`/`clean`.

**Does it commit my changes automatically?**
Only if `commit_policy.auto_commit` is `true`. Otherwise a dirty repo is `skipped` (and shown in the report).

**What if my repo gets renamed on GitHub?**
URGithub detects it and renames the local folder + registry entry automatically. GitHub is the source of truth for names.

**Where does my data live?**
In your **base location** (e.g. `D:\Data\urgithub\`) — not in this project folder. The project is just the engine. The only thing written outside the base location is `~\.urgithub\base.txt`.

**Does it work on Linux/macOS?**
The engine and GUI work anywhere Python 3.10+ runs; the Windows Task Scheduler integration and shutdown quick-push are Windows-only. Cross-platform scheduling is on the [roadmap](docs/ROADMAP.md).

---

## Roadmap

See **[`docs/ROADMAP.md`](docs/ROADMAP.md)** — v1.0 (done), v1.1 (Linux/macOS + notifications), v1.2 (web dashboard + multi-account), v2.0 (cross-platform daemon + policies).

## Contributing

Bugs, ideas and pull requests are welcome. Start at **[`docs/ISSUE-BACKLOG.md`](docs/ISSUE-BACKLOG.md)** — a set of concrete, labeled issues with acceptance criteria. The engineering docs live in **[`docs/`](docs/README.md)**.

## Security

- Secret detection is on by default (`security.block_on_secrets`). Anything flagged is reported and **never pushed**.
- To report a vulnerability, open a private advisory on GitHub or email the maintainer — do not post keys in issues.

## License

[MIT](LICENSE) — Copyright (c) 2026 Ganesh Bakkera

---

## Reference — layouts

**Deployed layout**

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

**Project layout**

```
<project folder>\
├── urgithub.py            ← entry point (thin: cli.main)
├── urgithub_core\
│   ├── cli.py             ← argument handling + config/schedule/watch/tray/status commands
│   ├── runner.py          ← universal run_trigger() pipeline + gates
│   ├── discovery.py       ← registry, reconciliation, adoption, clone, quarantine, rename
│   ├── scan.py            ← 23-point inspection + validation gates
│   ├── sync.py            ← safe pull/commit/push + shutdown quick-push
│   ├── report.py          ← report.html (dark theme) + archiving + show rules + toasts
│   ├── scheduler.py       ← Task Scheduler integration + launcher deploy + next-run math
│   ├── watch.py           ← debounced file watcher
│   ├── tray.py            ← control panel GUI
│   ├── gui.py             ← Control Center (Dashboard / Repos / Schedule / Settings / Logs / Help)
│   ├── wizard.py          ← registration wizard (GUI + console fallback)
│   ├── envcheck.py        ← registration environment checks
│   ├── config.py          ← defaults, deep-merge, locator, load/save
│   ├── paths.py           ← path derivation + ensure_all
│   ├── registry.py        ← JSON repo registry
│   ├── journal.py         ← append-only JSONL journal
│   ├── lock.py            ← PID-based run lock
│   ├── logs.py            ← rotating logging
│   ├── prompt.py          ← unified GUI/terminal confirmation funnel
│   └── gitops.py          ← non-interactive git/gh wrappers
├── Run\                   ← dev launchers (start/scan/sync/shutdown/schedule/manual.bat)
├── docs\                  ← guides + roadmap + spec/00..05
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
