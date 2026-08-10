import json
import logging
import os
import queue
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from . import prompt
from . import scheduler
from . import watch
from .config import Config
from .envcheck import EnvCheck
from .journal import Journal
from .registry import Registry
from .runner import run_trigger

TICK_MS = 20_000
MAX_LOG_LINES = 3000
LOG_KEEP = 1500

OK = "#1a7f37"
BAD = "#cf222e"
WARN = "#9a6700"
MUTED = "#57606a"
BG = "#f6f8fa"
PANEL = "#ffffff"
SIDEBAR = "#24292f"
SIDEBAR_FG = "#e6edf3"
SIDEBAR_ACTIVE = "#2f3742"


def _get_key(data, dotted, default=None):
    node = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def _set_key(data, dotted, value):
    parts = dotted.split(".")
    node = data
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value


class _WidgetHandler(logging.Handler):
    def __init__(self, emit):
        super().__init__()
        self._emit = emit
        self.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S"))

    def emit(self, record):
        try:
            self._emit(self.format(record))
        except Exception:
            pass


class ControlCenter:
    def __init__(self, cfg, log, root=None):
        import tkinter as tk

        self.cfg = cfg
        self.log = log
        self._firing = False
        self.output = None
        self._log_lines = []
        self._dash_values = {}
        self._settings_fields = []
        self._json_text = None
        self._ui_queue = queue.Queue()
        self.root = root if root is not None else tk.Tk()
        self.root.title("URGithub Control Center")
        self.root.geometry("980x660")
        self.root.minsize(840, 560)
        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        self._build_shell()
        self._attach_handler()
        prompt.register_confirm(self._ask_user)
        self._show("dashboard")
        self._start_resident()
        self._start_watcher()
        self._pump()

    def _ask_user(self, message):
        """Answer pipeline confirmations with a modal dialog.

        Runs from a worker thread: the dialog is queued to the Tk main thread
        and this method blocks until the user answers.
        """
        import threading

        from tkinter import messagebox

        if threading.current_thread() is threading.main_thread():
            return messagebox.askyesno("URGithub", message)
        result = {}
        done = threading.Event()

        def _dialog():
            try:
                result["ok"] = messagebox.askyesno("URGithub", message)
            finally:
                done.set()

        self._ui(_dialog)
        done.wait(timeout=3600)
        return bool(result.get("ok"))

    # ------------------------------------------------------------- shell
    def _build_shell(self):
        import tkinter as tk

        header = tk.Frame(self.root, bg=PANEL, padx=16, pady=10)
        header.pack(fill="x")
        tk.Label(header, text="URGithub", font=("Segoe UI", 18, "bold"), fg=SIDEBAR, bg=PANEL).pack(side="left")
        self._header_lbl = tk.Label(header, text="", font=("Segoe UI", 10), bg=PANEL)
        self._header_lbl.pack(side="left", padx=12)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)
        sidebar = tk.Frame(body, bg=SIDEBAR, width=180)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self._content = tk.Frame(body, bg=BG)
        self._content.pack(side="left", fill="both", expand=True)

        self._nav_buttons = {}
        for name, label in (("dashboard", "Dashboard"), ("repos", "Repositories"),
                            ("schedule", "Schedule"), ("settings", "Settings"),
                            ("logs", "Logs"), ("help", "Help")):
            btn = tk.Button(sidebar, text=label, command=lambda n=name: self._show(n),
                            bg=SIDEBAR, fg=SIDEBAR_FG, activebackground=SIDEBAR_ACTIVE,
                            activeforeground="#ffffff", relief="flat", anchor="w",
                            padx=18, pady=11, font=("Segoe UI", 11), bd=0)
            btn.pack(fill="x")
            self._nav_buttons[name] = btn

        statusbar = tk.Frame(self.root, bg="#eaeef2", padx=12, pady=5)
        statusbar.pack(fill="x", side="bottom")
        self._status_lbl = tk.Label(statusbar, text="", bg="#eaeef2", anchor="w")
        self._status_lbl.pack(side="left", fill="x", expand=True)
        self._next_lbl = tk.Label(statusbar, text="", bg="#eaeef2", anchor="e")
        self._next_lbl.pack(side="right")

    def _show(self, name):
        import tkinter as tk

        for n, btn in self._nav_buttons.items():
            if n == name:
                btn.configure(bg=PANEL, fg=SIDEBAR)
            else:
                btn.configure(bg=SIDEBAR, fg=SIDEBAR_FG)
        self.output = None
        for child in self._content.winfo_children():
            child.destroy()
        frame = tk.Frame(self._content, bg=BG, padx=18, pady=14)
        frame.pack(fill="both", expand=True)
        getattr(self, f"_build_{name}")(frame)
        self._refresh_statusbar()

    # ------------------------------------------------------------- helpers
    def _spawn(self, fn, *args):
        threading.Thread(target=fn, args=args, daemon=True).start()

    def _ui(self, fn, *args):
        """Queue a call to run on the Tk main thread (thread-safe)."""
        self._ui_queue.put((fn, args))

    def _pump(self):
        try:
            while True:
                fn, args = self._ui_queue.get_nowait()
                try:
                    fn(*args)
                except Exception:
                    pass
        except queue.Empty:
            pass
        try:
            self.root.after(100, self._pump)
        except Exception:
            pass

    def _log(self, message):
        line = f"{datetime.now().strftime('%H:%M:%S')}  {message}"
        self._log_lines.append(line)
        if len(self._log_lines) > MAX_LOG_LINES:
            self._log_lines = self._log_lines[-LOG_KEEP:]
        self._ui(self._append_log, line)

    def _append_log(self, line):
        if self.output is not None:
            try:
                self.output.configure(state="normal")
                self.output.insert("end", line + "\n")
                self.output.see("end")
                self.output.configure(state="disabled")
            except Exception:
                pass

    def _attach_handler(self):
        logging.getLogger().addHandler(_WidgetHandler(self._log))

    def _quit(self):
        prompt.register_confirm(None)
        self.root.destroy()

    def run(self):
        self.root.mainloop()

    # ------------------------------------------------------------- status
    @staticmethod
    def _last_outcome(journal):
        try:
            lines = journal.path.read_text(encoding="utf-8").strip().splitlines()
        except OSError:
            return None
        for line in reversed(lines):
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("phase") == "run-end":
                return record.get("outcome")
        return None

    @staticmethod
    def _outcome_color(outcome):
        if outcome in ("ok", "clean"):
            return OK
        if outcome == "partial":
            return WARN
        if outcome == "failed":
            return BAD
        return MUTED

    @staticmethod
    def _fmt_next(nexts):
        if not nexts:
            return "no repeating schedule"
        return ", ".join(f"{kind}: {when:%Y-%m-%d %H:%M}" for kind, when in nexts[:2])

    def _refresh_statusbar(self):
        snapshot = self.cfg.get("environment_snapshot", {})
        github = snapshot.get("github", {})
        login = github.get("login", "")
        if self.cfg.registered:
            self._header_lbl.configure(text=f"GitHub: {login or '?'}   Base: {self.cfg.paths.base_location}", fg=OK)
        else:
            self._header_lbl.configure(text="Not registered — open Settings -> Re-run setup wizard", fg=BAD)
        outcome = self._last_outcome(Journal(self.cfg.paths.journal))
        parts = []
        parts.append("registered" if self.cfg.registered else "NOT REGISTERED")
        parts.append(f"last run: {outcome or '-'}")
        try:
            registry = Registry(self.cfg.paths.registry).load()
            parts.append(f"repos: {len(registry)}")
        except Exception:
            pass
        self._status_lbl.configure(text="  |  ".join(parts))
        try:
            nexts = scheduler.compute_next_runs(self.cfg)
            self._next_lbl.configure(text="next: " + self._fmt_next(nexts))
        except Exception:
            pass

    # ------------------------------------------------------------- resident
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
        self._refresh_statusbar()
        self.root.after(TICK_MS, self._tick)

    def _start_watcher(self):
        if self.cfg.get("triggers", {}).get("file_change"):
            threading.Thread(
                target=watch.run_watcher,
                args=(self.cfg, self.log, 10, 30),
                daemon=True,
            ).start()

    def _fire(self, trigger):
        if trigger == "scheduled" and self._firing:
            return
        self._log(f"Firing trigger: {trigger}")
        if trigger == "scheduled":
            self._firing = True

        def worker():
            try:
                run_trigger(trigger, interactive=False)
            except Exception as exc:
                self._log(f"Run failed: {exc}")
            finally:
                if trigger == "scheduled":
                    self._firing = False
                self._ui(self._refresh_statusbar)

        self._spawn(worker)

    # ------------------------------------------------------------- dashboard
    def _build_dashboard(self, frame):
        import tkinter as tk

        if not self.cfg.registered:
            tk.Label(frame, text="Not registered", font=("Segoe UI", 16, "bold"), fg=BAD, bg=BG).pack(pady=(60, 8))
            tk.Label(frame, text="URGithub needs a one-time registration before it can operate.", bg=BG).pack()
            tk.Button(frame, text="Open Setup Wizard", command=self._open_setup, width=24).pack(pady=16)
            tk.Label(frame, text="The wizard checks Git, GitHub CLI, authentication and your base folder,\n"
                                 "then this Control Center becomes your dashboard.", bg=BG, justify="center",
                     font=("Segoe UI", 9), fg=MUTED).pack(pady=8)
            return

        tk.Label(frame, text="Dashboard", font=("Segoe UI", 15, "bold"), bg=BG).pack(anchor="w")

        actions = tk.Frame(frame, bg=BG)
        actions.pack(fill="x", pady=(10, 8))
        for label, cmd in (("Scan now", lambda: self._fire("manual_scan")),
                           ("Sync now", lambda: self._fire("manual_sync")),
                           ("Open report", self._open_report),
                           ("Re-check environment", self._refresh_dashboard)):
            tk.Button(actions, text=label, command=cmd, padx=8).pack(side="left", padx=3)

        grid = tk.Frame(frame, bg=PANEL, bd=1, relief="solid")
        grid.pack(fill="x")
        self._dash_values = {}
        rows = [
            "Registered", "Base location", "Git installed", "Git version",
            "Identity", "GitHub login", "Push scope (repo)", "GitHub reachable",
            "Base writable", "Managed repos", "Last run outcome", "Next scheduled",
        ]
        for i, label in enumerate(rows):
            tk.Label(grid, text=label, bg=PANEL, anchor="w", width=22,
                     font=("Segoe UI", 10)).grid(row=i // 2, column=(i % 2) * 2, sticky="w", padx=(14, 4), pady=4)
            value = tk.Label(grid, text="-", bg=PANEL, anchor="w", fg=MUTED, font=("Segoe UI", 10))
            value.grid(row=i // 2, column=(i % 2) * 2 + 1, sticky="w", padx=(4, 16), pady=4)
            self._dash_values[label] = value
        self._dash_warn = tk.Label(frame, text="", bg=BG, font=("Segoe UI", 9), fg=MUTED)
        self._dash_warn.pack(anchor="w", pady=(10, 0))
        self._refresh_dashboard()

    def _refresh_dashboard(self):
        def worker():
            checks = EnvCheck(self.cfg.paths.base_location).run()
            registry = Registry(self.cfg.paths.registry).load()
            outcome = self._last_outcome(Journal(self.cfg.paths.journal))
            nexts = scheduler.compute_next_runs(self.cfg)
            self._ui(self._update_dashboard, checks, registry, outcome, nexts)

        self._spawn(worker)

    def _update_dashboard(self, checks, registry, outcome, nexts):
        values = {
            "Registered": ("YES" if self.cfg.registered else "NO", OK if self.cfg.registered else BAD),
            "Base location": (str(self.cfg.paths.base_location), MUTED),
            "Git installed": ("YES" if checks.git_installed else "NO", OK if checks.git_installed else BAD),
            "Git version": (checks.git_version or "-", MUTED),
            "Identity": (f"{checks.identity['name']} <{checks.identity['email']}>"
                         if checks.identity["name"] else "not configured",
                         OK if checks.identity["name"] else BAD),
            "GitHub login": (checks.github_login or "-", MUTED),
            "Push scope (repo)": ("YES" if checks.can_push else "NO", OK if checks.can_push else BAD),
            "GitHub reachable": ("YES" if checks.github_reachable else "NO", OK if checks.github_reachable else BAD),
            "Base writable": ("YES" if checks.base_writable else "NO", OK if checks.base_writable else BAD),
            "Managed repos": (str(len(registry)), MUTED),
            "Last run outcome": (outcome or "-", self._outcome_color(outcome)),
            "Next scheduled": (self._fmt_next(nexts), MUTED),
        }
        for label, (value, color) in values.items():
            if label in self._dash_values:
                self._dash_values[label].configure(text=value, fg=color)
        self._dash_warn.configure(
            text="All environment checks passed." if checks.all_pass
            else "Some environment checks failed — open Settings -> Re-run setup wizard.",
            fg=OK if checks.all_pass else BAD,
        )

    def _open_report(self):
        html = self.cfg.paths.report_html
        if html.exists():
            os.startfile(str(html))
        else:
            self._log("No report.html yet — run a scan or sync first")

    # ------------------------------------------------------------- setup
    def _open_setup(self):
        subprocess.Popen([sys.executable, scheduler.script_path(), "--setup"])
        self._log("Setup wizard launched in a new window. Return here after registering.")
        self.root.after(5000, self._reload_after_setup)

    def _reload_after_setup(self):
        self.cfg = Config.load()
        if self.cfg.registered:
            self.cfg.paths.ensure_all()
            self._log("Registration detected — Control Center is now active.")
            self._refresh_statusbar()
            self._show("dashboard")
        else:
            self.root.after(5000, self._reload_after_setup)

    # ------------------------------------------------------------- repos
    def _build_repos(self, frame):
        import tkinter as tk
        from tkinter import ttk

        tk.Label(frame, text="Repositories", font=("Segoe UI", 15, "bold"), bg=BG).pack(anchor="w")
        actions = tk.Frame(frame, bg=BG)
        actions.pack(fill="x", pady=(10, 6))
        for label, cmd in (("Refresh", self._repos_refresh),
                           ("Open on GitHub", self._repo_github),
                           ("Open folder", self._repo_folder),
                           ("Verify all", self._repos_verify),
                           ("Forget selected", self._repo_forget),
                           ("Prune stale", self._repos_prune)):
            tk.Button(actions, text=label, command=cmd, padx=6).pack(side="left", padx=3)

        tree_frame = tk.Frame(frame, bg=BG)
        tree_frame.pack(fill="both", expand=True, pady=4)
        tree = ttk.Treeview(tree_frame, columns=("name", "status", "url", "last_sync", "path"), show="headings")
        for col, width in (("name", 170), ("status", 110), ("url", 210), ("last_sync", 80), ("path", 250)):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=width, anchor="w", stretch=True)
        tree.tag_configure("ok", foreground=OK)
        tree.tag_configure("bad", foreground=BAD)
        tree.tag_configure("warn", foreground=WARN)
        tree.tag_configure("muted", foreground=MUTED)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        tree.bind("<Double-1>", lambda _e: self._repo_github())
        self._repo_tree = tree
        self._repos_refresh()

    def _repos_refresh(self):
        def worker():
            registry = Registry(self.cfg.paths.registry).load()
            rows = sorted(registry.data.items())
            self._ui(self._render_repos, rows)

        self._spawn(worker)

    def _render_repos(self, rows):
        tree = getattr(self, "_repo_tree", None)
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)
        for name, entry in rows:
            status = entry.get("status", "?")
            if status in ("active", "ok", "clean"):
                tag = "ok"
            elif status in ("partial", "diverged"):
                tag = "warn"
            elif status in ("failed", "blocked", "quarantined", "deleted", "missing", "LOCAL_MISSING"):
                tag = "bad"
            else:
                tag = "muted"
            last_sync = (entry.get("last_sync_sha") or "")[:8]
            tree.insert("", "end", values=(name, status, entry.get("url", ""), last_sync, entry.get("path", "")),
                        tags=(tag,))

    def _selected_repo(self):
        tree = getattr(self, "_repo_tree", None)
        if tree is None:
            return None
        selection = tree.selection()
        if not selection:
            return None
        name = tree.item(selection[0], "values")[0]
        registry = Registry(self.cfg.paths.registry).load()
        return name, registry.get(name, {})

    def _repo_github(self):
        selected = self._selected_repo()
        if not selected:
            self._log("Select a repository first.")
            return
        url = selected[1].get("url", "")
        if not url:
            self._log(f"No remote URL for {selected[0]}.")
            return
        webbrowser.open(url)

    def _repo_folder(self):
        selected = self._selected_repo()
        if not selected:
            self._log("Select a repository first.")
            return
        path = selected[1].get("path", "")
        if path and Path(path).is_dir():
            os.startfile(path)
        else:
            self._log(f"Folder missing for {selected[0]}.")

    def _repos_verify(self):
        from . import gitops

        def worker():
            registry = Registry(self.cfg.paths.registry).load()
            if not registry.data:
                self._log("No repositories in the registry.")
                return
            ok_count = 0
            for name, entry in sorted(registry.data.items()):
                path = Path(entry.get("path", ""))
                problems = []
                if not path.is_dir():
                    problems.append("folder missing")
                elif not (path / ".git").exists():
                    problems.append("not a git repository")
                else:
                    remote = gitops.run_git(["remote", "get-url", "origin"], cwd=path, timeout=15)
                    if remote.returncode != 0:
                        problems.append("no origin remote")
                if problems:
                    self._log(f"Verify [{name}] PROBLEM: {', '.join(problems)}")
                else:
                    ok_count += 1
                    self._log(f"Verify [{name}] OK")
            self._log(f"Verified {ok_count}/{len(registry)} entries.")
            self._ui(self._repos_refresh)

        self._spawn(worker)

    def _repo_forget(self):
        import tkinter as tk
        from tkinter import messagebox

        selected = self._selected_repo()
        if not selected:
            self._log("Select a repository first.")
            return
        name = selected[0]
        if not messagebox.askyesno("URGithub", f"Forget '{name}' from the registry?\nFolder left on disk as-is."):
            return
        registry = Registry(self.cfg.paths.registry).load()
        registry.remove(name)
        registry.save()
        self._log(f"Forgot {name} (folder left on disk as-is).")
        self._repos_refresh()
        self._refresh_statusbar()

    def _repos_prune(self):
        import tkinter as tk
        from tkinter import messagebox

        stale = {"missing", "LOCAL_MISSING", "quarantined", "deleted"}
        registry = Registry(self.cfg.paths.registry).load()
        names = [n for n, e in registry.data.items() if e.get("status") in stale]
        if not names:
            self._log("No stale entries to prune.")
            return
        if not messagebox.askyesno("URGithub", f"Remove {len(names)} stale entr{'y' if len(names) == 1 else 'ies'}?\n" + ", ".join(sorted(names))):
            return
        for name in names:
            registry.remove(name)
        registry.save()
        self._log(f"Pruned {len(names)} stale entr{'y' if len(names) == 1 else 'ies'}.")
        self._repos_refresh()
        self._refresh_statusbar()

    # ------------------------------------------------------------- schedule
    def _build_schedule(self, frame):
        import tkinter as tk
        from tkinter import ttk

        tk.Label(frame, text="Schedule", font=("Segoe UI", 15, "bold"), bg=BG).pack(anchor="w")
        actions = tk.Frame(frame, bg=BG)
        actions.pack(fill="x", pady=(10, 6))
        for label, cmd in (("Refresh", self._schedule_refresh),
                           ("Install tasks", self._schedule_install),
                           ("Uninstall tasks", self._schedule_uninstall)):
            tk.Button(actions, text=label, command=cmd, padx=6).pack(side="left", padx=3)

        tree_frame = tk.Frame(frame, bg=BG)
        tree_frame.pack(fill="both", expand=True, pady=4)
        tree = ttk.Treeview(tree_frame, columns=("task", "state", "next_run"), show="headings")
        for col, width in (("task", 220), ("state", 120), ("next_run", 180)):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=width, anchor="w")
        tree.tag_configure("ok", foreground=OK)
        tree.tag_configure("bad", foreground=BAD)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._sched_tree = tree

        self._sched_next_lbl = tk.Label(frame, text="", bg=BG, anchor="w", font=("Segoe UI", 9), fg=MUTED)
        self._sched_next_lbl.pack(fill="x", pady=(6, 0))
        tk.Label(frame, text="This Control Center is resident while open: it also fires the scheduled trigger when a run is due,"
                             " and runs the file-change watcher when enabled.",
                 bg=BG, anchor="w", justify="left", font=("Segoe UI", 9), fg=MUTED).pack(anchor="w", pady=4)
        self._schedule_refresh()

    def _schedule_refresh(self):
        def worker():
            rows = scheduler.status(self.log)
            nexts = scheduler.compute_next_runs(self.cfg)
            self._ui(self._render_schedule, rows, nexts)

        self._spawn(worker)

    def _render_schedule(self, rows, nexts):
        tree = getattr(self, "_sched_tree", None)
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)
        if not rows:
            tree.insert("", "end", values=("(no tasks installed)", "", ""), tags=("bad",))
        for name, state, next_run in rows:
            tag = "ok" if "running" in state.lower() or "ready" in state.lower() else "ok"
            tree.insert("", "end", values=(name, state, next_run), tags=(tag,))
        self._sched_next_lbl.configure(text="Next runs from config: " + self._fmt_next(nexts))

    def _schedule_install(self):
        def worker():
            try:
                ok = scheduler.install(self.cfg, self.log)
                self._log("Schedule install: " + ("OK" if ok else "FAILED"))
                if not ok:
                    self._log("Shutdown task needs elevation — retrying with a UAC prompt...")
                    if scheduler.elevate_shutdown(self.cfg, self.log):
                        self._log("All scheduled tasks installed.")
                    else:
                        self._log("Shutdown task skipped (declined).")
            except Exception as exc:
                self._log(f"Schedule install failed: {exc}")
            self._ui(self._schedule_refresh)

        self._spawn(worker)

    def _schedule_uninstall(self):
        import tkinter as tk
        from tkinter import messagebox

        if not messagebox.askyesno("URGithub", "Uninstall all URGithub scheduled tasks?"):
            return

        def worker():
            try:
                ok = scheduler.uninstall(self.log)
                self._log("Schedule uninstall: " + ("OK" if ok else "FAILED"))
            except Exception as exc:
                self._log(f"Schedule uninstall failed: {exc}")
            self._ui(self._schedule_refresh)

        self._spawn(worker)

    # ------------------------------------------------------------- settings
    def _build_settings(self, frame):
        import tkinter as tk
        from tkinter import messagebox

        tk.Label(frame, text="Settings", font=("Segoe UI", 15, "bold"), bg=BG).pack(anchor="w")

        form = tk.Frame(frame, bg=PANEL, bd=1, relief="solid")
        form.pack(fill="x", pady=(10, 8))
        self._settings_fields = []
        fields = [
            ("triggers.startup", "Startup trigger", "bool"),
            ("triggers.shutdown", "Shutdown quick-push", "bool"),
            ("triggers.file_change", "File-change watcher", "bool"),
            ("triggers.every_hours", "Repeat every (hours, 0 = off)", "int"),
            ("triggers.every_minutes", "Repeat every (minutes, 0 = off)", "int"),
            ("triggers.at_time", "Daily at (HH:MM, empty = off)", "str"),
            ("commit_policy.auto_commit", "Auto-commit changes", "bool"),
            ("push.push_all_branches", "Push all branches", "bool"),
            ("report.auto_open", "Auto-open report after run", "bool"),
        ]
        for key, label, kind in fields:
            row = tk.Frame(form, bg=PANEL)
            row.pack(fill="x", padx=10, pady=3)
            tk.Label(row, text=label, width=34, anchor="w", bg=PANEL).pack(side="left")
            if kind == "bool":
                var = tk.BooleanVar(value=bool(_get_key(self.cfg._data, key)))
                tk.Checkbutton(row, variable=var, bg=PANEL).pack(side="left")
            else:
                var = tk.StringVar(value=str(_get_key(self.cfg._data, key) or ""))
                tk.Entry(row, textvariable=var, width=18).pack(side="left")
            self._settings_fields.append((key, var, kind))
        tk.Button(form, text="Save settings", command=self._save_settings).pack(pady=8)

        raw = tk.LabelFrame(frame, text="Advanced — raw config JSON", padx=8, pady=8, bg=BG)
        raw.pack(fill="both", expand=True, pady=(4, 0))
        self._json_text = tk.Text(raw, height=12, font=("Consolas", 9), bg="#0d1117", fg="#c9d1d9",
                                  insertbackground="#c9d1d9")
        self._json_text.pack(fill="both", expand=True)
        rbtns = tk.Frame(raw, bg=BG)
        rbtns.pack(fill="x", pady=(6, 0))
        tk.Button(rbtns, text="Load current config", command=self._load_raw).pack(side="left", padx=3)
        tk.Button(rbtns, text="Validate and save", command=self._save_raw).pack(side="left", padx=3)
        tk.Button(rbtns, text="Re-run setup wizard", command=self._open_setup).pack(side="right", padx=3)
        self._load_raw()

    def _save_settings(self):
        import tkinter as tk
        from tkinter import messagebox

        for key, var, kind in self._settings_fields:
            if kind == "bool":
                value = bool(var.get())
            elif kind == "int":
                raw = str(var.get()).strip()
                value = int(raw) if raw else 0
            else:
                value = str(var.get()).strip()
            _set_key(self.cfg._data, key, value)
        try:
            self.cfg.save()
        except OSError as exc:
            messagebox.showerror("URGithub", f"Could not save config:\n{exc}")
            return
        self._log("Settings saved.")
        if any(key.startswith("triggers.") for key, _, _ in self._settings_fields):
            self._log("Trigger settings changed — re-install the schedule to apply (Schedule tab).")
        self._refresh_statusbar()
        if self._json_text is not None:
            self._load_raw()
        messagebox.showinfo("URGithub", "Settings saved.")

    def _load_raw(self):
        self._json_text.delete("1.0", "end")
        self._json_text.insert("1.0", json.dumps(self.cfg._data, indent=2, ensure_ascii=False))

    def _save_raw(self):
        import tkinter as tk
        from tkinter import messagebox

        try:
            data = json.loads(self._json_text.get("1.0", "end"))
        except json.JSONDecodeError as exc:
            messagebox.showerror("URGithub", f"Invalid JSON:\n{exc}")
            return
        if not isinstance(data, dict):
            messagebox.showerror("URGithub", "Config must be a JSON object.")
            return
        try:
            new_cfg = Config(data, base_location=self.cfg.paths.base_location)
            new_cfg.save()
            self.cfg = new_cfg
        except OSError as exc:
            messagebox.showerror("URGithub", f"Could not save config:\n{exc}")
            return
        self._log("Raw config saved.")
        self._refresh_statusbar()
        messagebox.showinfo("URGithub", "Raw config saved.")

    # ------------------------------------------------------------- logs
    def _build_logs(self, frame):
        import tkinter as tk

        tk.Label(frame, text="Logs", font=("Segoe UI", 15, "bold"), bg=BG).pack(anchor="w")
        actions = tk.Frame(frame, bg=BG)
        actions.pack(fill="x", pady=(8, 6))
        tk.Button(actions, text="Clear view", command=self._clear_log_view).pack(side="left", padx=3)
        tk.Button(actions, text="Open log file", command=self._open_log_file).pack(side="left", padx=3)

        self.output = tk.Text(frame, height=16, state="disabled", font=("Consolas", 9),
                              bg="#0d1117", fg="#c9d1d9", insertbackground="#c9d1d9", wrap="word")
        self.output.pack(fill="both", expand=True)
        self.output.configure(state="normal")
        for line in self._log_lines:
            self.output.insert("end", line + "\n")
        self.output.configure(state="disabled")
        self.output.see("end")

    def _clear_log_view(self):
        self._log_lines.clear()
        if self.output is not None:
            self.output.configure(state="normal")
            self.output.delete("1.0", "end")
            self.output.configure(state="disabled")
        self._log("Log view cleared.")

    def _open_log_file(self):
        path = self.cfg.paths.logs / "application.log"
        if path.exists():
            os.startfile(str(path))
        else:
            self._log("No application.log yet.")

    # ------------------------------------------------------------- help
    def _build_help(self, frame):
        import tkinter as tk
        from . import __version__

        tk.Label(frame, text="Help", font=("Segoe UI", 15, "bold"), bg=BG).pack(anchor="w")
        lines = [
            ("URGithub", f"version {__version__} — universal Git repository operations manager."),
            ("Pipeline", "Every trigger (startup, scheduled, file change, manual) runs one pipeline: "
                         "discover repos → scan for changes/secrets → validate → sync/commit/push → report."),
            ("Triggers", "Scheduled tasks are managed on the Schedule tab. While this window is open it is also "
                         "resident: it fires the scheduled trigger when a run is due and watches for file changes."),
            ("Repositories", "Repos live under the base 'urgithub\\repos in github' folder. New folders are picked "
                             "up on the next scan. Use the Repositories tab to verify, open, forget or prune."),
            ("Report", "Each run writes reports/report.html plus an archive. Use 'Open report' on the Dashboard."),
            ("Logs", "All activity streams to the Logs tab and to logs/application.log."),
        ]
        card = tk.Frame(frame, bg=PANEL, bd=1, relief="solid")
        card.pack(fill="x", pady=(10, 8))
        for title, text in lines:
            tk.Label(card, text=title, bg=PANEL, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x", padx=12, pady=(10, 0))
            tk.Label(card, text=text, bg=PANEL, anchor="w", justify="left", wraplength=760,
                     font=("Segoe UI", 9)).pack(fill="x", padx=12, pady=(2, 0))
        paths_frame = tk.Frame(frame, bg=PANEL, bd=1, relief="solid")
        paths_frame.pack(fill="x")
        tk.Label(paths_frame, text="Paths", bg=PANEL, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x", padx=12, pady=(10, 0))
        for label, path in (("Base", self.cfg.paths.base_location), ("Config", self.cfg.paths.config),
                            ("Registry", self.cfg.paths.registry), ("Reports", self.cfg.paths.report_html),
                            ("Logs", self.cfg.paths.logs)):
            tk.Label(paths_frame, text=f"{label}:  {path}", bg=PANEL, anchor="w", justify="left",
                     font=("Consolas", 8), fg=MUTED).pack(fill="x", padx=12, pady=1)

        links_frame = tk.Frame(frame, bg=PANEL, bd=1, relief="solid")
        links_frame.pack(fill="x", pady=(8, 0))
        tk.Label(links_frame, text="Software download links", bg=PANEL, font=("Segoe UI", 10, "bold"),
                 anchor="w").pack(fill="x", padx=12, pady=(10, 0))
        from .wizard import DOWNLOAD_LINKS, SYSTEM
        for label, kind in (("Git", "git"), ("GitHub CLI", "gh"), ("Python", "python")):
            url = DOWNLOAD_LINKS[kind].get(SYSTEM, DOWNLOAD_LINKS[kind]["windows"])
            link = tk.Label(links_frame, text=f"{label}: {url}", bg=PANEL, fg="#0969da", cursor="hand2",
                            anchor="w", font=("Segoe UI", 9))
            link.pack(fill="x", padx=12, pady=1)
            link.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))
        buttons = tk.Frame(frame, bg=BG)
        buttons.pack(fill="x", pady=(10, 0))
        tk.Button(buttons, text="Open base folder", command=lambda: os.startfile(str(self.cfg.paths.base_location))).pack(side="left", padx=3)
        tk.Button(buttons, text="Open docs folder", command=lambda: os.startfile(str(Path(__file__).resolve().parent.parent / "docs"))).pack(side="left", padx=3)


def run_control_center():
    cfg = Config.load()
    if not cfg.registered:
        from .wizard import run_wizard

        base = run_wizard()
        if not base:
            return 1
        cfg = Config.load()
    cfg.paths.ensure_all()
    from .logs import setup_logging

    log = setup_logging(cfg.paths)
    try:
        ControlCenter(cfg, log).run()
    except Exception as exc:
        print(f"Control Center unavailable: {exc}")
        return 1
    return 0
