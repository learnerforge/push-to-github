import logging
import platform
import subprocess
import threading
import webbrowser
from pathlib import Path

from . import gitops
from .config import Config, write_locator
from .envcheck import EnvCheck
from .paths import Paths

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog

    TKINTER_OK = True
except Exception:
    TKINTER_OK = False

CREATE_NEW_CONSOLE = 0x00000010

SYSTEM = platform.system().lower()

_APT_DISTROS = {"ubuntu", "debian", "linuxmint", "pop", "elementary"}
_DNF_DISTROS = {"fedora", "rhel", "centos", "rocky", "alma"}
_PACMAN_DISTROS = {"arch", "manjaro", "endeavouros"}

# Official download pages, per OS. SYSTEM is platform.system().lower().
DOWNLOAD_LINKS = {
    "git": {
        "windows": "https://git-scm.com/download/win",
        "macos": "https://git-scm.com/download/mac",
        "linux": "https://git-scm.com/download/linux",
    },
    "gh": {
        "windows": "https://cli.github.com/",
        "macos": "https://cli.github.com/",
        "linux": "https://cli.github.com/",
    },
    "python": {
        "windows": "https://www.python.org/downloads/windows/",
        "macos": "https://www.python.org/downloads/macos/",
        "linux": "https://www.python.org/downloads/source/",
    },
}


def download_link(kind):
    links = DOWNLOAD_LINKS[kind]
    return links.get(SYSTEM, links["windows"])


def _linux_distro():
    try:
        text = Path("/etc/os-release").read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        if line.startswith("ID="):
            return line.split("=", 1)[1].strip().strip('"')
    return ""


def _git_linux_hints():
    distro = _linux_distro()
    if distro in _APT_DISTROS:
        hints = ["Detected: Debian/Ubuntu family", "sudo apt update", "sudo apt install -y git"]
    elif distro in _DNF_DISTROS:
        hints = ["Detected: Fedora/RHEL family", "sudo dnf install -y git"]
    elif distro in _PACMAN_DISTROS:
        hints = ["Detected: Arch family", "sudo pacman -S --noconfirm git"]
    else:
        hints = [
            "Distro not recognized — use your package manager:",
            "sudo apt install git      (Debian/Ubuntu)",
            "sudo dnf install git      (Fedora/RHEL)",
            "sudo pacman -S git        (Arch)",
        ]
    hints.append("Download: " + DOWNLOAD_LINKS["git"]["linux"])
    return hints


def _gh_linux_hints():
    distro = _linux_distro()
    if distro in _APT_DISTROS:
        hints = [
            "Detected: Debian/Ubuntu family",
            "sudo mkdir -p -m 755 /etc/apt/keyrings",
            "wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null",
            "sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg",
            'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null',
            "sudo apt update && sudo apt install -y gh",
        ]
    elif distro in _DNF_DISTROS:
        hints = [
            "Detected: Fedora/RHEL family",
            "sudo dnf install -y dnf-plugins-core",
            "sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo",
            "sudo dnf install -y gh",
        ]
    elif distro in _PACMAN_DISTROS:
        hints = ["Detected: Arch family", "sudo pacman -S --noconfirm gh"]
    else:
        hints = ["Distro not recognized — try the snap package:", "sudo snap install gh"]
    hints.append("Download: " + DOWNLOAD_LINKS["gh"]["linux"])
    return hints


class RegistrationWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("URGithub — Registration")
        self.root.geometry("660x520")
        self.root.minsize(560, 440)
        self.base = tk.StringVar(master=self.root)
        self.install_schedule = None
        self.result = None
        self.page_frame = None
        self.checks = None
        self.check_frame = None
        self.fixes_frame = None
        self.register_btn = None
        self.show_welcome()

    def run(self):
        self.root.mainloop()
        return self.result

    def clear(self):
        if self.page_frame is not None:
            self.page_frame.destroy()
            self.page_frame = None

    def show_welcome(self):
        self.clear()
        frame = tk.Frame(self.root, padx=30, pady=30)
        self.page_frame = frame
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="URGithub", font=("Segoe UI", 22, "bold")).pack()
        tk.Label(frame, text="Universal Git repository operations manager", font=("Segoe UI", 11)).pack(pady=(4, 20))
        tk.Label(
            frame,
            text=(
                "URGithub scans, synchronizes, commits, pushes, verifies and\n"
                "reports on your Git repositories. A one-time registration\n"
                "must succeed before any operation is allowed."
            ),
            justify="center",
        ).pack()
        tk.Button(frame, text="Start", width=16, command=self.show_workspace).pack(pady=24)
        tk.Button(frame, text="Exit", width=16, command=self.root.destroy).pack()

    def show_workspace(self):
        self.clear()
        frame = tk.Frame(self.root, padx=30, pady=30)
        self.page_frame = frame
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Workspace", font=("Segoe UI", 16, "bold")).pack()
        tk.Label(
            frame,
            text="Choose the base location. URGithub creates one 'urgithub' folder inside it.",
            justify="center",
        ).pack(pady=10)
        row = tk.Frame(frame)
        row.pack(pady=10)
        entry = tk.Entry(row, textvariable=self.base, width=46)
        entry.pack(side="left")
        tk.Button(row, text="Browse...", command=self.browse).pack(side="left", padx=6)
        nav = tk.Frame(frame)
        nav.pack(side="bottom", pady=10)
        tk.Button(nav, text="Back", command=self.show_welcome).pack(side="left", padx=6)
        tk.Button(nav, text="Next", command=self.show_env).pack(side="left", padx=6)

    def browse(self):
        folder = filedialog.askdirectory(title="Select base location")
        if folder:
            self.base.set(folder)

    def show_env(self):
        base = self.base.get().strip()
        if not base:
            messagebox.showwarning("URGithub", "Select a base location first.")
            return
        self.clear()
        frame = tk.Frame(self.root, padx=30, pady=30)
        self.page_frame = frame
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Environment check", font=("Segoe UI", 16, "bold")).pack()
        self.check_frame = tk.Frame(frame)
        self.check_frame.pack(pady=12)
        nav = tk.Frame(frame)
        nav.pack(side="bottom", pady=10)
        tk.Button(nav, text="Back", command=self.show_workspace).pack(side="left", padx=6)
        self.register_btn = tk.Button(nav, text="Register", state="disabled", command=self.finish)
        self.register_btn.pack(side="left", padx=6)
        self.install_schedule = tk.BooleanVar(value=True)
        tk.Checkbutton(
            frame,
            text="Also install Windows scheduled tasks (startup / 3-hour timer / shutdown quick-push)",
            variable=self.install_schedule,
        ).pack(side="bottom", pady=(0, 8))
        self.recheck()

    def recheck(self):
        self.checks = EnvCheck(self.base.get().strip())
        self.checks.run()
        self.render_checks()

    def render_checks(self):
        import platform

        for widget in self.check_frame.winfo_children():
            widget.destroy()
        if self.fixes_frame is not None:
            self.fixes_frame.destroy()
            self.fixes_frame = None
        checks = self.checks
        scopes = ", ".join(checks.github_scopes) if checks.github_scopes else "(none)"
        rows = [
            ("Python", True, platform.python_version()),
            ("Git installed", checks.git_installed, ""),
            ("Git version", checks.git_installed, checks.git_version),
            ("Git username", bool(checks.identity["name"]), checks.identity["name"]),
            ("Git email", bool(checks.identity["email"]), checks.identity["email"]),
            ("GitHub CLI (gh) installed", checks.gh_installed, ""),
            ("GitHub authentication", checks.github_authenticated, checks.github_login),
            ("Push scope (repo) present", checks.can_push, scopes),
            ("GitHub connection (live)", checks.github_reachable, ""),
            ("Base location writable", checks.base_writable, ""),
        ]
        for label, ok, value in rows:
            row = tk.Frame(self.check_frame)
            row.pack(fill="x", pady=2)
            mark = "\u2713" if ok else "\u2717"
            color = "#1a7f37" if ok else "#cf222e"
            tk.Label(row, text=mark, fg=color, font=("Segoe UI", 12, "bold"), width=2).pack(side="left")
            tk.Label(row, text=label, anchor="w", width=28).pack(side="left")
            tk.Label(row, text=value, fg="#57606a", anchor="w").pack(side="left", fill="x", expand=True)
        fixes = tk.Frame(self.page_frame)
        self.fixes_frame = fixes
        fixes.pack(pady=8)
        if not checks.git_installed:
            tk.Button(fixes, text="Install Git", command=self.install_git).pack(side="left", padx=4)
        if not (checks.identity["name"] and checks.identity["email"]):
            tk.Button(fixes, text="Configure identity", command=self.configure_identity).pack(side="left", padx=4)
        if not checks.gh_installed:
            tk.Button(fixes, text="Install GitHub CLI", command=self.install_gh).pack(side="left", padx=4)
        if not checks.github_authenticated or not checks.can_push:
            tk.Button(fixes, text="Authenticate GitHub (gh auth login)", command=self.authenticate_github).pack(side="left", padx=4)
        self.register_btn.config(state="normal" if checks.all_pass else "disabled")

    def install_git(self):
        if SYSTEM == "windows":
            self._install_via_winget("Git.Git", DOWNLOAD_LINKS["git"]["windows"])
            return
        if SYSTEM == "linux":
            self._show_hint("Install Git (Linux)", _git_linux_hints())
            return
        webbrowser.open(download_link("git"))

    def install_gh(self):
        if SYSTEM == "windows":
            self._install_via_winget("GitHub.cli", DOWNLOAD_LINKS["gh"]["windows"])
            return
        if SYSTEM == "linux":
            self._show_hint("Install GitHub CLI (Linux)", _gh_linux_hints())
            return
        webbrowser.open(download_link("gh"))

    def _install_via_winget(self, package_id, url):
        def worker():
            try:
                res = subprocess.run(
                    ["winget", "install", "--id", package_id,
                     "--accept-source-agreements", "--accept-package-agreements"],
                    capture_output=True, text=True, timeout=180,
                )
                ok = res.returncode == 0
            except (subprocess.TimeoutExpired, OSError):
                ok = False
            self.root.after(0, lambda: self._after_install(ok, url))

        threading.Thread(target=worker, daemon=True).start()

    def _after_install(self, ok, url):
        if ok:
            self.recheck()
        else:
            webbrowser.open(url)

    def _show_hint(self, title, lines):
        text = "\n\n".join(lines)
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except Exception:
            pass
        messagebox.showinfo(title, text + "\n\n(Commands copied to clipboard — paste them into a terminal.)")

    def configure_identity(self):
        name = simpledialog.askstring("URGithub", "Git user.name:", parent=self.root)
        if name:
            gitops.run_git(["config", "--global", "user.name", name])
        email = simpledialog.askstring("URGithub", "Git user.email:", parent=self.root)
        if email:
            gitops.run_git(["config", "--global", "user.email", email])
        self.recheck()

    def authenticate_github(self):
        if SYSTEM == "linux":
            self._show_hint(
                "Authenticate GitHub",
                ["Run this in a terminal:", "gh auth login --web",
                 "Then verify: gh auth status"],
            )
            self.root.after(30000, self.recheck)
            return
        subprocess.Popen(["gh", "auth", "login"], creationflags=CREATE_NEW_CONSOLE)
        self.root.after(2000, self.recheck)

    def finish(self):
        base = self.base.get().strip()
        try:
            Paths(base).ensure_all()
            cfg = Config({}, base_location=base)
            cfg.register(self.checks.snapshot())
            write_locator(base)
            self.result = base
            if self.install_schedule is not None and self.install_schedule.get():
                notes = self.install_schedule_tasks(cfg)
            else:
                notes = ""
            messagebox.showinfo(
                "URGithub",
                f"Registration complete.\nBase location: {base}\n\n"
                f"Next: run  python urgithub.py  (no arguments) to open the Control Center "
                f"and click 'Sync now'.\n\n"
                f"The first Sync now clones all your GitHub repos "
                f"(private + forks) into 'repos in github'.{notes}",
            )
            self.root.destroy()
        except OSError as exc:
            messagebox.showerror("URGithub", f"Could not create the folder structure:\n{exc}")

    def install_schedule_tasks(self, cfg):
        from . import scheduler

        log = logging.getLogger("urgithub")
        ok = scheduler.install(cfg, log)
        notes = "\nScheduled tasks installed (startup / timer / shutdown)."
        if not ok:
            notes += "\nShutdown task needs elevation — retrying with a UAC prompt..."
            if scheduler.elevate_shutdown(cfg, log):
                notes += "\nAll scheduled tasks installed."
            else:
                notes += "\nShutdown task skipped (declined). Run  --schedule install  from an elevated prompt later."
        return notes


def console_wizard():
    print("URGithub — Registration (console mode)")
    base = input("Base location: ").strip()
    if not base:
        print("Cancelled.")
        return None
    checks = EnvCheck(base).run()
    print()
    print("Environment check")
    print(f"  Python:                 {platform.python_version()}")
    print(f"  Git installed:          {'YES' if checks.git_installed else 'NO'}")
    print(f"  Git version:            {checks.git_version}")
    print(f"  Git username:           {checks.identity['name'] or 'MISSING'}")
    print(f"  Git email:              {checks.identity['email'] or 'MISSING'}")
    print(f"  GitHub CLI (gh):        {'YES' if checks.gh_installed else 'NO'}")
    print(f"  GitHub authentication:  {'YES' if checks.github_authenticated else 'NO'}")
    print(f"  Push scope (repo):      {'YES' if checks.can_push else 'NO  (' + ', '.join(checks.github_scopes) + ')'}")
    print(f"  GitHub connection:      {'YES' if checks.github_reachable else 'NO'}")
    print(f"  Base location writable: {'YES' if checks.base_writable else 'NO'}")
    print()
    if not checks.all_pass:
        print("Environment checks failed. Fix the failures and run --setup again.")
        return None
    cfg = Config({}, base_location=base)
    cfg.register(checks.snapshot())
    write_locator(base)
    print(f"Registration complete. Base location: {base}")
    print("The first run (e.g. --sync) clones all your GitHub repos into 'repos in github'.")
    answer = input("Install Windows scheduled tasks (startup / timer / shutdown)? [Y/n] ").strip().lower()
    if answer in ("", "y", "yes"):
        from . import scheduler
        from .logs import setup_logging

        log = setup_logging(cfg.paths)
        ok = scheduler.install(cfg, log)
        if not ok:
            print("Shutdown task needs elevation — retrying with a UAC prompt...")
            ok = scheduler.elevate_shutdown(cfg, log)
        print("Scheduled tasks installed." if ok else "Scheduled tasks partial/declined — run --schedule install from an elevated prompt later.")
    return base


def run_wizard():
    if not TKINTER_OK:
        return console_wizard()
    try:
        root = tk.Tk()
        return RegistrationWizard(root).run()
    except Exception:
        log = logging.getLogger("urgithub")
        log.exception("GUI wizard failed — falling back to console wizard")
        return console_wizard()
