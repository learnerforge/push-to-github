# URGithub — Launch kit

Everything needed to present URGithub as a product, not a script. Follow the
"no bought stars" rule at the bottom — all growth below is genuine.

---

## 1. Positioning

**One line**

> The safe, automatic Git repository manager for your local machine.

**Second line (the pitch)**

> Automatically discover, scan, synchronize, commit, push, verify and monitor
> all your Git repositories — with safety gates and a complete HTML activity
> report after every run.

**The frame**

URGithub is **the safety layer between your filesystem and GitHub**:

```
DISCOVER → SCAN → SECURITY → VALIDATE → SYNC → COMMIT → PUSH → JOURNAL → REPORT
```

What makes it interesting is not "it pushes Git". It is that **every trigger —
startup, shutdown, timer, file change, manual — enters the same gated
pipeline**, and anything unsafe (secrets, oversized files, divergence,
unreachable remotes) blocks that repo instead of clobbering it.

## 2. Repository description (GitHub)

```
The safe, automatic Git repository manager for your local machine. Discover, scan, synchronize, commit, push and report on all your Git repos — with safety gates and an HTML activity report.
```

## 3. Topics (GitHub)

Apply with:

```powershell
gh repo edit --repo learnerforge/urgithub `
  --add-topic git --add-topic github --add-topic git-automation `
  --add-topic git-manager --add-topic repository-manager `
  --add-topic developer-tools --add-topic devtools `
  --add-topic automation --add-topic python --add-topic windows `
  --add-topic github-cli --add-topic git-sync --add-topic git-operations
```

Do not add unrelated topics.

## 4. Launch announcement (ready to post)

Lead with the problem, not the feature list:

> I got tired of manually managing Git operations across dozens of local
> repositories.
>
> So I built **URGithub**.
>
> It automatically discovers repositories, scans them, checks for secrets and
> divergence, synchronizes them safely, pushes changes, and generates an HTML
> report after every run.
>
> It can run on:
>
> - Windows startup
> - shutdown
> - scheduled intervals
> - file changes
> - manual triggers
>
> The interesting part is that every trigger goes through the same safety
> pipeline: a secret, an oversized file, or a diverged history blocks that one
> repo — it never force-pushes, never resets, and never clobbers your work.
> It writes a human-readable report and an append-only journal after every
> run, so you can always see exactly what happened and why.
>
> Open source, Python standard library only, no cloud, no daemon:
> https://github.com/learnerforge/urgithub
>
> I'd especially like feedback from people who manage a lot of local Git
> repositories. What does your safety layer need to do?

## 5. Communities to target (native posts, no spam)

| Community | Native angle |
|---|---|
| Hacker News ("Show HN") | The safety-first design + the report + "no third-party deps" |
| r/selfhosted | Local-first, no cloud, data stays on your machine |
| r/Python | Standard library only, 23-point scan, real test suite |
| r/github | GitHub CLI integration, quarantine workflow, first-run clone-all |
| r/windows | Task Scheduler + shutdown quick-push |
| r/opensource | The transparency story (journal + report) |
| DEV Community / Hashnode | Tutorial: "from a folder of repos to an auto-synced fleet" |
| LinkedIn / X | Short version of the announcement; link for detail |

Every post should be **native to that community** and answer: what problem does
this solve, and how do I try it in 30 seconds. The goal is not 1 000 eyeballs;
it is 100 developers interested enough to run `python urgithub.py --setup-all`.

## 6. The 7-day plan

| Day | Work |
|-----|------|
| **Day 1** | Repo hygiene: rename to `urgithub`, description, topics, LICENSE, sample report (tasks A1–A4, A7) |
| **Day 2** | Proof: CI workflows green + tests moved into `tests/` (A5, A9) |
| **Day 3** | Demo: screenshots, GIF, `demo/` scenario scripts (A6, A8) |
| **Day 4** | Trust: create the issue backlog, CONTRIBUTING note, security advisory note (A13 + issue-backlog) |
| **Day 5** | Release: `v1.0.0` with release notes + first launch post (A12, A14) |
| **Day 6** | Ship: post to the community list, gather first real users |
| **Day 7** | Respond: fix reported bugs, close the loop with issue updates |

## 7. Campaign targets (aspirational, not guarantees)

```
100+ genuine stars
 20+ forks
 10+ real issues
  5+ contributors
 20+ installations/users
  1 strong release
  1 excellent demo (GIF + sample report)
  1 excellent README
  1 active development week
```

## 8. The hard rules

- **Never buy stars, forks or engagement.** No bot accounts, no star exchanges,
  no fake issues or PRs, no automated comment flooding, no fake download
  counts. Inflated numbers do not create project activity — real users do.
- Every public claim must be backed by something verifiable: a passing CI, a
  committed sample report, a reproducible `demo/` scenario.
- Issue feedback and respond to every question; momentum compounds.

## 9. Metrics to watch (weekly)

- Stars / forks / issues / PRs / contributors
- `report.html` sample views (GitHub traffic for the repo)
- Users who report back: OS, number of repos, repos synced, failures, bugs
- Open issue age and response time
