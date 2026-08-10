# Detail 0 — Environment Detection & Registration

## Purpose

Installation and registration come **first**. No scan, sync, push, or schedule operation is allowed before registration succeeds. First launch opens the registration wizard; the application refuses to operate until `config.json` has `"registered": true`.

Registration is a **one-time** event. It:

1. lets the user pick a **base location**,
2. verifies the machine can actually push to GitHub (the four-layer model below),
3. creates the full folder structure (see Detail 2),
4. writes `config.json` with `registered=true` and an `environment_snapshot`,
5. writes the locator file `~/.urgithub/base.txt`,
6. optionally installs the Windows scheduled tasks.

---

## The four-layer model

Four independent layers — each is checked separately and **never** assumed from another.

| Layer | What is checked | Command | When | Fail remediation |
|-------|-----------------|---------|------|------------------|
| 1. Git **installed** | Is `git` on `PATH`? | `git --version` | Registration + every run | Wizard "Install Git" button |
| 2. Git **configured** | Global identity set? | `git config --global user.name` + `user.email` | Registration + drift check each run | Wizard "Configure identity" dialog |
| 3. GitHub **authenticated** | Logged into GitHub with the `repo` push scope? | `gh auth status` (scopes parsed from `token scopes:` line) + `gh api user` | Registration + every run | Wizard "Authenticate GitHub" button |
| 4. Repo **authorized** | Permission to push *this specific repo*? | `gh api repos/{owner}/{name} --jq .permissions.push` | Per-repo, during the scan, not registration | Reported `NO_PERMISSION` / `AUTH_FAIL`, retried next run |

**Rule:** `Git installed` ≠ `Git configured` ≠ `GitHub authenticated` ≠ `repo authorized`.

Layer 4 is what makes URGithub safe: being logged in is not enough — the engine asks GitHub whether the current account may **push** to each repository before it will.

---

## The environment checks (`urgithub_core/envcheck.py`)

`EnvCheck(base_location).run()` collects every fact the wizard (and the report) needs:

| Field | Source command | Meaning |
|-------|----------------|---------|
| `git_installed` | `git --version` exit code | Git present on `PATH` |
| `git_version` | `git --version` stdout | e.g. `git version 2.45.1` |
| `identity["name"]` | `git config --global user.name` | Identity set? |
| `identity["email"]` | `git config --global user.email` | Identity set? |
| `gh_installed` | `gh --version` exit code | GitHub CLI present |
| `github_authenticated` | `gh auth status` exit code | Logged in? |
| `github_scopes` | parsed `token scopes:` line from `gh auth status` | e.g. `repo`, `read:org` |
| `github_login` | `gh api user --jq .login` | GitHub username |
| `github_reachable` | `gh api user` exit code | Live API connection works |
| `base_writable` | write/delete probe `.urgithub_probe` | Base location is writable |

Derived booleans:

- `can_push` = `github_authenticated` **and** `"repo" in github_scopes`.
- `all_pass` = git installed **and** identity name **and** identity email **and** gh installed **and** `can_push` **and** `github_reachable` **and** `base_writable`.

> The **`repo` scope** is the difference between "logged in" and "can push". Without it, registration stays blocked even when `gh auth status` succeeds.

The registration wizard renders ten check rows (from `wizard.py`):

```
✓ Python                    <version>
✓ Git installed
✓ Git version               git version 2.45.1
✓ Git username              Your Name
✓ Git email                 you@example.com
✓ GitHub CLI (gh) installed
✓ GitHub authentication     yourlogin
✓ Push scope (repo) present repo
✓ GitHub connection (live)
✓ Base location writable
```

Only when **all** pass does the **Register** button enable.

### Snapshot

On successful registration `EnvCheck.snapshot()` is stored as `config.json → environment_snapshot`:

```json
{
  "git":    { "installed": true, "version": "git version 2.45.1" },
  "identity": { "name": "Your Name", "email": "you@example.com" },
  "github": {
    "authenticated": true,
    "host": "github.com",
    "login": "yourlogin",
    "cli_installed": true,
    "scopes": ["repo", "read:org"],
    "can_push": true
  },
  "last_check": "2026-08-10T18:45:00Z"
}
```

---

## First-launch flow (`urgithub_core/wizard.py`)

```
Launch: python urgithub.py --setup
   │
   ▼
GUI available (tkinter)? ──no──► Console wizard (interactive prompts)
   │ yes
   ▼
tkinter RegistrationWizard
   │
   ├── Page 1 — Welcome
   │     "Start" / "Exit"
   │
   ├── Page 2 — Workspace
   │     Browse… → select base location (parent folder)
   │     "Next" (blocked until a folder is chosen)
   │
   ├── Page 3 — Environment check
   │     Runs EnvCheck and renders the 10 rows above
   │     One-click fix buttons appear only for the failing layer:
   │       · Install Git                    → webbrowser → git-scm.com
   │       · Configure identity             → dialog → git config --global …
   │       · Install GitHub CLI             → webbrowser → cli.github.com
   │       · Authenticate GitHub (gh auth)  → new console → gh auth login
   │     Checkbox: "Also install Windows scheduled tasks"
   │     [Register] enabled only when all_pass
   │
   ▼
finish():
   Paths(base).ensure_all()          → create urgithub\ structure (Detail 2)
   cfg = Config({}, base_location=base)
   cfg.register(checks.snapshot())   → registered=true, registered_at, snapshot, save
   write_locator(base)               → ~\.urgithub\base.txt
   (optional) scheduler.install()    → startup/timer/shutdown tasks (+ UAC for shutdown)
   └► success dialog → ready
```

Any step that raises (e.g. folder creation fails) shows an error dialog and registration does **not** complete.

---

## Registration gate (Rule 0)

- **Rule 0:** No registration → no operations.
- Implemented in `runner.run_trigger()`: `Config.load().registered` is `False` whenever `config.json` is absent **or** has `"registered": false`. The command exits with:

  ```
  URGithub is not registered. Run: python urgithub.py --setup
  ```

  and returns exit code `1`.
- The same guard is applied to `--scan`, `--sync`, `--shutdown`, `--run`, `--schedule`, `--watch`, `--status`, `--repos`, `--verify`, `--report`, `--forget`, `--prune`. The only commands allowed before registration are `--setup` and `--setup-all`.
- `--tray` is allowed to attempt launch but itself refuses when unregistered.

### The locator (`~/.urgithub/base.txt`)

The **only** file ever written outside the base location. It stores the base location string so the app can find `config.json`:

- Written by `write_locator()` at registration.
- Read by `Config.load()` on every invocation.
- Nothing else is ever written outside the base location.

---

## Env re-check policy

| Scope | When | What it verifies |
|-------|------|------------------|
| **Full check** | Registration only | All ten rows via `EnvCheck` |
| **Light check** | Every run start (`runner._light_env_check`) | `git --version` exit code · `gh auth status` exit code · base location directory exists |
| **Drift detection** | Every run end (`runner._drift_warnings`) | Git **version** and global **name/email** compared against `environment_snapshot` |

Drift results are journaled under phase `drift` (outcome `warning`) and surfaced in `report.html` under **Environment Drift**:

```
Git version changed: git version 2.44.0 → git version 2.45.1
Git identity name changed: Old Name → New Name
Git identity email changed: old@example.com → new@example.com
```

A changed identity/version is a **warning, not an error** — the run continues and the change is recorded.

---

## Deleted-repos quarantine rules

`deleted repos\` is an **archive/quarantine area — not a trash bin**. URGithub never permanently deletes automatically.

### Deletion is NOT suspected when…

GitHub temporarily unreachable, internet disconnected, auth fails, GitHub API returns a non-404 error, remote cannot be contacted, local repo has errors, or the repo is temporarily unavailable. These are **connection/operation failures** → the repo keeps its status and is retried next run.

### The staged workflow (suspicion → confirmation → action)

Implemented in `discovery.py` (`_reconcile` → `_check_remote` → `_deletion_hit` → `_confirm_quarantine` → `_quarantine`):

```
Repository in registry with a GitHub remote
       │
       ▼  (reconcile step, every run)
Is the repo in `gh repo list`?
       │ yes → active; deletion_hits reset to 0
       │ no  → is it a GitHub URL?
       │         no → skip (not subject to quarantine)
       ▼ yes
gh api repos/{owner}/{name} --jq .name
   ├── 404
   │      ▼  FIRST DETECTION
   │      deletion_hits += 1
   │      status → "pending", deletion_suspected_at → now    (DO NOT MOVE)
   │      journal: phase=quarantine outcome=suspected
   │      ▼  on every later run
   │      deletion_hits >= confirm_scans (default 3)
   │      AND elapsed >= confirm_days (default 7)
   │             ▼  CONFIRMED → require user confirmation (default on)?
   │             ├── interactive run → prompt:
   │             │     "Move to 'deleted repos'? [y/N]"  → y: quarantine
   │             │                                        → N: keep; journal "kept"
   │             └── background run  → defer; journal note; try again on an interactive run
   │
   ├── 200 with a DIFFERENT name → RENAME on GitHub detected
   │      → rename local folder + registry entry (see below)
   │
   ├── 200 (same name) → alive: deletion_hits = 0; pending → active
   │
   └── any other error → connection failure → ignore (not deletion)
```

### Quarantine move

- Target: `<base>\urgithub\deleted repos\<name>` (a `_1`, `_2`, … suffix is appended if the target already exists, so nothing is ever overwritten).
- Registry: `status=quarantined`, `quarantined_at=now`, `quarantined_to=<dest>`; `deletion_hits=0`.
- Journaled: phase `quarantine`, outcome `moved`.
- A `removed` event is emitted for the report timeline.

### Case A — GitHub deleted, local exists

Do **not** delete the local repository. After confirmation the local copy is **moved** to `deleted repos\`. The user may instead keep the local copy (answer `N`).

### Case B — Local deleted, remote alive

The folder is gone but GitHub still has the repo. Marked `missing` (registry status; scan returns `MISSING`). Per `clone_missing_repos` (default `true`) the repo is **re-cloned** from its remote. If `clone_missing_repos` is off it stays `missing` until the user intervenes.

### First-run clone-all (bootstrap)

A fresh registration has an **empty registry**, so a repo-by-repo recovery could never clone anything. On every discovery run (`discovery.py → _bootstrap_seed`), every repo returned by `gh repo list` that is **not already in the registry** is seeded as a `missing` entry (journal phase `discover`, outcome `seeded`), and the clone step then pulls it into `repos in github\`. The result: the **first run after registration** (any trigger — Sync now, startup, scheduled) downloads the whole account — private repos and forks included (forks only excluded when `skip_forks` is enabled).

Clones use `gh repo clone <owner>/<name>` (authenticated session handles private repos), falling back to `git clone <url>`.

### Decision matrix

| Local folder | Remote (GitHub) | Result |
|--------------|-----------------|--------|
| Present | Deleted / renamed (404) | Suspect (`pending`) → confirm after `confirm_scans`/`confirm_days` → **ask user** → move to `deleted repos\`, registry `quarantined` |
| Absent | Deleted (404) | Nothing to move → registry `deleted` / `missing`, journaled |
| Absent | Alive, **not in registry** | seeded → cloned into `repos in github\` (first-run clone-all) |
| Absent | Alive, in registry | `missing` → re-cloned per `clone_missing_repos` |
| Present | Alive | `active` — normal scan/sync |
| Present, moved folder | Alive | local **rename** adopted: registry entry reused under its origin name (see below) |

### Registry statuses

`active` | `missing` | `LOCAL_MISSING` (legacy marker for local-deleted) | `pending` (deletion suspected, awaiting confirmation) | `quarantined` (moved to `deleted repos\`) | `deleted`.

- Repos inside `deleted repos\` are **excluded** from discovery/scan/sync — the scan returns `QUARANTINED` and the sync engine never touches them.
- Every suspicion, confirmation, keep, and move is journaled with its reason and timestamp.

---

## Rename handling (GitHub is the source of truth for names)

- **Renamed on GitHub only** → `gh api` returns the new name; URGithub renames the local folder and moves the registry entry (`renamed` event; journal phase `rename`, outcome `done`). Renames are skipped if the target folder or registry entry already exists.
- **Renamed locally only** → a folder whose `origin` remote matches a registry entry that is `missing`/`LOCAL_MISSING`, whose recorded path no longer exists, or whose path equals the folder, is **adopted**: the existing entry is reused (path updated, no duplicate clone, no false quarantine). Emits an `adopted` event. Then rename it on GitHub to match.

---

## Configuration knobs that affect this detail

```jsonc
"deleted_repo_policy": {
  "confirm_scans": 3,                    // 404 hits required
  "confirm_days": 7,                     // and this many days since first suspicion
  "require_remote_confirmation": true,   // remote 404 is the trigger source
  "require_user_confirmation": true      // never quarantine silently when true
},
"clone_missing_repos": true,             // re-clone local-deleted / missing repos (also gates first-run clone-all)
"skip_forks": false,                     // true = exclude forks from clone-all
"github_owner": "auto"                   // "auto" = the gh login from the snapshot
```
