from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install.sh"
SKILLS_DIR = REPO_ROOT / "skills"
MANIFEST_PATH = REPO_ROOT / "manifest.yaml"


class InstallScriptTests(unittest.TestCase):
    def _run_install(self, home: Path) -> subprocess.CompletedProcess:
        env = {**os.environ, "HOME": str(home)}
        return subprocess.run(
            ["bash", str(INSTALL_SCRIPT)],
            cwd=REPO_ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_install_links_enabled_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self._run_install(home)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((home / ".agents" / "skills" / "save-conversation").is_symlink())
            self.assertTrue((home / ".agents" / "skills" / "restore-conversation").is_symlink())
            self.assertTrue((home / ".agents" / "skills" / "task-report-slides").is_symlink())

    def test_install_removes_stale_links_from_this_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            runtime = home / ".agents" / "skills"
            runtime.mkdir(parents=True)

            stale_link = runtime / "deleted-skill"
            stale_target = SKILLS_DIR / "deleted-skill"
            stale_link.symlink_to(stale_target)
            self.assertTrue(stale_link.is_symlink())

            result = self._run_install(home)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(stale_link.exists())

    def test_install_does_not_touch_foreign_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            runtime = home / ".agents" / "skills"
            runtime.mkdir(parents=True)

            foreign_link = runtime / "foreign-skill"
            foreign_link.symlink_to("/some/other/path")
            self.assertTrue(foreign_link.is_symlink())

            result = self._run_install(home)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(foreign_link.is_symlink())
            self.assertEqual(os.readlink(foreign_link), "/some/other/path")

    def test_install_skips_disabled_skills(self) -> None:
        original_manifest = MANIFEST_PATH.read_text()
        try:
            # Replace manifest with one that disables save-conversation
            manifest_content = """\
repo:
  name: agent-skills
  runtime_dir: ~/.agents/skills
skills:
  - name: save-conversation
    enabled: false
    category: conversation
  - name: restore-conversation
    enabled: true
    category: conversation
"""
            MANIFEST_PATH.write_text(manifest_content)

            with tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                result = self._run_install(home)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((home / ".agents" / "skills" / "save-conversation").exists())
                self.assertTrue((home / ".agents" / "skills" / "restore-conversation").is_symlink())
        finally:
            MANIFEST_PATH.write_text(original_manifest)


if __name__ == "__main__":
    unittest.main()
