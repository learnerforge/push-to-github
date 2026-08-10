import html
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from . import gitops

CSS = """*,
*::before,
*::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #0d1117; color: #e6edf3; padding: 32px 16px;
  display: flex; flex-direction: column; align-items: center;
}
.container { max-width: 900px; width: 100%; }
h1 { font-size: 26px; font-weight: 700; color: #f0f6fc; letter-spacing: -0.3px; }
header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px; }
header h1 { margin: 0; }
header .sub { color: #8b949e; font-size: 13px; margin-bottom: 28px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; margin: 0 0 28px; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 18px 16px; text-align: center; }
.card .num { font-size: 28px; font-weight: 700; color: #f0f6fc; }
.card .lbl { font-size: 12px; color: #8b949e; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }
.card-push .num { color: #58a6ff; }
.card-clone .num { color: #3fb950; }
.card-rename .num { color: #d2a8ff; }
.card-init .num { color: #56d4dd; }
.card-removed .num { color: #d29922; }
.card-fail .num { color: #f85149; }
.section { margin-bottom: 28px; }
.section-title, section h2 { font-size: 14px; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 12px; }
.tl-event { display: flex; align-items: center; gap: 10px; padding: 8px 14px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 6px; font-size: 13px; }
.tl-time { color: #484f58; font-family: "SF Mono", Consolas, monospace; font-size: 12px; min-width: 44px; }
.tl-icon { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0; }
.tl-push .tl-icon { background: #1c2a3d; color: #58a6ff; }
.tl-clone .tl-icon { background: #003d1f; color: #3fb950; }
.tl-init .tl-icon { background: #003d3d; color: #56d4dd; }
.tl-rename .tl-icon { background: #1c1a3d; color: #d2a8ff; }
.tl-removed .tl-icon { background: #3d2e00; color: #d29922; }
.tl-fail .tl-icon { background: #3d1014; color: #f85149; }
.tl-blocked .tl-icon { background: #3d2e00; color: #d29922; }
.tl-skipped .tl-icon { background: #21262d; color: #8b949e; }
.tl-repo { font-weight: 600; color: #e6edf3; min-width: 120px; }
.tl-desc { color: #8b949e; }
.tl-link { font-family: "SF Mono", Consolas, monospace; font-size: 11px; color: #58a6ff; text-decoration: none; background: #21262d; padding: 1px 6px; border-radius: 4px; margin-left: auto; }
.tl-link:hover { background: #30363d; }
.tl-event code { color: #d2a8ff; font-size: 12px; }
.detail-block { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 16px 20px; margin-bottom: 12px; }
.detail-block.detail-fail { border-color: #f85149; }
.detail-block.detail-removed { border-color: #d29922; }
.detail-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
.detail-repo { font-size: 16px; font-weight: 600; color: #f0f6fc; }
.detail-badge { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px; letter-spacing: 0.5px; }
.badge-push { background: #1c2a3d; color: #58a6ff; }
.badge-clone { background: #003d1f; color: #3fb950; }
.badge-rename { background: #1c1a3d; color: #d2a8ff; }
.badge-init { background: #003d3d; color: #56d4dd; }
.badge-removed { background: #3d2e00; color: #d29922; }
.badge-fail { background: #3d1014; color: #f85149; }
.badge-ok { background: #003d1f; color: #3fb950; }
.badge-warn { background: #3d2e00; color: #d29922; }
.detail-stats { font-size: 12px; color: #8b949e; }
.detail-link { margin-left: auto; font-size: 12px; color: #58a6ff; text-decoration: none; }
.detail-link:hover { text-decoration: underline; }
.file-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.file-table th { text-align: left; color: #8b949e; font-weight: 500; padding: 5px 8px; border-bottom: 1px solid #21262d; }
.file-table td { padding: 5px 8px; border-bottom: 1px solid #21262d; font-family: "SF Mono", Consolas, monospace; font-size: 12px; }
.file-status { font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 4px; display: inline-block; }
.file-a { background: #003d1f; color: #3fb950; }
.file-m { background: #1c2a3d; color: #79c0ff; }
.file-d { background: #3d1014; color: #f85149; }
.file-r { background: #1c1a3d; color: #d2a8ff; }
.file-path { color: #e6edf3; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #21262d; }
th { color: #8b949e; font-weight: 600; }
.badge { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.ok { background: #003d1f; color: #3fb950; }
.bad { background: #3d1014; color: #f85149; }
.warn { background: #3d2e00; color: #d29922; }
.dim { color: #8b949e; }
.mono { font-family: "SF Mono", Consolas, monospace; font-size: 12px; }
ul { padding-left: 20px; color: #8b949e; }
.footer { margin-top: 32px; text-align: center; font-size: 12px; color: #484f58; }
"""


def _escape(text):
    return html.escape(str(text))


def _now_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _local_now():
    return datetime.now().strftime("%d %b %Y %H:%M")


def _status_for_repo(path):
    if not (Path(path) / ".git").exists():
        return "UNINIT", None
    branch = gitops.run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path, timeout=15)
    st = gitops.run_git(["status", "--porcelain"], cwd=path, timeout=20)
    branch_name = (branch.stdout or "").strip()
    if (st.stdout or "").strip():
        return "DIRTY", branch_name
    return "CLEAN", branch_name


class Reporter:
    """Phase 5 — report.html generation, archiving, and show rules."""

    def __init__(self, cfg, log, run_id, trigger, interactive=False):
        self.cfg = cfg
        self.paths = cfg.paths
        self.log = log
        self.run_id = run_id
        self.trigger = trigger
        self.interactive = interactive

    # -- Generation -----------------------------------------------------

    def generate(self, events, sync_results, registry, duration, outcome, drift=None, scan_results=None):
        events = sorted(events, key=lambda e: e.get("timestamp", ""))
        cards = self._cards(events)
        timeline = self._timeline(events)
        details = self._details(sync_results, registry)
        all_repos = self._all_repos(registry)
        drift_html = self._drift(drift)
        security_html = self._security(scan_results)
        files_html = self._files_and_commits(scan_results)

        body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>URGithub — Synchronization Report</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>URGithub — Synchronization Report</h1>
    <div class="sub">Time: {_local_now()} · Trigger: {_escape(self.trigger)} · Duration: {duration:.1f}s · Run: {_escape(self.run_id)} · Outcome: {_escape(outcome)}</div>
  </header>

  <div class="cards">
    <div class="card card-push"><div class="num">{cards['pushed']}</div><div class="lbl">Pushed</div></div>
    <div class="card card-clone"><div class="num">{cards['cloned']}</div><div class="lbl">Cloned</div></div>
    <div class="card card-rename"><div class="num">{cards['renamed']}</div><div class="lbl">Renamed</div></div>
    <div class="card card-init"><div class="num">{cards['initialized']}</div><div class="lbl">Initialized</div></div>
    <div class="card card-removed"><div class="num">{cards['removed']}</div><div class="lbl">Removed</div></div>
    <div class="card card-fail"><div class="num">{cards['failed']}</div><div class="lbl">Failed</div></div>
    <div class="card"><div class="num">{cards['events']}</div><div class="lbl">Events</div></div>
  </div>

  <section class="section"><h2>Activity Timeline</h2>{timeline}</section>
  <section class="section"><h2>Details</h2>{details}</section>
  <section class="section"><h2>All Repositories</h2>{all_repos}</section>
  {security_html}
  {files_html}
  {drift_html}
</div>
</body>
</html>
"""
        self._write(body)
        return self.paths.report_html

    def _write(self, body):
        self.paths.reports.mkdir(parents=True, exist_ok=True)
        tmp = self.paths.report_html.with_suffix(".html.tmp")
        tmp.write_text(body, encoding="utf-8")
        tmp.replace(self.paths.report_html)

        archive_cfg = self.cfg.get("report", {})
        if archive_cfg.get("archive", True):
            self.paths.report_archive.mkdir(parents=True, exist_ok=True)
            archived = self.paths.report_archive / f"report-{_now_ts()}.html"
            archived.write_text(body, encoding="utf-8")
            self._prune_archive(int(archive_cfg.get("archive_keep_days", 90)))

    def _prune_archive(self, keep_days):
        if keep_days <= 0 or not self.paths.report_archive.exists():
            return
        cutoff = datetime.now().timestamp() - keep_days * 86400
        for f in self.paths.report_archive.glob("report-*.html"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
            except OSError:
                pass

    def _cards(self, events):
        counter = {"pushed": 0, "cloned": 0, "renamed": 0, "initialized": 0, "removed": 0, "failed": 0}
        for e in events:
            t = e.get("type", "")
            if t == "pushed":
                counter["pushed"] += 1
            elif t == "cloned":
                counter["cloned"] += 1
            elif t == "renamed" or t == "adopted":
                counter["renamed"] += 1
            elif t == "discovered":
                counter["initialized"] += 1
            elif t == "removed":
                counter["removed"] += 1
            elif t in ("fail", "failed"):
                counter["failed"] += 1
        counter["events"] = len(events)
        return counter

    def _timeline(self, events):
        if not events:
            return '<p class="dim">No events this run.</p>'
        icon_map = {
            "pushed": ("push", "P"), "cloned": ("clone", "C"),
            "discovered": ("init", "I"), "adopted": ("rename", "R"),
            "renamed": ("rename", "R"), "removed": ("removed", "D"),
            "fail": ("fail", "X"), "failed": ("fail", "X"),
            "blocked": ("blocked", "B"), "skipped": ("skipped", "-"),
        }
        rows = []
        for e in events:
            kind, icon = icon_map.get(e.get("type", ""), ("", "•"))
            link = f'<a class="tl-link" href="{_escape(e.get("url", ""))}">↗</a>' if e.get("url") else ""
            cls = f" tl-{kind}" if kind else ""
            rows.append(
                f'<div class="tl-event{cls}">'
                f'<span class="tl-icon">{icon}</span>'
                f'<span class="tl-time">{_escape(e.get("timestamp", ""))}</span>'
                f'<span class="tl-repo">{_escape(e.get("repo", ""))}</span>'
                f'<span class="tl-desc">{_escape(e.get("detail", ""))}</span>'
                f"{link}"
                "</div>"
            )
        return "".join(rows)

    def _details(self, sync_results, registry):
        if not sync_results:
            return '<p class="dim">No sync results this run.</p>'
        blocks = []
        action_style = {"pushed": ("push", "PUSHED"), "clean": ("ok", "CLEAN"),
                        "committed": ("ok", "COMMITTED"), "skipped": ("warn", "SKIPPED"),
                        "blocked": ("warn", "BLOCKED"), "failed": ("fail", "FAILED")}
        for r in sync_results:
            style, label = action_style.get(r.action, ("", r.action.upper()))
            entry = registry.get(r.repo, {}) if registry else {}
            url = entry.get("url", "") if entry else ""
            rows = ""
            for f in r.changed:
                cls = {"A": "file-a", "M": "file-m", "D": "file-d", "R": "file-r"}.get(f.get("status"), "")
                rows += f'<tr><td class="{cls}">{_escape(f.get("status", ""))}</td><td class="file-path">{_escape(f.get("path", ""))}</td></tr>'
            table = f'<table class="file-table"><tr><th>Status</th><th>File</th></tr>{rows}</table>' if rows else ""
            reason = f' — {_escape(r.reason)}' if r.reason else ""
            link = f'<a class="detail-link" href="{_escape(url)}">Open on GitHub ↗</a>' if url else ""
            blocks.append(
                '<div class="detail-block' + (f' detail-{style}' if style else "") + '">'
                '<div class="detail-header">'
                f'<span class="detail-repo">{_escape(r.repo)}</span>'
                f'<span class="detail-badge badge-{style}">{label}</span>'
                f'<span class="detail-stats">{len(r.changed)} file(s) changed{reason}</span>'
                f"{link}"
                "</div>"
                f'<div class="detail-stats mono">{_escape(r.before_sha)} → {_escape(r.after_sha)}</div>'
                f"{table}"
                "</div>"
            )
        return "".join(blocks)

    def _all_repos(self, registry):
        rows = []
        for name in sorted(registry.data):
            entry = registry.data[name]
            if entry.get("status") in ("quarantined", "deleted"):
                continue
            path = entry.get("path", "")
            if not path:
                continue
            state, branch = _status_for_repo(path)
            badge = {"CLEAN": ("ok", "CLEAN"), "DIRTY": ("warn", "DIRTY"), "UNINIT": ("bad", "UNINIT")}.get(state, ("dim", state))
            url = entry.get("url", "")
            link = f'<a href="{_escape(url)}">{_escape(name)}</a>' if url else _escape(name)
            rows.append(
                "<tr>"
                f'<td>{link}</td>'
                f'<td>{_escape(entry.get("status", ""))}</td>'
                f'<td class="mono">{_escape(branch or "—")}</td>'
                f'<td><span class="badge {badge[0]}">{badge[1]}</span></td>'
                "</tr>"
            )
        if not rows:
            return '<p class="dim">No active repositories.</p>'
        return "<table><tr><th>Repository</th><th>Registry</th><th>Branch</th><th>Working Tree</th></tr>" + "".join(rows) + "</table>"

    def _drift(self, drift):
        if not drift:
            return ""
        items = "".join(f"<li>{_escape(item)}</li>" for item in drift)
        return f'<section><h2>Environment Drift</h2><ul>{items}</ul></section>'

    def _security(self, scan_results):
        if not scan_results:
            return ""
        rows = []
        for r in scan_results:
            for f in r.secret_findings:
                kind = "name" if f.get("kind") == "name" else "content"
                pat = f.get("patterns") or []
                detail = "; ".join(pat[:2]) + ("; …" if len(pat) > 2 else "")
                rows.append(
                    "<tr>"
                    f'<td>{_escape(r.repo)}</td>'
                    f'<td class="mono">{_escape(f.get("file", ""))}</td>'
                    f'<td><span class="badge bad">{kind}</span></td>'
                    f'<td class="mono dim">{_escape(detail)}</td>'
                    "</tr>"
                )
            for o in r.oversize:
                rows.append(
                    "<tr>"
                    f'<td>{_escape(r.repo)}</td>'
                    f'<td class="mono">{_escape(o.get("file", ""))}</td>'
                    '<td><span class="badge bad">oversize</span></td>'
                    f'<td>{o.get("bytes", 0) / (1024 * 1024):.1f} MB</td>'
                    "</tr>"
                )
            for l in r.large:
                rows.append(
                    "<tr>"
                    f'<td>{_escape(r.repo)}</td>'
                    f'<td class="mono">{_escape(l.get("file", ""))}</td>'
                    '<td><span class="badge warn">large</span></td>'
                    f'<td>{l.get("bytes", 0) / (1024 * 1024):.1f} MB</td>'
                    "</tr>"
                )
        if not rows:
            return ""
        table = "<table><tr><th>Repo</th><th>File</th><th>Kind</th><th>Detail</th></tr>" + "".join(rows) + "</table>"
        return f'<section><h2>Security &amp; Size</h2>{table}</section>'

    def _files_and_commits(self, scan_results):
        """Per-file last commit, GitHub file-browser style (section 5.5)."""
        if not scan_results:
            return ""
        report_cfg = self.cfg.get("report", {})
        if not report_cfg.get("show_files", True):
            return ""
        try:
            limit = int(report_cfg.get("files_max", 500))
        except (TypeError, ValueError):
            limit = 500
        if limit <= 0:
            return ""
        blocks = []
        for r in scan_results:
            items = [f for f in (getattr(r, "files", None) or []) if f.get("file")]
            if not items:
                continue
            committed = [f for f in items if f.get("committed_at")]
            uncommitted = [f for f in items if not f.get("committed_at")]
            committed.sort(key=lambda f: f["committed_at"], reverse=True)
            items = committed + uncommitted
            display = items[:limit]
            rows = ""
            for f in display:
                ts = f.get("committed_at") or "uncommitted"
                rows += (
                    f'<tr><td class="file-path">{_escape(f["file"])}</td>'
                    f'<td class="mono dim">{_escape(ts)}</td></tr>'
                )
            more = ""
            if len(items) > limit:
                more = f'<div class="dim">… and {len(items) - limit} more (report.files_max)</div>'
            blocks.append(
                '<div class="detail-block">'
                '<div class="detail-header">'
                f'<span class="detail-repo">{_escape(r.repo)}</span>'
                f'<span class="detail-stats">{len(items)} file(s)</span>'
                "</div>"
                f'<table class="file-table"><tr><th>File</th><th>Last Commit</th></tr>{rows}</table>{more}'
                "</div>"
            )
        if not blocks:
            return ""
        return '<section class="section"><h2>Files &amp; Last Commit</h2>' + "".join(blocks) + "</section>"

    # -- Show rules -----------------------------------------------------

    def show(self, outcome):
        if self.trigger == "shutdown":
            return
        if not self.paths.report_html.exists():
            self.log.warning("report.html missing — nothing to show")
            return
        if self.interactive:
            try:
                webbrowser.open(self.paths.report_html.as_uri())
            except webbrowser.Error as exc:
                self.log.warning("Could not open report: %s", exc)
            return
        toast(self.cfg, f"URGithub run complete — {outcome}")


def toast(cfg, message):
    if not cfg.get("notify", {}).get("toast_on_failure", True):
        return
    script = (
        "$ErrorActionPreference='Stop';"
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null;"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null;"
        "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
        "$n=$t.GetElementsByTagName('text');"
        "$n.Item(0).AppendChild($t.CreateTextNode('URGithub')) | Out-Null;"
        "$n.Item(1).AppendChild($t.CreateTextNode('{0}')) | Out-Null;"
        "$d=[Windows.UI.Notifications.ToastNotification]::new($t);"
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('URGithub').Show($d)"
    ).format(message.replace("'", "''"))
    try:
        import subprocess

        subprocess.run(
            ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
            capture_output=True,
            timeout=15,
        )
    except Exception:
        pass
