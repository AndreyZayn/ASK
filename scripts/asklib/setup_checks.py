"""Conservative, read-only setup and doctor readiness checks.

``assess`` accepts controller-observed Git and runtime snapshots. Missing evidence
is pending, not success. It never initializes a workspace or changes a runtime.
"""

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
from urllib.parse import quote


BOOTSTRAP = ("date.md", "INDEX.md", "agents.md", "knowledge-map.md")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_COMMIT = re.compile(r"^[0-9a-fA-F]{40,64}$")


def _check(ok, status, detail):
    return {"ok": bool(ok), "status": status, "detail": detail}


def _relative_path(value):
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def _covers(read_paths, note):
    return any(
        entry == "." or note == entry or note.startswith(entry.rstrip("/") + "/")
        for entry in read_paths
    )


def _config_check(config_path):
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(config, dict):
            raise ValueError("configuration is not an object")
        vault_name = _relative_path(config.get("vault_root"))
        boot = config.get("bootstrap_files")
        access = config.get("access")
        topology = config.get("validation")
        if config.get("ask_version") != "1.0.0":
            raise ValueError("ask_version is missing or invalid")
        if vault_name is None or vault_name == Path("."):
            raise ValueError("vault_root is unsafe")
        if not isinstance(topology, dict) or topology.get("topology") is not True:
            raise ValueError("topology is not enabled")
        if not isinstance(boot, list) or tuple(boot) != BOOTSTRAP:
            raise ValueError("ordered four-note bootstrap is missing")
        if not isinstance(access, dict) or any(
            not isinstance(access.get(k), list)
            or any(_relative_path(p) is None for p in access[k])
            for k in ("read", "write")
        ):
            raise ValueError("read/write declarations are invalid")
        if not all(_covers(access["read"], note) for note in BOOTSTRAP):
            raise ValueError("read declarations do not cover the bootstrap")
        vault = config_path.parent / vault_name
        if not vault.is_dir() or vault.is_symlink() or any(
            not (vault / note).is_file() or (vault / note).is_symlink()
            for note in BOOTSTRAP
        ):
            raise ValueError("bootstrap notes are missing")
        return config, _check(True, "ready", "Configuration and bootstrap are present")
    except (OSError, UnicodeError, ValueError, TypeError):
        # Do not expose configuration contents or exception text (paths may be private).
        return {}, _check(False, "invalid", "Configuration or bootstrap is incomplete")


def _origin_repo(origin):
    if not isinstance(origin, str):
        return None
    match = re.fullmatch(
        r"(?:git@github\.com:|ssh://git@github\.com/|https://github\.com/)"
        r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?", origin, re.I
    )
    return match.group(1) if match else None


def backup_status(config, git_status):
    """Verify current HEAD is clean, tracked on origin, and remotely private.

    Git facts are supplied by the controller after a remote fetch. ``remote_head``
    must be the observed upstream commit, not a locally inferred ahead count.
    """
    if not isinstance(git_status, dict):
        return _check(False, "unverified", "Git status was not observed")
    backup = config.get("backup")
    repository = (backup.get("repository") if isinstance(backup, dict) else None)
    if repository is None:
        repository = config.get("repository")
    if not isinstance(repository, str) or not _REPO.fullmatch(repository):
        return _check(False, "not-configured", "No backup repository is bound")
    origin = _origin_repo(git_status.get("origin"))
    if origin is None or origin.casefold() != repository.casefold():
        return _check(False, "unverified", "Origin does not match the bound repository")
    upstream = git_status.get("upstream")
    head = git_status.get("head")
    remote_head = git_status.get("remote_head")
    if not (
        isinstance(upstream, str) and upstream.startswith("origin/")
        and len(upstream) > len("origin/")
        and isinstance(head, str) and _COMMIT.fullmatch(head)
        and isinstance(remote_head, str) and _COMMIT.fullmatch(remote_head)
        and head.lower() == remote_head.lower()
        and type(git_status.get("ahead")) is int and git_status["ahead"] == 0
        and type(git_status.get("behind")) is int and git_status["behind"] == 0
        and git_status.get("clean") is True
    ):
        return _check(False, "unverified", "Clean HEAD at the observed origin upstream is not proven")
    try:
        result = subprocess.run(
            ["gh", "repo", "view", repository, "--json", "nameWithOwner,isPrivate"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if result.returncode != 0:
            return _check(False, "unverified", "Repository privacy could not be verified")
        data = json.loads(result.stdout)
        if (not isinstance(data, dict) or data.get("isPrivate") is not True
                or not isinstance(data.get("nameWithOwner"), str)
                or data["nameWithOwner"].casefold() != repository.casefold()):
            return _check(False, "unverified", "Repository is not verified private")
        branch = upstream[len("origin/"):]
        remote = subprocess.run(
            ["gh", "api", "repos/%s/git/ref/heads/%s" % (repository, quote(branch, safe=""))],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if remote.returncode != 0:
            return _check(False, "unverified", "Remote branch could not be verified")
        ref = json.loads(remote.stdout)
        if (not isinstance(ref, dict) or not isinstance(ref.get("object"), dict)
                or not isinstance(ref["object"].get("sha"), str)
                or ref["object"]["sha"].lower() != head.lower()):
            return _check(False, "unverified", "Remote branch does not match HEAD")
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        return _check(False, "unverified", "Repository privacy could not be verified")
    return _check(True, "verified", "Clean HEAD matches the private origin upstream")


def _runtime_checks(runtime_status):
    runtimes = runtime_status.get("runtimes") if isinstance(runtime_status, dict) else None
    if not isinstance(runtimes, dict) or not runtimes:
        return {"runtime": _check(False, "not-configured", "No runtime is registered")}
    checks = {}
    for name, record in sorted(runtimes.items()):
        if not isinstance(name, str) or not isinstance(record, dict):
            checks["runtime:invalid"] = _check(False, "unverified", "Invalid runtime record")
            continue
        proof = record.get("evidence")
        verified = (
            record.get("state") == "verified"
            and (record.get("block_present") is True or (name not in ('claude','codex') and record.get('target') is None))
            and isinstance(proof, dict)
            and proof.get('bootstrap_files') == list(BOOTSTRAP)
            and all(isinstance(proof.get(k),dict) and proof[k].get('session_id') and proof[k].get('observed_phrase') for k in ('inside_session','outside_session'))
        )
        state = "verified" if verified else (
            "not-configured" if record.get("state") == "not-configured"
            else "configured-unverified"
        )
        checks["runtime:" + name] = _check(
            verified, state, "Fresh inside/outside proof and current block" if verified
            else "Runtime registration or fresh-session proof is incomplete"
        )
    return checks


def _hook_check(config_path):
    hook = config_path.parent / ".ask" / "hooks" / "pre-commit"
    try:
        if not hook.is_file() or hook.is_symlink() or not os.access(hook, os.X_OK):
            return _check(False, "not-configured", "Executable pre-commit hook is missing")
        text = hook.read_text(encoding="utf-8")
        for line in text.splitlines():
            try:
                tokens = shlex.split(line, comments=True)
            except ValueError:
                continue
            if "--config" not in tokens:
                continue
            pos = tokens.index("--config")
            if pos + 1 >= len(tokens):
                continue
            if (Path(tokens[pos + 1]).expanduser().absolute() == config_path.absolute()
                    and any(Path(t).name == "ask.py" for t in tokens[:pos])
                    and "validate" in tokens[:pos] and "--staged" in tokens):
                return _check(True, "installed", "Executable hook uses this configuration")
    except (OSError, UnicodeError):
        pass
    return _check(False, "unverified", "Hook command does not match this configuration")


def assess(config_path: Path, git_status: dict, runtime_status: dict,
           validation_report: dict) -> dict:
    """Return deterministic readiness aggregation; never treat absent proof as ready."""
    config_path = Path(config_path)
    config, config_check = _config_check(config_path)
    counts = validation_report.get("counts") if isinstance(validation_report, dict) else None
    valid = (
        isinstance(counts, dict)
        and type(counts.get("errors")) is int and counts["errors"] == 0
        and type(counts.get("notes")) is int and counts["notes"] > 0
        and validation_report.get("issues") == []
    )
    checks = {
        "config": config_check,
        "validation": _check(valid, "valid" if valid else "invalid",
                             "Vault validation passed" if valid else "Vault validation is incomplete"),
        "backup": backup_status(config, git_status),
        "hook": _hook_check(config_path),
    }
    checks.update(_runtime_checks(runtime_status))
    pending = [name for name, check in checks.items() if not check["ok"]]
    return {"state": "setup-pending" if pending else "ready",
            "pending": pending, "checks": checks}
