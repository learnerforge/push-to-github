from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import gitops
from .journal import utcnow
from .scan import ScanResult, validate_result


@dataclass
class SyncResult:
    repo: str
    action: str = "skipped"          # pushed | clean | committed | skipped | blocked | failed
    before_sha: str = ""
    after_sha: str = ""
    reason: str = ""
    changed: list = field(default_factory=list)

    def to_dict(self):
        return {
            "repo": self.repo,
            "action": self.action,
            "before_sha": self.before_sha,
            "after_sha": self.after_sha,
            "reason": self.reason,
            "changed": self.changed,
        }


def _utc_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _short(ref):
    return (ref or "").strip()[:7]


class SyncEngine:
    """Phase 4 — safe pull, commit, push. Never force, never rebase, never reset."""

    FORBIDDEN = ["reset", "--force", "--hard", "rebase", "clean"]

    def __init__(self, cfg, journal, log, run_id, trigger, interactive=False):
        self.cfg = cfg
        self.journal = journal
        self.log = log
        self.run_id = run_id
        self.trigger = trigger
        self.interactive = interactive
        self.commit_policy = cfg.get("commit_policy", {})
        self.push_cfg = cfg.get("push", {})
        self.push_timeout = int(self.push_cfg.get("timeout_seconds", 60))

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

    # -- Full sync (startup / manual sync) ------------------------------

    def run(self, scan_results, registry):
        results = []
        for scan in scan_results:
            entry = registry.get(scan.repo)
            results.append(self.sync_repo(scan, entry))
        return results

    def sync_repo(self, scan, entry):
        path = Path(entry.get("path", "")) if entry else None
        if not path or not path.is_dir():
            return SyncResult(scan.repo, action="blocked", reason="missing")

        ok, reason = validate_result(scan, self.cfg)
        if not ok:
            return SyncResult(scan.repo, action="blocked", reason=reason)

        auto_commit = bool((entry or {}).get("auto_commit", self.commit_policy.get("auto_commit", False)))
        if scan.dirty and not auto_commit:
            self._j("sync", "skipped", {"action": "working-tree changes, auto_commit off"}, repo=scan.repo)
            return SyncResult(scan.repo, action="skipped", reason="dirty, auto_commit off")

        return self._perform(path, scan, auto_commit)

    def _perform(self, path, scan, auto_commit):
        result = SyncResult(scan.repo)
        result.before_sha = _short(gitops.run_git(["rev-parse", "HEAD"], cwd=path, timeout=15).stdout)

        # Safe pull: fetch then fast-forward only.
        fetch = gitops.run_git(["fetch", "origin"], cwd=path, timeout=self.push_timeout)
        if fetch.returncode != 0:
            result.action = "failed"
            result.reason = "fetch failed: " + (fetch.stderr or "").strip()[:100]
            self._j("sync", "failed", {"action": "pull", "error": result.reason}, repo=scan.repo)
            return result

        upstream_ok = gitops.run_git(["rev-parse", "--verify", "@{u}"], cwd=path, timeout=15)
        if upstream_ok.returncode != 0:
            result.action = "skipped"
            result.reason = "no upstream configured"
            self._j("sync", "skipped", {"action": "pull", "reason": result.reason}, repo=scan.repo)
            return result

        ff = gitops.run_git(["merge", "--ff-only", "@{u}"], cwd=path, timeout=self.push_timeout)
        if ff.returncode != 0:
            result.action = "blocked"
            result.reason = "divergence (fast-forward failed)"
            self._j("sync", "blocked", {"action": "pull", "error": (ff.stderr or "").strip()[:120]}, repo=scan.repo)
            return result

        # Commit if policy requires.
        if auto_commit and scan.dirty:
            add = gitops.run_git(["add", "-A"], cwd=path, timeout=self.push_timeout)
            if add.returncode != 0:
                result.action = "failed"
                result.reason = "git add failed"
                self._j("sync", "failed", {"action": "add"}, repo=scan.repo)
                return result
            prefix = self.commit_policy.get("message_prefix", "sync:")
            message = f"{prefix} {scan.branch} {_utc_ts()}"
            commit = gitops.run_git(["commit", "-m", message], cwd=path, timeout=self.push_timeout)
            if commit.returncode != 0:
                result.action = "failed"
                result.reason = (commit.stderr or "").strip()[:120]
                self._j("sync", "failed", {"action": "commit"}, repo=scan.repo)
                return result
            self._j("sync", "committed", {"message": message}, repo=scan.repo)

        # Recompute ahead/behind, then push.
        rc = gitops.run_git(["rev-list", "--left-right", "--count", "@{u}...HEAD"], cwd=path, timeout=30)
        ahead = 0
        if rc.returncode == 0:
            try:
                behind, ahead = (rc.stdout or "").split()
                behind, ahead = int(behind), int(ahead)
            except ValueError:
                ahead = 0
        if ahead <= 0:
            result.action = "clean"
            result.reason = "up to date"
            self._j("sync", "clean", repo=scan.repo)
            return result

        push = self._push(path)
        result.after_sha = _short(gitops.run_git(["rev-parse", "HEAD"], cwd=path, timeout=15).stdout)
        if push == "ok":
            result.action = "pushed"
            result.reason = ""
            result.changed = self._changed_files(path, scan.branch)
            self._j(
                "sync",
                "pushed",
                {"before": result.before_sha, "after": result.after_sha, "files": len(result.changed)},
                repo=scan.repo,
            )
        else:
            result.action = "failed"
            result.reason = "push failed: " + push
            self._j("sync", "failed", {"action": "push", "error": push}, repo=scan.repo)
        return result

    def _push(self, path):
        args = ["push"]
        if self.push_cfg.get("push_all_branches", False):
            args += ["--all"]
        if any(token in args for token in self.FORBIDDEN):
            return "refusing unsafe push arguments"
        push = gitops.run_git(args + ["origin"], cwd=path, timeout=self.push_timeout)
        if push.returncode == 0:
            return "ok"
        return (push.stderr or "").strip()[:120]

    def _changed_files(self, path, branch):
        log = gitops.run_git(["log", "-1", "--name-status", "--format="], cwd=path, timeout=30)
        files = []
        for line in (log.stdout or "").splitlines():
            parts = line.split("\t")
            if len(parts) == 2:
                status = parts[0][0]
                files.append({"status": status, "path": parts[1]})
        return files

    # -- Quick push (shutdown) ------------------------------------------

    def quick_push(self, name, entry, timeout_seconds):
        path = Path(entry.get("path", ""))
        result = SyncResult(name)
        result.before_sha = _short(gitops.run_git(["rev-parse", "HEAD"], cwd=path, timeout=15).stdout)
        if not (path / ".git").exists():
            result.action = "skipped"
            result.reason = "not a git repo"
            return result
        self._j("quick_push", "started", repo=name)
        push = gitops.run_git(["push", "origin", "HEAD"], cwd=path, timeout=timeout_seconds)
        if push.returncode == 0:
            result.action = "pushed"
            result.after_sha = _short(gitops.run_git(["rev-parse", "HEAD"], cwd=path, timeout=15).stdout)
            self._j("quick_push", "pushed", {"before": result.before_sha, "after": result.after_sha}, repo=name)
        else:
            result.action = "failed"
            result.reason = (push.stderr or "").strip()[:120]
            self._j("quick_push", "failed", {"error": result.reason}, repo=name)
        return result
