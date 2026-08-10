import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from .paths import Paths

HOME_CONFIG_DIR = Path.home() / ".urgithub"
LOCATOR_FILE = HOME_CONFIG_DIR / "base.txt"

DEFAULTS = {
    "base_location": "",
    "registered": False,
    "registered_at": None,
    "environment_snapshot": {},
    "github_owner": "auto",
    "clone_missing_repos": True,
    "skip_forks": False,
    "commit_policy": {
        "auto_commit": False,
        "message_prefix": "sync:",
    },
    "push": {
        "push_all_branches": False,
        "timeout_seconds": 60,
    },
    "shutdown": {
        "enabled": True,
        "quick_push": True,
        "timeout_seconds": 30,
        "open_report": False,
    },
    "report": {
        "auto_open": True,
        "archive": True,
        "archive_keep_days": 90,
        "show_files": True,
        "files_max": 500,
    },
    "security": {
        "block_on_secrets": True,
        "patterns": [".env*", "*.pem", "*.key", "credentials.json", "secrets.json", "*.p12"],
        "content_patterns": [
            "-----BEGIN [A-Z ]*PRIVATE KEY-----",
            "gh[opsur]_[A-Za-z0-9]{20,}",
            "AKIA[0-9A-Z]{16}",
            "AIza[0-9A-Za-z\\-_]{35}",
            "xox[baprs]-[0-9A-Za-z\\-]{10,}",
            "sk_live_[0-9A-Za-z]{20,}",
            "sk-[A-Za-z0-9_\\-]{24,}",
            "(?i)(api[_-]?key|secret|password|passwd|access[_-]?token)\\s*[:=]\\s*['\"][^'\"]{8,}['\"]",
        ],
        "allow_files": [],
        "max_scan_bytes": 1048576,
    },
    "limits": {
        "max_file_mb": 100,
        "warn_file_mb": 50,
        "block_on_oversize": True,
    },
    "deleted_repo_policy": {
        "confirm_scans": 3,
        "confirm_days": 7,
        "require_remote_confirmation": True,
        "require_user_confirmation": True,
    },
    "notify": {
        "toast_on_failure": True,
        "email": {
            "enabled": False,
            "smtp": "",
            "recipients": [],
        },
        "webhook": {
            "discord": "",
            "slack": "",
            "github_actions": False,
        },
    },
    "triggers": {
        "startup": True,
        "shutdown": True,
        "every_hours": 3,
        "every_minutes": 0,
        "at_time": None,
        "file_change": True,
        "manual": True,
    },
}


def deep_merge(base, override):
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def read_locator():
    try:
        if LOCATOR_FILE.exists():
            text = LOCATOR_FILE.read_text(encoding="utf-8").strip()
            if text:
                return text
    except OSError:
        pass
    return None


def write_locator(base_location):
    HOME_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOCATOR_FILE.write_text(str(base_location), encoding="utf-8")


class Config:
    def __init__(self, raw=None, base_location=None):
        self._data = deep_merge(DEFAULTS, raw or {})
        if base_location:
            self._data["base_location"] = base_location
        self.paths = Paths(self._data.get("base_location") or "")

    @classmethod
    def load(cls):
        base = read_locator()
        if not base:
            return cls({})
        cfg_path = Paths(base).config
        raw = {}
        try:
            if cfg_path.exists():
                raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raw = {}
        return cls(raw, base_location=base)

    def save(self):
        self._data["base_location"] = str(self.paths.base_location)
        self.paths.ensure_all()
        tmp = self.paths.config.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.paths.config)

    def register(self, snapshot):
        self._data["registered"] = True
        self._data["registered_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._data["environment_snapshot"] = snapshot
        self.save()

    @property
    def registered(self):
        return bool(self._data.get("registered"))

    def get(self, key, default=None):
        return self._data.get(key, default)
