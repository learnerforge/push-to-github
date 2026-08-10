# Detail 4 — The Sync / Commit / Push Engine

## Purpose

The component that actually moves data. It receives a **validated, safe, authorized** repository and returns a `SyncResult`. It never decides on its own to push arbitrary things — the scan engine authorizes first (Rule 1, Detail 3), and the engine re-validates immediately before acting.

## Output — `SyncResult` per repo

```python
@dataclass
class SyncResult:
    repo: str
    action: str = "skipped"     # pushed | clean | committed | skipped | blocked | failed
    before_sha: str = ""        # 7-char HEAD before the operation
    after_sha: str = ""         # 7-char HEAD after the operation
    reason: str = ""            # human-readable reason for skipped/blocked/failed
    changed: list = []          # [{status: "A"|"M"|"D"|"R", path}] from `git log -1 --name-status`
```

`to_dict()` serializes every field; the engine journals `before_sha`/`after_sha` around every write.

## Safety rules (absolute)

- **Forbidden git arguments** (`SyncEngine.FORBIDDEN`): `reset`, `--force`, `--hard`, `rebase`, `clean`. The push builder refuses any combination containing these.
- Never force-push, never auto-rebase, never reset, never clean.
- Pulls are **fetch + fast-forward only** (`git fetch origin` → `git merge --ff-only @{u}`).
- Every git subprocess runs with a hard timeout (`push.timeout_seconds`, default 60 s) and is killed on expiry.
- All operations are idempotent — re-running never duplicates commits, repos, or branches.
- Auth is always non-interactive: `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=Never` — fail fast, never hang.
- Push requires scan-granted authorization: GitHub login alone is insufficient (four-layer model, Detail 0).

## Full sync flow — `sync_repo(scan, entry)` → `_perform(path, scan, auto_commit)`

```
sync_repo(scan, entry)
  │
  ├─ path missing / not a dir
  │     → blocked "missing"
  ├─ validate_result(scan, cfg) fails        (Detail 3 gate order)
  │     → blocked <reason>    (secrets | oversize files | divergence |
  │                            remote unreachable | no push permission |
  │                            no remote configured | missing/not_git/quarantined)
  ├─ scan.dirty AND auto_commit is False
  │     → skipped "dirty, auto_commit off"    (never silently commits)
  └─ otherwise → _perform()

_perform(path, scan, auto_commit)
  1. before_sha = git rev-parse HEAD
  2. SAFE PULL
       git fetch origin                     → fail → failed "fetch failed: <stderr>"
       git rev-parse --verify @{u}          → fail → skipped "no upstream configured"
       git merge --ff-only @{u}             → fail → blocked "divergence (fast-forward failed)"
  3. COMMIT (only when policy requires)
       if auto_commit and scan.dirty:
         git add -A                         → fail → failed "git add failed"
         git commit -m "<prefix> <branch> <utc timestamp>"
                                            → fail → failed <stderr>
         journal phase=sync outcome=committed {message}
  4. RECOMPUTE
       git rev-list --left-right --count @{u}...HEAD → behind/ahead
       if ahead <= 0                        → clean "up to date"
  5. PUSH
       args = ["push", "origin"]
       + ["--all"] when push.push_all_branches
       forbid any FORBIDDEN token in args
       git push origin [--all]              → fail → failed "push failed: <stderr>"
  6. SUCCESS
       after_sha = git rev-parse HEAD
       action = "pushed"
       changed = git log -1 --name-status --format=   → [{status, path}]
       journal phase=sync outcome=pushed {before, after, files}
```

### Commit message format

`<message_prefix> <branch> <utc timestamp>`, e.g.

```
sync: master 2026-08-10 18:45:03
```

`message_prefix` defaults to `sync:` (`commit_policy.message_prefix`).

### Per-repo `auto_commit`

A registry entry may override the global policy with its own `auto_commit` field (set from `commit_policy.auto_commit` at discovery). Resolution: `entry.auto_commit` if present, else `commit_policy.auto_commit`.

## Decision table

| State | Action | `action` |
|-------|--------|----------|
| Local ahead / remote behind | **Safe push** | `pushed` |
| Local ahead **and** remote ahead | **BLOCKED — divergence.** `merge --ff-only` fails or `DIVERGED` scan status. Skip + retry every trigger. Never force-push, never auto-rebase. | `blocked "divergence…"` |
| Local = remote, clean | **Nothing to do** — journaled and reported as clean. Idempotent. | `clean "up to date"` |
| Dirty tree, `auto_commit=false` | **Skipped + reported.** Changes still appear in the report/journal. | `skipped "dirty, auto_commit off"` |
| Dirty tree, `auto_commit=true` | Commit with the `sync:` prefix, then push. | `committed` then `pushed` |
| No upstream | Fast-forward skipped. | `skipped "no upstream configured"` |
| Secret files | Blocked (gate 1). | `blocked "secrets"` |
| Oversized files | Blocked (gate 2). | `blocked "oversize files"` |
| Remote unreachable | Blocked (gate 4). | `blocked "remote unreachable"` |
| No push permission | Blocked (gate 5). | `blocked "no push permission"` |
| No origin remote | Blocked (gate 6). | `blocked "no remote configured"` |
| Folder missing / not git / quarantined | Blocked (gate 7). | `blocked "missing"` |
| Fetch / add / commit / push fails | Failed — journaled with the reason. | `failed "<step>: <stderr>"` |

Every case is journaled and visible in `report.html`. One bad repo never blocks the others.

## Registry bookkeeping (after sync, in the runner)

- `pushed` → `last_sync_sha = after_sha`, `diverged_since = None`
- `blocked` with a divergence reason → `diverged_since = diverged_since or now`
- any other non-blocked action → `diverged_since = None`

## Shutdown quick push — `quick_push(name, entry, timeout_seconds)`

The **only** deviation from the full flow (Detail 1):

```
before_sha = git rev-parse HEAD
not a git repo            → skipped "not a git repo"
journal quick_push started
git push origin HEAD      (hard timeout = shutdown.timeout_seconds, default 30 s)
  ok    → pushed; after_sha; journal quick_push pushed {before, after}
  fail  → failed <stderr>; journal quick_push failed {error}
```

- Never commits, never pulls, never scans.
- Hard timeout so Windows shutdown is never blocked.
- Runs for every registry entry with `status == "active"`.

## Outcome aggregation (runner `_outcome`)

```
failed    any action == "failed"
partial   else any action == "blocked"
ok        else any action in ("pushed", "committed")
clean     otherwise
```
