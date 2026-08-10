import time
from datetime import datetime, timezone

from . import gitops
from .config import Config
from .discovery import Discovery
from .journal import Journal, utcnow
from .lock import RunLock
from .logs import setup_logging
from .registry import Registry
from .report import Reporter
from .scan import Scanner
from .sync import SyncEngine

TRIGGERS = {
    "--startup": "startup",
    "--scan": "manual_scan",
    "--sync": "manual_sync",
    "--shutdown": "shutdown",
}

INTERACTIVE_TRIGGERS = ("manual_scan", "manual_sync")


def _light_env_check(paths):
    git_ok = gitops.run_git(["--version"]).returncode == 0
    gh_ok = gitops.run_gh(["auth", "status"]).returncode == 0
    base_ok = bool(paths) and paths.base_location.is_dir()
    return git_ok, gh_ok, base_ok


def _journal_phase(log, journal, run_id, trigger, phase, outcome, detail=None):
    record = {
        "ts": utcnow(),
        "run_id": run_id,
        "trigger": trigger,
        "phase": phase,
        "outcome": outcome,
    }
    if detail:
        record["detail"] = detail
    journal.write(record)


def _drift_warnings(cfg):
    snapshot = cfg.get("environment_snapshot", {})
    if not snapshot:
        return []
    warnings = []
    version = gitops.run_git(["--version"]).stdout.strip()
    if version and snapshot.get("git", {}).get("version") and version != snapshot["git"]["version"]:
        warnings.append(f"Git version changed: {snapshot['git']['version']} → {version}")
    name = gitops.run_git(["config", "--global", "user.name"]).stdout.strip()
    email = gitops.run_git(["config", "--global", "user.email"]).stdout.strip()
    if name and snapshot.get("identity", {}).get("name") and name != snapshot["identity"]["name"]:
        warnings.append(f"Git identity name changed: {snapshot['identity']['name']} → {name}")
    if email and snapshot.get("identity", {}).get("email") and email != snapshot["identity"]["email"]:
        warnings.append(f"Git identity email changed: {snapshot['identity']['email']} → {email}")
    return warnings


def _sync_events(results, registry=None):
    events = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for r in results:
        entry = registry.get(r.repo, {}) if registry else {}
        url = entry.get("url", "")
        if r.action == "pushed":
            events.append({
                "type": "pushed",
                "repo": r.repo,
                "timestamp": now,
                "url": url,
                "detail": f"{r.before_sha}..{r.after_sha} ({len(r.changed)} files)",
            })
        elif r.action == "failed":
            events.append({"type": "failed", "repo": r.repo, "timestamp": now, "url": url, "detail": r.reason})
        elif r.action == "blocked":
            events.append({"type": "blocked", "repo": r.repo, "timestamp": now, "url": url, "detail": r.reason})
        elif r.action == "skipped":
            events.append({"type": "skipped", "repo": r.repo, "timestamp": now, "url": url, "detail": r.reason})
    return events


def _run_pipeline(log, journal, run_id, trigger, paths, cfg, interactive):
    started = time.time()

    discovery = Discovery(cfg, journal, log, run_id, trigger, interactive=interactive)
    events = discovery.run()
    registry = discovery.registry

    scanner = Scanner(cfg, journal, log, run_id, trigger, interactive=interactive)
    scan_results = []
    for name, entry in registry.data.items():
        if entry.get("status") in ("quarantined", "deleted"):
            continue
        result = scanner.scan_repo(name, entry)
        entry["last_scan_sha"] = result.head_sha
        scan_results.append(result)
        log.info("Scan [%s] → %s", name, result.status)
    registry.save()

    outcome = "clean"
    sync_results = []

    if trigger == "shutdown":
        sync = SyncEngine(cfg, journal, log, run_id, trigger, interactive=interactive)
        timeout = int(cfg.get("shutdown", {}).get("timeout_seconds", 30))
        for name, entry in registry.data.items():
            if entry.get("status") != "active":
                continue
            sync_results.append(sync.quick_push(name, entry, timeout))
        outcome = _outcome(sync_results)

    elif trigger != "manual_scan":
        log.info("Phase 4 — sync/commit/push")
        sync = SyncEngine(cfg, journal, log, run_id, trigger, interactive=interactive)
        sync_results = sync.run(scan_results, registry)
        for r in sync_results:
            entry = registry.get(r.repo)
            if entry and r.action == "pushed":
                entry["last_sync_sha"] = r.after_sha
                entry["diverged_since"] = None
            elif entry and r.action == "blocked" and r.reason.startswith("divergence"):
                entry["diverged_since"] = entry.get("diverged_since") or utcnow()
            elif entry and r.action != "blocked":
                entry["diverged_since"] = None
        registry.save()
        events += _sync_events(sync_results, registry)
        outcome = _outcome(sync_results)

    duration = time.time() - started
    drift = _drift_warnings(cfg)
    if drift:
        _journal_phase(log, journal, run_id, trigger, "drift", "warning", {"items": drift})
        log.warning("Environment drift detected: %s", "; ".join(drift))

    reporter = Reporter(cfg, log, run_id, trigger, interactive=interactive)
    try:
        reporter.generate(events, sync_results, registry, duration, outcome, drift=drift, scan_results=scan_results)
        reporter.show(outcome)
    except Exception as exc:
        log.error("Report generation failed: %s", exc)
        _journal_phase(log, journal, run_id, trigger, "report", "failed",
                       {"error": str(exc)[:200]})

    _journal_phase(log, journal, run_id, trigger, "engine", outcome, {
        "duration_s": round(duration, 2),
        "scanned": len(scan_results),
        "synced": sum(1 for r in sync_results if r.action in ("pushed", "committed", "clean")),
        "blocked": sum(1 for r in sync_results if r.action == "blocked"),
        "failed": sum(1 for r in sync_results if r.action == "failed"),
    })
    return outcome


def _outcome(results):
    if any(r.action == "failed" for r in results):
        return "failed"
    if any(r.action == "blocked" for r in results):
        return "partial"
    if any(r.action in ("pushed", "committed") for r in results):
        return "ok"
    return "clean"


def run_trigger(trigger, interactive=None):
    cfg = Config.load()
    if not cfg.registered:
        print("URGithub is not registered. Run: python urgithub.py --setup")
        return 1
    paths = cfg.paths
    paths.ensure_all()
    log = setup_logging(paths)
    journal = Journal(paths.journal)
    lock = RunLock(paths.run_lock)

    if not lock.acquire():
        journal.write({
            "ts": utcnow(),
            "run_id": None,
            "trigger": trigger,
            "phase": "run-skip",
            "outcome": "skipped",
            "detail": {"reason": "lock held"},
        })
        log.info("Skipped [%s] — lock held by another run", trigger)
        return 0

    run_id = journal.open_run(trigger)
    log.info("Run started [%s] run_id=%s", trigger, run_id)
    try:
        git_ok, gh_ok, base_ok = _light_env_check(paths)
        if not (git_ok and gh_ok and base_ok):
            _journal_phase(log, journal, run_id, trigger, "env-check", "env_fail",
                           {"git": git_ok, "github_auth": gh_ok, "base_location": base_ok})
            log.error("Environment check failed [git=%s github_auth=%s base_location=%s] — aborting",
                      git_ok, gh_ok, base_ok)
            return 1

        log.info("Environment check passed [git=%s github_auth=%s base_location=%s]",
                 git_ok, gh_ok, base_ok)

        if interactive is None:
            interactive = trigger in INTERACTIVE_TRIGGERS
        outcome = _run_pipeline(log, journal, run_id, trigger, paths, cfg, interactive)

        journal.close_run(run_id, trigger, outcome)
        log.info("Run finished [%s] run_id=%s outcome=%s", trigger, run_id, outcome)
        return 0
    finally:
        lock.release()


def run_operation(flag):
    return run_trigger(TRIGGERS[flag])
