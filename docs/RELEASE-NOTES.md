# URGithub — Release notes

Draft release notes for publishing on GitHub Releases. Create the actual
release with `gh release create` (see [URGITHUB-TASKS.md](URGITHUB-TASKS.md),
item A12).

---

## v1.0.0

**URGithub — the safe, automatic Git repository manager for your local
machine.**

Universal Git repository management for Windows. It discovers every repository
under `repos in github\`, reconciles it with your GitHub account, scans each
one through a 23-point inspection, blocks anything unsafe, synchronizes the
rest, and writes a dark-theme HTML activity report after every run.

Highlights:

- **Automatic discovery + first-run clone-all** — the first run clones your
  entire GitHub account, private repos and forks included (unless
  `skip_forks`), into `repos in github\`.
- **Secret detection** — filename globs and content regexes. A secret stops
  that repo cold; nothing with a `.env` or a hard-coded key ever gets pushed.
- **Divergence protection** — a diverged repo is blocked, never clobbered.
- **Safe sync** — fetch + fast-forward-only pull, commit/push per policy.
  Never `reset`, `--force`, `rebase` or `clean`.
- **Startup / shutdown / scheduled triggers** — Windows Task Scheduler runs it
  at logon, on a repeating timer, and quick-pushes before shutdown.
- **File-change triggering** — a debounced watcher fires a full run when your
  repos folder changes.
- **HTML reporting** — every run writes `report.html` (atomic write +
  timestamped archive): stat cards, activity timeline, per-repo details,
  per-file last-commit dates, security & size findings, environment drift.
- **Repository quarantine** — repos confirmed deleted on GitHub are moved to
  `deleted repos\`, only with your confirmation.
- **Full audit trail** — append-only JSONL journal with before/after SHAs.
- **Control Center GUI** — dashboard, repository list, schedule, settings,
  logs and help, with a resident timer and streaming log.
- **No third-party Python dependencies** — pure standard library, no build
  step.

**Platform support:** the engine, registration wizard, Control Center GUI and
file watcher run on **Windows, Linux and macOS** (Python 3.10+ with tkinter).
The **Windows-only** features are the Task Scheduler tasks (startup / timer /
shutdown), the shutdown quick-push (EventID 1074) and Windows toasts. On
Linux/macOS, schedule runs with your own `cron` / `systemd` / `launchd` calling
`python3 urgithub.py --run scheduled`.

Requirements: Python 3.10+ (with tkinter) · Git · GitHub CLI (`gh`)
authenticated with the `repo` scope.

Quick start:

```powershell
python urgithub.py --setup-all
```

Full guide: [SETUP.md](../SETUP.md)

**Assets (TBD):** `URGithub-Setup.exe` when the installer build is added
([URGITHUB-TASKS.md](URGITHUB-TASKS.md), item A11).
