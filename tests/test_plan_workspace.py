from __future__ import annotations

import sys
import unittest


class PlanWorkspaceTests(unittest.TestCase):
    """init_planning_files.py is deprecated — planning structure now lives in Canon task pages.

    These tests verify the deprecated script exits cleanly with the right message,
    rather than testing old .planning/conversations/ workspace creation.
    """

    def test_init_is_deprecated(self) -> None:
        import subprocess
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "scripts" / "init_planning_files.py"

        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        # Deprecated script exits non-zero with guidance message
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DEPRECATED", result.stdout)

    def test_deprecated_script_points_to_execute(self) -> None:
        import subprocess
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "scripts" / "init_planning_files.py"

        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        self.assertIn("Execute", result.stdout)


if __name__ == "__main__":
    unittest.main()
