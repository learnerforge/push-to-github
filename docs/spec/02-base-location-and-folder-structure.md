# Detail 2 — Base Location & Folder Structure

## Base location

The user selects a base location at registration (e.g. `D:\Data`). The application creates **one root folder** inside it: `urgithub\`. Every path the program ever touches is derived from that single root by `Paths` (`urgithub_core/paths.py`).

The user only needs to remember the base location. Folder names intentionally contain spaces — **every** code path quotes paths.

## The locator — the only file outside the base location

```
~\.urgithub\base.txt     ← contains the base location, e.g. "D:\Data"
```

Written by `write_locator()` at registration; read by `Config.load()` on every invocation. Nothing else is ever written outside the base location.

## Folder structure (`paths.py`)

```
<base location>\urgithub\
├── logs\                     ← OPERATION HISTORY
│   ├── application.log       ← rotating (1 MB, 5 backups) — all operations
│   ├── error.log             ← rotating (500 KB, 3 backups) — errors only
│   └── history\              ← reserved for journal copies / historical archives
│
├── repos in github\          ← ACTIVE MANAGED REPOSITORY AREA
│   ├── CampusCart\
│   ├── Games\
│   └── NexaSite\
│
├── deleted repos\            ← ARCHIVED / QUARANTINED (never auto-deleted)
│   ├── CampusCart\
│   └── OldProject_1\         ← suffix avoids collisions when a name is reused
│
├── Run\                      ← WINDOWS TRIGGERS ONLY (thin .bat launchers)
│   ├── start.bat             ← python urgithub.py --startup
│   ├── scan.bat              ← python urgithub.py --scan
│   ├── sync.bat              ← python urgithub.py --sync
│   ├── shutdown.bat          ← python urgithub.py --shutdown
│   ├── schedule.bat          ← python urgithub.py --run scheduled
│   ├── manual.bat            ← python urgithub.py --tray
│   └── NOTES.md
│
└── .urgithub\                ← hidden internal data (never user-visible)
    ├── config.json           ← master configuration (schema below)
    ├── shutdown-task.xml     ← generated XML for the SYSTEM shutdown task
    ├── database\
    │   ├── journal.jsonl     ← append-only history (Detail 5)
    │   └── registry.json     ← known-repos registry (schema below)
    ├── reports\
    │   ├── report.html       ← latest, overwritten every run (atomic)
    │   └── archive\
    │       └── report-2026-08-10T18-45-00.html   ← timestamped copies
    ├── locks\
    │   └── run.lock          ← global run lock (PID; stale after 15 s)
    ├── cache\                ← reserved for gh/git metadata cache
    └── credentials\          ← credential *references* only (never tokens)
```

All folders are created up-front by `Paths.ensure_all()` at registration and again before every run.

## Core folder rules

```
repos in github   = ACTIVE MANAGED REPOSITORIES
deleted repos     = ARCHIVED / QUARANTINED REPOSITORIES (never auto-delete)
logs              = OPERATION HISTORY
Run               = WINDOWS TRIGGERS ONLY
.urgithub         = hidden internal data
```

## Rules for `repos in github\`

A folder belongs here only if:

1. It is a valid Git repository.
2. It has a `.git` directory.
3. It has a configured remote, where required.
4. The application recognizes it as a managed repository (registry entry).
5. It has not been intentionally archived/deleted.

The scanner must **not** assume every ordinary folder is a repository — folders without a `.git` directory are ignored during discovery.

## `config.json` (master config)

Location: `<base>\urgithub\.urgithub\config.json`. Written atomically (`.tmp` + rename) by `Config.save()`.

Defaults (`urgithub_core/config.py` — the program deep-merges any user file over these):

```json
{
  "base_location": "D:\\Data",
  "registered": true,
  "registered_at": "2026-08-10T18:45:00Z",
  "environment_snapshot": {
    "git":      { "installed": true, "version": "git version 2.45.1" },
    "identity": { "name": "Your Name", "email": "you@example.com" },
    "github":   { "authenticated": true, "host": "github.com", "login": "you",
                  "cli_installed": true, "scopes": ["repo"], "can_push": true },
    "last_check": "2026-08-10T18:45:00Z"
  },

  "github_owner": "auto",                 // "auto" = the gh login from the snapshot
  "clone_missing_repos": true,            // clone missing repos + first-run clone-all
  "skip_forks": false,                    // true = exclude forks from clone-all

  "commit_policy": {
    "auto_commit": false,                 // commit working-tree changes automatically?
    "message_prefix": "sync:"
  },

  "push": {
    "push_all_branches": false,
    "timeout_seconds": 60
  },

  "shutdown": {
    "enabled": true,
    "quick_push": true,
    "timeout_seconds": 30,                // hard cap so shutdown is never blocked
    "open_report": false
  },

  "report": {
    "auto_open": true,                    // interactive runs open the browser
    "archive": true,                      // keep timestamped report-*.html copies
    "archive_keep_days": 90,
    "show_files": true,                   // Files & Last Commit section in the report
    "files_max": 500                      // per-repo cap (0 disables the section)
  },

  "security": {
    "block_on_secrets": true,
    "patterns": [".env*", "*.pem", "*.key", "credentials.json", "secrets.json", "*.p12"],
    "content_patterns": [
      "-----BEGIN [A-Z ]*PRIVATE KEY-----",
      "gh[opsur]_[A-Za-z0-9]{20,}",
      "AKIA[0-9A-Z]{16}",
      "AIza[0-9A-Za-z\\-_]{35}",
      "xox[baprs]-[0-9A-Za-z\\-]{10,}",
      "sk_live_[0-9A-Za-z]{20,}",
      "sk-[A-Za-z0-9_\\-]{24,}",
      "(?i)(api[_-]?key|secret|password|passwd|access[_-]?token)\\s*[:=]\\s*['\"][^'\"]{8,}['\"]"
    ],
    "allow_files": [],                    // globs excluded from BOTH checks
    "max_scan_bytes": 1048576             // per-file content-scan cap
  },

  "limits": {
    "max_file_mb": 100,                   // GitHub hard limit — above this blocks the repo
    "warn_file_mb": 50,                   // above this is flagged "large" (warning only)
    "block_on_oversize": true
  },

  "deleted_repo_policy": {
    "confirm_scans": 3,                   // 3 consecutive 404s before quarantine
    "confirm_days": 7,                    // and at least 7 days elapsed
    "require_remote_confirmation": true,
    "require_user_confirmation": true
  },

  "notify": {
    "toast_on_failure": true,
    "email":    { "enabled": false, "smtp": "", "recipients": [] },
    "webhook":  { "discord": "", "slack": "", "github_actions": false }
  },

  "triggers": {
    "startup": true,
    "shutdown": true,
    "every_hours": 3,                     // 0 disables
    "every_minutes": 0,                   // wins over every_hours when > 0
    "at_time": null,                      // "HH:MM", e.g. "21:15"
    "file_change": true,
    "manual": true
  }
}
```

Edit with `python urgithub.py --config <dotted.key> <value>` (values are auto-coerced to bool/int/float) or any JSON editor, then re-run `--schedule install` to apply trigger changes.

## `registry.json` (per-repo state, survives across runs)

Location: `<base>\urgithub\.urgithub\database\registry.json`. Written atomically by `Registry.save()`.

```json
{
  "CampusCart": {
    "path": "D:\\Data\\urgithub\\repos in github\\CampusCart",
    "url": "https://github.com/you/CampusCart",
    "first_seen": "2026-08-10T10:00:00Z",
    "last_seen": "2026-08-10T18:45:00Z",
    "last_scan_sha": "a83f92c",
    "last_sync_sha": "b41c10e",
    "status": "active",
    "auto_commit": false,
    "diverged_since": null,
    "deletion_hits": 0,
    "deletion_suspected_at": null,
    "quarantined_at": null,
    "quarantined_to": null
  }
}
```

| Field | Meaning |
|-------|---------|
| `path` | absolute path of the working copy |
| `url` | origin URL (sans `.git`), refreshed from `git remote get-url origin` during discovery |
| `first_seen` / `last_seen` | UTC registration timestamps |
| `last_scan_sha` | `head_sha` recorded at the last scan (7-char) |
| `last_sync_sha` | commit SHA after the last successful push |
| `status` | see below |
| `auto_commit` | per-repo override of `commit_policy.auto_commit` (defaults to the global at discovery) |
| `diverged_since` | UTC timestamp when divergence was first observed (cleared after a successful push) |
| `deletion_hits` | consecutive remote-404 count |
| `deletion_suspected_at` | when the first 404 was seen |
| `quarantined_at` / `quarantined_to` | when and where the repo was moved |

Registry `status` values: `active` · `missing` (folder gone, remote alive) · `LOCAL_MISSING` (legacy marker) · `pending` (deletion suspected, awaiting confirmation) · `quarantined` · `deleted`.

Repos that disappear from `repos in github\` are flagged in reports — never silently deleted or re-cloned over. Repos inside `deleted repos\` are excluded from discovery/scan/sync.

## `Run\` launchers

`--schedule install` deploys the full launcher set (absolute paths to the current `python.exe` + `urgithub.py`) into `<base>\urgithub\Run\`:

| Launcher | Command | Purpose |
|----------|---------|---------|
| `start.bat` | `urgithub --startup` | Startup trigger |
| `scan.bat` | `urgithub --scan` | Manual scan only |
| `sync.bat` | `urgithub --sync` | Manual full sync |
| `shutdown.bat` | `urgithub --shutdown` | Quick push before shutdown |
| `schedule.bat` | `urgithub --run scheduled` | Scheduled-trigger entry (used by Task Scheduler) |
| `manual.bat` | `urgithub --tray` | Control panel GUI |

The launchers are thin `@echo off` wrappers — all logic lives in the Python application (see `Run\NOTES.md`).
