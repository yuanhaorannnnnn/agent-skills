from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = REPO_ROOT / "scripts" / "init_planning_files.py"
STATUS_SCRIPT = REPO_ROOT / "scripts" / "planning_status.py"


class PlanWorkspaceTests(unittest.TestCase):
    def run_script(self, script: Path, project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "scripts")}
        return subprocess.run(
            [sys.executable, str(script), "--project-dir", str(project), *args],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_init_creates_conversation_scoped_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            result = self.run_script(INIT_SCRIPT, project, "--conversation", "infra")

            planning_dir = project / ".planning" / "conversations" / "infra"
            self.assertIn(str(planning_dir / "exec_plan.md"), result.stdout)
            for name in ("spec.md", "exec_plan.md", "task_plan.md", "findings.md", "progress.md"):
                self.assertTrue((planning_dir / name).is_file(), name)
            self.assertEqual((project / ".agent-state" / "ACTIVE_CONVERSATION").read_text().strip(), "infra")

    def test_status_reports_exec_plan_and_workspace_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.run_script(INIT_SCRIPT, project, "--conversation", "infra")

            result = self.run_script(STATUS_SCRIPT, project, "--conversation", "infra")

            self.assertIn("Planning Status", result.stdout)
            self.assertIn("exec_plan.md", result.stdout)
            self.assertIn(".planning/conversations/infra", result.stdout)


if __name__ == "__main__":
    unittest.main()
