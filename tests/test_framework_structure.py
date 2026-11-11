"""A fresh installation exposes the reusable guidance needed for real work."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FrameworkStructureTests(unittest.TestCase):
    def test_fresh_workspace_routes_safety_and_maintenance_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve() / 'new workspace'
            result = subprocess.run(
                [sys.executable, str(ROOT / 'scripts/ask.py'), 'init', '--workspace', str(workspace)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            vault = workspace / 'Knowledge Base'
            routes = (vault / 'knowledge-map.md').read_text()
            index = (vault / 'Agents/rules/INDEX.md').read_text()
            for name in ('automation-management', 'communication-rules', 'follow-up-discipline', 'harness-improvement', 'loop-management',
                         'mcp-management', 'model-resource-safety', 'product-planning',
                         'project-wiki-maintenance', 'skill-management'):
                with self.subTest(rule=name):
                    self.assertTrue((vault / 'Agents/rules' / (name + '.md')).is_file())
                    self.assertIn('[[Agents/rules/' + name + ']]', index)
                    self.assertIn('[[Agents/rules/' + name + ']]', routes)
            engineering = (vault / 'Agents/rules/software-development/INDEX.md').read_text()
            for name in ('database-management', 'development-log-format', 'principles', 'pull-request-handoff'):
                with self.subTest(engineering_rule=name):
                    self.assertTrue((vault / 'Agents/rules/software-development' / (name + '.md')).is_file())
                    self.assertIn('[[Agents/rules/software-development/' + name + ']]', engineering)
            loops = (vault / 'Agents/loops/INDEX.md').read_text()
            self.assertTrue((vault / 'Agents/loops/personal-social-content.md').is_file())
            self.assertIn('[[Agents/loops/personal-social-content]]', loops)
            tasks = (vault / 'Tasks/INDEX.md').read_text()
            self.assertTrue((vault / 'Tasks/owner-task-contract.md').is_file())
            self.assertIn('[[Tasks/owner-task-contract]]', tasks)
            self.assertIn('[[Tasks/owner-task-contract]]', routes)
            config = workspace / 'ask.json'
            settings = json.loads(config.read_text())
            settings['validation'] = {'topology': True}
            config.write_text(json.dumps(settings))
            report = subprocess.run(
                [sys.executable, str(ROOT / 'scripts/ask.py'), 'validate', '--config', str(config)],
                capture_output=True, text=True,
            )
            self.assertEqual(report.returncode, 0, report.stdout + report.stderr)


if __name__ == '__main__':
    unittest.main()
