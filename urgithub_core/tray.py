import logging
import os
import threading
from datetime import datetime

from . import scheduler, watch
from .config import Config
from .journal import utcnow
from .logs import setup_logging
from .runner import run_trigger

TICK_MS = 20_000


class _WidgetHandler(logging.Handler):
    def __init__(self, emit):
        super().__init__()
        self._emit = emit
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        try:
            self._emit(self.format(record))
        except Exception:
            pass


class ControlPanel:
    def __init__(self, cfg, log):
        import tkinter as tk

        self.cfg = cfg
        self.log = log
        self._firing = False
        self.root = tk.Tk()
        self.root.title("URGithub Control Panel")
        self.root.geometry("480x560")
        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        self._build()
        self._attach_handler()
        self._start_resident()
        self._start_watcher()

    def _build(self):
        import tkinter as tk

        info = tk.Label(
            self.root,
            text=f"Base: {self.cfg.paths.base_location}",
            wraplength=450,
            justify="left",
            anchor="w",
        )
        info.pack(fill="x", padx=10, pady=(10, 4))

        row = tk.Frame(self.root)
        row.pack(fill="x", padx=10)
        tk.Button(row, text="Scan Now", command=lambda: self._fire("manual_scan")).pack(side="left", padx=2)
        tk.Button(row, text="Sync Now", command=lambda: self._fire("manual_sync")).pack(side="left", padx=2)
        tk.Button(row, text="Open Report", command=self._open_report).pack(side="left", padx=2)
        tk.Button(row, text="Schedule Status", command=self._schedule_status).pack(side="left", padx=2)
        tk.Button(row, text="Install Schedule", command=self._install_schedule).pack(side="left", padx=2)
        tk.Button(row, text="Quit", command=self._quit).pack(side="right", padx=2)

        self.output = tk.Text(self.root, height=20)
        self.output.pack(fill="both", expand=True, padx=10, pady=10)
        self.output.configure(state="disabled")

    def _log(self, message):
        def _append():
            self.output.configure(state="normal")
            self.output.insert("end", f"{utcnow()}  {message}\n")
            self.output.see("end")
            self.output.configure(state="disabled")

        self.root.after(0, _append)

    def _attach_handler(self):
        logging.getLogger().addHandler(_WidgetHandler(self._log))

    def _fire(self, trigger):
        if trigger == "scheduled" and self._firing:
            return
        self._log(f"Firing trigger: {trigger}")
        if trigger == "scheduled":
            self._firing = True
        threading.Thread(target=self._run_worker, args=(trigger,), daemon=True).start()

    def _run_worker(self, trigger):
        try:
            run_trigger(trigger, interactive=False)
        finally:
            if trigger == "scheduled":
                self._firing = False

    def _open_report(self):
        html = self.cfg.paths.report_html
        if html.exists():
            os.startfile(str(html))
        else:
            self._log("No report.html yet — run a scan first")

    def _schedule_status(self):
        self._log("Querying Task Scheduler...")
        threading.Thread(target=self._status_worker, daemon=True).start()

    def _status_worker(self):
        try:
            rows = scheduler.status(self.log)
            if not rows:
                self._log("No URGithub tasks registered.")
                return
            for name, state, next_run in rows:
                self._log(f"{name}  [{state}]" + (f"  next: {next_run}" if next_run else ""))
        except Exception as exc:
            self._log(f"Schedule status failed: {exc}")

    def _install_schedule(self):
        self._log("Installing tasks...")
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self):
        try:
            ok = scheduler.install(self.cfg, self.log)
            self._log("Schedule install: " + ("OK" if ok else "FAILED"))
        except Exception as exc:
            self._log(f"Install failed: {exc}")

    def _start_resident(self):
        self._tick()

    def _tick(self):
        try:
            for _, when in scheduler.compute_next_runs(self.cfg):
                if when <= datetime.now():
                    self._fire("scheduled")
                    break
        except Exception as exc:
            self.log.warning("Resident tick failed: %s", exc)
        self.root.after(TICK_MS, self._tick)

    def _start_watcher(self):
        if self.cfg.get("triggers", {}).get("file_change"):
            threading.Thread(
                target=watch.run_watcher,
                args=(self.cfg, self.log, 10, 30),
                daemon=True,
            ).start()

    def _quit(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def run_tray():
    cfg = Config.load()
    if not cfg.registered:
        print("URGithub is not registered. Run: python urgithub.py --setup")
        return 1
    cfg.paths.ensure_all()
    log = setup_logging(cfg.paths)
    try:
        ControlPanel(cfg, log).run()
    except Exception as exc:
        print(f"Control panel unavailable: {exc}")
        return 1
    return 0
