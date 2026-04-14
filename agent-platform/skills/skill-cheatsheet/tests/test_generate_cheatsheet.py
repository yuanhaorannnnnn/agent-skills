from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "generate_cheatsheet.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("generate_cheatsheet", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_skill(directory: Path, name: str, description: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n",
        encoding="utf-8",
    )


class CheatsheetScannerTests(unittest.TestCase):
    def test_codex_scan_classifies_sources(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_skills_dir = tmp_path / "repo" / "agent-platform" / "skills"
            codex_dir = tmp_path / ".codex"

            write_skill(repo_skills_dir / "pdf", "pdf", "Process PDF files")
            write_skill(repo_skills_dir / "fix-issue", "fix-issue", "Fix bugs")
            write_skill(repo_skills_dir / "planning-with-files", "planning-with-files", "Plan with files")
            write_skill(codex_dir / "skills" / ".system" / "skill-installer", "skill-installer", "Install skills")
            write_skill(codex_dir / "superpowers" / "skills" / "brainstorming", "brainstorming", "Brainstorm")

            (codex_dir / "skills").mkdir(parents=True, exist_ok=True)
            (codex_dir / "skills" / "pdf").symlink_to(repo_skills_dir / "pdf", target_is_directory=True)
            (codex_dir / "skills" / "fix-issue").symlink_to(repo_skills_dir / "fix-issue", target_is_directory=True)
            (codex_dir / "skills" / "planning-with-files").symlink_to(repo_skills_dir / "planning-with-files", target_is_directory=True)

            manifest_path = tmp_path / "upstream-manifest.yaml"
            manifest_path.write_text(
                yaml.safe_dump(
                    {
                        "upstreams": [
                            {
                                "id": "anthropics-skills",
                                "label": "Anthropic Official",
                                "tracked_skills": [
                                    {"name": "pdf"},
                                ],
                            },
                            {
                                "id": "planning-with-files-repo",
                                "label": "Third-Party Repo",
                                "tracked_skills": [
                                    {"name": "planning-with-files"},
                                ],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            scanner = module.SkillsScanner(
                root_dir=codex_dir,
                platform="codex",
                repo_skills_dir=repo_skills_dir,
                upstream_manifest_path=manifest_path,
                lang="en",
            )
            skills = {skill.name: skill for skill in scanner.scan_all()}

        self.assertEqual(skills["pdf"].source_kind, "upstream")
        self.assertEqual(skills["pdf"].source_label, "Anthropic Official")
        self.assertEqual(skills["fix-issue"].source_kind, "local")
        self.assertEqual(skills["fix-issue"].source_label, "Local Maintained")
        self.assertEqual(skills["planning-with-files"].source_kind, "upstream")
        self.assertEqual(skills["planning-with-files"].source_label, "Third-Party Repo")
        self.assertEqual(skills["skill-installer"].source_kind, "system")
        self.assertEqual(skills["brainstorming"].source_kind, "superpower")
        self.assertEqual(skills["brainstorming"].source_label, "Third-Party Repo")

    def test_render_includes_source_and_type_badges(self) -> None:
        module = load_module()

        skills = [
            module.SkillInfo(
                name="pdf",
                description="Process PDF files",
                path="/tmp/pdf",
                source_kind="upstream",
                source_key="anthropic-official",
                source_label="Anthropic Official",
            ),
            module.SkillInfo(
                name="fix-issue",
                description="Fix bugs",
                path="/tmp/fix-issue",
                source_kind="local",
                source_key="local",
                source_label="Local Maintained",
            ),
            module.SkillInfo(
                name="brainstorming",
                description="Brainstorm",
                path="/tmp/brainstorming",
                source_kind="superpower",
                source_key="third-party",
                source_label="Third-Party Repo",
            ),
        ]

        generator = module.CheatsheetGenerator(lang="zh")
        html = generator._render_html({"doc": skills, "design": [], "code": [], "comm": []}, total_count=3)

        self.assertIn("按来源", html)
        self.assertIn("按类型", html)
        self.assertIn("Anthropic Official", html)
        self.assertIn("Local Maintained", html)
        self.assertIn("Third-Party Repo", html)
        self.assertIn('class="badge badge-type"', html)
        self.assertIn('data-source="anthropic-official"', html)
        self.assertIn('data-type="doc"', html)
        self.assertIn("function applyFilters()", html)

    def test_generate_for_codex_uses_codex_title(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_skills_dir = tmp_path / "repo" / "agent-platform" / "skills"
            codex_dir = tmp_path / ".codex"
            output_path = tmp_path / "codex-cheatsheet.html"

            write_skill(repo_skills_dir / "pdf", "pdf", "Process PDF files")
            (codex_dir / "skills").mkdir(parents=True, exist_ok=True)
            (codex_dir / "skills" / "pdf").symlink_to(repo_skills_dir / "pdf", target_is_directory=True)

            manifest_path = tmp_path / "upstream-manifest.yaml"
            manifest_path.write_text(
                yaml.safe_dump({"upstreams": [{"id": "anthropics-skills", "tracked_skills": [{"name": "pdf"}]}]}),
                encoding="utf-8",
            )

            module.generate(
                output=str(output_path),
                lang="zh",
                claude_dir=str(codex_dir),
                open_browser=False,
                platform="codex",
                repo_skills_dir=str(repo_skills_dir),
                upstream_manifest_path=str(manifest_path),
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertIn("Codex Skills", html)


if __name__ == "__main__":
    unittest.main()
