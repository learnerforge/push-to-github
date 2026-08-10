import time

from . import runner


def _snapshot(repos_dir):
    """Map of {relative_path: (mtime, size)} for every file under repos_dir.

    Dot-directories (`.git`, `.idea`, ...) and dot-files are ignored so the
    watcher reacts to real content changes, not git-internal churn.
    """
    snap = {}
    if not repos_dir.is_dir():
        return snap
    for path in repos_dir.rglob("*"):
        if any(part.startswith(".") for part in path.parts):
            continue
        if path.is_file():
            try:
                stat = path.stat()
            except OSError:
                continue
            snap[str(path.relative_to(repos_dir))] = (stat.st_mtime, stat.st_size)
    return snap


def _changed(before, after):
    return len(before) != len(after) or any(before.get(k) != v for k, v in after.items())


def run_watcher(cfg, log, interval=10, debounce=30):
    """Poll for changes under the 'repos in github' folder and fire the file_change trigger.

    Changes are debounced (default 30s of quiet) before firing so that a burst of
    writes settles into a single pipeline run. Blocks until KeyboardInterrupt.
    """
    paths = cfg.paths
    paths.ensure_all()
    previous = _snapshot(paths.repos)
    pending_since = None
    log.info("File watcher started on %s (interval=%ss, debounce=%ss)",
             paths.repos, interval, debounce)
    try:
        while True:
            time.sleep(interval)
            current = _snapshot(paths.repos)
            if _changed(previous, current):
                if pending_since is None:
                    pending_since = time.time()
                    log.info("Change detected — debouncing for %ss", debounce)
                elif time.time() - pending_since >= debounce:
                    log.info("Debounce elapsed — firing file_change trigger")
                    previous = current
                    pending_since = None
                    runner.run_trigger("file_change")
            else:
                pending_since = None
    except KeyboardInterrupt:
        log.info("File watcher stopped")
