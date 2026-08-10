# Reports & the Journal

Every run — success, failure, blocked, or nothing-changed — produces two audit records: a human-readable HTML report and a machine-readable JSONL journal. Neither is optional (Rule 2).

## The HTML report

Generated after every run to:

```text
<base>\urgithub\.urgithub\reports\report.html
<base>\urgithub\.urgithub\reports\archive\
```

Older reports are archived and kept per `report.archive_keep_days` (default 90 days). Open it with `python urgithub.py --report` or let it auto-open (`report.auto_open`, default on).

## What a report contains

| Section | Records |
|---|---|
| Header & run summary | When the run started, the trigger that started it, overall result |
| Stat cards | Counts: discovered, scanned, synchronized, commits created, pushes, failures, blocked |
| Activity timeline | Chronological log of every step in the run |
| Per-repository details | State, before/after commit identifiers, actions taken |
| All repositories | Full discovery view across your account |
| Files & last commit | Changed files (up to `report.files_max`, default 500) and latest commit per repo |
| Security & size | Secret findings, oversized files, warnings |
| Environment drift | Changes detected in the environment snapshot |

The report is an **execution record, not only a success page** — failures and blocked operations are reported as clearly as successes.

## First place to look when something is wrong

When synchronization is blocked, open `report.html` and check for:

- divergence
- detected secrets
- invalid repository state
- missing remote
- authorization failure
- repository access failure
- unsupported state

## The JSONL journal

An append-only, machine-readable event log stored as one JSON object per line:

```json
{"ts":"...","op":"scan","repo":"...","trigger":"startup","success":true,"sha_before":"...","sha_after":"...","blocked":false}
{"ts":"...","op":"push","repo":"...","trigger":"every_hours","success":true,"sha_before":"...","sha_after":"..."}
{"ts":"...","op":"sync","repo":"...","trigger":"file_change","success":false,"blocked":true,"reason":"secrets"}
```

Each event represents one operation or state transition and supports analysis of:

- when the operation occurred
- which repository was involved
- what trigger initiated it
- whether the operation succeeded
- what commit identifiers were involved
- whether the operation was blocked

> **Do not manually edit runtime journal files** unless you understand the consequences — they are append-only audit records.

## Related settings

| Setting | Default | Purpose |
|---|---|---|
| `report.auto_open` | `true` | Open `report.html` in the browser after a run |
| `report.archive` | `true` | Archive old reports |
| `report.archive_keep_days` | `90` | Retention for archived reports |
| `report.show_files` / `files_max` | `true` / `500` | Show file lists, capped at 500 per repo |

Next: [Troubleshooting](troubleshooting.md) — common problems and their fixes.
