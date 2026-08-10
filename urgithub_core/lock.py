import os
import time


class RunLock:
    def __init__(self, path, stale_seconds=15):
        self.path = path
        self.stale_seconds = stale_seconds

    def acquire(self):
        if not self.path.exists():
            self.path.write_text(str(os.getpid()), encoding="utf-8")
            return True
        try:
            age = time.time() - self.path.stat().st_mtime
            if age > self.stale_seconds:
                self.path.write_text(str(os.getpid()), encoding="utf-8")
                return True
            return False
        except OSError:
            self.path.write_text(str(os.getpid()), encoding="utf-8")
            return True

    def release(self):
        try:
            if self.path.exists() and self.path.read_text(encoding="utf-8").strip() == str(os.getpid()):
                self.path.unlink()
        except OSError:
            pass
