from __future__ import annotations

import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = yaml.safe_load((REPO_ROOT / "manifest.yaml").read_text(encoding="utf-8"))


class ManifestMetadataTests(unittest.TestCase):
    def test_every_skill_declares_invocation_role_calls_and_handoffs(self) -> None:
        skills = MANIFEST["skills"]
        names = {skill["name"] for skill in skills}
        self.assertEqual(len(names), len(skills))

        for skill in skills:
            with self.subTest(skill=skill["name"]):
                self.assertIn(skill.get("invocation"), {"user", "model"})
                self.assertIn(
                    skill.get("role"),
                    {"orchestrator", "discipline", "renderer", "adapter"},
                )
                self.assertIsInstance(skill.get("calls"), list)
                self.assertTrue(set(skill["calls"]).issubset(names))
                self.assertNotIn(skill["name"], skill["calls"])
                self.assertIsInstance(skill.get("handoffs"), list)
                self.assertTrue(set(skill["handoffs"]).issubset(names))
                self.assertNotIn(skill["name"], skill["handoffs"])

    def test_user_invoked_skills_call_only_model_invoked_skills(self) -> None:
        skills = {skill["name"]: skill for skill in MANIFEST["skills"]}
        for skill in skills.values():
            if skill["invocation"] != "user":
                continue
            for callee in skill["calls"]:
                with self.subTest(caller=skill["name"], callee=callee):
                    self.assertEqual(skills[callee]["invocation"], "model")

    def test_handoffs_transfer_only_between_independent_user_entrypoints(self) -> None:
        skills = {skill["name"]: skill for skill in MANIFEST["skills"]}
        for skill in skills.values():
            for target_name in skill["handoffs"]:
                target = skills[target_name]
                with self.subTest(caller=skill["name"], target=target_name):
                    self.assertEqual(skill["invocation"], "user")
                    self.assertIn(skill["role"], {"orchestrator", "adapter"})
                    self.assertEqual(target["invocation"], "user")
                    self.assertIn(target["role"], {"orchestrator", "adapter"})


if __name__ == "__main__":
    unittest.main()
