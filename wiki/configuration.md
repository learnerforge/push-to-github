# Configuration

URGithub stores its configuration in `<base>\urgithub\.urgithub\config.json`. Every setting is also exposed through the CLI — you never need to hand-edit JSON.

## Reading and setting values

```bash
python urgithub.py --config                        # show full configuration
python urgithub.py --config triggers.every_hours   # read one value (dot path)
python urgithub.py --config triggers.every_hours 6 # set one value
```

After changing scheduling-related settings, reapply the scheduler and verify:

```bash
python urgithub.py --schedule install
python urgithub.py --schedule status
```

## Settings reference

### Repository behavior

| Key | Default | Purpose |
|---|---|---|
| `github_owner` | `auto` | GitHub owner to reconcile against (`auto` = logged-in user) |
| `clone_missing_repos` | `true` | Clone local repos that exist remotely but not locally |
| `skip_forks` | `false` | Skip forked repositories |

### Commit policy

| Key | Default | Purpose |
|---|---|---|
| `commit_policy.auto_commit` | `false` | Automatically commit local changes |
| `commit_policy.message_prefix` | `sync:` | Prefix prepended to auto-commit messages |

### Push

| Key | Default | Purpose |
|---|---|---|
| `push.push_all_branches` | `false` | Push every branch instead of the current branch |
| `push.timeout_seconds` | `60` | Timeout per push operation |

### Shutdown (Windows)

| Key | Default | Purpose |
|---|---|---|
| `shutdown.enabled` | `true` | Enable quick-push before shutdown |
| `shutdown.quick_push` | `true` | Push pending changes during shutdown |
| `shutdown.timeout_seconds` | `30` | Time budget for the shutdown push |
| `shutdown.open_report` | `false` | Open the report during shutdown |

### Report

| Key | Default | Purpose |
|---|---|---|
| `report.auto_open` | `true` | Open `report.html` in the browser after a run |
| `report.archive` | `true` | Archive old reports |
| `report.archive_keep_days` | `90` | How long archived reports are kept |
| `report.show_files` | `true` | Show file lists in the report |
| `report.files_max` | `500` | Maximum files listed per repository |

### Security

| Key | Default | Purpose |
|---|---|---|
| `security.block_on_secrets` | `true` | Block sync when secrets are detected |
| `security.patterns` | see below | Filename patterns treated as secrets |
| `security.content_patterns` | see below | Content regexes for secret detection |
| `security.allow_files` | `[]` | Explicit file allow-list exceptions |
| `security.max_scan_bytes` | `1048576` | Maximum bytes scanned per file |

### Limits

| Key | Default | Purpose |
|---|---|---|
| `limits.max_file_mb` | `100` | Hard size limit per file |
| `limits.warn_file_mb` | `50` | Warning threshold per file |
| `limits.block_on_oversize` | `true` | Block sync for files over the hard limit |

### Deleted / renamed repos

| Key | Default | Purpose |
|---|---|---|
| `deleted_repo_policy.confirm_scans` | `3` | Consecutive scans before a deletion is flagged |
| `deleted_repo_policy.confirm_days` | `7` | Days before a deletion is confirmed |
| `deleted_repo_policy.require_remote_confirmation` | `true` | Require the remote to confirm deletion |
| `deleted_repo_policy.require_user_confirmation` | `true` | Require explicit user confirmation |

### Notifications

| Key | Default | Purpose |
|---|---|---|
| `notify.toast_on_failure` | `true` | Show a desktop toast on failed runs |
| `notify.email.enabled` | `false` | Email notifications (off by default) |
| `notify.email.smtp` / `recipients` | — | SMTP host and recipient list |
| `notify.webhook.discord` / `slack` | `""` | Webhook URLs (empty = disabled) |
| `notify.webhook.github_actions` | `false` | Send GitHub Actions-compatible events |

### Triggers

| Key | Default | Purpose |
|---|---|---|
| `triggers.startup` | `true` | Run at login |
| `triggers.shutdown` | `true` | Quick-push at shutdown (Windows) |
| `triggers.every_hours` | `3` | Repeat interval in hours (`0` = off) |
| `triggers.every_minutes` | `0` | Repeat interval in minutes (`0` = off) |
| `triggers.at_time` | `null` | Single daily time, e.g. `18:00` |
| `triggers.file_change` | `true` | Run when watched files change |
| `triggers.manual` | `true` | Allow manual runs |

Next: [Automation](automation.md) — how triggers become real scheduled runs on each OS.
