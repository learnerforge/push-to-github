# Security Policy

URGithub is a local Git repository operations manager. Its security model is conservative by design: it **never** runs destructive Git operations (`reset`, force-push, rebase, `clean`), detects secrets before anything is pushed, and blocks — rather than silently fixing — anything unsafe.

## Supported Versions

Only the current release line receives security fixes. Older releases are supported for migration only.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

Please **do not post security issues or secrets in public issues.** Report privately:

- **Private advisory:** use GitHub's "Report a vulnerability" flow at
  https://github.com/learnerforge/push-to-github/security/advisories/new
- **Email:** the maintainer (Ganesh Bakkera) with the subject `URGithub security report`

When reporting, include:

- Operating system, Python version, Git version, GitHub CLI version
- URGithub version and the trigger used
- Steps to reproduce and the relevant `report.html` information
- What you expected vs. what actually happened

**Redact all secrets before sending** — GitHub tokens, passwords, private keys, personal access tokens, and private repository contents.

### What happens next

- Acknowledgment within **48 hours**.
- A status update within **7 days** of triage.
- If accepted, a fix is prepared and released, and the vulnerability is disclosed after the fix ships.
- If declined, you will receive an explanation of why the report does not qualify.

## Security baseline

- Secret detection is on by default (`security.block_on_secrets`). Anything flagged is reported and **never pushed**.
- The engine never force-pushes and never merges divergent history automatically — blocked operations are intentional safety results, not bugs.
- Use the least-privilege GitHub token scopes possible; URGithub authenticates through your GitHub CLI session and never stores GitHub credentials itself.
