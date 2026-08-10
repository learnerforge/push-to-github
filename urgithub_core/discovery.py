import json
from datetime import datetime, timezone
from pathlib import Path

from . import gitops
from .journal import utcnow
from .registry import Registry


def _local_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _utcnow_dt():
    return datetime.now(timezone.utc)


def _repo_name(url):
    """Extract the repository name from a git remote URL.

    Handles https://github.com/owner/Repo.git, https://..., and the scp-like
    git@github.com:owner/Repo.git form.
    """
    text = (url or "").strip().rstrip("/").replace("\\", "/").rstrip("/")
    if not text:
        return ""
    if "://" in text:
        path = text.split("://", 1)[1]
    elif ":" in text and "@" in text:
        path = text.split(":", 1)[1]
    else:
        path = text
    segments = [s for s in path.rstrip("/").split("/") if s]
    if not segments:
        return ""
    name = segments[-1]
    return name[:-4] if name.endswith(".git") else name


class Discovery:
    """Phase 2 — find and register repositories.

    Scans 'repos in github\\' for valid git repos, reconciles against the
    GitHub account (gh repo list), clones repos known to be missing, and
    runs the staged quarantine workflow for repos deleted on GitHub.
    """

    def __init__(self, cfg, journal, log, run_id, trigger, interactive=False):
        self.cfg = cfg
        self.paths = cfg.paths
        self.journal = journal
        self.log = log
        self.run_id = run_id
        self.trigger = trigger
        self.interactive = interactive
        self.owner = self._owner()
        self.registry = Registry(self.paths.registry).load()
        self.events = []
        self.github_names = set()
        self.github_urls = {}
        self.github_fork_names = set()

    def _owner(self):
        owner = self.cfg.get("github_owner")
        if owner and owner != "auto":
            return owner
        login = self.cfg.get("environment_snapshot", {}).get("github", {}).get("login", "")
        return login or None

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

    def event(self, type_, repo, **extra):
        event = {"type": type_, "repo": repo, "timestamp": _local_ts()}
        event.update(extra)
        self.events.append(event)

    def run(self):
        self._j("discover", "started")
        github_repos = self._list_github_repos() if self.owner else {}
        self.github_names = set(github_repos)
        self.github_urls = github_repos
        self._discover_local()
        if self.owner and self.github_names:
            self._reconcile(self.github_names)
        self._bootstrap_seed()
        self._clone_missing()
        self._mark_missing()
        self.registry.save()
        self._j("discover", "done", {"managed": len(self.registry)})
        return self.events

    # -- GitHub listing -------------------------------------------------

    def _list_github_repos(self):
        result = gitops.run_gh(
            ["repo", "list", self.owner, "--limit", "1000", "--json", "nameWithOwner,url,isFork"],
            timeout=60,
        )
        if result.returncode != 0:
            self.log.warning(
                "Could not list GitHub repos (%s) — reconciliation skipped",
                (result.stderr or "").strip()[:80],
            )
            return {}
        try:
            rows = json.loads(result.stdout)
            self.github_fork_names = {
                e["nameWithOwner"].split("/")[-1] for e in rows if e.get("isFork")
            }
            return {e["nameWithOwner"].split("/")[-1]: e["url"] for e in rows}
        except (ValueError, KeyError, TypeError):
            return {}

    # -- Local discovery ------------------------------------------------

    def _discover_local(self):
        if not self.paths.repos.is_dir():
            return
        for item in sorted(self.paths.repos.iterdir()):
            if not item.is_dir() or item.name.startswith(("_", ".")):
                continue
            if not (item / ".git").exists():
                continue
            entry = self.registry.get(item.name)
            if entry is None:
                entry = self._adopt_or_create(item)
            else:
                entry["path"] = str(item)
                entry["last_seen"] = utcnow()
                if entry.get("status") in ("missing", "LOCAL_MISSING"):
                    entry["status"] = "active"
                    self.log.info("[%s] reappeared — restored to active", item.name)
                    self._j("discover", "restored", repo=item.name)
                url = gitops.run_git(["remote", "get-url", "origin"], cwd=item, timeout=15)
                if url.returncode == 0:
                    entry["url"] = url.stdout.strip().removesuffix(".git")

    def _origin_info(self, item):
        """Return (repo name from the origin remote, origin url sans .git)."""
        url = gitops.run_git(["remote", "get-url", "origin"], cwd=item, timeout=15)
        if url.returncode != 0:
            return "", ""
        raw = url.stdout.strip()
        return _repo_name(raw), raw.removesuffix(".git")

    def _adopt_or_create(self, item):
        """A folder not in the registry is either a brand-new repo or the local
        rename of an existing one. When its origin remote matches a registry
        entry that is currently missing, we adopt it — reusing that entry and
        its history instead of creating a duplicate that would later be
        quarantined as 'deleted on GitHub' (the case-B problem).
        """
        origin_name, origin_url = self._origin_info(item)
        if origin_name:
            existing = self.registry.get(origin_name)
            if existing is not None:
                stale = existing.get("status") in ("missing", "LOCAL_MISSING")
                original = Path(existing.get("path", ""))
                moved = not original.is_dir()
                same_folder = original.resolve() == item.resolve()
                if stale or moved or same_folder:
                    self._adopt(existing, item, origin_name)
                    return existing
        entry = {
            "path": str(item),
            "url": origin_url,
            "first_seen": utcnow(),
            "last_seen": utcnow(),
            "last_scan_sha": "",
            "last_sync_sha": "",
            "status": "active",
            "auto_commit": self.cfg.get("commit_policy", {}).get("auto_commit", False),
            "diverged_since": None,
            "deletion_hits": 0,
            "deletion_suspected_at": None,
            "quarantined_at": None,
            "quarantined_to": None,
        }
        self.registry.set(item.name, entry)
        self.event("discovered", item.name)
        self.log.info("[%s] discovered — added to registry", item.name)
        return entry

    def _adopt(self, entry, item, origin_name):
        old_key = None
        for key, candidate in self.registry.data.items():
            if candidate is entry:
                old_key = key
                break
        entry["path"] = str(item)
        entry["last_seen"] = utcnow()
        entry["status"] = "active"
        entry["diverged_since"] = None
        if old_key and old_key != origin_name:
            self.registry.remove(old_key)
            self.registry.set(origin_name, entry)
        self.event("adopted", origin_name, local_folder=item.name, reason="local rename")
        self.log.info(
            "[%s] adopted local folder '%s' (origin %s) — local rename reconciled",
            origin_name, item.name, origin_name,
        )
        self._j("discover", "adopted", {"local_folder": item.name}, repo=origin_name)

    # -- GitHub reconciliation ------------------------------------------

    def _reconcile(self, github_names):
        for name, entry in list(self.registry.data.items()):
            if entry.get("status") in ("quarantined", "deleted"):
                continue
            local_path = Path(entry.get("path", ""))
            if not local_path.is_dir() or not (local_path / ".git").exists():
                continue
            if name in github_names:
                entry["deletion_hits"] = 0
                if entry.get("status") == "pending":
                    entry["status"] = "active"
                    entry["deletion_suspected_at"] = None
                    self.log.info("[%s] confirmed alive on GitHub — cleared", name)
                    self._j("quarantine", "cleared", repo=name)
                if entry.get("status") != "active":
                    entry["status"] = "active"
                continue
            if not gitops.is_github_url(entry.get("url", "")):
                continue
            self._check_remote(name, entry, local_path)

    def _check_remote(self, name, entry, local_path):
        result = gitops.run_gh(["api", f"repos/{self.owner}/{name}", "--jq", ".name"], timeout=30)
        if result.returncode == 404:
            self._deletion_hit(name, entry, local_path)
        elif result.returncode == 0:
            actual = (result.stdout or "").strip()
            if actual and actual != name:
                self._rename_repo(name, actual, entry, local_path)
            else:
                entry["deletion_hits"] = 0
                if entry.get("status") == "pending":
                    entry["status"] = "active"
                    entry["deletion_suspected_at"] = None
        else:
            self.log.debug(
                "[%s] gh api check failed (%s) — treated as connection failure, not deletion",
                name,
                (result.stderr or "").strip()[:80],
            )

    def _deletion_hit(self, name, entry, local_path):
        entry["deletion_hits"] = entry.get("deletion_hits", 0) + 1
        if entry.get("status") != "pending":
            entry["status"] = "pending"
            entry["deletion_suspected_at"] = utcnow()
            self.log.warning(
                "[%s] remote 404 — deletion suspected (hit %d)",
                name,
                entry["deletion_hits"],
            )
            self._j("quarantine", "suspected", {"hits": entry["deletion_hits"]}, repo=name)
        policy = self.cfg.get("deleted_repo_policy", {})
        hits_needed = int(policy.get("confirm_scans", 3))
        days_needed = int(policy.get("confirm_days", 7))
        elapsed_ok = True
        if days_needed > 0 and entry.get("deletion_suspected_at"):
            try:
                suspected = datetime.strptime(entry["deletion_suspected_at"], "%Y-%m-%dT%H:%M:%SZ")
                elapsed_days = (_utcnow_dt() - suspected.replace(tzinfo=timezone.utc)).days
                elapsed_ok = elapsed_days >= days_needed
            except ValueError:
                elapsed_ok = True
        if entry["deletion_hits"] >= hits_needed and elapsed_ok:
            self._confirm_quarantine(name, entry, local_path, policy)

    def _confirm_quarantine(self, name, entry, local_path, policy):
        from . import prompt

        require_user = bool(policy.get("require_user_confirmation", True))
        if require_user:
            message = (
                f"[{name}] confirmed deleted on GitHub ({entry['deletion_hits']}x 404). "
                "Move to 'deleted repos'?"
            )
            if not prompt.confirm(message, interactive=self.interactive):
                self.log.info("[%s] user chose to keep local copy", name)
                self._j("quarantine", "kept", repo=name)
                return
        self._quarantine(name, entry, local_path)

    def _quarantine(self, name, entry, local_path):
        dest = self.paths.deleted / name
        counter = 1
        while dest.exists():
            dest = self.paths.deleted / f"{name}_{counter}"
            counter += 1
        try:
            local_path.rename(dest)
        except OSError as exc:
            self.log.error("[%s] quarantine move failed: %s", name, exc)
            self.event("fail", name, reason="quarantine move failed")
            return
        entry["status"] = "quarantined"
        entry["quarantined_at"] = utcnow()
        entry["quarantined_to"] = str(dest)
        entry["deletion_hits"] = 0
        self.event("removed", name, dest=str(dest))
        self.log.info("[%s] quarantined to %s", name, dest)
        self._j("quarantine", "moved", {"to": str(dest)}, repo=name)

    def _rename_repo(self, old_name, new_name, entry, local_path):
        target = self.paths.repos / new_name
        if target.exists():
            self.log.warning("[%s] target %s already exists — skipping rename", old_name, new_name)
            return
        existing = self.registry.get(new_name)
        if existing is not None and existing is not entry:
            self.log.warning("[%s] registry entry %s already exists — skipping rename", old_name, new_name)
            return
        try:
            local_path.rename(target)
        except OSError as exc:
            self.log.error("[%s] rename to %s failed: %s", old_name, new_name, exc)
            self.event("fail", old_name, reason="rename failed")
            return
        self.registry.remove(old_name)
        entry["path"] = str(target)
        entry["status"] = "active"
        self.registry.set(new_name, entry)
        self.event("renamed", new_name, renamed_from=old_name)
        self.log.info("[%s] renamed to %s", old_name, new_name)
        self._j("rename", "done", {"from": old_name, "to": new_name})

    # -- Clone missing --------------------------------------------------

    def _bootstrap_seed(self):
        """Seed the registry with every GitHub repo not present locally.

        Without this, a fresh registration never clones anything: the registry
        starts empty and ``_clone_missing`` only recovers entries that already
        exist. Seeding marks remote-only repos as ``missing`` so the existing
        clone step pulls them all into 'repos in github'. Forks are skipped
        only when ``skip_forks`` is enabled.
        """
        if not self.owner or not self.github_names:
            return
        if not self.cfg.get("clone_missing_repos", True):
            return
        skip_forks = bool(self.cfg.get("skip_forks", False))
        for name in sorted(self.github_names):
            if self.registry.get(name) is not None:
                continue
            if skip_forks and name in self.github_fork_names:
                self.log.debug("[%s] fork — skipped per skip_forks", name)
                continue
            entry = {
                "path": "",
                "url": self.github_urls.get(name, self._github_url(name)),
                "first_seen": utcnow(),
                "last_seen": utcnow(),
                "last_scan_sha": "",
                "last_sync_sha": "",
                "status": "missing",
                "auto_commit": self.cfg.get("commit_policy", {}).get("auto_commit", False),
                "diverged_since": None,
                "deletion_hits": 0,
                "deletion_suspected_at": None,
                "quarantined_at": None,
                "quarantined_to": None,
            }
            self.registry.set(name, entry)
            self._j("discover", "seeded", {"url": entry["url"]}, repo=name)
            self.log.info("[%s] not local — seeded for clone", name)

    def _clone_missing(self):
        if not self.cfg.get("clone_missing_repos", True):
            return
        for name, entry in list(self.registry.data.items()):
            if entry.get("status") not in ("missing", "LOCAL_MISSING"):
                continue
            url = entry.get("url") or self.github_urls.get(name) or self._github_url(name)
            if not url:
                continue
            if name not in self.github_names and not entry.get("url"):
                self.log.debug("[%s] no known remote for missing repo — skipping clone", name)
                continue
            target = self.paths.repos / name
            if target.exists():
                continue
            self._clone(name, url, target, entry)

    def _github_url(self, name):
        if not self.owner:
            return ""
        return f"https://github.com/{self.owner}/{name}.git"

    def _clone(self, name, url, target, entry):
        self.log.info("[%s] cloning missing repo from %s", name, url)
        self._j("clone", "started", {"url": url}, repo=name)
        if self.owner:
            result = gitops.run_gh(["repo", "clone", f"{self.owner}/{name}", str(target)], timeout=180)
            if result.returncode != 0:
                result = gitops.run_git(["clone", url, str(target)], timeout=180)
        else:
            result = gitops.run_git(["clone", url, str(target)], timeout=180)
        if result.returncode != 0:
            self.log.warning(
                "[%s] clone failed (%s)", name, (result.stderr or "").strip()[:80]
            )
            self._j("clone", "failed", {"error": (result.stderr or "").strip()[:120]}, repo=name)
            return
        entry["path"] = str(target)
        entry["status"] = "active"
        entry["last_seen"] = utcnow()
        self.event("cloned", name)
        self.log.info("[%s] cloned", name)
        self._j("clone", "done", repo=name)

    # -- Missing marker -------------------------------------------------

    def _mark_missing(self):
        for name, entry in self.registry.data.items():
            if entry.get("status") in ("quarantined", "deleted"):
                continue
            path = Path(entry.get("path", ""))
            if not path.exists():
                if entry.get("status") not in ("missing", "LOCAL_MISSING"):
                    entry["status"] = "missing"
                    self.log.warning("[%s] local folder missing", name)
                    self._j("discover", "missing", repo=name)
