"""Source-label coverage and near-miss cases, not a visual-recognition benchmark."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("route", ROOT / "skills/cover/scripts/style_route.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)
CATALOG = json.loads(router.DEFAULT_CATALOG.read_text())
LABELS = "纯粹主义 新客观主义 精确主义 立体主义 唯美主义 样式主义 未来主义 漩涡主义 德国表现主义 象征主义 社会现实主义 新印象主义 美国地区主义 现实主义 摄影写实主义 新艺术运动 维也纳分离派 工艺美术运动 国际哥特式 盛期文艺复兴 印象派 后印象派 拉斐尔前派 野兽派 纳比派 哈莱姆文艺复兴 苏格兰色彩派 卡姆登镇画派 形而上绘画".split()


def observe(*features):
    return [{"feature": f, "source": "fixture/work", "scope": "same-frame",
             "locator": "frame 1", "level": "frames", "note": "Synthetic test evidence"} for f in features]


class ArtStyleCoverageTests(unittest.TestCase):
    def test_all_original_labels_select_across_media(self):
        selected = set()
        for label in LABELS:
            for medium in ("page", "image", "video"):
                with self.subTest(label=label, medium=medium):
                    result = router.route({"medium": medium, "explicit_style": label}, CATALOG)
                    self.assertEqual(result["status"], "selected")
                    self.assertTrue(result["sources"])
                    self.assertTrue(result["artifact_direction_required"])
                    selected.add(result["selected"])
        self.assertEqual(len(selected), 29)
        self.assertEqual(len(CATALOG["styles"]), 32)
        self.assertEqual(set(CATALOG["coverage"]["source_label_map"]), set(LABELS))

    def test_historical_sources_and_media_limits_required(self):
        for style in CATALOG["styles"]:
            if "source_label" not in style:
                continue
            self.assertTrue(style["historical_scope"])
            self.assertTrue(style["distinguish"])
            self.assertTrue(style["media_status"])
            self.assertTrue(style["refinement"])
        bad = copy.deepcopy(CATALOG)
        bad["styles"][0]["sources"] = []
        with self.assertRaises(ValueError):
            router.validate_catalog(bad)

    def test_purism_and_cubism_do_not_collapse_to_polygons(self):
        a = router.route({"medium": "image", "observations": observe("essential-solid-forms", "ordered-object-relations")}, CATALOG)
        b = router.route({"medium": "image", "observations": observe("faceted-planes", "simultaneous-viewpoints")}, CATALOG)
        self.assertEqual([x["id"] for x in a["candidates"]], ["purism"])
        self.assertEqual([x["id"] for x in b["candidates"]], ["cubism"])
        partial = router.route({"medium": "image", "observations": observe("faceted-planes")}, CATALOG)
        self.assertEqual(partial["status"], "needs_observation")

    def test_fauvism_and_expressionism_need_different_second_feature(self):
        a = router.route({"medium": "image", "observations": observe("nonlocal-colour", "bold-open-brushwork")}, CATALOG)
        b = router.route({"medium": "image", "observations": observe("nonlocal-colour", "distorted-expressive-forms")}, CATALOG)
        self.assertEqual([x["id"] for x in a["candidates"]], ["fauvism"])
        self.assertEqual([x["id"] for x in b["candidates"]], ["german-expressionism"])

    def test_impressionism_is_not_divisionist_neo_impressionism(self):
        for features, expected in [(("broken-spontaneous-marks", "light-coloured-shadows"), "impressionism"),
                                   (("separated-colour-marks", "optical-colour-relations"), "neo-impressionism")]:
            result = router.route({"medium": "image", "observations": observe(*features)}, CATALOG)
            self.assertEqual([x["id"] for x in result["candidates"]], [expected])

    def test_group_or_umbrella_appearance_requires_context(self):
        for features, expected in [(("geometric-ornamental-fields", "integrated-arts-layout"), "vienna-secession"),
                                   (("constructed-form", "nonoptical-colour"), "post-impressionism"),
                                   (("modernist-figuration", "modern-life-narrative"), "harlem-renaissance"),
                                   (("nonlocal-colour", "structured-colour-planes"), "scottish-colourists")]:
            result = router.route({"medium": "image", "observations": observe(*features)}, CATALOG)
            self.assertEqual(result["status"], "needs_context")
            self.assertEqual(result["candidates"], [])
            self.assertEqual(result["context_candidates"][0]["id"], expected)

    def test_explicit_broad_label_is_supported_but_needs_specific_work(self):
        result = router.route({"medium": "video", "explicit_style": "哈莱姆文艺复兴"}, CATALOG)
        self.assertEqual(result["status"], "selected")
        self.assertTrue(result["reference_refinement_required"])
        self.assertTrue(result["refinement"])

    def test_existing_project_cannot_erase_context_refinement(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "DESIGN.md"
            path.write_text("# Existing Harlem-inspired project")
            result = router.route({"medium": "page", "project": {"style_id": "harlem-renaissance", "design": str(path)}}, CATALOG)
            self.assertEqual(result["status"], "selected")
            self.assertTrue(result["reference_refinement_required"])

    def test_social_realism_is_not_socialist_realism_alias(self):
        result = router.route({"medium": "image", "explicit_style": "社会主义现实主义"}, CATALOG)
        self.assertEqual(result["status"], "needs_style_definition")
        result = router.route({"medium": "image", "explicit_style": "社会现实主义"}, CATALOG)
        self.assertEqual(result["selected"], "social-realism")

    def test_unknown_future_label_still_does_not_fallback(self):
        result = router.route({"medium": "video", "explicit_style": "未定义的新风格"}, CATALOG)
        self.assertEqual(result["status"], "needs_style_definition")
        self.assertIsNone(result["selected"])


if __name__ == "__main__":
    unittest.main()
