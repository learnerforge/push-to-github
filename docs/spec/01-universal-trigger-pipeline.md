# Detail 1 — The Universal Trigger Pipeline

## Purpose

Every trigger enters **one and only one** pipeline. There is never a second implementation of synchronization. Whether the run was started by Windows logon, a timer, a file change, the shutdown event, a launcher `.bat`, or a GUI button, the code path through `runner.run_trigger()` → `_run_pipeline()` is identical.

## Triggers (config-driven, combinable)

| Trigger | When it fires | How it reaches the pipeline |
|---------|---------------|-----------------------------|
| `startup` | Windows logon (scheduled task `URGithub-startup`) or `--startup` | `run_trigger("startup")` |
| `shutdown` | User-initiated shutdown/restart/logoff (EventID 1074, scheduled task `URGithub-shutdown`, 10 s delay, SYSTEM, network-only, 2 min cap) or `--shutdown` | `run_trigger("shutdown")` — **special case**, see below |
| `scheduled` | `every_hours` / `every_minutes` repeating task (`URGithub-scheduled`) | `run_trigger("scheduled")` |
| `at_time` | A specific time daily (same `URGithub-scheduled` task, `/ST HH:MM`) | `run_trigger("scheduled")` |
| `file_change` | Debounced change under `repos in github\` (watcher) | `run_trigger("file_change")` |
| `manual` | `--run manual`, launcher, or control panel | `run_trigger("manual")` |
| `manual_scan` / `manual_sync` | Control panel buttons / tray | `run_trigger("manual_scan"\|"manual_sync")` |
| `event_hook` | *(roadmap)* webhook/email | same entry point |

Flag→trigger mapping (`cli.py`):

```
--startup   → run_operation("--startup")  → run_trigger("startup")
--scan      → run_operation("--scan")     → run_trigger("manual_scan")
--sync      → run_operation("--sync")     → run_trigger("manual_sync")
--shutdown  → run_operation("--shutdown") → run_trigger("shutdown")
--report    → run_operation("--scan")     → run_trigger("manual_scan")   (report is regenerated from a fresh scan)
--run <t>   → run_trigger(<t>)            → any named trigger
```

Two triggers are "interactive" (`INTERACTIVE_TRIGGERS`): `manual_scan` and `manual_sync`. Interactive runs open `report.html` in the browser instead of sending a toast.

## The pipeline — `run_trigger(trigger)` / `_run_pipeline(...)`

### Gate chain (`run_trigger`, `runner.py`)

```
0.  REGISTRATION GATE (Rule 0)
      Config.load().registered != true
        → print "URGithub is not registered. Run: python urgithub.py --setup" → exit 1
1.  ENSURE STRUCTURE
      paths.ensure_all() → create all folders if missing
2.  LOGGING
      setup_logging(paths) → application.log + error.log + console
3.  JOURNAL OPEN
      journal.open_run(trigger) → run_id (uuid4 hex[:8]); write phase=run-start
4.  GLOBAL LOCK (never queues)
      RunLock(paths.run_lock, stale_seconds=15).acquire()
        → already held and fresh → journal "run-skip / skipped / lock held"
          → log "Skipped [trigger] — lock held by another run" → exit 0
        → held but stale (>15 s) → steal the lock
5.  LIGHT ENV CHECK (Detail 0)
      git --version rc · gh auth status rc · base_location is_dir
        → any failure → journal phase=env-check outcome=env_fail → exit 1
6.  RUN THE PIPELINE (below)
7.  CLOSE JOURNAL RUN
      journal.close_run(run_id, trigger, outcome) → phase=run-end
8.  RELEASE LOCK
      finally: lock.release()
```

### The pipeline itself (`_run_pipeline`, `runner.py`)

```
started = time.time()

DISCOVER  (Discovery(cfg, journal, log, run_id, trigger).run())
    · list GitHub repos:  gh repo list <owner> --limit 1000 --json nameWithOwner,url,isFork
    · discover local:     every folder in "repos in github\" with a valid .git
                          → registry entry (create or adopt); update path/last_seen/url
    · reconcile:          repos missing from GitHub → quarantine workflow (Detail 0);
                          renamed on GitHub → rename local folder + entry (Detail 0)
    · bootstrap seed:     every GitHub repo NOT in the registry → seeded as missing
                          (first-run clone-all; forks excluded only if skip_forks)
    · clone missing:      registry status missing/LOCAL_MISSING + clone_missing_repos
                          → gh repo clone <owner>/<name> (git clone <url> fallback)
                          → <base>\urgithub\repos in github\<name>
    · mark missing:       entries whose recorded path no longer exists → status missing
    → returns events[]     (discovered/cloned/renamed/adopted/removed/fail)

SCAN      (Scanner(...).scan_repo(name, entry) per active registry entry)
    · 20-point inspection per repo → ScanResult (Detail 3)
    · quarantined/deleted repos are skipped
    · last_scan_sha stored into the registry entry, registry saved
    → ScanResult[]

BRANCH — trigger == "shutdown"
    · quick_push only:  SyncEngine.quick_push(name, entry, 30s)
      → git push origin HEAD with a hard timeout; NEVER commit/pull/scan
      → SyncResult per active repo
    · outcome from results

BRANCH — trigger != "manual_scan"
    · SYNC (SyncEngine.run(scan_results, registry))
      for each ScanResult → sync_repo(scan, entry):
          path missing                 → blocked "missing"
          validation gates             → blocked <reason> (secrets / oversize / divergence / …)
          dirty && !auto_commit        → skipped "dirty, auto_commit off"
          else                         → fetch → merge --ff-only @{u} → maybe commit
                                         → recompute ahead → push → SyncResult
      (Detail 4 for the full flow)
    · registry bookkeeping: last_sync_sha / diverged_since / cleared after push
    · events += _sync_events(sync_results, registry)   → pushed/failed/blocked/skipped
      timeline events now carry the repo URL for the report's ↗ links
    · outcome = _outcome(sync_results)

END
    duration = time.time() - started
    drift = _drift_warnings(cfg)            → journal phase=drift outcome=warning (if any)
    REPORT  Reporter(...).generate(events, sync_results, registry, duration,
                                   outcome, drift=drift, scan_results=scan_results)
              → report.html (atomic write) + timestamped archive (Detail 5)
              → Rule 2: EVERY run produces report.html
    SHOW    Reporter(...).show(outcome)
              · interactive (manual_scan/manual_sync) → open browser
              · background                         → Windows toast with the outcome
              · shutdown                           → never (returns immediately)
    ENGINE journal entry: phase=engine outcome=<outcome> with duration/scanned/synced/blocked/failed
```

### Outcome aggregation (`_outcome`)

```
failed      if any result.action == "failed"
partial     else if any result.action == "blocked"
ok          else if any result.action in ("pushed", "committed")
clean       else
```

---

## Hard invariants (the rules)

- **Rule 0 — No registration → no operations.** Only `--setup` / `--setup-all` run first.
- **Rule 1 — No scan → no sync.** The sync engine only touches `ScanResult`s produced by the current run's scanner. There is no way to call sync without a scan in the same process; `--scan` alone never syncs.
- **Rule 2 — Every run produces `report.html`.** Success, failure, nothing-changed, and shutdown all produce one (atomic write + archive).
- **Rule 3 — Trigger type does not matter.** `startup`, `every 3h`, `manual`, `file_change`, and future triggers all call `run_trigger()` → the identical gate chain and pipeline.

## Shutdown exceptions (the only permitted deviations)

| Aspect | Full pipeline | Shutdown |
|--------|---------------|----------|
| Discover / scan | yes | no |
| Pull (`fetch` + `merge --ff-only`) | yes | no |
| Commit | per policy | **never** |
| Push | per policy | `git push origin HEAD` only — pushes commits that already exist locally |
| Timeout | `push.timeout_seconds` (60 s) | hard `shutdown.timeout_seconds` (30 s) so Windows is never blocked |
| Report file | written | still written (Rule 2) |
| Report shown | interactive→browser, background→toast | **never opened** |
| On failure | surfaced in this report | surfaced in the next run's report |

If the shutdown quick-push cannot finish in time, it aborts and the journal records it; Windows proceeds with the shutdown regardless.

## How every trigger reaches the pipeline

- **Task Scheduler** (`scheduler.py`) registers tasks whose action is `"<python>" "<urgithub.py>" --run <trigger>` — the logon/startup task, the repeating task, and the EventID-1074 shutdown task.
- **Launchers** (`Run\*.bat`, deployed to `<base>\urgithub\Run\`) are thin `@echo off` wrappers around the same command.
- **Watcher** (`watch.py`) calls `runner.run_trigger("file_change")` after debounce.
- **Control panel** (`tray.py`) calls `runner.run_trigger(...)` in background threads for the buttons and its resident timer.
- **CLI** maps every flag to `run_trigger(...)`.

## Locking guarantees

- The global lock is a single file `locks\run.lock` holding the owning PID.
- Concurrent runs: the second run logs `skipped — lock held` and exits 0 — it **never queues**.
- Crash safety: a lock older than `stale_seconds` (15 s) is stolen automatically, so a crashed run cannot wedge the schedule.
- Release only removes the file if this process still owns it (PID match).
