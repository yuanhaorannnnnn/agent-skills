from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install.sh"
SKILLS_DIR = REPO_ROOT / "skills"
MANIFEST_PATH = REPO_ROOT / "manifest.yaml"
RUNTIME_DIRS = [
    (".agents", "skills"),
    (".claude", "skills"),
]


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
            for runtime_parts in RUNTIME_DIRS:
                runtime = home.joinpath(*runtime_parts)
                # Enabled skills from manifest should be linked
                self.assertTrue((runtime / "Codify").is_symlink())
                self.assertTrue((runtime / "Neutralize").is_symlink())
                self.assertTrue((runtime / "Execute").is_symlink())
                self.assertTrue((runtime / ".scripts").is_symlink())

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
            manifest_content = """\
repo:
  name: agent-skills
  runtime_dir: ~/.agents/skills
skills:
  - name: Codify
    enabled: false
    category: workflow
  - name: Neutralize
    enabled: true
    category: workflow
"""
            MANIFEST_PATH.write_text(manifest_content)

            with tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                result = self._run_install(home)
                self.assertEqual(result.returncode, 0, result.stderr)
                for runtime_parts in RUNTIME_DIRS:
                    runtime = home.joinpath(*runtime_parts)
                    self.assertFalse((runtime / "Codify").exists())
                    self.assertTrue((runtime / "Neutralize").is_symlink())
        finally:
            MANIFEST_PATH.write_text(original_manifest)


if __name__ == "__main__":
    unittest.main()
