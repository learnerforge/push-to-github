# Installation & Setup

## 1. Install the tools

| Tool | Windows | Linux / macOS |
|---|---|---|
| Python 3.10+ | `winget install Python.Python.3.12` | Distro package / `brew install python` |
| Git | `winget install Git.Git` | `apt install git` / `brew install git` |
| GitHub CLI | `winget install GitHub.cli` | `apt install gh` / `brew install gh` |

> **Note:** Restart your terminal after installing Git / `gh` so `PATH` updates.

## 2. Verify the environment

```bash
python --version
git --version
gh --version
gh auth status
git config --global user.name
git config --global user.email
```

If the `git` identity is empty, set it before committing works:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## 3. Clone the repository

```bash
gh repo clone learnerforge/push-to-github
cd push-to-github
```

## 4. Run the setup wizard

```bash
# Linux / macOS
python3 urgithub.py --setup

# Windows (PowerShell / CMD)
python urgithub.py --setup
```

The wizard checks, in order:

1. Python
2. Git
3. GitHub CLI
4. GitHub authentication
5. Repository permissions
6. The selected workspace
7. Creates the URGithub directory structure
8. Registers the installation
9. Creates the initial configuration
10. Prepares URGithub for its first run

### Everything in one command (Windows)

```bash
python urgithub.py --setup-all
```

Registers (if needed), installs the scheduled tasks (UAC prompt for the shutdown task), runs the first sync and shows status.

## 5. First run

Recommended sequence for a new installation:

```bash
python urgithub.py --scan      # discover repos
python urgithub.py --repos     # list what was found
python urgithub.py --verify    # health check
python urgithub.py --sync      # synchronize
```

Open the report with `python urgithub.py --report` or find it at `<base>\urgithub\.urgithub\reports\report.html`.

## 6. Minimal setup

```bash
gh repo clone learnerforge/push-to-github
cd push-to-github
python3 urgithub.py --setup
python3 urgithub.py
```

That is enough to be registered, synchronized and reporting.

## Useful commands

| Command | What it does |
|---|---|
| `--setup` | One-time registration wizard |
| `--setup-all` | Register + schedule + first run + status (Windows) |
| `--scan` / `--sync` | Run discovery / synchronization now |
| `--repos` / `--verify` | List repositories / verify the environment |
| `--watch` | Start the file watcher |
| `--tray` / (no args) | Open the Control Center GUI |
| `--schedule install` | Install scheduling (Windows Task Scheduler) |
| `--config` | Show / read / set configuration |
| `--version` / `--help` | Version / help |

Next: [Configuration](configuration.md) — every config key and how to change it.
