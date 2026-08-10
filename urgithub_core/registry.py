import json
from pathlib import Path


class Registry:
    def __init__(self, path):
        self.path = Path(path)
        self._data = {}

    def load(self):
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}
        return self

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def get(self, name, default=None):
        return self._data.get(name, default)

    def set(self, name, entry):
        self._data[name] = entry

    def remove(self, name):
        self._data.pop(name, None)

    @property
    def data(self):
        return self._data

    def __len__(self):
        return len(self._data)
