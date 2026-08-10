# URGithub Wiki

![URGithub](../assets/urgithub.svg)

> The safe, automatic Git repository manager for your local machine.

> **In one line:** URGithub watches your repositories folder, discovers every repo, scans each one through a **23-point inspection**, blocks anything unsafe, synchronizes the rest, and writes a human-readable HTML report of everything that happened.

## Pages

| Page | Contents |
|---|---|
| [Installation](installation.md) | System requirements, setup wizard, first-run procedure |
| [Configuration](configuration.md) | Config keys, `--config` CLI, commit & push policies |
| [Automation](automation.md) | Triggers and scheduling on Windows, Linux and macOS |
| [Security](security.md) | Secret detection, the safety model, blocked-operation reasons |
| [Report & Journal](report.md) | What `report.html` and the JSONL journal contain |
| [Troubleshooting](troubleshooting.md) | Common problems and fixes |

## What URGithub does

- **Discovers** every repository under `repos in github\` and reconciles it against `gh repo list`. On first run it clones your entire GitHub account.
- **Scans** each repository through a 23-point inspection.
- **Protects** you with safety gates — secrets, oversized files, divergence and permissions.
- **Synchronizes** safely: fetch → fast-forward-only pull → commit (per policy) → push. Never `reset`, `--force`, `rebase` or `clean`.
- **Reports** every run to `report.html` — success, failure, or nothing-changed alike.
- **Journals** every action to an append-only JSONL file with before/after SHAs.

## One pipeline, every trigger

```
DISCOVER → SCAN → SECURITY → VALIDATE → SYNC → COMMIT → PUSH → JOURNAL → REPORT
```

Every trigger — startup, shutdown, a timer, a file change, a button click — enters this **one pipeline**. There is never a second, unsafer path.

## The four rules

| Rule | Meaning |
|---|---|
| **Rule 0** | No registration → no operations. Only `--setup` runs first. |
| **Rule 1** | No scan → no sync. The sync engine only touches repos scanned in the current run. |
| **Rule 2** | Every run produces `report.html` — success, failure, and nothing-changed alike. |
| **Rule 3** | Trigger type does not matter. Startup, timer, manual and future triggers all call the same entry point. |

## Quick start

```bash
# Linux / macOS
gh repo clone learnerforge/push-to-github
cd push-to-github
python3 urgithub.py --setup
python3 urgithub.py

# Windows (PowerShell / CMD)
python urgithub.py --setup
python urgithub.py
```

URGithub runs the moment you have Python, Git and GitHub CLI — three commands, nothing else. See the full walkthrough on the [Installation](installation.md) page.

## Platform support

| Feature | Windows 10/11 | Linux | macOS |
|---|---|---|---|
| Repository engine | ✓ | ✓ | ✓ |
| Registration wizard & Control Center | ✓ | ✓ | ✓ |
| File watcher & resident scheduler | ✓ | ✓ | ✓ |
| Task Scheduler integration | ✓ | — | — |
| Scheduled runs | ✓ | cron / systemd | launchd / cron |
| Shutdown quick-push & toasts | ✓ | — | — |

## Requirements

| Requirement | Version / details |
|---|---|
| Python | 3.10+ |
| Python GUI | `tkinter` required for the wizard and Control Center |
| Git | Installed and available in `PATH` |
| GitHub CLI | `gh` installed and authenticated |
| GitHub permissions | Authentication with the required repository access |
