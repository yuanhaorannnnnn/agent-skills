from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install.sh"
SKILLS_DIR = REPO_ROOT / "skills"
RUNTIME_DIRS = [
    (".agents", "skills"),
    (".claude", "skills"),
]


class InstallScriptTests(unittest.TestCase):
    def _run_install(
        self, home: Path, manifest: Path | None = None
    ) -> subprocess.CompletedProcess:
        env = {**os.environ, "HOME": str(home)}
        if manifest is not None:
            env["AGENT_SKILLS_MANIFEST"] = str(manifest)
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
                self.assertTrue((runtime / "codify").is_symlink())
                self.assertTrue((runtime / "neutralize").is_symlink())
                self.assertTrue((runtime / "execute").is_symlink())
                self.assertTrue((runtime / "herdr-carla-tune").is_symlink())
                self.assertFalse((runtime / "SweepHer").exists())
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
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifest_path = tmp_path / "manifest.yaml"
            manifest_content = """\
repo:
  name: agent-skills
  runtime_dir: ~/.agents/skills
skills:
  - name: codify
    enabled: false
    category: workflow
  - name: neutralize
    enabled: true
    category: workflow
"""
            manifest_path.write_text(manifest_content)
            home = tmp_path / "home"
            result = self._run_install(home, manifest_path)
            self.assertEqual(result.returncode, 0, result.stderr)
            for runtime_parts in RUNTIME_DIRS:
                runtime = home.joinpath(*runtime_parts)
                self.assertFalse((runtime / "codify").exists())
                self.assertTrue((runtime / "neutralize").is_symlink())


if __name__ == "__main__":
    unittest.main()
