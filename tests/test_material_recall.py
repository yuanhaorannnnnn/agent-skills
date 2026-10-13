import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/material_recall.py"
CANON = "/media/yhr/2T/Canon"
SKILLS = "/home/yhr/.agents/repos/agent-skills"
WIKI = "/media/yhr/2T/files/wiki"


class MaterialRecallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.tree = self.root / "mirror"
        self.index = self.root / "artifact-index.md"
        self.index.write_text(
            """```yaml
- id: skill-system-five-principles-hardening
  kind: historical-summary
  title: Skill System Five-Principles Hardening
  status: historical
  date: 2026-08-10
  source_path: /home/yhr/.agents/repos/agent-skills/.proposal/skill-system-five-principles-hardening/goal.md
  task_path: /media/yhr/2T/Canon/tasks/skill-system-five-principles-hardening.md
  update_card: /media/yhr/2T/Canon/raw/update-cards/20260810-skill-five-principles-hardening.md
  original_terms: ["Model-complementary", "Open to optimization", "Workflow-grounded", "Observable/evaluable", "Stable contract"]
  aliases: ["自建 skill system 五原则", "自建 harness", "模型能力解耦"]
  alias_note: 整组关联记忆线索，需核对原文。
- id: intent-harness-six-principles
  kind: historical-summary
  title: Intent Harness Six Operating Principles
  status: historical
  date: 2026-08-27
  source_path: /media/yhr/2T/files/wiki/.proposal/intent-harness/index.html
  update_card: /media/yhr/2T/Canon/raw/update-cards/20260827-breach-intent-harness.md
  original_terms: ["来源开放", "证据先于结论", "渐进承诺", "人类确认", "干净交接", "可度量"]
  aliases: ["Intent 六原则", "intent 来源开放", "渐进承诺"]
  alias_note: 别名是检索线索。
```""",
            encoding="utf-8",
        )
        self._touch(SKILLS, ".proposal/skill-system-five-principles-hardening/goal.md")
        self._touch(CANON, "/tasks/skill-system-five-principles-hardening.md")
        self._touch(CANON, "/raw/update-cards/20260810-skill-five-principles-hardening.md")
        self._touch(WIKI, "/.proposal/intent-harness/index.html")
        self._touch(CANON, "/raw/update-cards/20260827-breach-intent-harness.md")

    def tearDown(self):
        self.temp.cleanup()

    def _touch(self, prefix, suffix):
        mapped = self.tree / prefix.strip("/")
        path = mapped / suffix.lstrip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")

    def _run(self, *args):
        maps = [
            f"--map-prefix={CANON}={self.tree / CANON.strip('/')}",
            f"--map-prefix={SKILLS}={self.tree / SKILLS.strip('/')}",
            f"--map-prefix={WIKI}={self.tree / WIKI.strip('/')}",
        ]
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--index", str(self.index), *maps, *args],
            check=False,
            capture_output=True,
            text=True,
        )
        return result

    def _payload(self, result):
        self.assertIn(result.returncode, (0, 1), result.stderr)
        self.assertTrue(result.stdout, result.stderr)
        return json.loads(result.stdout)

    def test_fuzzy_memory_clue_ranks_self_built_five_principles_first(self):
        result = self._run("query", "自建 harness 的几个品质，其中一条与模型能力解耦")
        payload = self._payload(result)
        self.assertEqual(payload["candidates"][0]["id"], "skill-system-five-principles-hardening")
        self.assertEqual(payload["candidates"][0]["title"], "Skill System Five-Principles Hardening")
        self.assertIn("模型能力解耦", payload["candidates"][0]["matched_terms"])

    def test_variation_of_memory_clue_still_finds_self_built_summary(self):
        payload = self._payload(self._run("query", "模型解耦和自建harness总结"))
        self.assertEqual(payload["candidates"][0]["id"], "skill-system-five-principles-hardening")

    def test_intent_clues_find_six_principles(self):
        payload = self._payload(self._run("query", "intent 来源开放 渐进承诺"))
        self.assertEqual(payload["candidates"][0]["id"], "intent-harness-six-principles")

    def test_external_factory_is_not_misidentified_as_self_built_summary(self):
        payload = self._payload(self._run("query", "external Factory three principles Model Independence"))
        self.assertEqual(payload["candidates"], [])

    def test_alias_does_not_replace_original_terms_or_claim_source_was_read(self):
        payload = self._payload(self._run("query", "模型能力解耦"))
        candidate = payload["candidates"][0]
        self.assertIn("Model-complementary", candidate["original_terms"])
        self.assertIn("Stable contract", candidate["original_terms"])
        self.assertIn("Open to optimization", candidate["original_terms"])
        self.assertFalse(candidate["source_read"])
        self.assertEqual(candidate["source_status"], "exists_not_read")

    def test_missing_source_is_reported_and_link_check_fails(self):
        source = self.tree / SKILLS.strip("/") / ".proposal/skill-system-five-principles-hardening/goal.md"
        source.unlink()
        candidate = self._payload(self._run("query", "自建 harness"))["candidates"][0]
        self.assertEqual(candidate["source_status"], "missing")
        checked = self._run("check-links", "skill-system-five-principles-hardening")
        payload = self._payload(checked)
        self.assertEqual(checked.returncode, 1)
        self.assertIn("source_path", payload["missing"])
        self.assertFalse(payload["ok"])

    def test_missing_source_field_cannot_pass_link_check(self):
        text = self.index.read_text(encoding="utf-8")
        text = text.replace(
            "  source_path: /home/yhr/.agents/repos/agent-skills/.proposal/skill-system-five-principles-hardening/goal.md\n",
            "",
            1,
        )
        self.index.write_text(text, encoding="utf-8")
        checked = self._run("check-links", "skill-system-five-principles-hardening")
        payload = self._payload(checked)
        self.assertEqual(checked.returncode, 1)
        self.assertEqual(payload["missing"], ["source_path"])

    def test_relative_source_path_resolves_from_index_outside_cwd(self):
        fixture_dir = self.root / "relative-index"
        fixture_dir.mkdir()
        source = fixture_dir / "source.html"
        source.write_text("fixture", encoding="utf-8")
        relative_index = fixture_dir / "artifact-index.md"
        relative_index.write_text(
            '```yaml\n- id: sample\n  kind: historical-summary\n  title: Sample\n  source_path: source.html\n  original_terms: ["intent"]\n  aliases: ["intent recall"]\n```',
            encoding="utf-8",
        )
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--index", str(relative_index), "query", "intent recall"],
            cwd=elsewhere,
            check=False,
            capture_output=True,
            text=True,
        )
        candidate = self._payload(result)["candidates"][0]
        self.assertEqual(candidate["source_path"], "source.html")
        self.assertEqual(candidate["source_status"], "exists_not_read")

    def test_unknown_query_returns_no_candidates(self):
        payload = self._payload(self._run("query", "unrelated glacier acoustics"))
        self.assertEqual(payload["candidates"], [])

    def test_unrelated_chinese_phrase_does_not_match_generic_quality_words(self):
        payload = self._payload(self._run("query", "一个城市的几个品质"))
        self.assertEqual(payload["candidates"], [])


if __name__ == "__main__":
    unittest.main()
