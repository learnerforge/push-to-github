import os
import subprocess

NON_INTERACTIVE_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GCM_INTERACTIVE": "Never",
}


def merged_env():
    env = dict(os.environ)
    env.update(NON_INTERACTIVE_ENV)
    return env


class _Result:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _timed_out():
    return _Result(124, "", "operation timed out")


def _missing(tool):
    return _Result(127, "", f"{tool} not found on PATH")


def run_git(args, cwd=None, timeout=60):
    try:
        return subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=merged_env(),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return _timed_out()
    except FileNotFoundError:
        return _missing("git")


def run_gh(args, timeout=60):
    try:
        return subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            env=merged_env(),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return _timed_out()
    except FileNotFoundError:
        return _missing("gh")


def is_github_url(url):
    return "github.com" in (url or "").lower()
