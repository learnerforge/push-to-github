# URGithub Setup Guide

> Complete installation, registration, configuration, scheduling, verification, and troubleshooting guide for URGithub.

URGithub is a local Git repository operations manager that discovers, scans, validates, synchronizes, commits, pushes, verifies, and reports on Git repositories.

The setup process is designed around one principle:

```text
INSTALL
   ↓
VERIFY ENVIRONMENT
   ↓
AUTHENTICATE GITHUB
   ↓
REGISTER URGITHUB
   ↓
CHOOSE REPOSITORY BASE
   ↓
DISCOVER REPOSITORIES
   ↓
SCAN
   ↓
VALIDATE
   ↓
SYNC / COMMIT / PUSH
   ↓
VERIFY
   ↓
GENERATE REPORT
```

URGithub does not require a cloud service or a permanently running URGithub server. Its core engine uses Python and the tools installed on your own machine.

---

# 1. Platform Support

URGithub's **core engine is cross-platform**.

| Component / Feature         | Windows 10/11 |     Linux    |     macOS    |
| --------------------------- | :-----------: | :----------: | :----------: |
| Repository discovery        |       ✓       |       ✓      |       ✓      |
| Scan engine                 |       ✓       |       ✓      |       ✓      |
| Validation                  |       ✓       |       ✓      |       ✓      |
| Synchronization             |       ✓       |       ✓      |       ✓      |
| Commit / push operations    |       ✓       |       ✓      |       ✓      |
| Registration wizard         |       ✓       |       ✓      |       ✓      |
| Control Center GUI          |       ✓       |       ✓      |       ✓      |
| File watcher                |       ✓       |       ✓      |       ✓      |
| Resident timer              |       ✓       |       ✓      |       ✓      |
| Windows Task Scheduler      |       ✓       |       —      |       —      |
| Startup task integration    |       ✓       | cron/systemd | launchd/cron |
| Shutdown quick-push         |       ✓       |       —      |       —      |
| Windows toast notifications |       ✓       |       —      |       —      |

### Important distinction

The **Git operations engine is cross-platform**, but operating-system integrations are not.

Windows-specific functionality includes:

* Windows Task Scheduler
* Windows startup tasks
* Windows shutdown-event integration
* Windows toast notifications
* EventID 1074 shutdown detection

Linux users should use `cron` or `systemd` for scheduling.

macOS users should use `launchd` or `cron`.

---

# 2. System Requirements

Before installing URGithub, make sure the following are available.

## Required

### Python

Python **3.10 or newer**.

Check:

```bash
python --version
```

On systems where `python` points to Python 2 or is unavailable:

```bash
python3 --version
```

URGithub uses the Python standard library for its core functionality and does not require a third-party Python package installation for the base engine.

---

### Git

Git must be installed and available through `PATH`.

Check:

```bash
git --version
```

Example:

```text
git version 2.x.x
```

Configure your Git identity if you have not already done so:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Verify:

```bash
git config --global user.name
git config --global user.email
```

URGithub does not use these values as your GitHub authentication credentials. They are the author identity used for Git commits.

---

### GitHub CLI

URGithub uses GitHub CLI (`gh`) for GitHub authentication and GitHub-related operations.

Check:

```bash
gh --version
```

Then authenticate:

```bash
gh auth login
```

Follow the GitHub CLI prompts.

After authentication:

```bash
gh auth status
```

The authentication check must report that you are logged in successfully.

---

# 3. GitHub Permissions

URGithub needs sufficient GitHub permissions to perform repository operations.

For the current GitHub CLI workflow, the project expects repository access suitable for pushing to repositories.

Check the authentication state with:

```bash
gh auth status
```

Do not copy or manually place GitHub tokens into the URGithub configuration files.

URGithub should use the authenticated GitHub CLI session instead.

> Never commit GitHub tokens, passwords, `.env` secrets, private keys, or other credentials into a repository.

For more information about GitHub authentication and available connection methods, see the official GitHub documentation.

---

# 4. Install URGithub

Clone the repository:

```bash
git clone https://github.com/learnerforge/push-to-github.git
```

Enter the project:

```bash
cd push-to-github
```

Verify the project:

```bash
python urgithub.py --version
```

If your system uses `python3`:

```bash
python3 urgithub.py --version
```

You should receive the installed URGithub version.

---

# 5. Verify the Environment Before Setup

Before registering URGithub, verify the required tools manually.

Run:

```bash
python --version
git --version
gh --version
gh auth status
```

Then verify Git identity:

```bash
git config --global user.name
git config --global user.email
```

A healthy environment should look approximately like:

```text
Python       ✓
Git          ✓
Git identity ✓
GitHub CLI   ✓
GitHub auth  ✓
```

If one of these checks fails, fix it before continuing.

---

# 6. Register URGithub

URGithub uses a one-time registration process.

Run:

```bash
python urgithub.py --setup
```

The setup wizard will guide you through the initial configuration.

The registration process checks the environment and establishes the location where URGithub will keep its managed data.

---

# 7. Choose the Base Location

During registration, URGithub asks you to select a **base location**.

For example:

```text
D:\Data
```

URGithub can create its managed structure underneath that location.

A typical layout is:

```text
D:\Data\
└── urgihub\
    ├── config.json
    ├── registry.json
    ├── journal.jsonl
    ├── report.html
    ├── logs\
    ├── repos in github\
    ├── deleted repos\
    └── Run\
```

The exact generated structure may vary with the current URGithub version.

### Important

The base location is **not the same thing as the URGithub source-code directory**.

The source repository contains the application.

The base location contains URGithub's runtime data and managed repository state.

This separation allows you to update the URGithub application without mixing application files with the repositories it manages.

---

# 8. What Registration Does

Registration establishes the relationship between the URGithub application and its runtime data.

The setup process verifies items such as:

1. Python availability
2. Git installation
3. Git version
4. Git username
5. Git email
6. GitHub CLI availability
7. GitHub authentication
8. Required GitHub repository access
9. GitHub connectivity
10. Base-directory writability

URGithub should not begin normal repository operations until the required registration checks succeed.

---

# 9. Complete Setup in One Command

Windows users can use:

```bash
python urgithub.py --setup-all
```

This is the recommended shortcut for a first-time Windows installation.

The command performs the major setup stages in sequence:

```text
Registration
     ↓
Environment validation
     ↓
Base initialization
     ↓
Scheduled-task installation
     ↓
Initial repository operation
     ↓
Status verification
```

If Windows requests administrator permission for an operating-system integration, review the requested operation before accepting it.

---

# 10. First Repository Scan

Before allowing synchronization, perform a scan.

Run:

```bash
python urgithub.py --scan
```

The scan should identify the repositories that URGithub can manage.

This is important because URGithub follows a safety rule:

> **No scan → no sync.**

The synchronization engine should only operate on repositories that have been scanned and validated during the relevant run.

---

# 11. First Synchronization

After the environment and repository state are confirmed, run:

```bash
python urgithub.py --sync
```

The expected pipeline is:

```text
DISCOVER
   ↓
SCAN
   ↓
VALIDATE
   ↓
SYNC
   ↓
COMMIT
   ↓
PUSH
   ↓
VERIFY
   ↓
REPORT
```

The exact actions performed for an individual repository depend on its local and remote state.

URGithub should not blindly overwrite repository history.

---

# 12. Safety Model

URGithub is designed around conservative Git operations.

The project currently documents the following safety principles:

* No `git reset`
* No `git push --force`
* No automatic rebase
* No automatic `git clean`
* Fast-forward-only pull behavior
* Secret detection can block a repository
* Divergence can block synchronization
* Repository authorization is checked separately from authentication
* Scanning happens before synchronization

The intended behavior is:

```text
SAFE
  ↓
CONTINUE

UNSAFE
  ↓
BLOCK
  ↓
REPORT
```

A blocked repository should not silently become a destructive operation.

---

# 13. Repository Discovery

URGithub can discover Git repositories within its configured repository area.

A repository generally needs to:

* exist as a valid directory
* contain a Git working tree
* have valid Git metadata
* have an appropriate remote
* be accessible by the authenticated GitHub account

Use:

```bash
python urgithub.py --repos
```

to inspect repositories currently managed by URGithub.

Use:

```bash
python urgithub.py --verify
```

to verify registry entries, folders, Git state, and remote information.

---

# 14. Manual Commands

The primary commands are:

| Command                | Purpose                                                |
| ---------------------- | ------------------------------------------------------ |
| `--setup`              | Run the registration wizard                            |
| `--setup-all`          | Perform the complete setup flow                        |
| `--scan`               | Discover and scan repositories without synchronization |
| `--sync`               | Run the complete synchronization pipeline              |
| `--startup`            | Execute the startup trigger                            |
| `--shutdown`           | Perform a shutdown-oriented quick push                 |
| `--status`             | Display registration and repository status             |
| `--verify`             | Verify registry entries and repository state           |
| `--repos`              | List managed repositories                              |
| `--report`             | Regenerate the HTML report                             |
| `--tray`               | Open the Control Center                                |
| `--watch`              | Start the file-change watcher                          |
| `--schedule install`   | Install Windows scheduled tasks                        |
| `--schedule uninstall` | Remove scheduled tasks                                 |
| `--schedule status`    | Display scheduling status                              |
| `--forget NAME`        | Remove a repository from the registry                  |
| `--prune`              | Remove stale registry entries                          |
| `--version`            | Display the URGithub version                           |

Run:

```bash
python urgithub.py --help
```

for the command list supported by your installed version.

---

# 15. Configure Automatic Triggers

URGithub supports multiple trigger types.

## Startup

Run automatically when the user logs into Windows:

```text
startup
```

This executes the normal pipeline.

---

## Scheduled

Run periodically.

For example:

```text
every 3 hours
```

or another configured interval.

The exact interval should be configured through URGithub's configuration system.

---

## File Change

URGithub can monitor configured repository locations and trigger processing when relevant files change.

Git's internal `.git` directory should not be treated as ordinary source-file changes.

---

## Manual

You can always execute a run manually:

```bash
python urgithub.py --run manual
```

---

## Shutdown

Windows can invoke a shutdown-oriented quick-push when a user-initiated shutdown/restart event is detected.

This mode is intentionally constrained because Windows shutdown provides limited time for applications to finish work.

The shutdown operation should therefore be treated differently from a normal full synchronization.

---

# 16. Windows Scheduling

Windows users can install the supported scheduled tasks with:

```bash
python urgithub.py --schedule install
```

Check their status:

```bash
python urgithub.py --schedule status
```

Remove them:

```bash
python urgithub.py --schedule uninstall
```

Depending on the enabled configuration, scheduled integration can include:

```text
Windows logon
     ↓
URGithub startup trigger

Timer
     ↓
URGithub scheduled trigger

Windows shutdown event
     ↓
URGithub quick-push trigger
```

---

# 17. Linux Scheduling

Linux does not use Windows Task Scheduler.

Use your preferred operating-system scheduler.

For example:

```bash
python3 urgithub.py --run scheduled
```

You can invoke that command from `cron` or a `systemd` service/timer.

The important distinction is:

```text
Operating-system scheduler
          ↓
URGithub trigger
          ↓
Same URGithub engine
```

The scheduling mechanism changes, but the repository-processing engine should remain the same.

---

# 18. macOS Scheduling

macOS users can use `launchd` or `cron`.

For example:

```bash
python3 urgithub.py --run scheduled
```

The same URGithub processing pipeline is used after the operating-system scheduler launches the command.

---

# 19. Control Center

URGithub provides a Control Center GUI.

Launch it with:

```bash
python urgithub.py --tray
```

The GUI requires Python's `tkinter` support.

If the GUI does not start, verify that your Python installation includes Tk support.

On some Linux distributions, `tkinter` is packaged separately from the main Python installation.

---

# 20. File Watcher

Start the file watcher with:

```bash
python urgithub.py --watch
```

The watcher monitors configured repository locations for relevant changes.

The watcher should not implement a separate synchronization engine.

Instead:

```text
File change
    ↓
Trigger
    ↓
runner
    ↓
Discover
    ↓
Scan
    ↓
Validate
    ↓
Sync
    ↓
Report
```

This preserves the project's single-pipeline architecture.

---

# 21. Reports

URGithub generates a human-readable:

```text
report.html
```

The report is intended to provide an audit-friendly view of repository activity.

A run can contain information such as:

* repositories discovered
* repositories scanned
* repositories synchronized
* commits created
* pushes performed
* failures
* blocked operations
* security findings
* repository state
* before/after commit identifiers
* activity timeline

The report should be generated even when a run produces no changes or encounters failures.

This makes the report useful as an execution record rather than only a success page.

---

# 22. Journal

URGithub also maintains an append-oriented journal for machine-readable activity.

The journal is stored as JSONL.

Conceptually:

```text
event
event
event
event
event
```

Each event represents an operation or state transition.

This allows later tooling to analyze:

* when an operation occurred
* which repository was involved
* what trigger initiated it
* whether the operation succeeded
* what commit identifiers were involved
* whether the operation was blocked

Do not manually edit runtime journal files unless you understand the consequences.

---

# 23. Configuration

URGithub exposes configuration through the CLI.

Display configuration:

```bash
python urgithub.py --config
```

Read a value:

```bash
python urgithub.py --config triggers.every_hours
```

Set a value:

```bash
python urgithub.py --config triggers.every_hours 6
```

After changing scheduling-related settings, reapply the scheduler configuration:

```bash
python urgithub.py --schedule install
```

Always verify the resulting schedule:

```bash
python urgithub.py --schedule status
```

---

# 24. Recommended First-Run Procedure

For a new installation, use this sequence:

### Step 1 — Verify Python

```bash
python --version
```

### Step 2 — Verify Git

```bash
git --version
```

### Step 3 — Verify Git identity

```bash
git config --global user.name
git config --global user.email
```

### Step 4 — Verify GitHub CLI

```bash
gh --version
```

### Step 5 — Verify GitHub authentication

```bash
gh auth status
```

### Step 6 — Register

```bash
python urgithub.py --setup
```

### Step 7 — Scan

```bash
python urgithub.py --scan
```

### Step 8 — Inspect repositories

```bash
python urgithub.py --repos
```

### Step 9 — Verify

```bash
python urgithub.py --verify
```

### Step 10 — Run synchronization

```bash
python urgithub.py --sync
```

### Step 11 — Inspect the report

Open:

```text
report.html
```

### Step 12 — Configure automation

Windows:

```bash
python urgithub.py --schedule install
```

Linux/macOS:

Configure `cron`, `systemd`, or `launchd` to invoke the appropriate URGithub trigger.

---

# 25. Recommended Production Setup

For a machine containing important repositories, do not immediately enable every automatic trigger.

Use this progression:

```text
Stage 1
Manual scan
   ↓
Stage 2
Manual sync
   ↓
Stage 3
Verify reports
   ↓
Stage 4
Enable scheduled synchronization
   ↓
Stage 5
Enable file watching
   ↓
Stage 6
Enable startup integration
   ↓
Stage 7
Enable shutdown quick-push
```

This gives you an opportunity to validate the behavior before allowing automation to operate continuously.

---

# 26. What URGithub Should Never Be Expected To Do

URGithub is an automation and safety layer around Git operations.

It should not be treated as a replacement for:

* Git
* GitHub
* GitHub authentication
* repository backups
* source-control understanding
* code review
* release management

Automatic synchronization does not eliminate the need for good repository practices.

Important repositories should still have appropriate backups and recovery procedures.

---

# 27. Troubleshooting

## `python` is not recognized

Try:

```bash
python3 --version
```

If that works, use:

```bash
python3 urgithub.py ...
```

Otherwise install Python and ensure it is available through `PATH`.

---

## `git` is not recognized

Run:

```bash
git --version
```

If it fails, install Git and restart your terminal.

---

## `gh` is not recognized

Run:

```bash
gh --version
```

If it fails, install GitHub CLI and restart your terminal.

---

## GitHub authentication fails

Run:

```bash
gh auth status
```

If authentication is missing:

```bash
gh auth login
```

Then verify again:

```bash
gh auth status
```

---

## Git commit fails because identity is missing

Configure:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Then retry.

---

## A repository is not discovered

Check:

```bash
python urgithub.py --repos
```

Then:

```bash
python urgithub.py --verify
```

Confirm that:

* the folder exists
* it is a Git repository
* Git metadata is valid
* the remote is configured
* the repository is accessible

---

## Synchronization is blocked

Do not bypass the safety mechanism immediately.

First inspect the generated report:

```text
report.html
```

Look for:

* divergence
* detected secrets
* invalid repository state
* missing remote
* authorization failure
* repository access failure
* unsupported state

A blocked operation is often an intentional safety result.

---

## GUI does not open

Verify Python's Tk support.

```bash
python -c "import tkinter; print('tkinter OK')"
```

If this fails on Linux, install the appropriate Tk package for your distribution.

---

## Scheduled task does not run

On Windows:

```bash
python urgithub.py --schedule status
```

Then verify:

* the task exists
* the task is enabled
* Python is accessible
* the project path is correct
* the configured base directory exists
* the GitHub CLI authentication is available to the executing user

Run the underlying trigger manually first:

```bash
python urgithub.py --startup
```

If the manual trigger fails, fix that problem before debugging the scheduler.

---

# 28. Resetting a Registration

Before deleting URGithub runtime data, understand that configuration, registry information, journals, reports, and managed-repository metadata may be stored in the configured base location.

Do not delete the base directory simply to solve an individual repository problem.

Prefer the supported commands:

```bash
python urgithub.py --forget NAME
```

or:

```bash
python urgithub.py --prune
```

Use:

```bash
python urgithub.py --help
```

to confirm the commands supported by your installed version.

---

# 29. Removing Automatic Scheduling

Windows:

```bash
python urgithub.py --schedule uninstall
```

Then verify:

```bash
python urgithub.py --schedule status
```

Removing the scheduled tasks does **not** necessarily delete your repositories or runtime data.

It only removes the operating-system scheduling integration managed by URGithub.

---

# 30. Updating URGithub

Before updating:

1. Finish or stop active URGithub operations.
2. Verify repository state.
3. Review the current report.
4. Back up important configuration/runtime data if required.
5. Update the URGithub source code.
6. Run the version command.
7. Run the environment checks.
8. Perform a manual scan.
9. Perform a manual synchronization.
10. Reinstall/update scheduled integrations if required by the release.

Check the installed version:

```bash
python urgithub.py --version
```

After a major release, read the release notes before enabling automation again.

---

# 31. Security Recommendations

URGithub can interact with repositories containing valuable source code and credentials.

Follow these rules:

### Never commit credentials

Do not commit:

```text
.env
private keys
GitHub tokens
password files
cloud credentials
API keys
```

unless they are intentionally test values with no security impact.

### Protect the runtime directory

The URGithub base directory may contain operational information about your repositories.

Use normal operating-system permissions to restrict access where appropriate.

### Review blocked operations

If URGithub blocks a repository because of a security or repository-state check, investigate the reason instead of disabling the protection blindly.

### Use least privilege

Only grant the GitHub account and tools the permissions necessary for the repositories you intend to manage.

---

# 32. Architecture of a Normal Run

The important architectural concept is that different triggers should converge into one engine.

```text
                ┌──────────────┐
                │   Startup    │
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │   Schedule   │
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │ File Change   │
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │    Manual    │
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │   Shutdown   │
                └──────┬───────┘
                       │
                       ▼
              ┌─────────────────┐
              │  SINGLE RUNNER  │
              └────────┬────────┘
                       ▼
                 DISCOVER
                       ▼
                    SCAN
                       ▼
                  VALIDATE
                       ▼
                     SYNC
                       ▼
                   COMMIT
                       ▼
                    PUSH
                       ▼
                   VERIFY
                       ▼
                  JOURNAL
                       ▼
               report.html
```

The advantage of this architecture is consistency: a trigger should select **when** the operation starts, not create a second implementation of the Git synchronization logic.

---

# 33. Understanding the Safety Boundary

URGithub separates:

```text
TRIGGER
```

from:

```text
REPOSITORY OPERATION
```

A trigger means:

> "Start a run."

It does not mean:

> "Immediately push everything."

The run must pass through the project's safety pipeline.

Conceptually:

```text
Trigger
  ↓
Discover
  ↓
Scan
  ↓
Security checks
  ↓
Repository-state validation
  ↓
Determine safe action
  ↓
Sync
  ↓
Commit
  ↓
Push
  ↓
Verify
  ↓
Report
```

This distinction is central to the project's design.

---

# 34. Before Asking for Help

When reporting a problem, include:

```text
Operating system:
Python version:
Git version:
GitHub CLI version:
URGithub version:
Trigger used:
Command executed:
Expected behavior:
Actual behavior:
Relevant report.html information:
Relevant error output:
```

Do not include:

* GitHub tokens
* passwords
* private keys
* personal access tokens
* secrets
* private repository contents

Redact sensitive information before opening an issue.

---

# 35. Quick Verification Checklist

After installation, all of the following should be true:

```text
[ ] Python 3.10+ installed
[ ] Git installed
[ ] Git identity configured
[ ] GitHub CLI installed
[ ] GitHub CLI authenticated
[ ] Required repository access available
[ ] URGithub registered
[ ] Base directory created
[ ] Repositories discovered
[ ] Initial scan successful
[ ] Repository verification successful
[ ] First synchronization completed
[ ] report.html generated
[ ] Scheduled triggers tested
[ ] Control Center tested
[ ] File watcher tested if enabled
```

A production installation should not be considered complete until the manual workflow succeeds.

---

# 36. Minimal Setup

If you already have Python, Git, and GitHub CLI configured:

```bash
git clone https://github.com/learnerforge/push-to-github.git
cd push-to-github
python urgithub.py --setup-all
```

Then verify:

```bash
python urgithub.py --status
```

Run a scan:

```bash
python urgithub.py --scan
```

Run the first synchronization:

```bash
python urgithub.py --sync
```

Finally inspect:

```text
report.html
```

---

# 37. Setup Philosophy

URGithub deliberately separates **installation**, **registration**, **scanning**, **validation**, and **synchronization**.

The intended relationship is:

```text
Installation
    ≠
Registration
    ≠
Scanning
    ≠
Synchronization
```

This prevents a newly installed tool from immediately making uncontrolled repository changes.

The safest first interaction with a new machine is therefore:

```text
INSTALL
   ↓
CHECK
   ↓
REGISTER
   ↓
SCAN
   ↓
VERIFY
   ↓
SYNC
   ↓
AUTOMATE
```

That is the recommended URGithub setup path.
