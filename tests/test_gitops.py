import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from asklib import gitops  # noqa: E402


def git(*args, cwd, env=None):
    e = dict(os.environ)
    e["GIT_CONFIG_NOSYSTEM"] = "1"
    e["GIT_TERMINAL_PROMPT"] = "0"
    if env:
        e.update(env)
    return subprocess.run(["git", *args], cwd=str(cwd), text=True,
                          capture_output=True, env=e)


def make_workspace(base, name="ws", vault_name="Knowledge Base"):
    ws = base / name
    (ws / vault_name).mkdir(parents=True)
    (ws / "ask.json").write_text(json.dumps({
        "version": 1, "vault_root": vault_name,
        "schema_path": "note.schema.json",
        "bootstrap_files": ["INDEX.md", "agents.md"],
        "access": {"read": ["."], "write": ["."]},
    }))
    (ws / "note.schema.json").write_text("{}")
    (ws / "AGENTS.md").write_text("adapter\n")
    (ws / vault_name / "INDEX.md").write_text("idx\n")
    (ws / vault_name / "agents.md").write_text("policy\n")
    (ws / vault_name / "notes.md").write_text("ordinary\n")
    (ws / vault_name / "Agents").mkdir(exist_ok=True)
    (ws / vault_name / "Agents" / "rules").mkdir(exist_ok=True)
    (ws / vault_name / "Agents" / "rules" / "r.md").write_text("rule\n")
    (ws / vault_name / "Agents" / "roster.md").write_text("roster\n")
    return ws


def set_identity(ws):
    git("config", "user.name", "Test Owner", cwd=ws).check_returncode()
    git("config", "user.email", "owner@example.test", cwd=ws).check_returncode()


class FakeGh:
    """Injectable `gh` on PATH. Visibility driven only by env."""

    def __init__(self, tmp):
        self.bindir = tmp / "fakebin"
        self.bindir.mkdir()
        gh = self.bindir / "gh"
        gh.write_text(
            "#!/bin/sh\n"
            "if [ \"$FAKE_GH_MISSING\" = \"1\" ]; then exit 1; fi\n"
            "if [ \"$1\" = \"repo\" ] && [ \"$2\" = \"view\" ]; then\n"
            "  echo \"{\\\"visibility\\\": \\\"$FAKE_GH_VISIBILITY\\\"}\"\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"repo\" ] && [ \"$2\" = \"create\" ]; then\n"
            "  echo \"created $3\" >&2\n"
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def env(self, visibility="PRIVATE"):
        e = dict(os.environ)
        e["PATH"] = str(self.bindir) + os.pathsep + e["PATH"]
        e["FAKE_GH_VISIBILITY"] = visibility
        return e


class GitopsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.gh = FakeGh(self.base)
        self._old_path = os.environ.get("PATH", "")
        self._old_vis = os.environ.get("FAKE_GH_VISIBILITY")
        self._old_miss = os.environ.get("FAKE_GH_MISSING")
        self.ws = make_workspace(self.base)

    def tearDown(self):
        os.environ["PATH"] = self._old_path
        for k, v in (("FAKE_GH_VISIBILITY", self._old_vis),
                     ("FAKE_GH_MISSING", self._old_miss)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def run_gitops(self, fn, *a, **k):
        old = dict(os.environ)
        os.environ.update(self.gh.env(k.pop("visibility", "PRIVATE")))
        try:
            return fn(*a, **k)
        finally:
            os.environ.clear()
            os.environ.update(old)

    def add_remote(self, name="origin"):
        remote = self.base / "remote.git"
        subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(remote)],
                       check=True, capture_output=True)
        git("remote", "add", name, str(remote), cwd=self.ws).check_returncode()
        return remote

    def verified_file_remote(self):
        # Only tests, never production, bypass visibility for synthetic bare repos.
        return mock.patch.object(gitops, "_ensure_private_remote",
                                 return_value="verified synthetic remote")

    def test_scaffold_gitignore_is_protected_but_not_secret(self):
        (self.ws/'.gitignore').write_text('.ask/\n')
        self.assertEqual(gitops._check_rel(self.ws,'.gitignore'),'.gitignore')
        self.assertTrue(gitops.is_protected(self.ws,'.gitignore'))
        self.assertTrue(gitops.is_protected(self.ws,'Knowledge Base/Agents/ontology.md'))

    def test_privacy_check_offline_returns_local_commit_pending(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        with mock.patch.object(gitops,'_ensure_private_remote',side_effect=gitops.GitError('gh cannot see repo: network unavailable')):
            result=gitops.checkpoint(self.ws,['Knowledge Base/notes.md'],'offline note',lambda:None)
        self.assertTrue(result['committed'])
        self.assertTrue(result['backup_pending'])
        self.assertFalse(result['pushed'])

    def test_initialize_creates_main_no_network(self):
        out = gitops.initialize(self.ws)
        self.assertTrue(out["initialized"])
        r = git("symbolic-ref", "--short", "HEAD", cwd=self.ws)
        self.assertEqual(r.stdout.strip(), "main")
        again = gitops.initialize(self.ws)
        self.assertFalse(again["initialized"])

    def test_initialize_refuses_containing_repo(self):
        outer = self.base / "outer"
        outer.mkdir()
        subprocess.run(["git", "init", "-b", "main", str(outer)],
                       check=True, capture_output=True)
        inner = outer / "inner"
        inner.mkdir()
        with self.assertRaises(gitops.GitError):
            gitops.initialize(inner)

    def test_status_clean_and_dirty(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        st = gitops.status(self.ws)
        self.assertIn("branch", st)
        (self.ws / "Knowledge Base" / "notes.md").write_text("edit\n")
        st2 = gitops.status(self.ws)
        self.assertFalse(st2["clean"])

    def test_checkpoint_needs_identity(self):
        gitops.initialize(self.ws)
        (self.ws / "Knowledge Base" / "notes.md").write_text("edit\n")
        with self.assertRaises(gitops.GitError) as cm:
            self.run_gitops(gitops.checkpoint, self.ws,
                            paths=["Knowledge Base/notes.md"],
                            message="edit", validator=lambda: None)
        self.assertIn("user.name", str(cm.exception))

    def test_checkpoint_commit_and_push_file_remote(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        self.add_remote()
        with self.verified_file_remote():
            out = self.run_gitops(
                gitops.checkpoint, self.ws,
                paths=["Knowledge Base/notes.md"],
                message="ordinary edit", validator=lambda: None)
        self.assertTrue(out["committed"])
        self.assertTrue(out["pushed"])
        self.assertFalse(out["backup_pending"])
        r = git("log", "--oneline", cwd=self.ws)
        self.assertIn("ordinary edit", r.stdout)

    def test_checkpoint_rejects_unrelated_staged(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        (self.ws / "Knowledge Base" / "notes.md").write_text("a\n")
        (self.ws / "Knowledge Base" / "other.md").write_text("b\n")
        git("add", "--", "Knowledge Base/other.md", cwd=self.ws).check_returncode()
        with self.assertRaises(gitops.GitError) as cm:
            self.run_gitops(gitops.checkpoint, self.ws,
                            paths=["Knowledge Base/notes.md"],
                            message="x", validator=lambda: None)
        self.assertIn("staged", str(cm.exception).lower())

    def test_checkpoint_rejects_staged_runtime_file(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        (self.ws / ".ask").mkdir()
        (self.ws / ".ask" / "unexpected").write_text("user work\n")
        git("add", "-f", "--", ".ask/unexpected", cwd=self.ws).check_returncode()
        with self.assertRaisesRegex(gitops.GitError, "staged"):
            gitops.checkpoint(self.ws, ["Knowledge Base/notes.md"],
                              "ordinary", lambda: None)

    def test_checkpoint_rejects_secret_and_state_paths(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        for bad in [".env", ".env.local", "id_rsa", "k.pem", ".ask/writers/x"]:
            with self.assertRaises(gitops.GitError, msg=bad):
                self.run_gitops(gitops.checkpoint, self.ws, paths=[bad],
                                message="x", validator=lambda: None)

    def test_checkpoint_rejects_unsafe_paths(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        for bad in ["/abs/path", "../escape", "a/../../b"]:
            with self.assertRaises(gitops.GitError, msg=bad):
                self.run_gitops(gitops.checkpoint, self.ws, paths=[bad],
                                message="x", validator=lambda: None)

    def test_checkpoint_protected_needs_owner_approval(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        protected = ["ask.json", "note.schema.json", "AGENTS.md",
                     "Knowledge Base/Agents/rules/r.md",
                     "Knowledge Base/Agents/roster.md"]
        for p in protected:
            full = self.ws / p
            if p != "ask.json":
                full.write_text(full.read_text() + "more\n")
            with self.assertRaises(gitops.GitError, msg=p):
                self.run_gitops(gitops.checkpoint, self.ws, paths=[p],
                                message="x", validator=lambda: None)
        # ordinary nested index is not protected
        nested = self.ws / "Knowledge Base" / "Projects"
        nested.mkdir(exist_ok=True)
        (nested / "INDEX.md").write_text("idx\n")
        out = self.run_gitops(
            gitops.checkpoint, self.ws,
            paths=["Knowledge Base/Projects/INDEX.md"],
            message="nested index", validator=lambda: None)
        self.assertTrue(out["committed"])
        # owner approval unlocks protected
        out2 = self.run_gitops(
            gitops.checkpoint, self.ws, paths=["ask.json"],
            message="cfg", validator=lambda: None, owner_approved=True)
        self.assertTrue(out2["committed"])

    def test_checkpoint_validator_failure_commits_nothing(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)

        def bad():
            raise ValueError("schema says no")

        with self.assertRaises(gitops.GitError):
            self.run_gitops(gitops.checkpoint, self.ws,
                            paths=["Knowledge Base/notes.md"],
                            message="x", validator=bad)
        r = git("log", "--oneline", cwd=self.ws)
        self.assertNotIn("x", r.stdout)
        r2 = git("diff", "--cached", "--name-only", cwd=self.ws)
        self.assertEqual(r2.stdout.strip(), "")

    def test_checkpoint_offline_leaves_commit_pending(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        # no remote at all -> commit stays, backup pending
        out = self.run_gitops(gitops.checkpoint, self.ws,
                              paths=["Knowledge Base/notes.md"],
                              message="offline work", validator=lambda: None)
        self.assertTrue(out["committed"])
        self.assertFalse(out["pushed"])
        self.assertTrue(out["backup_pending"])
        r = git("log", "--oneline", cwd=self.ws)
        self.assertIn("offline work", r.stdout)
        no_change = gitops.checkpoint(self.ws, ["Knowledge Base/notes.md"],
                                      "nothing new", lambda: None)
        self.assertTrue(no_change["backup_pending"])

    def test_validator_cannot_stage_extra_files(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        def stage_extra():
            git("add", "--", "Knowledge Base/agents.md", cwd=self.ws).check_returncode()
        with self.assertRaisesRegex(gitops.GitError, "staged"):
            gitops.checkpoint(self.ws, ["Knowledge Base/notes.md"],
                              "no extra", stage_extra)
        self.assertNotEqual(git("rev-parse", "--verify", "HEAD", cwd=self.ws).returncode, 0)

    def test_production_rejects_file_remote_without_test_flag(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        self.add_remote()
        os.environ["ASK_TEST_FILE_REMOTE"] = "1"
        with self.assertRaises(gitops.GitError):
            self.run_gitops(gitops.checkpoint, self.ws,
                            paths=["Knowledge Base/notes.md"],
                            message="x", validator=lambda: None)

    def test_checkpoint_refuses_public_repo(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        self.run_gitops(gitops.configure_remote, self.ws,
                        repository="o/r", visibility="PRIVATE")
        with self.assertRaises(gitops.GitError) as cm:
            self.run_gitops(gitops.checkpoint, self.ws,
                            paths=["Knowledge Base/notes.md"],
                            message="x", validator=lambda: None,
                            visibility="PUBLIC")
        self.assertIn("public", str(cm.exception).lower())

    def test_checkpoint_refuses_credential_remote(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        git("remote", "add", "origin",
            "https://token123@github.com/o/r.git", cwd=self.ws).check_returncode()
        with self.assertRaises(gitops.GitError):
            self.run_gitops(gitops.checkpoint, self.ws,
                            paths=["Knowledge Base/notes.md"],
                            message="x", validator=lambda: None)

    def test_configure_remote_private_and_create(self):
        gitops.initialize(self.ws)
        out = self.run_gitops(gitops.configure_remote, self.ws,
                              repository="owner/repo", create=True)
        self.assertEqual(out["visibility"], "PRIVATE")
        r = git("remote", "get-url", "origin", cwd=self.ws)
        self.assertIn("github.com", r.stdout)
        with self.assertRaises(gitops.GitError):
            self.run_gitops(gitops.configure_remote, self.ws,
                            repository="owner/other", visibility="PUBLIC")

    def test_sync_ff_only_and_no_push_when_diverged(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        remote = self.add_remote()
        git("add", "-A", cwd=self.ws).check_returncode()
        git("commit", "-m", "seed", cwd=self.ws).check_returncode()
        (self.ws / "Knowledge Base" / "notes.md").write_text("base edit\n")
        with self.verified_file_remote():
            self.run_gitops(gitops.checkpoint, self.ws,
                            paths=["Knowledge Base/notes.md"],
                            message="base", validator=lambda: None)
        # remote moves ahead via a second clone
        clone = self.base / "clone"
        subprocess.run(["git", "clone", str(remote), str(clone)],
                       check=True, capture_output=True)
        git("config", "user.name", "T", cwd=clone).check_returncode()
        git("config", "user.email", "t@t.t", cwd=clone).check_returncode()
        (clone / "Knowledge Base").mkdir(parents=True, exist_ok=True)
        (clone / "Knowledge Base" / "notes.md").write_text("remote side\n")
        git("add", "-A", cwd=clone).check_returncode()
        git("commit", "-m", "remote ahead", cwd=clone).check_returncode()
        git("push", "origin", "HEAD:refs/heads/main", cwd=clone).check_returncode()
        with self.verified_file_remote():
            out = self.run_gitops(gitops.sync, self.ws)
        self.assertTrue(out["pulled"], (out, gitops.status(self.ws)))
        # dirty workspace must not pull/merge
        (self.ws / "Knowledge Base" / "notes.md").write_text("dirty local\n")
        (clone / "Knowledge Base" / "notes.md").write_text("remote2\n")
        git("add", "-A", cwd=clone).check_returncode()
        git("commit", "-m", "remote2", cwd=clone).check_returncode()
        git("push", "origin", "HEAD:refs/heads/main", cwd=clone).check_returncode()
        with self.verified_file_remote():
            out2 = self.run_gitops(gitops.sync, self.ws)
        self.assertFalse(out2["pulled"])

    def test_protection_is_semantic_not_bootstrap(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        for name in ("INDEX.md", "date.md"):
            rel = "Knowledge Base/" + name
            (self.ws / rel).write_text("ordinary\n")
            self.assertFalse(gitops.is_protected(self.ws, rel))
        for name in ("taxonomy.md", "tags.md", "ontology.md",
                     "knowledge-map.md", "continuity.md"):
            self.assertTrue(gitops.is_protected(self.ws, "Knowledge Base/" + name))

    def test_invalid_ask_config_fails_closed(self):
        gitops.initialize(self.ws)
        (self.ws / "ask.json").write_text("[]")
        with self.assertRaises(gitops.GitError):
            gitops.is_protected(self.ws, "Knowledge Base/notes.md")

    def test_checkpoint_rejects_directory_and_existing_staging(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        for rel in (".", "Knowledge Base", "Knowledge Base/Agents/rules"):
            with self.assertRaises(gitops.GitError, msg=rel):
                gitops.checkpoint(self.ws, [rel], "sweep", lambda: None)
        rel = "Knowledge Base/notes.md"
        git("add", "--", rel, cwd=self.ws).check_returncode()
        before = git("diff", "--cached", "--name-only", cwd=self.ws).stdout
        with self.assertRaisesRegex(gitops.GitError, "staged"):
            gitops.checkpoint(self.ws, [rel], "existing", lambda: None)
        self.assertEqual(git("diff", "--cached", "--name-only", cwd=self.ws).stdout, before)

    def test_validator_preserves_unborn_empty_index(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        with self.assertRaisesRegex(gitops.GitError, "validator"):
            gitops.checkpoint(self.ws, ["Knowledge Base/notes.md"], "bad",
                              lambda: (_ for _ in ()).throw(ValueError("no")))
        self.assertEqual(git("ls-files", "--stage", cwd=self.ws).stdout, "")
        self.assertNotEqual(git("rev-parse", "--verify", "HEAD", cwd=self.ws).returncode, 0)

    def test_porcelain_preserves_names_and_renames(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        for name in (" space ü.md", '"quoted".md', "a -> b.md"):
            (self.ws / "Knowledge Base" / name).write_text("x\n")
        st = gitops.status(self.ws)
        self.assertTrue({"Knowledge Base/" + n for n in
                         (" space ü.md", '"quoted".md', "a -> b.md")}
                        <= set(st["untracked"]))
        git("add", "--", "Knowledge Base/a -> b.md", cwd=self.ws).check_returncode()
        git("commit", "-m", "first", cwd=self.ws).check_returncode()
        git("mv", "Knowledge Base/a -> b.md",
            "Knowledge Base/new ü.md", cwd=self.ws).check_returncode()
        self.assertIn("Knowledge Base/new ü.md", gitops.status(self.ws)["staged"])

    def test_remote_pushurl_and_ssh_privacy(self):
        gitops.initialize(self.ws)
        git("remote", "add", "origin", "git@github.com:owner/repo.git",
            cwd=self.ws).check_returncode()
        with mock.patch.object(gitops, "_gh_visibility", return_value="PRIVATE") as visibility:
            self.assertEqual(gitops._ensure_private_remote(self.ws),
                             "git@github.com:owner/repo.git")
            visibility.assert_called_with("owner/repo")
        for pushurl in ("https://token@github.com/owner/repo.git",
                        "https://github.com/other/repo.git", str(self.base / "remote.git")):
            git("remote", "set-url", "--push", "origin", pushurl, cwd=self.ws).check_returncode()
            with self.assertRaises(gitops.GitError, msg=pushurl):
                gitops._ensure_private_remote(self.ws)
        git("remote", "set-url", "--push", "origin",
            "git@github.com:owner/repo.git", cwd=self.ws).check_returncode()
        git("remote", "set-url", "--add", "origin",
            "https://github.com/owner/another.git", cwd=self.ws).check_returncode()
        with self.assertRaises(gitops.GitError):
            gitops._ensure_private_remote(self.ws)

    def test_begin_write_obeys_gitops_lock(self):
        gitops.initialize(self.ws)
        lock = gitops._acquire_lock(self.ws)
        try:
            with self.assertRaises(gitops.GitError):
                gitops.begin_write(self.ws, "other")
        finally:
            gitops._release_lock(self.ws)

    def test_runtime_symlink_is_never_written(self):
        gitops.initialize(self.ws)
        outside = self.base / "outside-state"
        outside.mkdir()
        (self.ws / ".ask").symlink_to(outside)
        with self.assertRaises(gitops.GitError):
            gitops.begin_write(self.ws, "agent")
        self.assertEqual(list(outside.iterdir()), [])

    def test_sync_without_remote_or_commit(self):
        gitops.initialize(self.ws)
        self.assertEqual(gitops.push_pending(self.ws)["reason"], "no-commits")
        out = gitops.sync(self.ws)
        self.assertTrue(out["backup_pending"])
        self.assertFalse(out["pushed"])

    def test_sync_refuses_public_before_fetch_and_active_writer(self):
        gitops.initialize(self.ws)
        git("remote", "add", "origin", "https://github.com/owner/repo.git",
            cwd=self.ws).check_returncode()
        with mock.patch.object(gitops, "_gh_visibility", return_value="PUBLIC"), \
                mock.patch.object(gitops, "_git", wraps=gitops._git) as command:
            with self.assertRaises(gitops.GitError):
                gitops.sync(self.ws)
            self.assertFalse(any(c.args[1] == "fetch" for c in command.call_args_list))
        token = gitops.begin_write(self.ws, "agent")["token"]
        try:
            with mock.patch.object(gitops, "_git", wraps=gitops._git) as command:
                self.assertEqual(gitops.sync(self.ws)["pull_reason"], "active-writers")
                self.assertFalse(any(c.args[1] == "fetch" for c in command.call_args_list))
        finally:
            gitops.end_write(self.ws, token)

    def test_sync_does_not_push_if_fetch_failed(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        self.add_remote()
        original = gitops._git
        with self.verified_file_remote():
            with mock.patch.object(gitops, "_git", wraps=gitops._git) as command:
                def fail_fetch(ws, *args, **kwargs):
                    if args and args[0] == "fetch":
                        return subprocess.CompletedProcess(["git", "fetch"], 1, "", "offline")
                    return original(ws, *args, **kwargs)
                command.side_effect = fail_fetch
                out = gitops.sync(self.ws)
                self.assertTrue(out["backup_pending"])
                self.assertFalse(any(c.args[1] == "push" for c in command.call_args_list))

    def test_push_rejection_reports_divergence_not_offline(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        remote = self.add_remote()
        git("add", "-A", cwd=self.ws).check_returncode()
        git("commit", "-m", "base", cwd=self.ws).check_returncode()
        with self.verified_file_remote():
            gitops.push_pending(self.ws)
        clone = self.base / "clone"
        subprocess.run(["git", "clone", str(remote), str(clone)],
                       check=True, capture_output=True)
        git("config", "user.name", "T", cwd=clone).check_returncode()
        git("config", "user.email", "t@t.t", cwd=clone).check_returncode()
        (clone / "Knowledge Base" / "notes.md").write_text("remote\n")
        git("add", "-A", cwd=clone).check_returncode()
        git("commit", "-m", "remote", cwd=clone).check_returncode()
        git("push", "origin", "HEAD:refs/heads/main", cwd=clone).check_returncode()
        (self.ws / "Knowledge Base" / "notes.md").write_text("local\n")
        git("add", "-A", cwd=self.ws).check_returncode()
        git("commit", "-m", "local", cwd=self.ws).check_returncode()
        with self.verified_file_remote():
            self.assertEqual(gitops.push_pending(self.ws)["reason"], "diverged")

    def test_write_session_markers(self):
        tok = gitops.begin_write(self.ws, actor="agent")["token"]
        self.assertTrue(tok)
        act = gitops.active_writes(self.ws)
        self.assertEqual(len(act), 1)
        # stale markers are never silently cleared
        tok2 = gitops.begin_write(self.ws, actor="agent2")["token"]
        self.assertEqual(len(gitops.active_writes(self.ws)), 2)
        with self.assertRaises(gitops.GitError):
            gitops.end_write(self.ws, "wrong-token")
        self.assertEqual(len(gitops.active_writes(self.ws)), 2)
        gitops.end_write(self.ws, tok)
        self.assertEqual(len(gitops.active_writes(self.ws)), 1)
        gitops.end_write(self.ws, tok2)
        self.assertEqual(gitops.active_writes(self.ws), [])

    def test_lock_blocks_overlapping_ops(self):
        gitops.initialize(self.ws)
        set_identity(self.ws)
        lock = self.ws / ".ask" / "gitops.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("{}")
        with self.assertRaises(gitops.GitError):
            self.run_gitops(gitops.checkpoint, self.ws,
                            paths=["Knowledge Base/notes.md"],
                            message="x", validator=lambda: None)


if __name__ == "__main__":
    unittest.main()
