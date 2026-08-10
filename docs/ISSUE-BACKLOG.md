# URGithub — Issue backlog

A starter set of real, well-scoped issues with labels and acceptance criteria.
These are **not** manufactured engagement — they are genuine gaps and
improvements any contributor can pick up. Create them on GitHub with the
commands below (after the repo rename, see [URGITHUB-TASKS.md](URGITHUB-TASKS.md)).

## Labels to create first

```powershell
gh label create "good first issue" --repo learnerforge/urgithub --color 0e8a16 --description "Small, well-scoped task for new contributors"
gh label create "help wanted"      --repo learnerforge/urgithub --color 008672 --description "Extra attention is needed"
gh label create "enhancement"      --repo learnerforge/urgithub --color a2eeef --description "New feature or request"
gh label create "bug"              --repo learnerforge/urgithub --color d73a4a --description "Something is not working"
gh label create "documentation"    --repo learnerforge/urgithub --color 0075ca --description "Docs-only change"
gh label create "security"         --repo learnerforge/urgithub --color d93f0b --description "Security-related"
```

---

## Good first issues

### G1. Add JSON export for the report

**Labels:** `good first issue`, `enhancement`

Add `python urgithub.py --report --json` (or a `--export json` flag) that
writes the same data as `report.html` to `report.json` in the reports folder.

Acceptance criteria:

- [ ] Output is a single valid JSON object with run metadata, events, sync
      results and scan findings.
- [ ] No new third-party dependencies.
- [ ] Existing `report.html` generation is unchanged.
- [ ] Covered by a test in `tests/`.

---

### G2. Add repository statistics to the report

**Labels:** `good first issue`, `enhancement`

Show per-repo commit counts and last-activity velocity in the "All
Repositories" section of `report.html`.

Acceptance criteria:

- [ ] Uses existing `git rev-list --count HEAD` output; no new subprocess per
      file.
- [ ] Shown only when cheap to compute (capped repos already exist via
      `report.files_max`).
- [ ] Covered by a test in `tests/`.

---

### G3. Add Linux environment detection hints for the wizard

**Labels:** `good first issue`, `enhancement`

The wizard already detects distro from `/etc/os-release`. Add package-manager
hints for more distros (e.g. openSUSE `zypper`, Alpine `apk`, Void `xbps`).

Acceptance criteria:

- [ ] `/etc/os-release` values `ID=opensuse-*`, `ID=alpine`, `ID=void` map to
      the correct install commands.
- [ ] Unknown distros still fall back to the existing generic hint.
- [ ] Covered by tests (the distro parser is pure and already tested).

---

### G4. Add a `--health` console summary

**Labels:** `good first issue`, `enhancement`

Print a compact per-repo health table to the console: status, local/remote
SHA, ahead/behind, last sync, security PASS/FAIL.

Acceptance criteria:

- [ ] Reuses `ScanResult` data; no separate scan implementation.
- [ ] Rows sorted by worst health first (failed/blocked/diverged first).
- [ ] Exit code 0 when all healthy, 1 when anything is blocked/failed.

---

### G5. Add macOS LaunchAgent generator

**Labels:** `good first issue`, `enhancement`

Generate a `~/Library/LaunchAgents/io.urgithub.plist` that fires the `startup`
and `scheduled` triggers, mirroring the Windows Task Scheduler support.

Acceptance criteria:

- [ ] `--schedule install` detects the OS and writes the correct plist.
- [ ] `--schedule uninstall` removes it.
- [ ] Runs only on Darwin; Windows behavior is unchanged.

---

### G6. Add Linux systemd / cron generator

**Labels:** `good first issue`, `enhancement`

Generate a systemd user service+timer (or a `crontab` line) for the
`scheduled` trigger.

Acceptance criteria:

- [ ] `--schedule install` on Linux writes a valid systemd unit (or prints a
      copy-paste crontab line).
- [ ] The `shutdown` concept is gracefully skipped with a clear message.

---

## Help wanted

### H1. Divergence review UI in the Control Center

**Labels:** `help wanted`, `enhancement`

When a repo is `blocked: divergence`, show a diff summary in the Repositories
tab and a "pull and merge after review" action.

Acceptance criteria:

- [ ] Read-only — never performs the merge automatically.
- [ ] Diff summary computed from existing `git fetch` + `git log` data.
- [ ] Action requires an explicit confirmation dialog.

---

### H2. Webhook / email notification delivery

**Labels:** `help wanted`, `enhancement`

The `notify` config schema already exists (`email`, `webhook.discord`,
`webhook.slack`, `github_actions`). Implement delivery on run completion.

Acceptance criteria:

- [ ] Sends on configurable events (outcome, failures only).
- [ ] SMTP via standard library `smtplib`; webhooks via `urllib`.
- [ ] Failures to notify are logged, never crash a run.
- [ ] Defaults stay disabled.

---

### H3. Report history index page

**Labels:** `help wanted`, `enhancement`

Generate `index.html` in the archive folder listing all archived reports with
links, so history is browsable without the filesystem.

Acceptance criteria:

- [ ] Built during `_write()` archiving.
- [ ] Sorted newest-first, shows trigger + outcome per report.

---

## Bugs worth fixing (verify first)

### B1. Very large repos: cap the history walk

**Labels:** `bug`, `help wanted`

The per-file last-commit walk in `scan.py` is a single `git log`, which is
fine for typical repos but can be slow on repositories with very large
histories. Investigate bounding it (e.g. `--max-count` fallback with
`uncommitted` for the rest).

Acceptance criteria:

- [ ] The report still shows the newest files' commit times.
- [ ] No change in behavior for normal-sized repos.
- [ ] Covered by a test with a synthetic long history.

---

### B2. GitHub rename with a vanished local folder leaves a stale `missing` entry

**Labels:** `bug`, `help wanted`

If a repo is renamed on GitHub while the local folder is also gone, the old
registry entry stays `missing` forever even though the new name is cloned.
Investigate auto-clearing the stale entry once the new name is active.

Acceptance criteria:

- [ ] No data loss; the stale entry is removed only when the new entry is
      `active`.
- [ ] Journaled when it happens.
- [ ] Covered by a test in `tests/`.

---

## Creating the issues

For each issue above, e.g. G1:

```powershell
gh issue create --repo learnerforge/urgithub \
  --title "Add JSON export for the report" \
  --label "good first issue,enhancement" \
  --body "<paste the issue body from above>"
```

Tip: put the acceptance-criteria checklist verbatim in the body. Do **not**
create duplicate issues or artificial engagement — the point is a small,
honest backlog that external contributors can actually land.
