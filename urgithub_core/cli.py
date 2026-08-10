import argparse
import json

from . import runner
from .config import Config
from .registry import Registry

RUN_FLAGS = ["--startup", "--scan", "--sync", "--shutdown"]

TRIGGER_HELP = (
    "run any trigger through the universal pipeline: startup, scheduled, "
    "at_time, file_change, event_hook, manual, manual_scan, manual_sync"
)

SCHEDULE_ACTIONS = ["install", "uninstall", "status"]


def build_parser():
    parser = argparse.ArgumentParser(
        prog="urgithub",
        description="URGithub — universal Git repository operations manager.",
    )
    parser.add_argument("--setup", action="store_true", help="run the one-time registration wizard")
    parser.add_argument("--setup-all", action="store_true",
                        help="full setup in one command: register (if needed) + install schedule + first run + status")
    parser.add_argument("--startup", action="store_true", help="startup trigger (full pipeline)")
    parser.add_argument("--scan", action="store_true", help="manual scan only")
    parser.add_argument("--sync", action="store_true", help="manual full sync (scan -> validate -> sync -> report)")
    parser.add_argument("--shutdown", action="store_true", help="quick push before shutdown")
    parser.add_argument("--status", action="store_true", help="show registration and repo status")
    parser.add_argument("--verify", action="store_true", help="verify all registry entries")
    parser.add_argument("--repos", action="store_true", help="list managed repositories")
    parser.add_argument("--report", action="store_true", help="generate report.html from a fresh scan")
    parser.add_argument("--config", nargs="*", metavar="KEY [VALUE]",
                        help="get a config value (dotted key) or set it: --config triggers.every_hours 3")
    parser.add_argument("--run", metavar="TRIGGER", help=TRIGGER_HELP)
    parser.add_argument("--schedule", nargs="?", const="status", choices=SCHEDULE_ACTIONS,
                        metavar="ACTION",
                        help="manage Windows Task Scheduler tasks (install | uninstall | status)")
    parser.add_argument("--watch", action="store_true",
                        help="run the file-change watcher (blocks; fires file_change trigger)")
    parser.add_argument("--tray", action="store_true",
                        help="open the Control Center GUI (resident timer + watcher + buttons)")
    parser.add_argument("--gui", action="store_true",
                        help="open the Control Center GUI (default when no arguments are given)")
    parser.add_argument("--forget", metavar="NAME",
                        help="remove one repository from the registry (no disk changes)")
    parser.add_argument("--prune", action="store_true",
                        help="remove all stale registry entries (missing/deleted/quarantined)")
    parser.add_argument("--yes", action="store_true", help="answer yes to confirmation prompts")
    parser.add_argument("--version", action="store_true", help="show version")
    return parser


def _dig(data, dotted, default=None):
    node = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def _set_key(data, dotted, value):
    parts = dotted.split(".")
    node = data
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value


def _coerce(raw):
    lowered = raw.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    try:
        if "." in raw or "e" in lowered:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def cmd_config(args):
    cfg = Config.load()
    if not args.config:
        print(json.dumps(cfg._data, indent=2, ensure_ascii=False))
        return 0
    key = args.config[0]
    if len(args.config) == 1:
        value = _dig(cfg._data, key, "__missing__")
        if value == "__missing__":
            print(f"Key not found: {key}")
            return 1
        if isinstance(value, dict):
            print(json.dumps(value, indent=2, ensure_ascii=False))
        else:
            print(value)
        return 0
    if len(args.config) > 2:
        print("Usage: --config KEY VALUE  (one key and one value)")
        return 1
    _set_key(cfg._data, key, _coerce(args.config[1]))
    cfg.save()
    print(f"Set {key} = {_dig(cfg._data, key)!r}")
    if key.startswith("triggers."):
        print("Hint: re-run  python urgithub.py --schedule install  to apply trigger changes.")
    return 0


def cmd_schedule(action):
    cfg = Config.load()
    if not cfg.registered:
        print("URGithub: not registered. Run: python urgithub.py --setup")
        return 1
    cfg.paths.ensure_all()
    from . import scheduler
    from .logs import setup_logging

    log = setup_logging(cfg.paths)
    if action == "install":
        ok = scheduler.install(cfg, log)
        print("Schedule install: " + ("OK" if ok else "FAILED"))
        return 0 if ok else 1
    if action == "uninstall":
        ok = scheduler.uninstall(log)
        print("Schedule uninstall: " + ("OK" if ok else "FAILED"))
        return 0 if ok else 1
    rows = scheduler.status(log)
    if not rows:
        print("No URGithub tasks registered.")
        return 0
    for name, state, next_run in rows:
        print(f"{name}  [{state}]" + (f"  next: {next_run}" if next_run else ""))
    return 0


def cmd_setup_all():
    """One-command setup: register (if needed) → install schedule → first run → status."""
    from . import runner
    from . import scheduler
    from .logs import setup_logging

    cfg = Config.load()
    if not cfg.registered:
        print("Step 1/4 — registration")
        from .wizard import run_wizard

        base = run_wizard()
        if not base:
            print("Setup cancelled.")
            return 1
        cfg = Config.load()
        print(f"Registered. Base location: {base}")

    cfg.paths.ensure_all()
    log = setup_logging(cfg.paths)
    print("Step 2/4 — deploy launchers + install scheduled tasks")
    ok = scheduler.install(cfg, log)
    if not ok:
        print("  The shutdown task needs elevation — retrying with a UAC prompt...")
        if scheduler.elevate_shutdown(cfg, log):
            ok = True
        else:
            print("  Shutdown task skipped (declined). You can run later from an elevated prompt.")
    print("  Schedule install: " + ("OK" if ok else "PARTIAL"))

    print("Step 3/4 — first run (discover → scan → validate → sync → report)")
    run_rc = runner.run_trigger("startup")

    print("Step 4/4 — schedule status")
    cmd_schedule("status")
    print()
    print("Setup complete.")
    print(f"  Base:      {cfg.paths.base_location}")
    print(f"  Config:    {cfg.paths.config}")
    print(f"  Launchers: {cfg.paths.run}")
    return 0 if (ok and run_rc == 0) else 1


def cmd_watch():
    cfg = Config.load()
    if not cfg.registered:
        print("URGithub: not registered. Run: python urgithub.py --setup")
        return 1
    cfg.paths.ensure_all()
    from . import watch
    from .logs import setup_logging

    log = setup_logging(cfg.paths)
    watch.run_watcher(cfg, log)
    return 0


def cmd_gui():
    from .gui import run_control_center

    return run_control_center()


def cmd_status():
    cfg = Config.load()
    if not cfg.registered:
        print("URGithub: not registered. Run: python urgithub.py --setup")
        return 1
    paths = cfg.paths
    print(f"Base location: {paths.base_location}")
    print(f"Registered:    {cfg.get('registered_at')}")
    snapshot = cfg.get("environment_snapshot", {})
    git = snapshot.get("git", {})
    identity = snapshot.get("identity", {})
    github = snapshot.get("github", {})
    print(f"Git version:   {git.get('version', '')}")
    print(f"Identity:      {identity.get('name', '')} <{identity.get('email', '')}>")
    print(f"GitHub:        {github.get('login', '')} (authenticated={github.get('authenticated', False)})")
    registry = Registry(paths.registry).load()
    print(f"Managed repos: {len(registry)}")
    for name in sorted(registry.data):
        entry = registry.data[name]
        print(f"  {name}  {entry.get('status', '?')}  {entry.get('url', '')}")
    return 0


def cmd_repos():
    cfg = Config.load()
    if not cfg.registered:
        print("URGithub: not registered. Run: python urgithub.py --setup")
        return 1
    registry = Registry(cfg.paths.registry).load()
    if not registry.data:
        print("No repositories in registry.")
        return 0
    for name in sorted(registry.data):
        entry = registry.data[name]
        print(f"{name}\t{entry.get('status', '?')}\t{entry.get('url', '')}")
    return 0


def cmd_verify():
    cfg = Config.load()
    if not cfg.registered:
        print("URGithub: not registered. Run: python urgithub.py --setup")
        return 1
    from pathlib import Path

    from . import gitops

    registry = Registry(cfg.paths.registry).load()
    errors = 0
    print("Verifying registry entries...")
    for name in sorted(registry.data):
        entry = registry.data[name]
        path = Path(entry.get("path", ""))
        problems = []
        if not path.is_dir():
            problems.append("folder missing")
        elif not (path / ".git").exists():
            problems.append("not a git repository")
        else:
            remote = gitops.run_git(["remote", "get-url", "origin"], cwd=path, timeout=15)
            if remote.returncode != 0:
                problems.append("no origin remote")
        status = entry.get("status", "?")
        if problems:
            errors += 1
            print(f"  {name}  [{status}]  PROBLEM: {', '.join(problems)}")
        else:
            print(f"  {name}  [{status}]  OK")
    if errors:
        print(f"{errors} problem(s) found.")
        return 1
    print("All entries OK.")
    return 0


def cmd_forget(args):
    cfg = Config.load()
    if not cfg.registered:
        print("URGithub: not registered. Run: python urgithub.py --setup")
        return 1
    registry = Registry(cfg.paths.registry).load()
    if args.forget not in registry.data:
        print(f"Not in registry: {args.forget}")
        return 1
    if not args.yes:
        from . import prompt

        if not prompt.confirm(f"Forget '{args.forget}' from the registry?", interactive=True):
            print("Cancelled.")
            return 1
    registry.remove(args.forget)
    registry.save()
    print(f"Forgot {args.forget} (folder left on disk as-is).")
    return 0


STALE_STATUSES = ("missing", "LOCAL_MISSING", "quarantined", "deleted")


def cmd_prune(args):
    cfg = Config.load()
    if not cfg.registered:
        print("URGithub: not registered. Run: python urgithub.py --setup")
        return 1
    registry = Registry(cfg.paths.registry).load()
    stale = [name for name, entry in registry.data.items()
             if entry.get("status") in STALE_STATUSES]
    if not stale:
        print("No stale entries to prune.")
        return 0
    print("Stale entries: " + ", ".join(sorted(stale)))
    if not args.yes:
        from . import prompt

        if not prompt.confirm(
            f"Remove {len(stale)} stale entr{'y' if len(stale) == 1 else 'ies'}?",
            interactive=True,
        ):
            print("Cancelled.")
            return 1
    for name in stale:
        registry.remove(name)
    registry.save()
    print(f"Pruned {len(stale)} entr{'y' if len(stale) == 1 else 'ies'}.")
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.version:
        from . import __version__

        print(f"URGithub {__version__}")
        return 0

    if args.setup:
        from .wizard import run_wizard

        return 0 if run_wizard() else 1

    if args.setup_all:
        return cmd_setup_all()

    if args.tray or args.gui:
        return cmd_gui()

    if args.watch:
        return cmd_watch()

    if args.forget:
        return cmd_forget(args)

    if args.prune:
        return cmd_prune(args)

    if args.config is not None:
        return cmd_config(args)

    if args.schedule is not None:
        return cmd_schedule(args.schedule)

    if args.run:
        return runner.run_trigger(args.run)

    for flag in RUN_FLAGS:
        if getattr(args, flag.lstrip("-")):
            return runner.run_operation(flag)

    if args.status:
        return cmd_status()

    if args.repos:
        return cmd_repos()

    if args.verify:
        return cmd_verify()

    if args.report:
        return runner.run_operation("--scan")

    return cmd_gui()
