from pathlib import Path

from . import gitops


class EnvCheck:
    def __init__(self, base_location=None):
        self.base_location = Path(base_location) if base_location else None
        self.git_installed = False
        self.git_version = ""
        self.identity = {"name": "", "email": ""}
        self.gh_installed = False
        self.github_authenticated = False
        self.github_login = ""
        self.github_scopes = []
        self.github_reachable = False
        self.base_writable = False

    def run(self):
        self._check_git()
        self._check_identity()
        self._check_gh()
        self._check_base()
        return self

    def _check_git(self):
        result = gitops.run_git(["--version"])
        self.git_installed = result.returncode == 0
        self.git_version = result.stdout.strip() if self.git_installed else ""

    def _check_identity(self):
        if not self.git_installed:
            return
        result = gitops.run_git(["config", "--global", "user.name"])
        self.identity["name"] = result.stdout.strip() if result.returncode == 0 else ""
        result = gitops.run_git(["config", "--global", "user.email"])
        self.identity["email"] = result.stdout.strip() if result.returncode == 0 else ""

    def _check_gh(self):
        version = gitops.run_gh(["--version"])
        self.gh_installed = version.returncode == 0
        if not self.gh_installed:
            return
        auth = gitops.run_gh(["auth", "status"])
        self.github_authenticated = auth.returncode == 0
        self.github_scopes = self._parse_scopes(auth.stdout or "")
        if self.github_authenticated:
            user = gitops.run_gh(["api", "user", "--jq", ".login"])
            self.github_login = user.stdout.strip() if user.returncode == 0 else ""
            self.github_reachable = user.returncode == 0
        else:
            self.github_reachable = False

    @staticmethod
    def _parse_scopes(text):
        for line in text.splitlines():
            lowered = line.lower()
            if "token scopes" not in lowered:
                continue
            _, _, value = line.partition(":")
            return [s.strip().strip("'\"") for s in value.split(",") if s.strip()]
        return []

    def _check_base(self):
        if not self.base_location:
            return
        try:
            self.base_location.mkdir(parents=True, exist_ok=True)
            probe = self.base_location / ".urgithub_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            self.base_writable = True
        except OSError:
            self.base_writable = False

    @property
    def can_push(self):
        return self.github_authenticated and "repo" in self.github_scopes

    @property
    def all_pass(self):
        return (
            self.git_installed
            and bool(self.identity["name"])
            and bool(self.identity["email"])
            and self.gh_installed
            and self.can_push
            and self.github_reachable
            and self.base_writable
        )

    def snapshot(self):
        from .journal import utcnow

        return {
            "git": {
                "installed": self.git_installed,
                "version": self.git_version,
            },
            "identity": {
                "name": self.identity["name"],
                "email": self.identity["email"],
            },
            "github": {
                "authenticated": self.github_authenticated,
                "host": "github.com",
                "login": self.github_login,
                "cli_installed": self.gh_installed,
                "scopes": self.github_scopes,
                "can_push": self.can_push,
            },
            "last_check": utcnow(),
        }
