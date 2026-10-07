#!/usr/bin/env python3
"""ASK GitHub private-workspace versioning (Python 3.9+ standard library only).

No network except through the installed `gh` CLI (repo visibility checks and
creation) and Git remote operations. No force-push, no stash, no rebase.
"""
import json
import os
import re
import secrets
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit

class GitError(Exception):
    pass


ASK_DIR = ".ask"
LOCK_NAME = "gitops.lock"
WRITERS_DIR = "writers"

WORKSPACE_FILES = ("ask.json", "note.schema.json", "AGENTS.md", ".gitignore")
# Vault-root policy/schema/tag notes.
# Ordinary vault-root notes and nested indexes are NOT protected.
VAULT_ROOT_PROTECTED = frozenset({
    "agents.md", "knowledge-map.md", "knowledge-continuity-loop.md",
    "frontmatter-schema.md", "continuity.md", "schema.md",
    "tags.md", "taxonomy.md", "ontology.md",
})
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
SECRET_BASENAMES = {
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "credentials", "credentials.json", "secrets.json", "tokens.json",
    "secret.yaml", "secrets.yaml", "secret.yml", "secrets.yml",
}
SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GIT_TIMEOUT = 30
NETWORK_TIMEOUT = 60


def _ws(workspace):
    ws = Path(workspace).expanduser().absolute()
    if not ws.is_dir():
        raise GitError("workspace is not a directory: %s" % ws)
    return ws


def _git(ws, *args, check=True):
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(ws), text=True,
            capture_output=True, env=_git_env(),
            timeout=NETWORK_TIMEOUT if args and args[0] in ("push", "fetch") else GIT_TIMEOUT)
    except FileNotFoundError:
        raise GitError("git is not installed")
    except subprocess.TimeoutExpired:
        raise GitError("git %s timed out" % args[0])
    if check and proc.returncode != 0:
        raise GitError("git %s failed: %s" % (
            " ".join(args), (proc.stderr or proc.stdout).strip()))
    return proc


def _git_env():
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    env["GIT_SSH_COMMAND"] = "ssh -oBatchMode=yes -oConnectTimeout=15"
    return env


def _toplevel(ws):
    proc = _git(ws, "rev-parse", "--show-toplevel", check=False)
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip()).resolve()


def _ensure_root(ws):
    ws = _ws(ws)
    top = _toplevel(ws)
    if top is None:
        raise GitError("not a git workspace (run initialize): %s" % ws)
    if top != ws.resolve():
        raise GitError("workspace root %s is inside containing repo %s"
                       % (ws, top))
    return ws


def _ask_dir(ws):
    d = ws / ASK_DIR
    if d.is_symlink():
        raise GitError("refusing symlinked ASK runtime directory")
    d.mkdir(exist_ok=True)
    if not d.is_dir():
        raise GitError("ASK runtime path is not a directory")
    return d


def _lock_path(ws):
    return ws / ASK_DIR / LOCK_NAME


def _acquire_lock(ws):
    _ask_dir(ws)
    path = _lock_path(ws)
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise GitError("another ASK git/backup operation is in progress")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"pid": os.getpid(), "time": time.time()}))
    return path


def _release_lock(ws):
    try:
        _lock_path(ws).unlink()
    except OSError:
        pass


def _writers_dir(ws):
    d = ws / ASK_DIR / WRITERS_DIR
    _ask_dir(ws)
    if d.is_symlink():
        raise GitError("refusing symlinked writer directory")
    d.mkdir(parents=True, exist_ok=True)
    return d


def begin_write(workspace, actor):
    """Record an active writer; returns an opaque token dict."""
    ws = _ws(workspace)
    if not actor or not isinstance(actor, str):
        raise GitError("actor must be a non-empty string")
    _acquire_lock(ws)
    try:
        token = secrets.token_urlsafe(16)
        marker = _writers_dir(ws) / token
        try:
            fd = os.open(str(marker), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise GitError("writer token collision; retry")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"actor": actor, "pid": os.getpid(),
                       "time": time.time()}, fh)
        return {"token": token, "actor": actor}
    finally:
        _release_lock(ws)


def end_write(workspace, token):
    """Remove only the matching writer marker; never clears others."""
    ws = _ws(workspace)
    if not token or not isinstance(token, str) or "/" in token:
        raise GitError("unknown write token")
    marker = ws / ASK_DIR / WRITERS_DIR / token
    if not marker.is_file():
        raise GitError("unknown write token")
    marker.unlink()
    return {"ended": True}


def active_writes(workspace):
    """List active writer markers; never clears stale entries."""
    ws = _ws(workspace)
    out = []
    d = ws / ASK_DIR / WRITERS_DIR
    if d.is_symlink():
        raise GitError("refusing symlinked writer directory")
    if not d.is_dir():
        return out
    for child in sorted(d.iterdir()):
        if not child.is_file():
            continue
        try:
            info = json.loads(child.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            info = {}
        if not isinstance(info, dict):
            info = {}
        info = dict(info)
        info["token"] = child.name
        out.append(info)
    return out


def _load_vault(ws):
    """Return (vault Path, bootstrap list) from ask.json.

    Tolerant only when ask.json is absent. An unreadable or corrupt ask.json
    fails closed so protected-path detection never silently degrades.
    """
    cfg_path = ws / "ask.json"
    if not cfg_path.exists():
        return ws, []
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise GitError("cannot read workspace ask.json: %s" % e)
    if not isinstance(cfg, dict):
        raise GitError("invalid workspace ask.json object")
    raw = cfg.get("vault_root", "")
    if not isinstance(raw, str):
        raise GitError("invalid vault_root in workspace ask.json")
    vault = (ws / raw).absolute() if raw and not os.path.isabs(raw) \
        else Path(raw).absolute() if raw else ws
    boot = cfg.get("bootstrap_files", [])
    if not isinstance(boot, list):
        boot = []
    if not vault.resolve().is_relative_to(ws.resolve()):
        raise GitError("vault_root escapes workspace")
    return vault, [b for b in boot if isinstance(b, str)]


def _policy_refusal(message):
    text = str(message)
    return any(k in text for k in (
        "refusing", "never accepted", "not accepted", "not a verifiable",
        "credential-bearing", "is not a directory", "not a git workspace",
        "containing repo"))


def is_secret_or_state(rel):
    """Public classifier for obvious secret/state paths."""
    return _is_secret_or_state(Path(rel).as_posix())


def is_protected(workspace, rel):
    """Public protected-path check; fails closed on unreadable config."""
    ws = _ws(workspace)
    norm = Path(rel).as_posix()
    if norm in WORKSPACE_FILES:
        return True
    return _is_protected(ws, norm)


def _is_secret_or_state(rel):
    if rel == ".gitignore":
        return False
    parts = Path(rel).parts
    if not parts or any(part.startswith(".") for part in parts) or parts[0] in (".git", ASK_DIR):
        return True
    base = parts[-1]
    if base.startswith(".env") and (base == ".env" or base.startswith(".env.")):
        return True
    if base.lower() in SECRET_BASENAMES or base.lower().endswith(SECRET_SUFFIXES):
        return True
    return False


def _check_rel(ws, value):
    if not isinstance(value, str) or not value:
        raise GitError("path must be a non-empty relative path")
    if "\\" in value:
        raise GitError("unsafe path: %s" % value)
    p = Path(value)
    if not p.parts or value.endswith("/") or value == ".":
        raise GitError("checkpoint paths must name individual files")
    if p.is_absolute() or any(x == ".." for x in p.parts):
        raise GitError("unsafe path escapes workspace: %s" % value)
    full = (ws / p).absolute()
    try:
        full.relative_to(ws.resolve())
    except ValueError:
        raise GitError("unsafe path escapes workspace: %s" % value)
    # Reject symlink traversal through existing components.
    cur = ws.resolve()
    for part in p.parts:
        cur = cur / part
        if cur.is_symlink():
            raise GitError("symlink path is not allowed: %s" % value)
    if p.parts[0] in (".git", ASK_DIR):
        raise GitError("refused runtime path: %s" % value)
    if _is_secret_or_state(p.as_posix()):
        raise GitError("refused secret/state path: %s" % value)
    if full.is_dir():
        raise GitError("checkpoint paths must name individual files: %s" % value)
    if not full.exists() and _git(ws, "ls-files", "--error-unmatch", "--",
                                  p.as_posix(), check=False).returncode != 0:
        raise GitError("checkpoint path does not exist or track a deletion: %s" % value)
    return p.as_posix()


def _is_protected(ws, rel):
    if rel in WORKSPACE_FILES:
        return True
    vault, boot = _load_vault(ws)
    try:
        vault_rel = (ws / rel).resolve().relative_to(vault.resolve())
    except ValueError:
        return False
    vrel = vault_rel.as_posix()
    parts = vault_rel.parts
    if not parts:
        return False
    if len(parts) == 1 and (parts[0].lower() in VAULT_ROOT_PROTECTED or
                            any(term in parts[0].lower() for term in
                                ("taxonomy", "ontology", "continuity", "schema", "tags"))):
        return True  # vault-root policy/schema/tag notes
    if parts[0] == "Agents":
        if len(parts) == 2 and parts[1] in ("roster.md", "ontology.md"):
            return True
        if len(parts) >= 2 and parts[1] == "rules":
            return True
    return False


def _porcelain(ws):
    proc = _git(ws, "status", "--porcelain=v1", "-z", "-uall", check=False)
    if proc.returncode != 0:
        raise GitError("git status failed: %s" % proc.stderr.strip())
    staged, unstaged, untracked, conflicts = [], [], [], []
    entries = iter(proc.stdout.split("\0"))
    for line in entries:
        if not line:
            continue
        x, y, path = line[0], line[1], line[3:]
        if x in "RC" or y in "RC":
            next(entries, None)  # -z rename/copy's second path is the source
        if x == "?" and (path == ASK_DIR or path.startswith(ASK_DIR + "/")):
            continue
        if x == "U" or y == "U" or (x == "A" and y == "A") or (x == "D" and y == "D"):
            conflicts.append(path)
        if x == "?" and y == "?":
            untracked.append(path)
            continue
        if x != " ":
            staged.append(path)
        if y != " ":
            unstaged.append(path)
    return {"staged": sorted(staged), "unstaged": sorted(unstaged),
            "untracked": sorted(untracked), "conflicts": sorted(conflicts)}


def _branch(ws):
    proc = _git(ws, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return "main"


def _upstream(ws):
    proc = _git(ws, "rev-parse", "--abbrev-ref", "@{u}", check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _ahead_behind(ws):
    up = _upstream(ws)
    if up is None:
        return {"ahead": 0, "behind": 0, "upstream": None}
    ahead = _git(ws, "rev-list", "--count", "%s..HEAD" % "@{u}",
                 check=False)
    behind = _git(ws, "rev-list", "--count", "HEAD..%s" % "@{u}",
                  check=False)
    try:
        return {"ahead": int(ahead.stdout.strip()),
                "behind": int(behind.stdout.strip()), "upstream": up}
    except ValueError:
        return {"ahead": 0, "behind": 0, "upstream": up}


def initialize(workspace):
    """Init git main if absent; refuse containing repos. No network."""
    ws = _ws(workspace)
    top = _toplevel(ws)
    if top is not None:
        if top != ws.resolve():
            raise GitError(
                "workspace %s is inside containing repo %s" % (ws, top))
        return {"initialized": False, "branch": _branch(ws),
                "path": str(ws)}
    proc = _git(ws, "init", "-b", "main", check=False)
    if proc.returncode != 0:  # git < 2.28 fallback
        _git(ws, "init")
        _git(ws, "symbolic-ref", "HEAD", "refs/heads/main")
    return {"initialized": True, "branch": "main", "path": str(ws)}


def status(workspace):
    ws = _ensure_root(workspace)
    porc = _porcelain(ws)
    ab = _ahead_behind(ws)
    clean = not any(porc.values())
    try:
        origin = _git(ws, "remote", "get-url", "origin",
                      check=False).stdout.strip() or None
    except GitError:
        origin = None
    return {"path": str(ws), "branch": _branch(ws), "clean": clean,
            "staged": porc["staged"], "unstaged": porc["unstaged"],
            "untracked": porc["untracked"], "conflicts": porc["conflicts"],
            "ahead": ab["ahead"],
            "behind": ab["behind"], "upstream": ab["upstream"],
            "origin": origin}


def _parse_slug(repository):
    if not isinstance(repository, str) or not repository.strip():
        raise GitError("repository must be 'owner/name' or a GitHub URL")
    repo = repository.strip()
    if "://" in repo:
        parts = urlsplit(repo)
        if parts.scheme not in ("https",):
            raise GitError("only https GitHub remote URLs are accepted")
        if parts.username or parts.password or "@" in parts.netloc:
            raise GitError("credential-bearing remote URLs are never accepted")
        if parts.hostname != "github.com":
            raise GitError("only github.com remotes are accepted")
        slug = parts.path.strip("/").removesuffix(".git")
        if not SLUG_RE.match(slug):
            raise GitError("cannot parse owner/name from URL")
        return slug
    slug = repo.removesuffix(".git").strip("/")
    if not SLUG_RE.match(slug):
        raise GitError("repository must look like 'owner/name'")
    return slug


def _gh(*args):
    try:
        proc = subprocess.run(
            ["gh", *args], text=True, capture_output=True,
            env=_git_env(), timeout=NETWORK_TIMEOUT)
    except FileNotFoundError:
        raise GitError("gh CLI is not installed; cannot verify remote privacy")
    except subprocess.TimeoutExpired:
        raise GitError("gh privacy verification timed out")
    return proc


def _gh_visibility(slug):
    proc = _gh("repo", "view", slug, "--json", "visibility")
    if proc.returncode != 0:
        raise GitError("gh cannot see repo %s: %s"
                       % (slug, (proc.stderr or proc.stdout).strip()))
    try:
        return json.loads(proc.stdout)["visibility"].upper()
    except (ValueError, KeyError, AttributeError):
        raise GitError("gh returned unreadable visibility for %s" % slug)


def _origin_slug(url):
    if url.startswith("git@github.com:"):
        slug = url.split(":", 1)[1].removesuffix(".git")
        return slug if SLUG_RE.match(slug) else None
    if "://" in url:
        parts = urlsplit(url)
        if (parts.hostname == "github.com" and parts.scheme == "https"
                and not parts.username and not parts.password
                and "@" not in parts.netloc and not parts.port
                and not parts.query and not parts.fragment):
            slug = parts.path.strip("/").removesuffix(".git")
            return slug if SLUG_RE.match(slug) else None
    return None


def _ensure_private_remote(ws):
    """Verify origin privacy via gh. Returns origin URL.

    Verify both fetch and effective push URLs before network access.
    """
    fetch = _git(ws, "remote", "get-url", "--all", "origin", check=False)
    if fetch.returncode != 0:
        return None
    push = _git(ws, "remote", "get-url", "--push", "--all", "origin")
    fetch_urls = fetch.stdout.splitlines()
    push_urls = push.stdout.splitlines()
    if len(fetch_urls) != 1 or len(push_urls) != 1:
        raise GitError("multiple remote URLs are not accepted")
    url = fetch_urls[0]
    slug = _origin_slug(url)
    if slug is None or _origin_slug(push_urls[0]) != slug:
        raise GitError("remote is not a verifiable matching github.com URL")
    visibility = _gh_visibility(slug)
    if visibility != "PRIVATE":
        raise GitError("refusing to push: remote %s is %s" % (slug, visibility))
    return url


def configure_remote(workspace, repository, create=False):
    """Verify/create a PRIVATE GitHub repo via gh and set origin."""
    ws = _ensure_root(workspace)
    slug = _parse_slug(repository)
    proc = _gh("repo", "view", slug, "--json", "visibility")
    if proc.returncode != 0:
        if not create:
            raise GitError("repo %s not visible to gh (use create=True): %s"
                           % (slug, (proc.stderr or proc.stdout).strip()))
        made = _gh("repo", "create", slug, "--private")
        if made.returncode != 0:
            raise GitError("gh could not create private repo %s: %s"
                           % (slug, (made.stderr or made.stdout).strip()))
        proc = _gh("repo", "view", slug, "--json", "visibility")
        if proc.returncode != 0:
            raise GitError("gh cannot verify created repo %s" % slug)
    try:
        visibility = json.loads(proc.stdout)["visibility"].upper()
    except (ValueError, KeyError, AttributeError):
        raise GitError("gh returned unreadable visibility for %s" % slug)
    if visibility != "PRIVATE":
        raise GitError("refusing remote: repo %s is %s (private only)"
                       % (slug, visibility))
    url = "https://github.com/%s.git" % slug
    exists = _git(ws, "remote", "get-url", "origin", check=False)
    if exists.returncode == 0:
        _git(ws, "remote", "set-url", "origin", url)
    else:
        _git(ws, "remote", "add", "origin", url)
    return {"repository": slug, "visibility": visibility, "origin": url}


def _push(ws):
    if _git(ws, "rev-parse", "--verify", "HEAD", check=False).returncode != 0:
        return {"pushed": False, "backup_pending": False, "reason": "no-commits"}
    url = _ensure_private_remote(ws)
    if url is None:
        return {"pushed": False, "backup_pending": True,
                "reason": "no-remote"}
    proc = _git(ws, "push", "-u", "origin", "HEAD", check=False)
    if proc.returncode != 0:
        out = (proc.stderr or proc.stdout).strip()
        if any(term in out.lower() for term in
               ("non-fast-forward", "fetch first", "rejected", "stale info")):
            return {"pushed": False, "backup_pending": True,
                    "reason": "diverged"}
        return {"pushed": False, "backup_pending": True,
                "reason": "offline", "detail": out[:500]}
    return {"pushed": True, "backup_pending": False}


def push_pending(workspace):
    """Push ahead commits after a privacy check; offline -> backup-pending."""
    ws = _ensure_root(workspace)
    _acquire_lock(ws)
    try:
        if _ahead_behind(ws)["ahead"] <= 0 and _upstream(ws) is None:
            pass
        return _push(ws)
    finally:
        _release_lock(ws)


def sync(workspace):
    """Fetch, ff-only merge when clean, push ahead. No force/stash/rebase."""
    ws = _ensure_root(workspace)
    _acquire_lock(ws)
    try:
        st = status(ws)
        out = {"clean": st["clean"], "fetched": False, "pulled": False,
               "pushed": False, "backup_pending": False, "offline": False,
               "ahead": st["ahead"], "behind": st["behind"]}
        if active_writes(ws) or st["conflicts"] or st["staged"]:
            out["pull_reason"] = "active-writers" if active_writes(ws) else "conflicts" if st["conflicts"] else "staged-work"
            return out
        url = _ensure_private_remote(ws)
        has_origin = url is not None
        if not has_origin:
            out["backup_pending"] = True
            out["push_reason"] = "no-remote"
            return out
        if has_origin:
            fetch = _git(ws, "fetch", "origin", check=False)
            if fetch.returncode != 0:
                out["offline"] = True
                out["backup_pending"] = True
                out["push_reason"] = "fetch-failed"
                return out
            else:
                out["fetched"] = True
        if out["fetched"] and st["clean"] and _upstream(ws):
            merge = _git(ws, "merge", "--ff-only", "@{u}", check=False)
            if merge.returncode == 0:
                out["pulled"] = True
            else:
                out["pull_reason"] = "non-fast-forward"
        elif not st["clean"]:
            out["pull_reason"] = "dirty"
        ab = _ahead_behind(ws)
        out["ahead"], out["behind"] = ab["ahead"], ab["behind"]
        if ab["ahead"] > 0 or (_upstream(ws) is None and has_origin):
            if ab["behind"] > 0:
                out["backup_pending"] = True
                out["push_reason"] = "behind"
                return out
            res = _push(ws)
            out["pushed"] = res["pushed"]
            out["backup_pending"] = res["backup_pending"]
            if res.get("reason"):
                out["push_reason"] = res["reason"]
        return out
    finally:
        _release_lock(ws)


def _identity(ws):
    # Repo-scoped only: global/system identity must not leak into ASK commits.
    name = _git(ws, "config", "--local", "user.name",
                check=False).stdout.strip()
    email = _git(ws, "config", "--local", "user.email",
                 check=False).stdout.strip()
    return name, email


def checkpoint(workspace, paths, message, validator, owner_approved=False,
               actor="agent"):
    """Stage exactly `paths`, validate the staged snapshot, commit, push."""
    ws = _ensure_root(workspace)
    if not isinstance(paths, (list, tuple)) or not paths:
        raise GitError("paths must be a non-empty list of workspace-relative paths")
    if not isinstance(message, str) or not message.strip():
        raise GitError("message must be a non-empty string")
    if not callable(validator):
        raise GitError("validator must be callable")
    if not isinstance(actor, str) or not actor:
        raise GitError("actor must be a non-empty string")
    rels = [_check_rel(ws, p) for p in paths]
    if len(set(rels)) != len(rels):
        raise GitError("duplicate paths in checkpoint")
    for rel in rels:
        if _is_protected(ws, rel) and not owner_approved:
            raise GitError("protected path needs owner approval: %s" % rel)
    _acquire_lock(ws)
    try:
        return _checkpoint_locked(ws, rels, message, validator)
    finally:
        _release_lock(ws)


def _checkpoint_locked(ws, rels, message, validator):
        porc = _porcelain(ws)
        if porc["conflicts"]:
            raise GitError("unresolved conflict present")
        if porc["staged"]:
            raise GitError("preexisting staged file present, refusing: %s" % porc["staged"][0])
        name, email = _identity(ws)
        if not name or not email:
            raise GitError(
                "missing repo-scoped identity; run: git -C %s config "
                "user.name 'Your Name' && git -C %s config "
                "user.email 'you@example.com'" % (ws, ws))
        _git(ws, "add", "-A", "--", *rels)
        if _git(ws, "diff", "--cached", "--quiet", check=False).returncode == 0:
            res = _push(ws) if (_ahead_behind(ws)["ahead"] > 0 or
                                _upstream(ws) is None) else \
                {"pushed": False, "backup_pending": False}
            return {"committed": False, "reason": "no-changes",
                    "pushed": res["pushed"],
                    "backup_pending": res["backup_pending"]}
        try:
            validator()
            extras = set(_porcelain(ws)["staged"]) - set(rels)
            if extras:
                raise GitError("validator staged undeclared files: %s" %
                               ", ".join(sorted(extras)[:5]))
        except Exception as e:
            if _git(ws, "rev-parse", "--verify", "HEAD", check=False).returncode == 0:
                _git(ws, "reset", "-q")
            else:
                indexed = _git(ws, "ls-files", "-z").stdout.split("\0")
                indexed = [p for p in indexed if p]
                if indexed:
                    _git(ws, "rm", "--cached", "-q", "--ignore-unmatch",
                         "--", *indexed)
            raise GitError("validator rejected staged snapshot: %s" % e)
        _git(ws, "commit", "-m", message.strip())
        sha = _git(ws, "rev-parse", "HEAD").stdout.strip()
        try:
            res = _push(ws)
        except GitError as e:
            if _policy_refusal(e):
                raise GitError('Local commit %s saved; remote refused: %s' % (sha, e))
            return {"committed": True, "commit": sha, "pushed": False,
                    "backup_pending": True, "reason": "privacy-unverified"}
        return {"committed": True, "commit": sha, "pushed": res["pushed"],
                "backup_pending": res["backup_pending"]}
