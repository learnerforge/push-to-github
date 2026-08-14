import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import gitops
from .journal import utcnow


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
    permission: str = "UNKNOWN"
    secrets: list = field(default_factory=list)
    secret_findings: list = field(default_factory=list)
    oversize: list = field(default_factory=list)
    large: list = field(default_factory=list)
    files: list = field(default_factory=list)
    status: str = "READY"

    def to_dict(self):
        return {
            "repo": self.repo,
            "branch": self.branch,
            "head_sha": self.head_sha,
            "dirty": self.dirty,
            "modified": self.modified,
            "added": self.added,
            "deleted": self.deleted,
            "untracked": self.untracked,
            "staged": self.staged,
            "ignored": self.ignored,
            "ahead": self.ahead,
            "behind": self.behind,
            "has_upstream": self.has_upstream,
            "remote_configured": self.remote_configured,
            "remote_reachable": self.remote_reachable,
            "permission": self.permission,
            "secrets": self.secrets,
            "secret_findings": self.secret_findings,
            "oversize": self.oversize,
            "large": self.large,
            "status": self.status,
        }


def _repo_owner(url, fallback):
    path = (url or "").rstrip("/")
    parts = path.split("/")
    if len(parts) >= 2 and parts[-2]:
        return parts[-2]
    return fallback


def _status_counts(lines):
    untracked = added = deleted = modified = staged = 0
    for line in lines:
        if line.startswith("??"):
            untracked += 1
            continue
        x = line[0] if len(line) > 1 else " "
        y = line[1] if len(line) > 1 else " "
        if x in "AMDRC":
            staged += 1
        if x == "A" or y == "A":
            added += 1
        elif x == "D" or y == "D":
            deleted += 1
        else:
            modified += 1
    return untracked, added, deleted, modified, staged


def _name_matches(files, patterns):
    return [f for f in files if any(fnmatch.fnmatch(f, p) or fnmatch.fnmatch(Path(f).name, p) for p in patterns)]


def _allowed_files(files, patterns):
    if not patterns:
        return set()
    return {f for f in files if any(fnmatch.fnmatch(f, p) or fnmatch.fnmatch(Path(f).name, p) for p in patterns)}


def _is_binary(file_path, chunk=8192):
    try:
        with open(file_path, "rb") as fh:
            return b"\x00" in fh.read(chunk)
    except OSError:
        return True


def _content_findings(file_path, patterns, max_bytes):
    if not patterns or _is_binary(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read(max_bytes)
    except OSError:
        return []
    hits = []
    for pattern in patterns:
        try:
            if re.search(pattern, text):
                hits.append(pattern)
        except re.error:
            continue
    return hits


class Scanner:
    """Phase 3 — the 23-point inspection producing a ScanResult per repo."""

    def __init__(self, cfg, journal, log, run_id, trigger, interactive=False):
        self.cfg = cfg
        self.journal = journal
        self.log = log
        self.run_id = run_id
        self.trigger = trigger
        self.interactive = interactive
        self.owner = self.cfg.get("github_owner", "auto")
        if self.owner == "auto":
            self.owner = self.cfg.get("environment_snapshot", {}).get("github", {}).get("login", "")
        self.security = self.cfg.get("security", {})
        self.patterns = self.security.get("patterns", [])
        self.content_patterns = self.security.get("content_patterns", [])
        self.allow_files = self.security.get("allow_files", [])
        self.max_scan_bytes = int(self.security.get("max_scan_bytes", 1048576))
        self.limits = self.cfg.get("limits", {})

    def _j(self, phase, outcome, detail=None, repo=None):
        record = {
            "ts": utcnow(),
            "run_id": self.run_id,
            "trigger": self.trigger,
            "phase": phase,
            "outcome": outcome,
        }
        if repo:
            record["repo"] = repo
        if detail:
            record["detail"] = detail
        self.journal.write(record)

    def scan_repo(self, name, entry):
        path = Path(entry.get("path", ""))
        registry_status = entry.get("status")

        if registry_status == "quarantined":
            return ScanResult(name, status="QUARANTINED")
        if registry_status in ("deleted", "missing", "LOCAL_MISSING"):
            return ScanResult(name, status="MISSING")
        if not path.is_dir() or not (path / ".git").exists():
            return ScanResult(name, status="MISSING")

        result = self._inspect(name, path)
        self._j(
            "scan",
            "done" if result.status != "NOT_GIT" else "failed",
            result.to_dict(),
            repo=name,
        )
        return result

    def _inspect(self, name, path):
        r = ScanResult(name)

        # 2/3/4 — git works and directory readable
        chk = gitops.run_git(["rev-parse", "--git-dir"], cwd=path, timeout=15)
        if chk.returncode != 0:
            r.status = "NOT_GIT"
            return r

        # 5 — current branch
        br = gitops.run_git(["symbolic-ref", "--short", "HEAD"], cwd=path, timeout=15)
        r.branch = br.stdout.strip() if br.returncode == 0 else "(detached)"

        # 6 — HEAD available
        head = gitops.run_git(["rev-parse", "HEAD"], cwd=path, timeout=15)
        r.head_sha = (head.stdout or "").strip()[:7] if head.returncode == 0 else ""

        # 7 — remote configured
        remote = gitops.run_git(["remote", "get-url", "origin"], cwd=path, timeout=15)
        r.remote_configured = remote.returncode == 0
        url = remote.stdout.strip() if r.remote_configured else ""

        # 8 — remote reachable (non-interactive, fails fast)
        if r.remote_configured:
            ls = gitops.run_git(["ls-remote", "--heads", "origin"], cwd=path, timeout=20)
            r.remote_reachable = ls.returncode == 0

        # 9 — per-repo authorization (GitHub remotes only)
        if r.remote_reachable and self.owner and gitops.is_github_url(url):
            r.permission = self._permission(_repo_owner(url, self.owner), name)

        # 10–15 — working tree
        st = gitops.run_git(["status", "--porcelain"], cwd=path, timeout=20)
        lines = (st.stdout or "").splitlines()
        r.untracked, r.added, r.deleted, r.modified, r.staged = _status_counts(lines)
        r.dirty = bool(lines)

        ig = gitops.run_git(["status", "--porcelain", "--ignored"], cwd=path, timeout=20)
        r.ignored = sum(1 for line in (ig.stdout or "").splitlines() if line.startswith("!!"))

        # 16 — potential secrets (name + content) on tracked + untracked non-ignored files
        candidates = self._candidate_files(path)
        to_scan = [f for f in candidates if f not in _allowed_files(candidates, self.allow_files)]
        name_hits = _name_matches(to_scan, self.patterns)
        content_hits = []
        for f in to_scan:
            if f in name_hits:
                continue
            hits = _content_findings(path / f, self.content_patterns, self.max_scan_bytes)
            if hits:
                content_hits.append({"file": f, "patterns": hits})
        r.secrets = name_hits + [c["file"] for c in content_hits]
        r.secret_findings = [{"file": f, "kind": "name"} for f in name_hits]
        r.secret_findings += [{"file": c["file"], "kind": "content", "patterns": c["patterns"]} for c in content_hits]

        # 21/22 — file-size gate (GitHub hard limit on 100 MB per file)
        r.oversize, r.large = self._candidate_sizes(path, candidates)

        # 23 — per-file last commit (report "Files & Last Commit" section)
        r.files = self._file_commits(path)

        # 17/18 — ahead / behind vs upstream
        upstream = gitops.run_git(["rev-parse", "--abbrev-ref", "@{u}"], cwd=path, timeout=15)
        r.has_upstream = upstream.returncode == 0
        if r.has_upstream:
            rc = gitops.run_git(["rev-list", "--left-right", "--count", "@{u}...HEAD"], cwd=path, timeout=30)
            if rc.returncode == 0:
                try:
                    behind, ahead = (rc.stdout or "").split()
                    r.behind, r.ahead = int(behind), int(ahead)
                except ValueError:
                    pass

        # 19/20 — composite status
        r.status = self._compose(r)
        return r

    def _permission(self, owner, name):
        result = gitops.run_gh(["api", f"repos/{owner}/{name}", "--jq", ".permissions.push"], timeout=30)
        if result.returncode == 0:
            return "PUSH" if result.stdout.strip() == "true" else "READ"
        return "UNKNOWN"

    def _candidate_files(self, path):
        tracked = gitops.run_git(["ls-files"], cwd=path, timeout=20)
        untracked = gitops.run_git(["ls-files", "--others", "--exclude-standard"], cwd=path, timeout=20)
        files = (tracked.stdout or "").splitlines() + (untracked.stdout or "").splitlines()
        return [f for f in files if f]

    def _file_commits(self, path):
        """Per-file last commit time, GitHub-style.

        One ``git log`` walk (newest-first, author date + touched files) records
        the first-seen commit date per path — the last time that file changed.
        Untracked files carry an empty ``committed_at`` (uncommitted).
        """
        tracked = (gitops.run_git(["ls-files"], cwd=path, timeout=20).stdout or "").splitlines()
        untracked = (gitops.run_git(["ls-files", "--others", "--exclude-standard"], cwd=path, timeout=20).stdout or "").splitlines()
        walk = gitops.run_git(
            ["log", "--date=iso-strict", "--pretty=format:%ad%x00", "--name-only"],
            cwd=path,
            timeout=60,
        )
        last = {}
        current = ""
        for line in (walk.stdout or "").splitlines():
            if "\x00" in line:
                current = line.replace("\x00", "")
            elif line and line not in last:
                last[line] = current
        files = [{"file": f, "committed_at": last.get(f, "")} for f in tracked if f]
        files += [{"file": f, "committed_at": ""} for f in untracked if f and f not in last]
        return files

    def _candidate_sizes(self, path, files):
        max_b = int(self.limits.get("max_file_mb", 100)) * 1024 * 1024
        warn_b = int(self.limits.get("warn_file_mb", 50)) * 1024 * 1024
        oversize, large = [], []
        for f in files:
            try:
                size = (path / f).stat().st_size
            except OSError:
                continue
            if size > max_b:
                oversize.append({"file": f, "bytes": size})
            elif size > warn_b:
                large.append({"file": f, "bytes": size})
        return oversize, large

    def _compose(self, r):
        if not r.remote_configured:
            return "NO_REMOTE"
        if not r.remote_reachable:
            return "AUTH_FAIL"
        if r.permission == "NONE":
            return "NO_PERMISSION"
        if r.ahead > 0 and r.behind > 0:
            return "DIVERGED"
        if r.dirty:
            return "DIRTY"
        return "READY"

    def render(self, result):
        lines = [
            result.repo,
            "─" * len(result.repo),
            f"Branch: {result.branch}",
            f"Working tree: {'DIRTY' if result.dirty else 'CLEAN'}",
        ]
        if result.dirty:
            lines += [
                f"Modified: {result.modified}",
                f"Added: {result.added}",
                f"Deleted: {result.deleted}",
                f"Untracked: {result.untracked}",
                f"Staged: {result.staged}",
            ]
        lines += [
            f"Local commits ahead: {result.ahead}",
            f"Remote commits ahead: {result.behind}",
            f"Remote: {'configured' if result.remote_configured else 'NOT CONFIGURED'}",
            f"Remote access: {result.permission}",
            f"Security: {'FAIL' if result.secrets else 'PASS'}",
            f"Oversize files: {len(result.oversize)}",
            f"Sync: {result.status}",
        ]
        if result.secrets:
            lines.append("  Flagged files:")
            for f in result.secrets:
                lines.append(f"    ! {f}")
        for o in result.oversize:
            lines.append(f"    ! oversized: {o['file']} ({o['bytes'] // (1024 * 1024)} MB)")
        return "\n".join(lines)


def validate_result(result, cfg):
    """Security + size + divergence + auth gates. Returns (ok, reason)."""
    security = cfg.get("security", {})
    if security.get("block_on_secrets", True) and result.secrets:
        return False, "secrets"
    limits = cfg.get("limits", {})
    if limits.get("block_on_oversize", True) and result.oversize:
        return False, "oversize files"
    if result.status == "DIVERGED":
        return False, "divergence"
    if result.status == "AUTH_FAIL":
        return False, "remote unreachable"
    if result.status == "NO_PERMISSION":
        return False, "no push permission"
    if result.status == "NO_REMOTE":
        return False, "no remote configured"
    if result.status in ("MISSING", "NOT_GIT", "QUARANTINED"):
        return False, result.status.lower()
    return True, ""
