import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/cover/scripts/style_route.py"
spec = importlib.util.spec_from_file_location("style_route", SCRIPT)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)
CATALOG = json.loads(router.DEFAULT_CATALOG.read_text())


def observation(feature, source="frame.png", scope="opening", level="frames"):
    return {"feature": feature, "source": source, "scope": scope,
            "locator": "00:02", "level": level, "note": "Fixture visual observation"}


class StyleRoutingTests(unittest.TestCase):
    def call(self, brief, references=None, catalog=None):
        return router.route(brief, catalog or CATALOG, references)

    def test_explicit_alias_and_no_color_fallback(self):
        self.assertEqual(self.call({"medium": "video", "explicit_style": "精确主义"})["selected"], "precisionism")
        result = self.call({"medium": "video", "explicit_style": "冷蓝高级"})
        self.assertEqual(result["status"], "needs_style_definition")
        self.assertIsNone(result["selected"])

    def test_unknown_request_does_not_use_project_default(self):
        result = self.call({"medium": "page", "explicit_style": "new-style", "project": {"style_id": "field-notes"}})
        self.assertEqual(result["status"], "needs_style_definition")

    def test_existing_design_without_catalog_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "DESIGN.md"
            p.write_text("# Existing project direction")
            brief = {"medium": "page", "project": {"design": str(p), "style_id": "legacy-project"}}
            self.assertEqual(self.call(brief)["selected"], "legacy-project")
            brief["explicit_style"] = "强字体编排"
            result = self.call(brief)
            self.assertEqual(result["selected"], "expressive-typography")
            self.assertIn("project_override", result)
            self.assertEqual(p.read_text(), "# Existing project direction")

    def test_explicit_exclusion_conflict(self):
        result = self.call({"medium": "video", "explicit_style": "精确主义", "exclude_styles": ["precisionism"]})
        self.assertEqual(result["status"], "conflict")

    def test_signature_requires_same_source_and_scope(self):
        a = observation("paper-fragments")
        for b in [observation("assembled-relationships", source="other.png"),
                  observation("assembled-relationships", scope="other-shot")]:
            self.assertEqual(self.call({"medium": "image", "observations": [a, b]})["status"], "needs_observation")
        result = self.call({"medium": "image", "observations": [a, observation("assembled-relationships")]})
        self.assertEqual(result["status"], "proposed")
        self.assertEqual(result["candidates"][0]["id"], "material-collage")
        self.assertIsNone(result["selected"])

    def test_mixed_complete_signatures_are_ambiguous(self):
        obs = [observation(f) for f in ["text-as-image", "scale-led-hierarchy", "industrial-geometry", "hard-edge-space"]]
        result = self.call({"medium": "video", "observations": obs})
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(len(result["candidates"]), 2)

    def test_frames_cannot_attest_motion_or_sound(self):
        for feature in ["narrative-type-motion", "material-sound"]:
            with self.assertRaises(ValueError):
                self.call({"medium": "video", "observations": [observation(feature)]})

    def test_unclassified_and_newly_annotated_reference(self):
        refs = {"references": [{"id": "new-film", "source_url": "https://example.org/film"}]}
        brief = {"medium": "video", "reference_ids": ["new-film"]}
        self.assertEqual(self.call(brief, refs)["status"], "needs_observation")
        refs["references"][0]["style_observations"] = [observation("text-as-image", source="https://example.org/film"), observation("scale-led-hierarchy", source="https://example.org/film")]
        self.assertEqual(self.call(brief, refs)["status"], "proposed")

    def test_reference_cannot_borrow_an_unrelated_source(self):
        refs = {"references": [{"id": "film", "source_url": "https://example.org/film",
                                "style_observations": [observation("text-as-image")]}]}
        with self.assertRaises(ValueError):
            self.call({"medium": "video", "reference_ids": ["film"]}, refs)

    def test_style_extension_requires_no_code_change(self):
        c = copy.deepcopy(CATALOG)
        new = copy.deepcopy(c["styles"][0])
        new.update(id="new-direction", aliases=["新方向"], signature_features=["text-as-image", "hard-edge-space"], media={"image": "New treatment"})
        c["styles"].append(new)
        result = self.call({"medium": "image", "observations": [observation("text-as-image"), observation("hard-edge-space")]}, catalog=c)
        self.assertEqual(result["candidates"][0]["id"], "new-direction")
        self.assertEqual(self.call({"medium": "video", "explicit_style": "新方向"}, catalog=c)["status"], "conflict")

    def test_alias_collision_rejected(self):
        c = copy.deepcopy(CATALOG)
        c["styles"][0]["aliases"].append("precisionism")
        with self.assertRaises(ValueError):
            router.validate_catalog(c)

    def test_missing_evidence_and_unknown_feature_rejected(self):
        for obs in [{"feature": "text-as-image"}, observation("blue"), observation("text-as-image", level="text")]:
            with self.assertRaises(ValueError):
                self.call({"medium": "video", "observations": [obs]})

    def test_typo_and_missing_reference_are_not_silently_ignored(self):
        for brief in [{"medium": "video", "explicit_stlye": "精确主义"},
                      {"medium": "video", "reference_ids": ["missing"]}]:
            with self.assertRaises(ValueError):
                self.call(brief)

    def test_family_selection_does_not_complete_artifact_design(self):
        briefs = [
            {"medium": "image", "explicit_style": "精确主义"},
            {"medium": "page", "explicit_style": "unknown"},
            {"medium": "video", "observations": [observation("text-as-image"), observation("scale-led-hierarchy")]},
        ]
        for brief in briefs:
            result = self.call(brief)
            self.assertEqual(result["selection_scope"], "style-family")
            self.assertTrue(result["artifact_direction_required"])

    def test_cli_outputs_status_and_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "brief.json"
            p.write_text(json.dumps({"medium": "video", "explicit_style": "unknown"}))
            result = subprocess.run([sys.executable, str(SCRIPT), "--brief", str(p)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["status"], "needs_style_definition")
            p.write_text('{"medium":"invalid"}')
            result = subprocess.run([sys.executable, str(SCRIPT), "--brief", str(p)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["status"], "error")


if __name__ == "__main__":
    unittest.main()
