# URGithub — Task assignment sheet

Everything **outside the `.md` files** that is needed to turn this project into
a discoverable, trustworthy open-source release. These tasks are yours; the
markdown (README, setup guide, roadmap, release notes, issue backlog, launch
kit) is already done in this repo.

Order matters: do **Phase A** before anything else — everything downstream
(CI, releases, issues) hangs off the rename and a clean repository.

---

## Phase A — Repo identity (do first, ~30 minutes)

### A1. Rename the repository

```powershell
gh repo rename urgithub --repo learnerforge/push-to-github --yes
```

GitHub redirects the old URL automatically. Update the remote URL in any local
clone:

```powershell
git remote set-url origin https://github.com/learnerforge/urgithub.git
```

### A2. Repository description

```powershell
gh repo edit --repo learnerforge/urgithub --description "The safe, automatic Git repository manager for your local machine."
```

### A3. Topics

Run the topic command from [`LAUNCH.md`](LAUNCH.md), section 3.

### A4. Add a LICENSE file (MIT)

Create `LICENSE` in the repo root with the MIT text (year, copyright holder).
The README already declares MIT and links nothing — add the file and update the
License badge.

### A5. Commit the code to GitHub

The source lives in `E:\Project-1` and is not yet a git repo. `git init`,
add the tree (respecting `.gitignore`), commit, and push to the renamed repo.
Then confirm `python urgithub.py --version` runs from a fresh clone.

---

## Phase B — Proof (tests + CI, days 1–2)

### B1. Move the test suites into the repo

The suites live today in `C:\Users\bakke\AppData\Local\Temp\opencode\`
(~114 checks across 5 files):

- `test_bootstrap.py` (19) — first-run clone-all, fork filtering, fallback
- `test_gui.py` (27) — Control Center panels, log stream, confirm dialog
- `test_wizard_os.py` (47) — distro detection, fix buttons, auth flows
- `test_file_commits.py` (18) — per-file last commit + report section
- `test_quarantine_path.py` — quarantine move / keep / decline paths

Create `tests/` in the repo, port the files (they already `sys.path.insert`
`E:\Project-1` — change that to the repo root), and add `tests/run_tests.py`
that discovers and runs every suite, exiting non-zero on any failure.

### B2. CI workflows

Add `.github/workflows/`:

- `tests.yml` — on push/PR: checkout, set up Python 3.10–3.13, run
  `python tests/run_tests.py`.
- `lint.yml` — `python -m compileall urgithub_core` and `pyflakes` (if added
  to a requirements file) or a standard-library-only syntax check.
- `security.yml` — [gitleaks](https://github.com/gitleaks/gitleaks) action.

Then uncomment the badge block at the top of `README.md` (marker comment is
already in place) so the CI status shows on the repo page.

### B3. Make CI green and add the badge screenshot to the README

A green CI is the single cheapest trust signal available. Fix any failures
before launching.

---

## Phase C — Demo (days 2–3)

### C1. Sample report

Generate a representative `report.html` and commit it as `docs/sample-report.html`:

```powershell
python urgithub.py --scan
Copy-Item "D:\urgithub\.urgithub\reports\report.html" "docs\sample-report.html"
```

Then uncomment the "View a sample report" link in `README.md` (marker already
in place).

### C2. Screenshots

Add `docs/screenshots/` with at least:

1. Setup wizard (screen 3 — environment check)
2. Control Center dashboard
3. HTML report (top half — cards + timeline)
4. HTML report (Files & Last Commit section)
5. A security block (`blocked: secrets`)
6. Terminal quick start (`--setup-all` run)

Reference them from the README's screenshot placeholders.

### C3. Demo GIF (30–60 s)

Record the loop: edit a file in a repo → file-change trigger → SCAN →
VALIDATE → SYNC → COMMIT → PUSH → report opens. Tools: ScreenToGif or OBS +
ffmpeg. Save as `docs/screenshots/demo.gif` and uncomment the GIF line at the
top of the README.

### C4. `demo/` scenario scripts (optional but strong)

Four reproducible scenarios against throwaway temp repos:

1. Normal change → scan → validate → commit → push
2. `.env` created → **PUSH BLOCKED** (secret detected)
3. Diverged history → **PUSH BLOCKED**
4. Shutdown quick-push simulation

Each script creates a temp base, runs the relevant trigger, and prints the
outcome. They double as the demo you can show live.

---

## Phase D — Feature (the differentiator)

### D1. Repository Health Dashboard

Add a **Health Summary** block to `report.html` and a `--health` console view:

```
Healthy / Needs Sync / Blocked / Diverged / Missing
Pushes today · Commits today · Failed operations
```

All data already exists (`ScanResult`, registry status, journal). This is
aggregation + rendering — roughly a day of work — and gives the project its
"wow" screenshot.

---

## Phase E — Release & launch (day 5)

### E1. Create the release

```powershell
gh release create v1.0.0 --repo learnerforge/urgithub `
  --title "URGithub v1.0.0" `
  --notes-file docs/RELEASE-NOTES.md
```

(Draft notes are in [`RELEASE-NOTES.md`](RELEASE-NOTES.md).)

### E2. Create the issue backlog

Create the labels, then the issues, exactly as written in
[`ISSUE-BACKLOG.md`](ISSUE-BACKLOG.md). Do not invent engagement.

### E3. Installer (optional, post-v1.0)

Add `build/`:

- `urgithub.spec` — PyInstaller one-file build of `urgithub.py`
- `urgithub.iss` — Inno Setup installer producing `URGithub-Setup.exe` with a
  "Detect Git/gh → GitHub auth → choose base → install triggers" flow

Attach the `.exe` to the release as an asset. This is a product milestone, not
a launch blocker.

### E4. Post the launch

Use the announcement in [`LAUNCH.md`](LAUNCH.md), section 4, and the community
list in section 5. Native posts only; no spam.

---

## Phase F — Sustain (days 6–7 and beyond)

- Reply to every issue/PR within 24 h.
- Fix the first reported bugs; journal the fixes as release notes.
- Track the weekly metrics in [`LAUNCH.md`](LAUNCH.md), section 9.
- Keep the hard rule: **no bought stars, forks, or engagement**.
