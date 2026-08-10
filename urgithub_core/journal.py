import json
import uuid
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Journal:
    def __init__(self, path):
        self.path = path

    def write(self, record):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def open_run(self, trigger):
        run_id = uuid.uuid4().hex[:8]
        self.write({
            "ts": utcnow(),
            "run_id": run_id,
            "trigger": trigger,
            "phase": "run-start",
            "outcome": "started",
        })
        return run_id

    def close_run(self, run_id, trigger, outcome, detail=None):
        record = {
            "ts": utcnow(),
            "run_id": run_id,
            "trigger": trigger,
            "phase": "run-end",
            "outcome": outcome,
        }
        if detail:
            record["detail"] = detail
        self.write(record)
