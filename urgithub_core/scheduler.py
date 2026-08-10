import getpass
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import urgithub_core.gitops as gitops

TASK_PREFIX = "URGithub"
LAUNCHERS = ["start", "scan", "sync", "shutdown", "schedule", "manual"]

# Shutdown is a special event trigger: EventID 1074 from provider User32 on the
# System log fires when a user-initiated shutdown/restart/logoff is requested.
SHUTDOWN_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>{date}</Date>
    <Author>{user}</Author>
    <Description>URGithub shutdown trigger — quick push of local commits before Windows shuts down. Never blocks shutdown (hard 30s timeout).</Description>
  </RegistrationInfo>
  <Triggers>
    <EventTrigger>
      <Subscription>&lt;QueryList&gt;&lt;Query Id="0" Path="System"&gt;&lt;Select Path="System"&gt;*[System[Provider[@Name='User32'] and (EventID=1074)]]&lt;/Select&gt;&lt;/Query&gt;&lt;/QueryList&gt;</Subscription>
      <Delay>PT10S</Delay>
    </EventTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT2M</ExecutionTimeLimit>
    <Priority>5</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python}</Command>
      <Arguments>&quot;{script}&quot; --run shutdown</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def script_path():
    if sys.argv and sys.argv[0]:
        return str(Path(sys.argv[0]).resolve())
    return str(Path("urgithub.py").resolve())


def _command(trigger):
    return f'"{sys.executable}" "{script_path()}" --run {trigger}'


def task_name(trigger):
    return f"{TASK_PREFIX}-{trigger.replace('_', '-')}"


def _run_schtasks(args, timeout=30):
    try:
        return subprocess.run(["schtasks"] + args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return gitops._Result(124, "", "schtasks timed out")
    except FileNotFoundError:
        return gitops._Result(127, "", "schtasks not found")


def _schedule_spec(cfg):
    """Return the repeating/daily schedule spec, or None when no schedule is set."""
    triggers = cfg.get("triggers", {})
    every_hours = int(triggers.get("every_hours", 0) or 0)
    every_minutes = int(triggers.get("every_minutes", 0) or 0)
    at_time = triggers.get("at_time")

    if every_minutes > 0:
        return {"schedule": "MINUTE", "modifier": every_minutes}
    if every_hours > 0:
        return {"schedule": "HOURLY", "modifier": every_hours}
    if at_time:
        return {"schedule": "DAILY", "start_time": at_time}
    return None


def deploy_launchers(paths):
    """Write the full launcher set (absolute python + script) into paths.run."""
    paths.run.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    script = script_path()
    written = []
    for name in LAUNCHERS:
        args = {
            "start": "--startup",
            "scan": "--scan",
            "sync": "--sync",
            "shutdown": "--shutdown",
            "schedule": "--run scheduled",
            "manual": "--tray",
        }[name]
        content = f'@echo off\n"{py}" "{script}" {args}\n'
        target = paths.run / f"{name}.bat"
        target.write_text(content, encoding="utf-8")
        written.append(str(target))
    return written


def install(cfg, log):
    deploy_launchers(cfg.paths)
    triggers = cfg.get("triggers", {})
    results = []

    if triggers.get("startup"):
        results.append(_create_logon(cfg, log, "startup"))

    if triggers.get("shutdown"):
        results.append(_create_shutdown(cfg, log))

    schedule = _schedule_spec(cfg)
    if schedule:
        results.append(_create_repeating(cfg, log, schedule))

    ok = all(r.get("rc", 0) == 0 for r in results)
    log.info("Schedule install: %s", "OK" if ok else "FAILED")
    return ok


def _create_logon(cfg, log, trigger):
    name = task_name(trigger)
    user = getpass.getuser()
    res = _run_schtasks(["/Create", "/F", "/TN", name, "/TR", _command(trigger),
                         "/SC", "ONLOGON", "/RU", user])
    log.info("Created logon task %s for user %s → rc=%s", name, user, res.returncode)
    return {"task": name, "rc": res.returncode}


def _create_repeating(cfg, log, schedule):
    name = task_name("scheduled")
    args = ["/Create", "/F", "/TN", name, "/TR", _command("scheduled"),
            "/SC", schedule["schedule"]]
    if schedule.get("modifier"):
        args += ["/MO", str(schedule["modifier"])]
    if schedule.get("start_time"):
        args += ["/ST", schedule["start_time"]]
    res = _run_schtasks(args)
    log.info("Created repeating task %s (%s) → rc=%s", name, schedule, res.returncode)
    return {"task": name, "rc": res.returncode}


def _create_shutdown(cfg, log):
    name = task_name("shutdown")
    xml = SHUTDOWN_XML.format(
        date=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        user=getpass.getuser(),
        python=sys.executable,
        script=script_path(),
    )
    xml_path = cfg.paths.data / "shutdown-task.xml"
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text(xml, encoding="utf-16")
    res = _run_schtasks(["/Create", "/F", "/TN", name, "/XML", str(xml_path)])
    log.info("Created shutdown task %s → rc=%s", name, res.returncode)
    return {"task": name, "rc": res.returncode}


def elevate_shutdown(cfg, log):
    """Create the SYSTEM shutdown task via a UAC-elevated schtasks call.

    The task's principal is S-1-5-18 (SYSTEM), which requires elevation.
    Returns True when the elevated call succeeded (or the task already exists).
    """
    name = task_name("shutdown")
    xml = SHUTDOWN_XML.format(
        date=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        user=getpass.getuser(),
        python=sys.executable,
        script=script_path(),
    )
    xml_path = cfg.paths.data / "shutdown-task.xml"
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text(xml, encoding="utf-16")
    script = (
        "$p = Start-Process -FilePath schtasks -ArgumentList "
        f"'/Create','/F','/TN','{name}','/XML','{xml_path}' "
        "-Verb RunAs -Wait -PassThru; exit $p.ExitCode"
    )
    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        log.info("Elevated shutdown task creation timed out")
        return False
    log.info("Elevated shutdown task %s → rc=%s", name, res.returncode)
    return res.returncode == 0


def uninstall(log):
    names = [task_name(t) for t in ("startup", "scheduled", "shutdown")]
    ok = True
    for name in names:
        res = _run_schtasks(["/Delete", "/TN", name, "/F"])
        if res.returncode != 0 and "not found" not in res.stderr.lower():
            ok = False
        log.info("Uninstall %s → rc=%s", name, res.returncode)
    return ok


def status(log):
    names = [task_name(t) for t in ("startup", "scheduled", "shutdown")]
    rows = []
    for name in names:
        res = _run_schtasks(["/Query", "/TN", name, "/FO", "LIST"])
        if res.returncode != 0:
            continue
        state = next_run = ""
        for line in res.stdout.splitlines():
            key, _, value = line.partition(":")
            if key.strip().lower() == "status":
                state = value.strip()
            elif key.strip().lower() == "next run time":
                next_run = value.strip()
        rows.append((name, state, next_run))
    return rows


def compute_next_runs(cfg, now=None):
    """Return [(kind, next_datetime), ...] for every_hours/every_minutes/at_time.

    Repeating schedules fire on fixed epoch-aligned interval boundaries so that
    e.g. every-3-hours always lands on :00 boundaries. at_time rolls to the
    next day when today's time has already passed.
    """
    now = now or datetime.now()
    triggers = cfg.get("triggers", {})
    next_runs = []

    hours = int(triggers.get("every_hours", 0) or 0)
    if hours > 0:
        interval = hours * 3600
        slot = int(now.timestamp() // interval) + 1
        next_runs.append(("every_hours", datetime.fromtimestamp(slot * interval)))

    minutes = int(triggers.get("every_minutes", 0) or 0)
    if minutes > 0:
        interval = minutes * 60
        slot = int(now.timestamp() // interval) + 1
        next_runs.append(("every_minutes", datetime.fromtimestamp(slot * interval)))

    at_time = triggers.get("at_time")
    if at_time:
        try:
            hour, minute = (int(p) for p in str(at_time).split(":", 1))
            when = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if when <= now:
                when += timedelta(days=1)
            next_runs.append(("at_time", when))
        except (TypeError, ValueError):
            pass

    next_runs.sort(key=lambda item: item[1])
    return next_runs
