# Security & the Safety Model

## Non-destructive by design

URGithub **never** runs destructive Git operations. It will not `reset`, force-push (`--force`), rebase, or clean your working tree — under any trigger, ever.

The synchronize operation is deliberately conservative:

```bash
git fetch
git pull --ff-only      # fast-forward only
git commit              # only when the policy allows
git push
```

## Secret detection

Every file is scanned before anything is pushed. Secrets are matched two ways (both configured under `security.*`):

### Filename patterns

```
.env*            *.pem            *.key
credentials.json secrets.json     *.p12
```

### Content patterns (regex)

| What it catches | Example pattern |
|---|---|
| Private keys | `-----BEGIN [A-Z ]*PRIVATE KEY-----` |
| GitHub tokens | `gh[opsur]_[A-Za-z0-9]{20,}` |
| AWS access keys | `AKIA[0-9A-Z]{16}` |
| Google API keys | `AIza[0-9A-Za-z\-_]{35}` |
| Slack tokens | `xox[baprs]-[0-9A-Za-z\-]{10,}` |
| Stripe live keys | `sk_live_[0-9A-Za-z]{20,}` |
| Generic API keys | `sk-[A-Za-z0-9_\-]{24,}` |
| Inline secrets | `(?i)(api_key|secret|password|token)\s*[:=]\s*"..."` |

Files larger than `security.max_scan_bytes` (default 1 MB) are not fully scanned. Add exceptions via `security.allow_files` when you are certain a match is a false positive.

## File size limits

| Setting | Default | Behavior |
|---|---|---|
| `limits.warn_file_mb` | 50 MB | Warned in the report |
| `limits.max_file_mb` | 100 MB | Blocks sync when `block_on_oversize` is on (default) |

## Blocked-operation reasons

Synchronization stops and reports when any of these are detected:

| Reason | What it means |
|---|---|
| **Divergence** | Local and remote histories have diverged — never merged automatically |
| **Secrets** | Secret patterns were detected in the working tree |
| **Invalid state** | Repository is in an unexpected/invalid condition |
| **Missing remote** | No `origin` remote is configured |
| **Authorization failure** | No permission to push |
| **Repository access failure** | Remote unreachable or inaccessible |
| **Oversize files** | Files over the hard size limit |
| **Uncommitted changes** | Dirty tree without `commit_policy.auto_commit` |

A blocked operation is an **intentional safety result**, not a bug. Do not bypass it — inspect `report.html` first.

## The four safety rules

| Rule | Why it exists |
|---|---|
| **Rule 0** — No registration → no operations | Unregistered runs only show the setup wizard; nothing else runs |
| **Rule 1** — No scan → no sync | The sync engine only touches repositories scanned in the same run |
| **Rule 2** — Every run produces a report | Failures and blocks are always visible, never silent |
| **Rule 3** — Trigger type does not matter | Scheduled and automatic runs use the same safe pipeline as manual ones |

## Deleted / renamed repository policy

URGithub will not act on a locally deleted repository without a confirmation chain:

- `deleted_repo_policy.confirm_scans` — **3** consecutive scans must flag it.
- `deleted_repo_policy.confirm_days` — **7** days must pass.
- `deleted_repo_policy.require_remote_confirmation` — the remote must confirm deletion.
- `deleted_repo_policy.require_user_confirmation` — you must explicitly confirm.

## Recommendations

- Never commit credentials or secrets into any repository — block-on-secrets is the last line of defense.
- Use the least-privilege GitHub token/permission set URGithub can work with.
- Keep the runtime directory (`urgithub\.urgithub`) protected — it holds configuration and reports.
- Review `report.html` for blocked operations before investigating further.
- Rotate any secret that was ever pushed, even once.

Next: [Report & Journal](report.md) — everything the report and journal record.
