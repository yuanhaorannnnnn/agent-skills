from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install.sh"


class InstallScriptTests(unittest.TestCase):
    def test_install_links_local_skills_into_agents_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = {
                **os.environ,
                "HOME": str(home),
            }

            result = subprocess.run(
                ["bash", str(INSTALL_SCRIPT)],
                cwd=REPO_ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertTrue((home / ".agents" / "skills" / "save-conversation").is_symlink())
            self.assertTrue((home / ".agents" / "skills" / "restore-conversation").is_symlink())
            self.assertTrue((home / ".agents" / "skills" / "task-report-slides").is_symlink())


if __name__ == "__main__":
    unittest.main()
