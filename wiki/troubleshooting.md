# Troubleshooting

## Python is not recognized

```bash
python --version   # or python3, or py -3
```

- Install Python 3.10+ from python.org or `winget install Python.Python.3.12`.
- Restart the terminal so `PATH` updates.
- If only `python3` is available (Linux/macOS), use `python3` in every command.

## Git is not recognized

```bash
git --version
```

Install Git and restart the terminal. URGithub runs Git through the `PATH`.

## GitHub CLI is not recognized

```bash
gh --version
```

Install GitHub CLI (`winget install GitHub.cli`, `apt install gh`, or `brew install gh`) and restart the terminal.

## Authentication check fails

```bash
gh auth status
```

If not logged in, authenticate:

```bash
gh auth login
```

The setup wizard's authentication step must report that you are logged in successfully. Choose the login flow that matches your setup (device flow for SSH/remote sessions).

## Commits fail with "user.name" / "user.email"

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Git refuses to commit without an identity.

## Synchronization is blocked

**Do not bypass the safety mechanism immediately.** First inspect `report.html` and check for:

- divergence
- detected secrets
- invalid repository state
- missing remote
- authorization failure
- repository access failure
- unsupported state

A blocked operation is often an **intentional safety result**. Resolve the cause — e.g. remove the secret file, fix the remote, or review a divergence manually — then rerun. For diverged repos, resolve the merge yourself; URGithub never does it for you.

## GUI does not open

```bash
python -c "import tkinter; print('tkinter OK')"
```

If this fails on Linux, install the Tk package for your distribution (e.g. `python3-tk`). The wizard and Control Center require `tkinter`.

## Scheduled task does not run (Windows)

```bash
python urgithub.py --schedule status
```

Reinstall the schedule and check the registered tasks:

```bash
python urgithub.py --schedule install
```

The shutdown quick-push task requires admin rights — run the install that triggers the UAC prompt. Confirm the tasks appear in Task Scheduler and that the Python path stored in the task is correct.

## Scheduled run fails on Linux/macOS

Cron and launchd jobs run with no terminal `PATH`. Use absolute paths:

```bash
0 */3 * * * cd /home/you/push-to-github && /usr/bin/python3 urgithub.py --run scheduled
```

Confirm the real interpreter path with `which python3`.

## Missing repositories

- Run `python urgithub.py --scan` then `python urgithub.py --repos` to see what is discovered.
- Reconciles against `gh repo list` — check the `github_owner` setting and `gh auth status`.
- Forked repos are skipped when `skip_forks` is enabled.
- New clones require `clone_missing_repos` to be enabled (default).

## Reporting a problem

Open `report.html` for the failed run and include:

- the trigger that started the run
- the repositories and operations involved
- the failure / blocked reason from the report
- relevant journal entries (`journal.jsonl`)
- your platform and Python/Git/gh versions

Back to [Home](index.md).
