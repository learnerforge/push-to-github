from pathlib import Path


class Paths:
    def __init__(self, base_location):
        self.base_location = Path(base_location)
        self.root = self.base_location / "urgithub"
        self.logs = self.root / "logs"
        self.logs_history = self.logs / "history"
        self.repos = self.root / "repos in github"
        self.deleted = self.root / "deleted repos"
        self.run = self.root / "Run"
        self.data = self.root / ".urgithub"
        self.config = self.data / "config.json"
        self.database = self.data / "database"
        self.journal = self.database / "journal.jsonl"
        self.registry = self.database / "registry.json"
        self.reports = self.data / "reports"
        self.report_html = self.reports / "report.html"
        self.report_archive = self.reports / "archive"
        self.locks = self.data / "locks"
        self.run_lock = self.locks / "run.lock"
        self.cache = self.data / "cache"
        self.credentials = self.data / "credentials"

    def ensure_all(self):
        targets = [
            self.logs,
            self.logs_history,
            self.repos,
            self.deleted,
            self.run,
            self.data,
            self.database,
            self.reports,
            self.report_archive,
            self.locks,
            self.cache,
            self.credentials,
        ]
        for path in targets:
            path.mkdir(parents=True, exist_ok=True)
