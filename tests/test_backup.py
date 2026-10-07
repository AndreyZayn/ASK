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

from asklib import backup, gitops  # noqa: E402
try:
    from tests.test_gitops import (  # noqa: E402
        FakeGh, git, make_workspace, set_identity)
except ImportError:  # direct-file run: tests/ on sys.path
    from test_gitops import (  # noqa: E402
        FakeGh, git, make_workspace, set_identity)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.gh = FakeGh(self.base)
        self._saved = dict(os.environ)
        # mocked home + launchctl: no real jobs ever
        self.home = self.base / "home"
        (self.home / "Library" / "LaunchAgents").mkdir(parents=True)
        os.environ["HOME"] = str(self.home)
        self.bindir = self.base / "bin"
        self.bindir.mkdir()
        self.calls = self.base / "launchctl-calls.log"
        ctl = self.bindir / "launchctl"
        ctl.write_text("#!/bin/sh\necho \"$@\" >> \"%s\"\nexit 0\n" % self.calls)
        ctl.chmod(ctl.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.environ["PATH"] = str(self.bindir) + os.pathsep + \
            str(self.gh.bindir) + os.pathsep + os.environ.get("PATH", "")
        os.environ["FAKE_GH_VISIBILITY"] = "PRIVATE"
        self.ws = make_workspace(self.base)
        gitops.initialize(self.ws)
        set_identity(self.ws)
        git("add", "-A", cwd=self.ws).check_returncode()
        git("commit", "-m", "synthetic seed", cwd=self.ws).check_returncode()
        remote = self.base / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)],
                       check=True, capture_output=True)
        git("remote", "add", "origin", str(remote), cwd=self.ws).check_returncode()
        self.notifies = []
        self.remote_verify = mock.patch.object(
            gitops, "_ensure_private_remote", return_value="verified synthetic remote")
        self.remote_verify.start()
        self._real_notify = backup._notify
        backup._notify = lambda title, msg: self.notifies.append((title, msg))  # noqa: E731

    def tearDown(self):
        backup._notify = self._real_notify
        self.remote_verify.stop()
        os.environ.clear()
        os.environ.update(self._saved)
        self.tmp.cleanup()

    def test_enable_installs_owned_plist_exact_command(self):
        out = backup.enable(self.ws, cli_path=Path("/tmp/x/ask.py"),
                            config_path=Path("/tmp/x/ask.json"), interval=900)
        plist = Path(out["plist"])
        self.assertTrue(plist.exists())
        self.assertIn(str(self.home), str(plist))
        import plistlib
        data = plistlib.loads(plist.read_bytes())
        self.assertEqual(data["ProgramArguments"],
                         [sys.executable, "/tmp/x/ask.py", "backup", "run",
                          "--config", "/tmp/x/ask.json"])
        self.assertEqual(data["WorkingDirectory"], str(self.ws))
        self.assertIn("PATH", data["EnvironmentVariables"])
        self.assertEqual(data["StartInterval"], 900)
        self.assertTrue(self.calls.exists())  # mocked launchctl got the load
        backup.enable(self.ws, cli_path=Path("/tmp/x/ask.py"),
                      config_path=Path("/tmp/x/ask.json"), interval=900)
        calls = self.calls.read_text().splitlines()
        self.assertIn("bootout", calls[-2])
        self.assertIn("bootstrap", calls[-1])
        # second workspace gets a distinct id
        ws2 = make_workspace(self.base, name="ws2")
        out2 = backup.enable(ws2, cli_path=Path("/tmp/x/ask.py"),
                             config_path=Path("/tmp/x/ask.json"))
        self.assertNotEqual(out["label"], out2["label"])

    def test_enable_never_overwrites_foreign_plist(self):
        out = backup.enable(self.ws, cli_path=Path("/tmp/x/ask.py"),
                            config_path=Path("/tmp/x/ask.json"))
        plist = Path(out["plist"])
        plist.write_bytes(b"foreign content")
        with self.assertRaises(backup.BackupError):
            backup.enable(self.ws, cli_path=Path("/tmp/x/ask.py"),
                          config_path=Path("/tmp/x/ask.json"))
        self.assertEqual(plist.read_bytes(), b"foreign content")
        with self.assertRaises(backup.BackupError):
            backup.disable(self.ws)

    def test_enable_reuses_owned_plist_when_job_not_loaded(self):
        backup.enable(self.ws, "/tmp/x/ask.py", "/tmp/x/ask.json")
        original = backup._launchctl
        def unloaded(*args):
            if args[0] == "bootout":
                raise backup.BackupError("job not loaded")
            return original(*args)
        with mock.patch.object(backup, "_launchctl", side_effect=unloaded):
            out = backup.enable(self.ws, "/tmp/x/ask.py", "/tmp/x/ask.json")
        self.assertTrue(out["enabled"])

    def test_disable_removes_only_owned(self):
        out = backup.enable(self.ws, cli_path=Path("/tmp/x/ask.py"),
                            config_path=Path("/tmp/x/ask.json"))
        r = backup.disable(self.ws)
        self.assertTrue(r["removed"])
        self.assertFalse(Path(out["plist"]).exists())
        r2 = backup.disable(self.ws)
        self.assertFalse(r2["removed"])

    def test_run_commits_ordinary_and_reports(self):
        (self.ws / "Knowledge Base" / "notes.md").write_text("new work\n")
        out = backup.run(self.ws, validator=lambda: None, quiet_seconds=0)
        self.assertEqual(out["state"], "ok")
        self.assertTrue(out["pushed"])
        status = json.loads((self.ws / ".ask" / "backup-status.json").read_text())
        self.assertEqual(status["state"], "ok")
        self.assertTrue((self.ws / ".ask" / "backup.log").exists())
        # status/log stay untracked, never committed
        r = git("ls-files", cwd=self.ws)
        self.assertNotIn("backup-status.json", r.stdout)

    def test_run_skips_active_writers_and_staged_work(self):
        tok = gitops.begin_write(self.ws, actor="agent")["token"]
        (self.ws / "Knowledge Base" / "notes.md").write_text("w\n")
        out = backup.run(self.ws, validator=lambda: None, quiet_seconds=0)
        self.assertTrue(out["state"].startswith("skipped"))
        self.assertIn("writer", out["state"])
        gitops.end_write(self.ws, tok)
        git("add", "--", "Knowledge Base/notes.md", cwd=self.ws).check_returncode()
        out2 = backup.run(self.ws, validator=lambda: None, quiet_seconds=0)
        self.assertIn("staged", out2["state"])
        self.assertEqual(self.notifies, [])  # ordinary skips are silent

    def test_run_skips_protected_and_quiet_files(self):
        agents = self.ws / "Knowledge Base" / "agents.md"
        orig = agents.read_text()
        agents.write_text(orig + "owner edit\n")
        out = backup.run(self.ws, validator=lambda: None, quiet_seconds=0)
        self.assertIn("protected", out["state"])
        r = git("log", "--oneline", cwd=self.ws)
        self.assertNotIn("backup", r.stdout)
        agents.write_text(orig)  # restore; only a fresh ordinary edit remains
        (self.ws / "Knowledge Base" / "notes.md").write_text("fresh\n")
        out2 = backup.run(self.ws, validator=lambda: None, quiet_seconds=3600)
        self.assertIn("quiet", out2["state"])

    def test_run_pushes_pending_with_no_new_edits(self):
        (self.ws / "Knowledge Base" / "notes.md").write_text("v1\n")
        git("add", "-A", cwd=self.ws).check_returncode()
        git("commit", "-m", "manual ahead", cwd=self.ws).check_returncode()
        out = backup.run(self.ws, validator=lambda: None, quiet_seconds=0)
        self.assertEqual(out["state"], "ok")
        self.assertTrue(out["pushed"])

    def test_run_validation_failure_skips_and_notifies_once(self):
        (self.ws / "Knowledge Base" / "notes.md").write_text("bad\n")

        def bad():
            raise ValueError("nope")

        out = backup.run(self.ws, validator=bad, quiet_seconds=0)
        self.assertIn("validation", out["state"])
        self.assertEqual(len(self.notifies), 1)
        r = git("log", "--oneline", cwd=self.ws)
        self.assertNotIn("backup", r.stdout)
        # dedup: same failure again -> no second notification
        (self.ws / "Knowledge Base" / "notes.md").write_text("bad2\n")
        backup.run(self.ws, validator=bad, quiet_seconds=0)
        self.assertEqual(len(self.notifies), 1)

    def test_run_requires_write_access_and_vault_candidates(self):
        (self.ws / "Knowledge Base" / "notes.md").write_text("new\n")
        cfg = json.loads((self.ws / "ask.json").read_text())
        cfg["access"]["write"] = []
        (self.ws / "ask.json").write_text(json.dumps(cfg))
        self.assertIn("access", backup.run(self.ws, lambda: None, 0)["state"])
        cfg["access"]["write"] = ["."]
        (self.ws / "ask.json").write_text(json.dumps(cfg))
        (self.ws / "other.md").write_text("root\n")
        out = backup.run(self.ws, lambda: None, 0)
        self.assertEqual(out["state"], "ok")
        self.assertNotIn("other.md", git("ls-files", cwd=self.ws).stdout)

    def test_run_never_commits_if_protected_or_conflict_present(self):
        (self.ws / "Knowledge Base" / "notes.md").write_text("ordinary\n")
        (self.ws / "Knowledge Base" / "agents.md").write_text("protected\n")
        out = backup.run(self.ws, lambda: None, 0)
        self.assertIn("protected", out["state"])
        self.assertNotIn("ASK backup", git("log", "--oneline", cwd=self.ws).stdout)

    def test_run_observes_deleted_file_until_quiet(self):
        rel = "Knowledge Base/notes.md"
        (self.ws / rel).unlink()
        first = backup.run(self.ws, lambda: None, 60)
        self.assertIn("quiet", first["state"])
        with mock.patch.object(backup.time, "time",
                               return_value=backup.time.time() + 61):
            second = backup.run(self.ws, lambda: None, 60)
        self.assertEqual(second["state"], "ok")
        self.assertNotIn(rel, git("ls-files", cwd=self.ws).stdout)

    def test_run_lock_blocks_write_started_during_pass(self):
        (self.ws / "Knowledge Base" / "notes.md").write_text("changed during backup\n")
        seen = []

        def validate():
            with self.assertRaises(gitops.GitError):
                gitops.begin_write(self.ws, "racer")
            seen.append(True)

        self.assertEqual(backup.run(self.ws, validate, 0)["state"], "ok")
        self.assertEqual(seen, [True])

    def test_plist_foreign_workspace_and_symlink_preserved(self):
        out = backup.enable(self.ws, "/tmp/x/ask.py", "/tmp/x/ask.json")
        plist = Path(out["plist"])
        import plistlib
        data = plistlib.loads(plist.read_bytes())
        data["ASKWorkspace"] = str(self.base / "elsewhere")
        plist.write_bytes(plistlib.dumps(data))
        with self.assertRaises(backup.BackupError):
            backup.disable(self.ws)
        with self.assertRaises(backup.BackupError):
            backup.enable(self.ws, "/tmp/x/ask.py", "/tmp/x/ask.json")
        plist.unlink()
        target = self.base / "foreign"
        target.write_text("foreign")
        plist.symlink_to(target)
        with self.assertRaises(backup.BackupError):
            backup.disable(self.ws)
        self.assertEqual(target.read_text(), "foreign")

    def test_run_does_not_stage_vault_symlink(self):
        target = self.base / "outside"
        target.write_text("external\n")
        (self.ws / "Knowledge Base" / "link.md").symlink_to(target)
        out = backup.run(self.ws, lambda: None, 0)
        self.assertNotEqual(out["state"], "ok")
        self.assertNotIn("link.md", git("ls-files", cwd=self.ws).stdout)

    def test_run_waits_if_any_candidate_recent(self):
        old = self.ws / "Knowledge Base" / "old.md"
        old.write_text("stable\n")
        os.utime(old, (1, 1))
        (self.ws / "Knowledge Base" / "new.md").write_text("recent\n")
        out = backup.run(self.ws, lambda: None, 600)
        self.assertIn("quiet", out["state"])
        self.assertNotIn("old.md", git("ls-files", cwd=self.ws).stdout)

    def test_run_does_not_stage_credentials(self):
        (self.ws / "Knowledge Base" / "credentials.json").write_text("{}")
        (self.ws / "Knowledge Base" / "notes.md").write_text("safe change\n")
        out = backup.run(self.ws, lambda: None, 0)
        self.assertEqual(out["state"], "ok")
        self.assertNotIn("credentials.json", git("ls-files", cwd=self.ws).stdout)

    def test_notification_arguments_are_not_script_source(self):
        title = 'unsafe "title"'
        message = '"; do shell script "touch /tmp/unsafe"; --'
        with mock.patch.object(backup.subprocess, "run") as proc:
            self._real_notify(title, message)
        argv = proc.call_args.args[0]
        self.assertNotIn(message, argv[2])
        self.assertEqual(argv[-2:], [title, message])

    def test_status_symlink_does_not_write_outside_workspace(self):
        target = self.base / "outside-status"
        target.write_text("untouched")
        (self.ws / ".ask").mkdir(exist_ok=True)
        (self.ws / ".ask" / "backup-status.json").symlink_to(target)
        with self.assertRaises(backup.BackupError):
            backup.run(self.ws, lambda: None, 0)
        self.assertEqual(target.read_text(), "untouched")


if __name__ == "__main__":
    unittest.main()
