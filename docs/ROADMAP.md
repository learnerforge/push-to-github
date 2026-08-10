# URGithub — Roadmap

Where the project is, and where it is going. Items are grouped by release
milestone; the current status of each item is tracked in this file and in the
[issue backlog](ISSUE-BACKLOG.md).

---

## v1.0 — Automatic & safe on Windows *(released)*

What already ships:

- [x] Registration wizard (GUI + console fallback, OS-aware fix buttons)
- [x] Automatic repository discovery under `repos in github\`
- [x] GitHub reconciliation with `gh repo list` (limit 1000, forks detected)
- [x] First-run clone-all: every account repo (private + forks unless `skip_forks`) is cloned automatically
- [x] 23-point scan: branch, HEAD, remote, reachability, authorization, dirty state, secrets (name + content), file sizes, ahead/behind, per-file last commit
- [x] Validation gates: secrets, oversize, divergence, unreachable remote, no permission, no remote, missing
- [x] Safe sync: fetch + fast-forward-only pull; commit/push per policy
- [x] Shutdown quick-push (EventID 1074, hard 30 s timeout, never blocks Windows)
- [x] Secret detection: filename globs + content regex, `allow_files` escape hatch
- [x] Divergence protection (blocked, never clobbered)
- [x] Repository quarantine workflow (3 scans + 7 days + user confirmation)
- [x] Rename handling: GitHub renames and local renames both adopted automatically
- [x] Dark-theme HTML report every run (cards, timeline, details, all-repos, files & last commit, security & size, drift)
- [x] Append-only JSONL journal with before/after SHAs
- [x] Windows Task Scheduler: startup, timer, shutdown tasks + launcher deploy
- [x] Debounced file-change watcher
- [x] Control Center GUI (Dashboard / Repos / Schedule / Settings / Logs / Help)
- [x] Config CLI (`--config`) + full config schema
- [x] Pure Python standard library — no third-party dependencies

## v1.1 — Cross-platform & better signals

- [ ] Linux environment detection + packaging support (already partially detected in the wizard)
- [ ] macOS environment detection + packaging support
- [ ] Linux/macOS scheduling: cron / systemd / launchd generators
- [ ] `event_hook` trigger (webhook/email entry point, same pipeline)
- [ ] Desktop notifications beyond Windows toasts (notify-win / terminal fallback)
- [ ] GitHub App authentication as an alternative to the PAT scope flow
- [ ] Repository health score (composite: sync state, secrets, size, divergence, last activity)
- [ ] JSON export of run results (`--report --json`)

## v1.2 — Visibility & fleet

- [ ] Web dashboard (read-only) served locally from `report.html` data
- [ ] Multi-account support (multiple GitHub identities)
- [ ] Remote monitoring endpoint (optional, opt-in)
- [ ] Repository statistics in the report (commit counts, per-repo velocity)
- [ ] Email / webhook notifications (config already has the schema)
- [ ] Policy presets per repo (e.g. `auto_commit: true` per repository)

## v2.0 — Fleet operations

- [ ] Cross-platform daemon (resident, no Task Scheduler dependency)
- [ ] Repository policies as versioned config files
- [ ] Team / organization management (org-level reconcile)
- [ ] GitLab support (remote provider abstraction)
- [ ] Conflict review UI inside the Control Center

---

## Contribution guidance

- The "help wanted" items above map to concrete issues with acceptance criteria
  in [`ISSUE-BACKLOG.md`](ISSUE-BACKLOG.md).
- Every issue is labeled and sized for a first-time contributor where possible.
- Engineering reference docs live in the [spec folder](README.md) (`spec/00`…`spec/05`).
