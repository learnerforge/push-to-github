# Automation: Triggers & Scheduling

URGithub is driven by triggers. Every trigger — startup, shutdown, a timer, a file change, a button — enters the exact same pipeline: `DISCOVER → SCAN → SECURITY → VALIDATE → SYNC → COMMIT → PUSH → JOURNAL → REPORT`.

## Trigger types

| Trigger | Config key | Notes |
|---|---|---|
| Login / startup | `triggers.startup` | Runs when you log in |
| Scheduled repeat | `triggers.every_hours` / `every_minutes` | e.g. `3` = every 3 hours |
| Daily at a time | `triggers.at_time` | e.g. `"18:00"` |
| File change | `triggers.file_change` | Watches `config.json`, base folder, local repos |
| Shutdown quick-push | `triggers.shutdown` | Windows only — push pending work before shutdown |
| Manual | `triggers.manual` | Control Center button / CLI |

## Windows — Task Scheduler

The `--schedule` family installs and manages everything through Windows Task Scheduler:

```bash
python urgithub.py --schedule install
python urgithub.py --schedule status
python urgithub.py --schedule uninstall
```

It creates tasks such as:

- **Run at logon** — starts URGithub when you sign in.
- **Scheduled runs** — every N hours, at a daily time, or every N minutes, aligned to your trigger settings.
- **Shutdown quick-push** — a *PowerShell window opens briefly and pushes pending changes* before shutdown (requires admin privileges; the installer triggers a UAC prompt).

### Resident scheduler (Windows)

Running URGithub from the system tray (`--tray` or the Control Center) starts a resident scheduler that repeats the run interval *while the app is running*, complementing the Task Scheduler tasks.

### Resident scheduler (Linux / macOS)

URGithub is a regular process. Run it from the terminal, or supervise it so it stays alive and the resident scheduler keeps repeating at your configured interval.

## Linux — cron / systemd

Add a cron entry using the absolute path to the CLI:

```bash
crontab -e
```

```cron
# every 3 hours
0 */3 * * * cd /home/you/push-to-github && /usr/bin/python3 urgithub.py --run scheduled

# at 18:00 daily
0 18 * * * cd /home/you/push-to-github && /usr/bin/python3 urgithub.py --run scheduled
```

Alternative: a `systemd` timer unit calling the same `--run scheduled` entry point.

## macOS — launchd / cron

Use a `launchd` plist (the `StartInterval` key repeats every N seconds) or plain cron, both calling `python3 urgithub.py --run scheduled` with the absolute path to `urgithub.py`.

## Shutdown quick-push

> **Windows only.** During shutdown, URGithub pushes pending changes within a short time budget (`shutdown.timeout_seconds`, default 30s). It never delays the machine indefinitely and does not open the report by default (`shutdown.open_report`).

## Best practices

- Use absolute paths in cron / launchd entries — scheduled runs have no terminal PATH.
- Keep `every_minutes` at `0` unless you need sub-hour runs.
- After any `triggers.*` change, reinstall the scheduler: `--schedule install`, then `--schedule status`.
- All triggers share one pipeline and one report — scheduled runs are never "weaker" than manual ones.

Next: [Security](security.md) — what the safety model blocks and why.
