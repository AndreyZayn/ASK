#!/usr/bin/env python3
"""ASK optional deterministic macOS backup backend (stdlib only).

Reuses gitops operations; never shells out with composed strings. No AI and
no automatic knowledge rewriting: ordinary note changes are staged through
gitops.checkpoint and pushed; protected files are left for the owner.
"""
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import gitops

try:
    from .gitops import GitError
except ImportError:  # pragma: no cover - direct script use
    from asklib.gitops import GitError


class BackupError(Exception):
    pass


ASK_LABEL_PREFIX = "com.ask.backup."
PLIST_MARKER = "ASKBackup"
LOG_MAX_LINES = 200
STATUS_NAME = "backup-status.json"
LOG_NAME = "backup.log"
NOTIFY_NAME = "backup-notify.json"
DELETIONS_NAME = "backup-deletions.json"


def _ws(workspace):
    ws = Path(workspace).expanduser().absolute()
    if not ws.is_dir():
        raise BackupError("workspace is not a directory: %s" % ws)
    return ws


def _abs(path, label):
    p = Path(path).expanduser()
    if not p.is_absolute():
        raise BackupError("%s must be an absolute path" % label)
    return p


def _label(workspace):
    digest = hashlib.sha1(str(workspace).encode("utf-8")).hexdigest()[:12]
    base = re.sub(r"[^A-Za-z0-9]+", "-", workspace.name).strip("-") or "ws"
    return "%s%s-%s" % (ASK_LABEL_PREFIX, base[:32], digest)


def _plist_path(label):
    return Path.home() / "Library" / "LaunchAgents" / (label + ".plist")


def _is_owned(data, workspace=None):
    try:
        if isinstance(data, bytes):
            info = plistlib.loads(data)
        else:
            info = data
    except Exception:
        return False
    return (isinstance(info, dict) and info.get(PLIST_MARKER) is True
            and (workspace is None or info.get("ASKWorkspace") == str(workspace)))


def _launchctl(*args):
    try:
        proc = subprocess.run(["launchctl", *args], text=True,
                              capture_output=True, timeout=20)
    except FileNotFoundError:
        raise BackupError("launchctl is not available on this system")
    except subprocess.TimeoutExpired:
        raise BackupError("launchctl timed out")
    if proc.returncode != 0:
        raise BackupError("launchctl %s failed: %s"
                          % (" ".join(args),
                             (proc.stderr or proc.stdout).strip()))
    return proc


def _notify(title, message):
    """Desktop notification hook; tests replace this with a mock."""
    try:
        subprocess.run(
            ["osascript", "-e",
             "on run argv\n"
             "display notification (item 2 of argv) with title (item 1 of argv)\n"
             "end run", title[:100], message[:300]],
            capture_output=True, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def enable(workspace, cli_path, config_path, interval=900):
    """Install only an ASK-owned user LaunchAgent. Never overwrites foreign."""
    ws = _ws(workspace)
    cli = _abs(cli_path, "cli_path")
    cfg = _abs(config_path, "config_path")
    if not isinstance(interval, int) or isinstance(interval, bool) \
            or interval <= 0:
        raise BackupError("interval must be a positive number of seconds")
    label = _label(ws)
    plist = _plist_path(label)
    if plist.is_symlink() or (plist.exists() and not _is_owned(plist.read_bytes(), ws)):
        raise BackupError("refusing to overwrite foreign plist: %s" % plist)
    existing = plist.exists()
    git_bin, gh_bin = shutil.which("git"), shutil.which("gh")
    if not git_bin or not gh_bin:
        raise BackupError("git and gh must be installed before enabling backup")
    search_path = os.pathsep.join(dict.fromkeys((
        str(Path(git_bin).resolve().parent), str(Path(gh_bin).resolve().parent),
        "/usr/bin", "/bin")))
    payload = {
        "Label": label,
        PLIST_MARKER: True,
        "ASKWorkspace": str(ws),
        "ProgramArguments": [sys.executable, str(cli), "backup", "run",
                             "--config", str(cfg)],
        "WorkingDirectory": str(ws),
        "EnvironmentVariables": {"PATH": search_path},
        "StartInterval": interval,
        "RunAtLoad": False,
    }
    plist.parent.mkdir(parents=True, exist_ok=True)
    uid = os.getuid() if hasattr(os, "getuid") else 501
    if existing:
        try:
            _launchctl("bootout", "gui/%d" % uid, str(plist))
        except BackupError as e:
            if "not loaded" not in str(e).lower() and "no such process" not in str(e).lower():
                raise
    plist.write_bytes(plistlib.dumps(payload))
    _launchctl("bootstrap", "gui/%d" % uid, str(plist))
    return {"enabled": True, "label": label, "plist": str(plist),
            "interval": interval}


def disable(workspace):
    """Remove only the ASK-owned LaunchAgent for this workspace."""
    ws = _ws(workspace)
    plist = _plist_path(_label(ws))
    if plist.is_symlink():
        raise BackupError("refusing to remove foreign plist: %s" % plist)
    if not plist.exists():
        return {"removed": False, "plist": str(plist)}
    if not _is_owned(plist.read_bytes(), ws):
        raise BackupError("refusing to remove foreign plist: %s" % plist)
    unloaded = True
    try:
        uid = os.getuid() if hasattr(os, "getuid") else 501
        _launchctl("bootout", "gui/%d" % uid, str(plist))
    except BackupError as e:
        if "not loaded" not in str(e).lower() and "no such process" not in str(e).lower():
            raise
        unloaded = False
    plist.unlink()
    return {"removed": True, "plist": str(plist), "unloaded": unloaded}


def _ask_file(ws, name):
    d = gitops._ask_dir(ws)
    target = d / name
    if target.is_symlink():
        raise BackupError("refusing symlinked backup state: %s" % name)
    return target


def _record(ws, state, detail=""):
    entry = {"time": time.time(), "state": state, "detail": detail}
    _ask_file(ws, STATUS_NAME).write_text(json.dumps(entry, indent=2) + "\n",
                                           encoding="utf-8")
    log = _ask_file(ws, LOG_NAME)
    line = "%s %s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), state, detail)
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    lines.append(line.strip())
    log.write_text("\n".join(lines[-LOG_MAX_LINES:]) + "\n", encoding="utf-8")
    return entry


def _should_notify(ws, signature):
    marker = _ask_file(ws, NOTIFY_NAME)
    try:
        last = json.loads(marker.read_text(encoding="utf-8")).get("signature")
    except (OSError, ValueError, AttributeError):
        last = None
    if last == signature:
        return False
    marker.write_text(json.dumps({"signature": signature,
                                  "time": time.time()}), encoding="utf-8")
    return True


def run(workspace, validator, quiet_seconds=300):
    """One deterministic backup pass. Never rewrites knowledge on its own."""
    ws = _ws(workspace)
    if not callable(validator):
        raise BackupError("validator must be callable")
    try:
        gitops._acquire_lock(ws)
    except gitops.GitError as e:
        return _record_entry(ws, "error", str(e), notify=True,
                             title="ASK backup failed")
    try:
        return _run_locked(ws, validator, quiet_seconds)
    finally:
        gitops._release_lock(ws)


def _run_locked(ws, validator, quiet_seconds):
    try:
        st = gitops.status(ws)
        vault, _ = gitops._load_vault(ws)
        cfg = json.loads((ws / "ask.json").read_text(encoding="utf-8"))
        writable = cfg.get("access", {}).get("write", [])
        if not isinstance(writable, list) or not all(isinstance(p, str) for p in writable):
            raise ValueError("invalid access.write")
        vault.resolve().relative_to(ws.resolve())
    except (gitops.GitError, ValueError, OSError, KeyError) as e:
        return _record_entry(ws, "error", str(e), notify=True,
                             title="ASK backup failed")
    if not writable:
        return _record_entry(ws, "skipped:access",
                             "access.write does not allow vault backup", notify=False)
    if gitops.active_writes(ws):
        return _record_entry(ws, "skipped:active-writers",
                             "a write session is active", notify=False)
    if st["conflicts"]:
        return _record_entry(ws, "skipped:conflicts",
                             "unresolved merge conflicts", notify=False)
    if st["staged"]:
        return _record_entry(ws, "skipped:staged-work",
                             "staged files present: %s"
                             % ", ".join(st["staged"][:5]), notify=False)
    candidates = st["unstaged"] + st["untracked"]
    ordinary, skipped_protected, skipped_secret, skipped_quiet = [], [], [], []
    deletions_path = _ask_file(ws, DELETIONS_NAME)
    try:
        observations = json.loads(deletions_path.read_text(encoding="utf-8"))
        if not isinstance(observations, dict):
            observations = {}
    except (OSError, ValueError):
        observations = {}
    current_deletions = set()
    now = time.time()
    for rel in candidates:
        if gitops.is_secret_or_state(rel):
            skipped_secret.append(rel)
            continue
        try:
            gitops._check_rel(ws, rel)
            protected = gitops.is_protected(ws, rel)
            vrel = (ws / rel).absolute().relative_to(vault.resolve()).as_posix()
        except gitops.GitError as e:
            return _record_entry(ws, "error", str(e), notify=True,
                                 title="ASK backup failed")
        except ValueError:
            continue
        if protected:
            skipped_protected.append(rel)
            continue
        if not any(p == "." or vrel == p.strip("/") or
                   vrel.startswith(p.strip("/") + "/") for p in writable if p):
            continue
        try:
            age = now - (ws / rel).stat().st_mtime
        except OSError:
            current_deletions.add(rel)
            age = now - observations.setdefault(rel, now)
        if age < quiet_seconds:
            skipped_quiet.append(rel)
            continue
        ordinary.append(rel)
    observations = {p: observations[p] for p in current_deletions}
    deletions_path.write_text(json.dumps(observations), encoding="utf-8")
    if skipped_protected:
        return _record_entry(ws, "skipped:protected-only",
                             "protected changes need owner approval", notify=False)
    if skipped_quiet:
        return _record_entry(ws, "skipped:quiet-period",
                             "%d file(s) changed recently" % len(skipped_quiet),
                             notify=False)
    if not ordinary:
        if st["ahead"] > 0 or (not candidates):
            try:
                res = gitops._push(ws)
            except gitops.GitError as e:
                return _record_entry(ws, "error", str(e), notify=True,
                                     title="ASK backup failed")
            if res["pushed"]:
                return _record_entry(ws, "ok", "pushed pending commits",
                                     notify=False)
            if res["backup_pending"]:
                return _record_entry(ws, "backup-pending",
                                     str(res.get("reason", "offline")),
                                     notify=res.get("reason") != "no-remote")
            if not candidates:
                return _record_entry(ws, "idle", "workspace clean",
                                     notify=False)
        return _record_entry(ws, "idle", "no eligible vault changes",
                             notify=False)
    try:
        res = gitops._checkpoint_locked(ws, sorted(ordinary),
                                        "ASK backup: %d file(s)" % len(ordinary),
                                        validator)
    except gitops.GitError as e:
        msg = str(e)
        if "validator rejected" in msg or "needs owner approval" in msg:
            return _record_entry(ws, "skipped:validation-failed", msg,
                                 notify=True, title="ASK backup needs attention")
        if "refusing to push" in msg or "never accepted" in msg:
            return _record_entry(ws, "error", msg, notify=True,
                                 title="ASK backup failed")
        return _record_entry(ws, "error", msg, notify=True,
                             title="ASK backup failed")
    if res.get("backup_pending"):
        return _record_entry(ws, "backup-pending",
                             res.get("reason", res.get("commit", "")),
                             notify=res.get("reason") not in (None, "no-remote"))
    return _record_entry(ws, "ok",
                         "committed %d file(s)%s"
                         % (len(ordinary),
                            " and pushed" if res.get("pushed") else ""),
                         notify=False)


def _record_entry(ws, state, detail, notify, title="ASK backup"):
    entry = _record(ws, state, detail)
    if notify and _should_notify(ws, "%s:%s" % (state, detail)):
        _notify(title, "%s: %s" % (state, detail))
    return {"state": state, "detail": detail,
            "pushed": state == "ok" and "pushed" in detail}
