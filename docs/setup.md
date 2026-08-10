# URGithub — Complete Setup Guide (A to Z)

This guide walks you through setting up URGithub from an empty machine to a
working, registered installation — **screen by screen**, with **every term
explained**, and **separate instructions for Windows, Linux and macOS**.

URGithub itself is pure Python (standard library only). The only external
tools it needs are **Git** and the **GitHub CLI (`gh`)**, and everything else
is verified for you by the built-in environment check.

---

## Table of contents

1. [What you are building — the terms first](#1-what-you-are-building--the-terms-first)
2. [Requirements (all OSes)](#2-requirements-all-oses)
3. [Part A — Prerequisites per OS](#part-a--prerequisites-per-os)
   - [Windows](#windows)
   - [Linux](#linux)
   - [macOS](#macos)
4. [Part B — Launching URGithub](#part-b--launching-urgithub)
5. [Part C — The Setup Wizard, screen by screen](#part-c--the-setup-wizard-screen-by-screen)
   - [Screen 1 — Welcome](#screen-1--welcome)
   - [Screen 2 — Workspace (base location)](#screen-2--workspace-base-location)
   - [Screen 3 — Environment check](#screen-3--environment-check)
   - [Screen 4 — Register & finish](#screen-4--register--finish)
6. [Part D — What setup actually created](#part-d--what-setup-actually-created)
7. [Part E — The Control Center, screen by screen](#part-e--the-control-center-screen-by-screen)
8. [Part F — One-command setup (Windows)](#part-f--one-command-setup-windows)
9. [Part G — Scheduled tasks, per OS](#part-g--scheduled-tasks-per-os)
10. [Part H — Troubleshooting each check](#part-h--troubleshooting-each-check)
11. [Appendix — Term glossary](#appendix--term-glossary)

---

## 1. What you are building — the terms first

| Term | What it means |
|---|---|
| **URGithub** | The program in this folder. It discovers, scans, commits, pushes, verifies and reports on your Git repositories automatically. |
| **Base location** | The folder you choose during setup. URGithub creates one `urgithub` sub-folder inside it and keeps **everything** there. |
| **Base folder / root** | `<base>\urgithub` — the working tree. |
| **Registration** | The one-time act of choosing a base location, passing the environment check, and saving your first `config.json`. Nothing works before registration (Rule 0). |
| **Locator** | A tiny file `~/.urgithub/base.txt` that remembers *where* the base location is, so URGithub can find itself later. |
| **Config** | `<base>\urgithub\.urgithub\config.json` — all settings, plus the environment snapshot taken at registration. |
| **Registry** | `<base>\urgithub\.urgithub\database\registry.json` — the list of managed repositories and their status. |
| **Journal** | `<base>\urgithub\.urgithub\database\journal.jsonl` — an append-only log of every run, phase and outcome. |
| **Environment check** | The 10 automatic checks the wizard runs before it lets you register (see Screen 3). |
| **Snapshot** | The record of your Git/gh/identity state at registration time, stored in the config. URGithub later detects **drift** when it changes. |
| **Trigger** | The event that starts a run: `startup`, `scheduled`, `file_change`, `shutdown`, or manual. |
| **Pipeline** | Every trigger runs the same chain: **discover → scan → validate → sync/commit/push → report**. |
| **Report** | `reports/report.html` — a human-readable page of what each run did. |
| **Control Center** | The GUI dashboard (`python urgithub.py` with no arguments) that operates everything without a terminal. |
| **Scheduled tasks** | Windows Task Scheduler jobs that fire triggers at login, on a timer, and at shutdown. |
| **UAC** | Windows "User Account Control" elevation prompt (the shutdown task needs admin rights). |

---

## 2. Requirements (all OSes)

| Requirement | Minimum | Notes |
|---|---|---|
| **Python** | 3.10+ | With **tkinter** installed (see per-OS notes below). |
| **Git** | any recent | Must be on `PATH` so `git` works in a terminal. |
| **GitHub CLI (`gh`)** | any recent | Must be on `PATH`. |
| **GitHub account** | one | With the `repo` (push) scope — see Screen 3. |
| **Network** | yes | Needed to reach `github.com` and to push. |

> Everything else is Python **standard library** — there is nothing to
> `pip install`.

### Download the software (official pages)

| Software | Windows | Linux | macOS |
|---|---|---|---|
| **Python 3.10+** | [python.org/downloads/windows](https://www.python.org/downloads/windows/) | [python.org/downloads/source](https://www.python.org/downloads/source/) | [python.org/downloads/macos](https://www.python.org/downloads/macos/) |
| **Git** | [git-scm.com/download/win](https://git-scm.com/download/win) | [git-scm.com/download/linux](https://git-scm.com/download/linux) | [git-scm.com/download/mac](https://git-scm.com/download/mac) |
| **GitHub CLI** | [cli.github.com](https://cli.github.com/) | [cli.github.com](https://cli.github.com/) | [cli.github.com](https://cli.github.com/) |
| **GitHub account** | [github.com/signup](https://github.com/signup) | [github.com/signup](https://github.com/signup) | [github.com/signup](https://github.com/signup) |

### Python / tkinter availability per OS

- **Windows** — the official installer from [python.org/downloads/windows](https://www.python.org/downloads/windows/) includes tkinter. `python --version` should work after install.
- **Linux** — `python3` ships with most distros, but **tkinter is often a separate package**:
  - Debian/Ubuntu/Mint: `sudo apt install -y python3-tk`
  - Fedora/RHEL: `sudo dnf install -y python3-tkinter`
  - Arch/Manjaro: `sudo pacman -S --noconfirm tk`
- **macOS** — Homebrew's `python` includes tkinter. If you see a `_tkinter` error, run `brew install python-tk@3.13` (or download Python from [python.org/downloads/macos](https://www.python.org/downloads/macos/)).

> If tkinter is missing, the setup wizard automatically falls back to a
> **console mode** (you type answers instead of clicking). The guide below
> describes the GUI, but every screen has a console equivalent.

---

## Part A — Prerequisites per OS

### Windows

Everything is one `winget` command each. Open **PowerShell** (or cmd).

> Manual downloads (if you prefer): [Git for Windows](https://git-scm.com/download/win) ·
> [GitHub CLI](https://cli.github.com/) · [Python](https://www.python.org/downloads/windows/)

```powershell
# 1. Git
winget install Git.Git

# 2. GitHub CLI
winget install GitHub.cli
```

Then **restart the terminal** so the new `PATH` takes effect, and verify:

```powershell
git --version     # → git version 2.xx
gh --version      # → gh version 2.xx
```

Authenticate once (browser flow):

```powershell
gh auth login     # choose: GitHub.com → HTTPS → "Login with a web browser"
gh auth status    # should show: Token scopes: ... 'repo' ...
```

> You can skip ALL of the above — the wizard's **fix buttons** install Git and
> gh for you automatically via `winget`, and launch `gh auth login` in a new
> console window (see Screen 3).

### Linux

Use your distribution's package manager. The wizard detects the distro from
`/etc/os-release` and shows exactly the right commands (and copies them to
your clipboard).

> Manual downloads (if you prefer): [Git for Linux](https://git-scm.com/download/linux) ·
> [GitHub CLI](https://cli.github.com/) · [Python source](https://www.python.org/downloads/source/)

**Debian / Ubuntu / Linux Mint / Pop!_OS / elementary (apt family):**

```bash
sudo apt update
sudo apt install -y git

# GitHub CLI — official keyring method
sudo mkdir -p -m 755 /etc/apt/keyrings
wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null
sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
  | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install -y gh
```

**Fedora / RHEL / CentOS / Rocky / Alma (dnf family):**

```bash
sudo dnf install -y git
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
sudo dnf install -y gh
```

**Arch / Manjaro / EndeavourOS (pacman family):**

```bash
sudo pacman -S --noconfirm git gh
```

**Any other distro:** try the snap package:

```bash
sudo snap install gh
```

Then authenticate. In the wizard's environment check, the **Authenticate
GitHub** button copies `gh auth login --web` to your clipboard — run it in a
terminal:

```bash
gh auth login --web
gh auth status
```

### macOS

Using Homebrew:

> Manual downloads (if you prefer): [Git for macOS](https://git-scm.com/download/mac) ·
> [GitHub CLI](https://cli.github.com/) · [Python for macOS](https://www.python.org/downloads/macos/)

```bash
brew install git
brew install gh

gh auth login     # GitHub.com → HTTPS → browser
gh auth status
```

The wizard opens the official download pages for you if the tools are missing.

---

## Part B — Launching URGithub

Open a terminal in the project folder and run URGithub **with no arguments**:

```powershell
# Windows (PowerShell / cmd)
cd E:\Project-1
python urgithub.py
```

```bash
# Linux / macOS
cd /path/to/Project-1
python3 urgithub.py
```

What you get depends on your state:

| State | What happens |
|---|---|
| **Not registered yet** | The **Setup Wizard** opens automatically (next part). |
| **Already registered** | The **Control Center** opens (Part E). |

Other useful ways to launch the wizard directly:

```powershell
python urgithub.py --setup       # open the setup wizard only
python urgithub.py --setup-all   # Windows only — full one-command setup (Part F)
python urgithub.py --gui         # force-open the Control Center
```

---

## Part C — The Setup Wizard, screen by screen

The wizard is a small window titled **"URGithub — Registration"**. It has four
screens, each with **Back / Next** navigation at the bottom.

### Screen 1 — Welcome

```
                    URGithub
        Universal Git repository operations manager

  URGithub scans, synchronizes, commits, pushes, verifies and
  reports on your Git repositories. A one-time registration
  must succeed before any operation is allowed.

              [ Start ]        [ Exit ]
```

| Element | Meaning |
|---|---|
| **Start** | Goes to Screen 2 (Workspace). |
| **Exit** | Closes the wizard without registering. |

### Screen 2 — Workspace (base location)

```
                      Workspace

  Choose the base location. URGithub creates one 'urgithub'
  folder inside it.

  [__________________________entry________________________] [ Browse... ]

                              [ Back ]  [ Next ]
```

| Element | Meaning |
|---|---|
| **Entry field** | The path of your **base location** (e.g. `C:\Users\you\Documents` on Windows, `/home/you` on Linux, `/Users/you` on macOS). |
| **Browse...** | Opens a folder picker so you don't have to type the path. |
| **Back** | Returns to Screen 1. |
| **Next** | Validates that the field is not empty, then runs the environment check. |

**What it does with the folder:** URGithub will create `<base>\urgithub\` and
the full folder tree inside it (see Part D). Nothing is deleted — it only
**creates** folders.

### Screen 3 — Environment check

This is the most important screen. URGithub checks **10 items** live and shows
each one with a green **✓** (pass) or red **✗** (fail). The **Register** button
stays greyed out until every check passes.

The 10 checks, in order:

| # | Check | Passes when | Fix button shown when it fails |
|---|---|---|---|
| 1 | **Python** | Always (you're running it) | — (shows your Python version) |
| 2 | **Git installed** | `git --version` succeeds | **Install Git** |
| 3 | **Git version** | Git is installed | — (shows the version) |
| 4 | **Git username** | `git config --global user.name` is set | **Configure identity** |
| 5 | **Git email** | `git config --global user.email` is set | **Configure identity** |
| 6 | **GitHub CLI (gh) installed** | `gh --version` succeeds | **Install GitHub CLI** |
| 7 | **GitHub authentication** | `gh auth status` succeeds | **Authenticate GitHub (gh auth login)** |
| 8 | **Push scope (repo) present** | Authenticated **and** scopes include `repo` | **Authenticate GitHub (gh auth login)** |
| 9 | **GitHub connection (live)** | `gh api user` answers (network OK) | — (check network / auth) |
| 10 | **Base location writable** | URGithub can create+delete a probe file in your base folder | — (pick a different folder) |

At the bottom there is a checkbox:

```
[✓] Also install Windows scheduled tasks
    (startup / 3-hour timer / shutdown quick-push)
```

| Term | Meaning |
|---|---|
| **Startup task** | Runs URGithub at Windows login (startup trigger). |
| **3-hour timer** | Runs URGithub every 3 hours (scheduled trigger). The interval comes from `triggers.every_hours` in the config. |
| **Shutdown quick-push** | A fast push of local commits before Windows shuts down (hard 30-second timeout, never blocks shutdown). Needs **UAC** because it runs as SYSTEM. |

> **Linux / macOS:** this checkbox is a **Windows** feature (it uses the
> Windows Task Scheduler). On Linux/macOS leave it unticked — use the
> Control Center's resident timer instead (Part E).

**The fix buttons (OS-aware):**

| Button | Windows | Linux | macOS/other |
|---|---|---|---|
| **Install Git** | Runs `winget install Git.Git` automatically; opens `git-scm.com/download/win` if that fails | Detects your distro and shows the exact `apt`/`dnf`/`pacman` command, **copied to your clipboard** | Opens the download page |
| **Install GitHub CLI** | Runs `winget install GitHub.cli` automatically | Shows the distro-specific install steps, copied to clipboard | Opens `cli.github.com` |
| **Configure identity** | Asks for your name and email, then sets `git config --global user.name` / `user.email` | same | same |
| **Authenticate GitHub** | Opens a new console running `gh auth login`, then re-checks after a moment | Copies `gh auth login --web` to your clipboard and re-checks 30 s later | — |

> Tip: after clicking **Install Git** / **Install GitHub CLI** on Windows, the
> checks re-run automatically when the install finishes. If you installed
> anything **manually**, click **Back** then **Next** to re-run the check
> (or use **Re-check environment** in the Control Center).

### Screen 4 — Register & finish

When all 10 checks pass, the **Register** button becomes active.

| Element | Meaning |
|---|---|
| **Back** | Return to Screen 2 (base location). |
| **Register** | Performs registration (next paragraph). |

Clicking **Register**:

1. Creates the whole folder tree under `<base>\urgithub\`.
2. Writes `config.json` with your settings **and** the environment snapshot.
3. Writes the locator `~/.urgithub/base.txt`.
4. If you ticked the checkbox — installs the Windows scheduled tasks
   (elevating with UAC if needed for the shutdown task).
5. Shows the completion message:

```
Registration complete.
Base location: C:\Users\you\Documents

Next: run  python urgithub.py  (no arguments) to open the
Control Center and click 'Sync now'.
```

> The first **Sync now** (or any first trigger) downloads **all** your GitHub
> repositories — private and forks included, unless `skip_forks` — into
> `repos in github\` automatically. No manual cloning needed.

6. Closes the wizard.

**You are now registered.** Every command and the Control Center will work.

---

## Part D — What setup actually created

```
<base>\
└── urgithub\
    ├── logs\
    │   ├── application.log        # full run log (rotates)
    │   ├── error.log              # errors only (rotates)
    │   └── history\               # rotated logs
    ├── repos in github\           # auto-filled with all your GitHub repos on the first run
    ├── deleted repos\             # repos quarantined/deleted go here
    ├── Run\                       # launcher .bat files (Windows)
    │   ├── start.bat  scan.bat  sync.bat
    │   └── shutdown.bat  schedule.bat  manual.bat
    └── .urgithub\
        ├── config.json            # settings + environment snapshot
        ├── database\
        │   ├── journal.jsonl      # every run, phase, outcome
        │   └── registry.json      # the managed-repo list
        ├── reports\
        │   ├── report.html        # latest report
        │   └── archive\           # old reports
        ├── locks\                 # run lock (prevents overlapping runs)
        ├── cache\
        └── credentials\
```

| Path | Purpose |
|---|---|
| `<base>\urgithub\repos in github` | Managed repositories. **Auto-filled on the first run**: every repo in your GitHub account (private + forks, unless `skip_forks`) is cloned here. You can also drop repos here manually. |
| `.urgithub\config.json` | All settings. Contains `base_location`, `registered`, `registered_at`, `environment_snapshot`, `triggers`, `commit_policy`, `push`, `shutdown`, `report`, `security`, `limits`, `notify`. |
| `database\registry.json` | Each repo's name → status, URL, path, last scan/sync SHA. |
| `database\journal.jsonl` | One JSON object per line; the "history" of every trigger. |
| `reports\report.html` | The readable result of the last run. |

---

## Part E — The Control Center, screen by screen

Run `python urgithub.py` (no arguments) after registering. The **Control
Center** window opens — this is where you get all the answers without a
terminal.

Layout:

```
┌──────────────────────────────────────────────────────────────┐
│  URGithub          GitHub: <login>  Base: <path>             │
├──────────────┬───────────────────────────────────────────────┤
│  Dashboard   │                                               │
│  Repositories│            (content area — changes per tab)   │
│  Schedule    │                                               │
│  Settings    │                                               │
│  Logs        │                                               │
│  Help        │                                               │
├──────────────┴───────────────────────────────────────────────┤
│  registered | last run: ok | repos: 3     next: every_hours: …│
└──────────────────────────────────────────────────────────────┘
```

### Dashboard tab

- **Scan now** — fires the `manual_scan` trigger (discover + scan only).
- **Sync now** — fires `manual_sync` (full pipeline: discover → scan → validate → sync/commit/push → report).
- **Open report** — opens `reports/report.html` in your browser.
- **Re-check environment** — re-runs the 10-check environment check live.
- A status grid with all 10 checks plus **Managed repos**, **Last run outcome**
  and **Next scheduled**.
- If not registered, you see a **Not registered** banner with an
  **Open Setup Wizard** button instead.

### Repositories tab

A table of every managed repo: **Name | Status | URL | Last sync | Path**.
Status colors: green = active/ok, orange = partial/diverged, red =
failed/blocked/quarantined/deleted/missing.

Buttons: **Refresh**, **Open on GitHub** (or double-click a row), **Open
folder**, **Verify all**, **Forget selected**, **Prune stale**.

| Term | Meaning |
|---|---|
| **Verify all** | Checks each folder exists, is a Git repo, and has an `origin` remote. |
| **Forget** | Removes a repo from the registry only — the folder stays on disk. |
| **Prune stale** | Removes entries whose status is missing / LOCAL_MISSING / quarantined / deleted. |

### Schedule tab

Shows the Windows Task Scheduler status of `URGithub-startup`,
`URGithub-scheduled`, `URGithub-shutdown`, plus **Install tasks** and
**Uninstall tasks** buttons and the **next runs** computed from your config.

> While the Control Center is open it is **resident**: it fires the
> `scheduled` trigger when a run is due, and starts the file-change watcher if
> `triggers.file_change` is on. On **Linux/macOS** (no Task Scheduler) this is
> your main scheduling mechanism.

### Settings tab

A form for the common settings:

| Setting (config key) | Meaning |
|---|---|
| `triggers.startup` | Run at Windows login. |
| `triggers.shutdown` | Quick-push at Windows shutdown. |
| `triggers.file_change` | Watch the repos folder and fire `file_change` on changes. |
| `triggers.every_hours` | Repeat every N hours (0 = off). |
| `triggers.every_minutes` | Repeat every N minutes (0 = off). |
| `triggers.at_time` | Run once daily at `HH:MM` (empty = off). |
| `commit_policy.auto_commit` | Automatically commit changed files. |
| `push.push_all_branches` | Push every branch, not just the current one. |
| `report.auto_open` | Open the report after each run. |

Plus an **Advanced — raw config JSON** editor (Load current config /
Validate and save) and a **Re-run setup wizard** button.

### Logs tab

A live console showing everything URGithub does (all log lines stream here
from every run). Buttons: **Clear view**, **Open log file** (opens
`logs/application.log`).

### Help tab

A summary of the pipeline, triggers, paths, and buttons to open the base
folder or the `docs` folder.

---

## Part F — One-command setup (Windows)

Windows-only convenience that does registration + schedule + first run +
status in one terminal command:

```powershell
python urgithub.py --setup-all
```

| Step | What it does |
|---|---|
| 1/4 Registration | Opens the wizard (Screen 1→4 above). Cancels if you close it. |
| 2/4 Deploy + schedule | Writes the `Run\*.bat` launchers and creates the tasks (UAC prompt for the shutdown task). |
| 3/4 First run | Fires the `startup` trigger (discover → scan → sync → report). |
| 4/4 Status | Prints the schedule status. |

> On Linux/macOS use `python urgithub.py --setup` (wizard only) and rely on
> the Control Center for the resident timer.

---

## Part G — Scheduled tasks, per OS

| OS | Mechanism | Supported? |
|---|---|---|
| **Windows** | Windows Task Scheduler (`schtasks`): `URGithub-startup` (at logon), `URGithub-scheduled` (timer), `URGithub-shutdown` (SYSTEM event, needs UAC) | **Full** — wizard checkbox, Schedule tab, `--setup-all` |
| **Linux** | No Task Scheduler. URGithub provides a **resident timer + file watcher inside the Control Center**; for always-on scheduling use your own `cron`/`systemd` calling `python3 urgithub.py --run scheduled` | Resident via GUI; cron optional |
| **macOS** | Same as Linux — use the Control Center, or `launchd`/`cron` calling `python3 urgithub.py --run scheduled` | Resident via GUI; launchd optional |

To invoke any trigger from a scheduler of your choice:

```bash
python3 urgithub.py --run startup      # startup trigger
python3 urgithub.py --run scheduled    # timer trigger
python3 urgithub.py --run shutdown     # shutdown quick-push
python3 urgithub.py --run manual_sync  # full manual sync
```

---

## Part H — Troubleshooting each check

| Symptom (✗ on) | Cause | Fix |
|---|---|---|
| **Git installed** | `git` not on `PATH` | Click **Install Git** (Windows auto winget; Linux gets distro commands) |
| **Git version** | Git just installed, terminal not restarted | Restart the terminal / re-open the wizard |
| **Git username / email** | `user.name` / `user.email` not set globally | Click **Configure identity** |
| **GitHub CLI installed** | `gh` not on `PATH` | Click **Install GitHub CLI** |
| **GitHub authentication** | Never ran `gh auth login`, or token revoked | Click **Authenticate GitHub** and complete the browser/device flow |
| **Push scope (repo) present** | Authenticated but scopes lack `repo` (e.g. used a fine-grained token or `--scopes` without repo) | Re-run `gh auth login` choosing GitHub.com + HTTPS, then `gh auth status` to confirm `repo` |
| **GitHub connection (live)** | No network, proxy, or GitHub down | Check connectivity (`gh auth status`, ping `github.com`) |
| **Base location writable** | Chose a read-only location (e.g. `C:\Program Files`) | Choose a normal user folder (e.g. Documents, `/home/you`) |
| **Register stays disabled** | One or more of the above | Fix the red rows; it enables automatically when all 10 are green |
| **Setup wizard won't open (falls to console)** | tkinter not installed | Windows: use the official Python installer. Linux: `apt install python3-tk` / `dnf install python3-tkinter` / `pacman -S tk`. macOS: `brew install python-tk` |

---

## Appendix — Term glossary

- **Base location** — the parent folder you pick in Screen 2; contains `urgithub\`.
- **Locator** — `~/.urgithub/base.txt`; points URGithub at the base location.
- **Config** — `.urgithub\config.json`; settings + environment snapshot.
- **Registry** — `database\registry.json`; the managed-repo list.
- **Journal** — `database\journal.jsonl`; append-only run history.
- **Snapshot** — the Git/gh/identity state saved at registration; drift is detected against it.
- **Environment check** — the 10 pre-registration checks (Screen 3).
- **can_push / Push scope** — authenticated + scopes contain `repo` = you may push.
- **all_pass** — every required check passed = Register enabled.
- **Trigger** — startup / scheduled / file_change / shutdown / manual events.
- **Pipeline** — discover → scan → validate → sync/commit/push → report.
- **Scan** — read each repo, detect changes, secrets and oversized files.
- **Sync** — commit, push (and pull/merge) changes per your policies.
- **Report** — `reports/report.html`, the readable output of a run.
- **Outcome** — `ok` / `clean` / `partial` / `failed` for a run.
- **Drift** — your Git/gh environment changed since the snapshot.
- **Scheduled tasks** — Windows Task Scheduler jobs (startup/timer/shutdown).
- **UAC** — Windows elevation prompt needed by the shutdown task.
- **Resident** — the Control Center being open and firing due triggers itself.
- **Watcher** — background thread firing `file_change` when the repos folder changes.
- **Control Center** — the GUI (`python urgithub.py`) — your terminal-free dashboard.
