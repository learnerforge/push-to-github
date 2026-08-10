# Detail 3 — The Scan Engine

## Purpose

A complete repository inspection, not just `git status`. Runs every time, for every repo, **before** anything can be synced (Rule 1). The scan is the only authority that decides a repo is safe to sync; the sync engine re-validates against the same `ScanResult`.

## Entry points (`urgithub_core/scan.py`)

- `Scanner.scan_repo(name, entry)` — per-repo wrapper; short-circuits on registry state:
  - `status == "quarantined"` → `ScanResult(status="QUARANTINED")`
  - `status in ("deleted", "missing", "LOCAL_MISSING")` → `ScanResult(status="MISSING")`
  - folder missing or no `.git` → `ScanResult(status="MISSING")`
- `Scanner._inspect(name, path)` — the 23-point inspection.
- `validate_result(result, cfg)` — the validation gate (see below).
- `Scanner.render(result)` — human-readable console block.

The scanner resolves its own owner: `github_owner` config, or `"auto"` → the `github.login` from the environment snapshot. GitHub-remote permission checks are only done when a resolved owner exists.

## The inspection (mapped to the actual code)

| # | Check | Implementation |
|---|-------|----------------|
| 1 | Discovered in `repos in github\`? | handled by Discovery (Detail 2) |
| 2–4 | Valid git repo, git runs, directory readable | `git rev-parse --git-dir` → fail = `NOT_GIT` |
| 5 | Current branch | `git symbolic-ref --short HEAD` → `(detached)` if detached |
| 6 | HEAD available | `git rev-parse HEAD` → `head_sha` (7 chars) |
| 7 | Remote configured | `git remote get-url origin` → `remote_configured` |
| 8 | Remote reachable (network, fails fast) | `git ls-remote --heads origin` (non-interactive) |
| 9 | Per-repo authorization (GitHub remotes only) | `gh api repos/{owner}/{repo} --jq .permissions.push` → `permission` |
| 10–15 | Working-tree state | `git status --porcelain` + `--ignored`: `untracked`, `added`, `deleted`, `modified`, `staged`, `ignored`, `dirty` |
| 16 | Potential secrets | filename patterns + content regexes (below) |
| 16a | File-size gate | `oversize` / `large` candidates (below) |
| 17–18 | Ahead / behind vs upstream | `git rev-parse --abbrev-ref @{u}` then `git rev-list --left-right --count @{u}...HEAD` |
| 19 | Divergence | `ahead > 0 AND behind > 0` |
| 20 | Composite status | `_compose()` (below) |

### Check 9 — the four-layer distinction (Detail 0)

GitHub authentication ≠ repository authorization. A user may be logged in (layer 3) but lack push permission on a specific repo (layer 4). `gh api repos/{owner}/{repo} --jq .permissions.push` returns:

- `"true"` → `permission = "PUSH"`
- `"false"` → `permission = "READ"`
- 404 / timeout in stderr → `permission = "UNKNOWN"`
- anything else → `permission = "NONE"`

Only GitHub remotes (`is_github_url`) are checked; other remotes keep `permission = "UNKNOWN"`.

### Checks 10–15 — working tree

`git status --porcelain` lines are counted as:

| Marker | Counted as |
|--------|------------|
| `??` | `untracked` |
| `A` in column 1 or 2 | `added` |
| `D` in column 1 or 2 | `deleted` |
| anything else (not `??`) | `modified` |
| `A/M/D/R/C` in column 1 | `staged` (one per staged entry) |

`dirty = any porcelain output`. `git status --porcelain --ignored` lines starting `!!` count as `ignored`.

### Check 16 — potential secrets (name **and** content)

Candidate files = tracked (`git ls-files`) **plus** untracked non-ignored (`git ls-files --others --exclude-standard`). Files matching `security.allow_files` globs are excluded from **both** checks (false-positive escape hatch).

**Name check** (`security.patterns`, filename globs — defaults `.env*`, `*.pem`, `*.key`, `credentials.json`, `secrets.json`, `*.p12`):
a candidate is flagged when the path **or** its basename matches any glob.

**Content check** (`security.content_patterns`, regex over file text — default patterns include private keys, `ghp_…`, `AKIA…`, `AIza…`, Slack `xox…`, `sk_live_…`, `sk-…`, and `api_key|secret|password = "…"` assignments):
- binary files are skipped (NUL byte probe in the first 8 KB),
- only the first `security.max_scan_bytes` (1 MB) of text is read,
- each matched pattern is recorded in `patterns`.

A file already caught by the name check is not content-scanned again.

### Check 16a — file-size gate

For every candidate file with a readable size:

- `size > limits.max_file_mb` (default 100 MB — GitHub's hard per-file limit) → appended to `oversize`
- `size > limits.warn_file_mb` (default 50 MB) → appended to `large` (warning only)

### Checks 17–18 — ahead / behind

Requires an upstream (`@{u}`). `git rev-list --left-right --count @{u}...HEAD` returns `<behind> <ahead>`. Failures leave the counters at 0.

### Check 23 — per-file last commit

Fills `ScanResult.files` with GitHub-style "committed at" info for the report's **Files & Last Commit** section. One `git log --date=iso-strict --pretty=format:%ad%x00 --name-only` walk per repo (newest-first); the **first** time a path appears records its last commit date. Untracked files (`git ls-files --others --exclude-standard`) carry `committed_at: ""` (uncommitted). The walk is a single subprocess regardless of history size (measured ~230 KB for a 3 600-file repo). `files` is deliberately **excluded from `to_dict()`** so the journal stays lean.

### Composite status (`_compose`)

| Condition | `status` |
|-----------|----------|
| no remote configured | `NO_REMOTE` |
| remote configured but unreachable | `AUTH_FAIL` |
| `permission == "NONE"` | `NO_PERMISSION` |
| `ahead > 0 and behind > 0` | `DIVERGED` |
| dirty working tree | `DIRTY` |
| otherwise | `READY` |

Plus the short-circuit statuses from `scan_repo`: `MISSING`, `NOT_GIT`, `QUARANTINED`.

## Output — `ScanResult` per repo

```python
@dataclass
class ScanResult:
    repo: str
    branch: str = ""
    head_sha: str = ""
    dirty: bool = False
    modified: int = 0
    added: int = 0
    deleted: int = 0
    untracked: int = 0
    staged: int = 0
    ignored: int = 0
    ahead: int = 0
    behind: int = 0
    has_upstream: bool = False
    remote_configured: bool = False
    remote_reachable: bool = False
    permission: str = "UNKNOWN"          # PUSH | READ | NONE | UNKNOWN
    secrets: list = []                   # flagged file paths (name or content)
    secret_findings: list = []           # [{file, kind: "name"|"content", patterns?}]
    oversize: list = []                  # [{file, bytes}] over max_file_mb
    large: list = []                     # [{file, bytes}] over warn_file_mb
    files: list = []                     # [{file, committed_at}] report-only (not in to_dict)
    status: str = "READY"                # READY | DIRTY | DIVERGED | AUTH_FAIL |
                                         # NO_PERMISSION | NO_REMOTE | MISSING | NOT_GIT | QUARANTINED
```

`to_dict()` serializes every field **except `files`** (kept out to avoid journal bloat); each scan is journaled (phase `scan`, outcome `done` or `failed`).

## Console rendering

```
CampusCart
──────────
Branch: master
Working tree: DIRTY
Modified: 7
Added: 3
Deleted: 1
Untracked: 2
Staged: 0
Local commits ahead: 1
Remote commits ahead: 0
Remote: configured
Remote access: PUSH
Security: PASS
Oversize files: 0
Sync: READY
```

Flagged secrets and oversized files are listed with `! ` markers.

## Validation gate — `validate_result(result, cfg)`

Called by the sync engine per repo, **in this order** — the first failure blocks the repo with its reason:

| # | Gate | Condition | Block reason |
|---|------|-----------|--------------|
| 1 | **Security** | `block_on_secrets` and `result.secrets` | `secrets` |
| 2 | **Size** | `block_on_oversize` and `result.oversize` | `oversize files` |
| 3 | **Divergence** | `status == "DIVERGED"` | `divergence` |
| 4 | **Auth (reachability)** | `status == "AUTH_FAIL"` | `remote unreachable` |
| 5 | **Auth (permission)** | `status == "NO_PERMISSION"` | `no push permission` |
| 6 | **Remote** | `status == "NO_REMOTE"` | `no remote configured` |
| 7 | **State** | `status in (MISSING, NOT_GIT, QUARANTINED)` | `<status>.lower()` |

A blocked repo **never reaches sync**; every other repo still completes the run. The reason string is exactly what appears in `SyncResult.reason`, the journal, and `report.html`.

## Safety guarantees

- The app **never deletes or modifies** flagged secret files — it only reports them and stops the repo.
- Content scanning reads at most `max_scan_bytes` per file, only text (binary skipped).
- Oversized files are reported but never touched; blocking is optional (`block_on_oversize`).
- A bad repo never blocks the others — validation is strictly per-repo.
