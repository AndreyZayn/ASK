"""Readiness checks use synthetic workspaces and never contact GitHub."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from asklib.setup_checks import assess


class SetupChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.config = self.workspace / "ask.json"
        self.config.write_text(json.dumps({
            "ask_version": "1.0.0", "version": 1, "vault_root": "Knowledge Base",
            "bootstrap_files": ["date.md", "INDEX.md", "agents.md", "knowledge-map.md"],
            "access": {"read": ["."], "write": ["Projects", "Tasks"]},
            "validation": {"topology": True},
            "backup": {"repository": "owner/private-notes"},
        }))
        self.vault = self.workspace / "Knowledge Base"
        self.vault.mkdir()
        for note in ("date.md", "INDEX.md", "agents.md", "knowledge-map.md"):
            (self.vault / note).write_text("synthetic\n")
        hook = self.workspace / ".ask" / "hooks" / "pre-commit"
        hook.parent.mkdir(parents=True)
        hook.write_text("#!/bin/sh\npython3 /public/scripts/ask.py validate --staged --config '%s'\n" % self.config)
        hook.chmod(0o755)
        self.git = {
            "origin": "git@github.com:owner/private-notes.git",
            "upstream": "origin/main", "head": "a" * 40,
            "remote_head": "a" * 40, "ahead": 0, "behind": 0,
            "clean": True,
        }
        self.runtime = {"runtimes": {"codex": {
            "state": "verified", "block_present": True,
            "expected_block": "four-note-bootstrap", "observed_block": "four-note-bootstrap",
            "evidence": {'bootstrap_files':['date.md','INDEX.md','agents.md','knowledge-map.md'], 'inside_session':{'session_id':'one','observed_phrase':'fixture'},'outside_session':{'session_id':'two','observed_phrase':'fixture'}},
        }}}
        self.validation = {"counts": {"notes": 4, "errors": 0}, "issues": []}

    def assess(self, gh=None, remote=None):
        privacy = type("Result", (), {
            "returncode": 0, "stdout": json.dumps({
                "nameWithOwner": "owner/private-notes", "isPrivate": True,
            }),
        })()
        commit = type("Result", (), {
            "returncode": 0, "stdout": json.dumps({"object": {"sha": "a" * 40}}),
        })()
        with patch("asklib.setup_checks.subprocess.run",
                   side_effect=[gh or privacy, remote or commit]) as run:
            report = assess(self.config, self.git, self.runtime, self.validation)
        return report, run

    def test_fully_verified_synthetic_setup(self):
        report, run = self.assess()
        self.assertEqual(report["state"], "ready")
        self.assertEqual(report["pending"], [])
        self.assertTrue(all(check["ok"] for check in report["checks"].values()))
        self.assertEqual(run.call_args.kwargs["timeout"], 15)
        self.assertEqual(run.call_args_list[0].args[0][:3], ["gh", "repo", "view"])
        self.assertEqual(run.call_args_list[1].args[0][:2], ["gh", "api"])

    def test_remote_branch_must_still_point_to_head(self):
        remote = type("Result", (), {
            "returncode": 0, "stdout": json.dumps({"object": {"sha": "b" * 40}}),
        })()
        report, _ = self.assess(remote=remote)
        self.assertIn("backup", report["pending"])

    def test_no_upstream_or_remote_commit_is_not_backup(self):
        for changes in ({"upstream": None}, {"remote_head": None},
                        {"ahead": 0, "remote_head": "b" * 40},
                        {"ahead": 1}, {"behind": 1}, {"clean": False}):
            with self.subTest(changes=changes):
                self.git.update({"upstream": "origin/main", "remote_head": "a" * 40,
                                 "ahead": 0, "behind": 0, "clean": True})
                self.git.update(changes)
                report, _ = self.assess()
                self.assertEqual(report["state"], "setup-pending")
                self.assertIn("backup", report["pending"])

    def test_public_or_wrong_repository_is_refused(self):
        for payload in ({"nameWithOwner": "owner/private-notes", "isPrivate": False},
                        {"nameWithOwner": "someone/else", "isPrivate": True}):
            gh = type("Result", (), {"returncode": 0, "stdout": json.dumps(payload)})()
            report, _ = self.assess(gh)
            self.assertIn("backup", report["pending"])
        self.git["origin"] = "https://github.com/someone/else.git"
        report, run = self.assess()
        self.assertIn("backup", report["pending"])
        run.assert_not_called()

    def test_offline_or_missing_credentials_are_unknown_not_verified(self):
        gh = type("Result", (), {"returncode": 1, "stdout": ""})()
        report, _ = self.assess(gh)
        self.assertIn("backup", report["pending"])
        self.assertEqual(report["checks"]["backup"]["status"], "unverified")

    def test_invalid_validation_and_missing_bootstrap(self):
        self.validation["counts"]["errors"] = 1
        self.validation["issues"] = [{"file": "INDEX.md", "message": "invalid"}]
        (self.vault / "agents.md").unlink()
        report, _ = self.assess()
        self.assertIn("validation", report["pending"])
        self.assertIn("config", report["pending"])

    def test_runtime_manual_state_or_missing_block_never_verified(self):
        runtime = self.runtime["runtimes"]["codex"]
        for changes in ({"state": "configured-unverified"},
                        {"state": "verified", "block_present": False},
                        {"state": "not-configured"},
                        {"state": "verified", "evidence": {}}):
            with self.subTest(changes=changes):
                self.runtime["runtimes"]["codex"] = dict(runtime, **changes)
                report, _ = self.assess()
                self.assertIn("runtime:codex", report["pending"])
        self.runtime = {"runtimes": {}}
        report, _ = self.assess()
        self.assertEqual(report["checks"]["runtime"]["status"], "not-configured")

    def test_hook_must_be_executable_and_bound_to_config(self):
        hook = self.workspace / ".ask" / "hooks" / "pre-commit"
        hook.chmod(0o644)
        self.assertIn("hook", self.assess()[0]["pending"])
        hook.chmod(0o755)
        hook.write_text("#!/bin/sh\npython3 /public/scripts/ask.py validate --staged --config /elsewhere/ask.json\n")
        self.assertIn("hook", self.assess()[0]["pending"])

    def test_missing_version_or_topology_or_read_access(self):
        for change in ({"ask_version": None}, {"validation": {"topology": False}},
                       {"access": {"read": [], "write": ["Projects"]}}):
            with self.subTest(change=change):
                config = json.loads(self.config.read_text())
                config.update(change)
                self.config.write_text(json.dumps(config))
                self.assertIn("config", self.assess()[0]["pending"])
