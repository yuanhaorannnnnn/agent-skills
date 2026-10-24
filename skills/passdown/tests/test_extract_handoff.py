import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import importlib.util
from io import StringIO
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "extract_handoff.py"

spec = importlib.util.spec_from_file_location("extract_handoff", SCRIPT)
extract_handoff = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = extract_handoff
spec.loader.exec_module(extract_handoff)


def claude_slug(cwd: str) -> str:
    return cwd.replace("/", "-").replace("_", "-")


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


try:
    import zstandard  # noqa: F401

    HAVE_ZSTD = True
except Exception:
    HAVE_ZSTD = False


def write_zstd_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")
    with open(path, "wb") as f:
        with zstandard.ZstdCompressor().stream_writer(f) as writer:
            writer.write(payload)


class PassdownExtractorTest(unittest.TestCase):
    def run_main_json(self, argv):
        stdout = StringIO()
        stderr = StringIO()
        with mock.patch.object(sys, "argv", [str(SCRIPT)] + argv):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = extract_handoff.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def make_codex(self, home, archived, name, project="/project"):
        folder = "archived_sessions" if archived else "sessions/2026/10/23"
        path = Path(home) / ".codex" / folder / name
        write_jsonl(path, [
            {"type": "session_meta", "payload": {"cwd": project}},
            {"type": "response_item", "payload": {"role": "user", "content": [
                {"type": "input_text", "text": "archive-test " + name}]}}
        ])
        return path

    def test_codex_archive_scope_and_explicit_id(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.object(Path, "home", return_value=Path(home)):
            active = self.make_codex(home, False, "active-id.jsonl")
            archived = self.make_codex(home, True, "archived-id.jsonl")
            argv = ["--former", "codex", "--dir", "/project", "--focus", "archive-test", "--retriever", "keyword", "--json"]
            code, out, err = self.run_main_json(argv)
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["session_files"], [str(active)])
            code, out, err = self.run_main_json(argv + ["--archived"])
            self.assertEqual(code, 0, err)
            self.assertEqual(set(json.loads(out)["session_files"]), {str(active), str(archived)})
            code, out, err = self.run_main_json(["--former", "codex", "--session", "archived-id", "--json"])
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["session_files"], [str(archived)])

    def test_zvec_moves_resolve_before_scope_and_cwd_filter(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.object(Path, "home", return_value=Path(home)):
            original = self.make_codex(home, False, "rollout-moved.jsonl")
            archived = Path(home) / ".codex/archived_sessions" / original.name
            archived.parent.mkdir(parents=True)
            original.rename(archived)
            index = Path(home) / "index"
            # Missing source_cwd forces original-log lookup after path recovery.
            write_jsonl(index / "metadata.jsonl", [{"id": "hit", "runtime": "codex", "session_file": str(original)}])
            fake_zvec = mock.Mock()
            fake_zvec.open.return_value.query.return_value = [type("Hit", (), {"id": "hit", "score": 0.8})()]
            with mock.patch.dict(sys.modules, {"zvec": fake_zvec}), mock.patch.object(extract_handoff, "passdown_zvec_path", return_value=index):
                self.assertEqual(extract_handoff.find_zvec_candidates(["/project"], ["codex"], "test"), [])
                hits = extract_handoff.find_zvec_candidates(["/project"], ["codex"], "test", include_archived=True)
                self.assertEqual([h["path"] for h in hits], [archived])
                self.assertEqual(extract_handoff.find_zvec_candidates(["/other"], ["codex"], "test", include_archived=True), [])
                # An index written after archive must also survive unarchive.
                write_jsonl(index / "metadata.jsonl", [{"id": "hit", "runtime": "codex", "session_file": str(archived)}])
                archived.rename(original)
                hits = extract_handoff.find_zvec_candidates(["/project"], ["codex"], "test")
                self.assertEqual([h["path"] for h in hits], [original])
                original.rename(archived)
                self.assertEqual(extract_handoff.find_zvec_candidates(["/project"], ["codex"], "test"), [])

    def test_auto_archived_supplements_partial_index(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.object(Path, "home", return_value=Path(home)):
            active = self.make_codex(home, False, "active.jsonl")
            archived = self.make_codex(home, True, "not-indexed.jsonl")
            hit = {"path": active, "runtime": "codex", "source_cwd": "/project", "focus_score": 1, "mtime": 1}
            with mock.patch.object(extract_handoff, "find_zvec_candidates", return_value=[hit]):
                code, out, err = self.run_main_json(["--former", "codex", "--dir", "/project", "--focus", "archive-test", "--archived", "--json"])
            self.assertEqual(code, 0, err)
            self.assertEqual(set(json.loads(out)["session_files"]), {str(active), str(archived)})
            self.assertEqual(json.loads(out)["retriever"], "zvec+keyword")

    def test_moved_path_rejects_ambiguous_or_unrelated_files(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.object(Path, "home", return_value=Path(home)):
            a = self.make_codex(home, True, "rollout-copy.jsonl")
            b = a.parent / "duplicate" / a.name
            write_jsonl(b, [])
            old = Path(home) / ".codex/sessions" / a.name
            self.assertIsNone(extract_handoff.resolve_indexed_codex_path(old, True, {}))
            b.unlink()
            self.assertIsNone(extract_handoff.resolve_indexed_codex_path(Path(home) / a.name, True, {}))
            self.assertEqual(extract_handoff.resolve_indexed_codex_path(old, True, {}), a)

    def test_index_discovery_archive_opt_in(self):
        index_script = SCRIPT.with_name("zvec_index.py")
        spec = importlib.util.spec_from_file_location("zvec_index", index_script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as home, mock.patch.object(Path, "home", return_value=Path(home)):
            active = self.make_codex(home, False, "active.jsonl")
            archived = self.make_codex(home, True, "archive.jsonl")
            self.assertEqual([c["path"] for c in module.discover_sessions(["/project"], ["codex"])], [active])
            self.assertEqual({c["path"] for c in module.discover_sessions(["/project"], ["codex"], True)}, {active, archived})

    def test_parse_claude_filters_tool_result_user_messages(self):
        with tempfile.TemporaryDirectory() as td:
            session = Path(td) / "session.jsonl"
            write_jsonl(session, [
                {"type": "user", "message": {"content": [
                    {"type": "tool_result", "content": "huge tool output"},
                    {"type": "text", "text": "请评估 zvec 盲测方案"},
                ]}},
                {"type": "user", "message": {"content": "<local-command-stdout>noise</local-command-stdout>"}},
                {"type": "assistant", "message": {"content": [
                    {"type": "text", "text": "建议做 A/B blind eval。"}
                ]}},
            ])
            result = extract_handoff.parse_claude(session)
            self.assertEqual([t["role"] for t in result["turns"]], ["user", "assistant"])
            self.assertEqual(result["turns"][0]["text"], "请评估 zvec 盲测方案")
            joined = "\n".join(t["text"] for t in result["turns"])
            self.assertNotIn("tool output", joined)
            self.assertNotIn("local-command", joined)

    def test_budget_turns_keeps_initial_recent_and_focus_context(self):
        turns = [
            {
                "role": "user" if index % 2 == 0 else "assistant",
                "text": f"turn-{index} " + ("filler " * 80),
            }
            for index in range(14)
        ]
        turns[7]["text"] = "rollover focus decision and current constraint"

        selected, stats = extract_handoff.budget_turns(turns, "rollover", 400)

        joined = "\n".join(turn["text"] for turn in selected)
        self.assertLessEqual(
            sum(
                extract_handoff.estimate_tokens(turn["text"])
                for turn in selected
            ),
            400,
        )
        self.assertIn("turn-0", joined)
        self.assertIn("turn-1", joined)
        self.assertIn("rollover focus", joined)
        self.assertIn("turn-11", joined)
        self.assertIn("turn-12", joined)
        self.assertIn("turn-13", joined)
        self.assertTrue(stats["budget_applied"])
        self.assertEqual(stats["source_turns"], 14)
        self.assertGreater(stats["source_estimated_tokens"], 400)

    def test_cli_applies_explicit_handoff_budget(self):
        with tempfile.TemporaryDirectory() as td:
            session = Path(td) / "session.jsonl"
            rows = []
            for index in range(20):
                text = f"turn-{index} " + ("long context " * 70)
                if index == 10:
                    text = "rollover focus " + text
                role = "user" if index % 2 == 0 else "assistant"
                rows.append({"type": role, "message": {"content": text}})
            write_jsonl(session, rows)

            code, stdout, stderr = self.run_main_json([
                "--former", "claude",
                "--file", str(session),
                "--focus", "rollover",
                "--max-tokens", "240",
                "--json",
            ])

        self.assertEqual(code, 0, stderr)
        payload = json.loads(stdout)
        self.assertLessEqual(payload["estimated_tokens"], 240)
        self.assertEqual(payload["budget"]["max_tokens"], 240)
        self.assertTrue(payload["budget"]["budget_applied"])
        self.assertGreater(payload["budget"]["dropped_turns"], 0)
        self.assertIn(
            "rollover focus",
            "\n".join(turn["text"] for turn in payload["turns"]),
        )

    def test_focus_with_no_hits_does_not_fallback_to_recent_sessions(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as project:
            project = str(Path(project).resolve())
            session = Path(home) / ".claude" / "projects" / claude_slug(project) / "a.jsonl"
            write_jsonl(session, [
                {"type": "user", "message": {"content": "unrelated topic"}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "unrelated reply"}]}},
            ])
            env = os.environ.copy()
            env["HOME"] = home
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--former", "claude", "--dir", project, "--focus", "zvec盲测", "--json"],
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("No session found matching focus", proc.stderr)
            self.assertEqual(proc.stdout.strip(), "")

    def test_focus_with_hits_returns_only_nonzero_sessions(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as project:
            project = str(Path(project).resolve())
            pdir = Path(home) / ".claude" / "projects" / claude_slug(project)
            write_jsonl(pdir / "hit.jsonl", [
                {"type": "user", "message": {"content": "zvec盲测 怎么做"}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "做 option-1/option-2 blind eval"}]}},
            ])
            write_jsonl(pdir / "miss.jsonl", [
                {"type": "user", "message": {"content": "unrelated"}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "unrelated"}]}},
            ])
            env = os.environ.copy()
            env["HOME"] = home
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--former", "claude", "--dir", project, "--focus", "zvec盲测", "--json"],
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["matched_sessions"], 1)
            self.assertEqual(len(payload["session_files"]), 1)
            self.assertTrue(payload["session_files"][0].endswith("hit.jsonl"))
            self.assertGreater(payload["candidates"][0]["focus_score"], 0)


    def test_auto_retriever_prefers_zvec_candidates_when_focus_present(self):
        with tempfile.TemporaryDirectory() as project:
            project = str(Path(project).resolve())
            session = Path(project) / "zvec-hit.jsonl"
            write_jsonl(session, [
                {"type": "user", "message": {"content": "zvec 低噪声候选"}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "回读原始 session 后总结"}]}},
            ])
            zvec_candidate = {
                "path": session,
                "runtime": "claude",
                "source_cwd": project,
                "focus_score": 42,
                "zvec_score": 0.9,
                "mtime": session.stat().st_mtime,
            }
            with mock.patch.object(extract_handoff, "find_zvec_candidates", return_value=[zvec_candidate]):
                with mock.patch.object(extract_handoff, "find_claude_candidates", side_effect=AssertionError("keyword finder should not run")):
                    code, stdout, stderr = self.run_main_json([
                        "--former", "claude",
                        "--dir", project,
                        "--focus", "zvec盲测",
                        "--retriever", "auto",
                        "--json",
                    ])
            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["retriever"], "zvec")
            self.assertEqual(payload["matched_sessions"], 1)
            self.assertEqual(payload["session_files"], [str(session)])
            self.assertEqual(payload["turns"][0]["text"], "zvec 低噪声候选")

    def test_auto_retriever_falls_back_to_keyword_when_zvec_empty(self):
        with tempfile.TemporaryDirectory() as project:
            project = str(Path(project).resolve())
            session = Path(project) / "keyword-hit.jsonl"
            write_jsonl(session, [
                {"type": "user", "message": {"content": "zvec盲测 关键词候选"}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "keyword fallback"}]}},
            ])
            keyword_candidate = {
                "path": session,
                "runtime": "claude",
                "source_cwd": project,
                "focus_score": 9,
                "mtime": session.stat().st_mtime,
            }
            with mock.patch.object(extract_handoff, "find_zvec_candidates", return_value=[]):
                with mock.patch.object(extract_handoff, "find_claude_candidates", return_value=[keyword_candidate]):
                    code, stdout, stderr = self.run_main_json([
                        "--former", "claude",
                        "--dir", project,
                        "--focus", "zvec盲测",
                        "--retriever", "auto",
                        "--json",
                    ])
            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["retriever"], "keyword")
            self.assertEqual(payload["retriever_fallback"], "zvec_no_hits")
            self.assertEqual(payload["session_files"], [str(session)])

    def test_keyword_retriever_skips_zvec(self):
        with tempfile.TemporaryDirectory() as project:
            project = str(Path(project).resolve())
            session = Path(project) / "keyword-only.jsonl"
            write_jsonl(session, [
                {"type": "user", "message": {"content": "zvec盲测 keyword only"}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "keyword only"}]}},
            ])
            keyword_candidate = {
                "path": session,
                "runtime": "claude",
                "source_cwd": project,
                "focus_score": 7,
                "mtime": session.stat().st_mtime,
            }
            with mock.patch.object(extract_handoff, "find_zvec_candidates", side_effect=AssertionError("zvec should not run")):
                with mock.patch.object(extract_handoff, "find_claude_candidates", return_value=[keyword_candidate]):
                    code, stdout, stderr = self.run_main_json([
                        "--former", "claude",
                        "--dir", project,
                        "--focus", "zvec盲测",
                        "--retriever", "keyword",
                        "--json",
                    ])
            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["retriever"], "keyword")
            self.assertNotIn("retriever_fallback", payload)

    @unittest.skipUnless(HAVE_ZSTD, "zstandard not available")
    def test_parse_dsh_filters_plugin_reasoning_and_empty(self):
        with tempfile.TemporaryDirectory() as td:
            session = Path(td) / "session.jsonl.zstd"
            write_zstd_jsonl(session, [
                {"type": "session", "seq": 0, "data": {"cwd": "/tmp/project"}},
                {"type": "user/message", "seq": 1, "data": {
                    "role": "user", "source": {"kind": "plugin", "plugin": "user-approval"},
                    "content": [{"type": "text", "text": "policy notice, drop me"}]}},
                {"type": "user/message", "seq": 2, "data": {
                    "role": "user", "source": {"kind": "user"},
                    "content": [{"type": "text", "text": "请评估 zvec 盲测方案"}]}},
                {"type": "user/message", "seq": 3, "data": {
                    "role": "user", "source": {"kind": "agent-instructions"},
                    "content": [{"type": "text", "text": "instructions dump, drop me"}]}},
                {"type": "assistant/message", "seq": 4, "data": {
                    "turn": 1, "message": {"role": "assistant", "content": [
                        {"type": "reasoning", "text": "think think"},
                        {"type": "text", "text": "建议做 A/B blind eval。"},
                    ]}}},
                {"type": "assistant/message", "seq": 5, "data": {
                    "turn": 2, "message": {"role": "assistant", "content": [
                        {"type": "text", "text": ""},
                    ]}}},
            ])
            result = extract_handoff.parse_dsh(session)
            self.assertEqual([t["role"] for t in result["turns"]], ["user", "assistant"])
            self.assertEqual(result["turns"][0]["text"], "请评估 zvec 盲测方案")
            self.assertEqual(result["turns"][1]["text"], "建议做 A/B blind eval。")
            joined = "\n".join(t["text"] for t in result["turns"])
            self.assertNotIn("policy notice", joined)
            self.assertNotIn("instructions dump", joined)
            self.assertNotIn("think think", joined)

    @unittest.skipUnless(HAVE_ZSTD, "zstandard not available")
    def test_dsh_cli_discovers_and_extracts_session(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as project:
            project = str(Path(project).resolve())
            slug = extract_handoff.slugify_dsh(project)
            session = (
                Path(home) / ".dsh" / "sessions" / slug / "session-abc123" / "session.jsonl.zstd"
            )
            write_zstd_jsonl(session, [
                {"type": "session", "seq": 0, "data": {"cwd": project}},
                {"type": "user/message", "seq": 1, "data": {
                    "role": "user", "source": {"kind": "user"},
                    "content": [{"type": "text", "text": "zvec盲测 dsh 候选"}]}},
                {"type": "assistant/message", "seq": 2, "data": {
                    "message": {"role": "assistant", "content": [
                        {"type": "text", "text": "DSH 支持完成"},
                    ]}}},
            ])
            env = os.environ.copy()
            env["HOME"] = home
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--former", "dsh", "--dir", project, "--focus", "zvec盲测", "--json"],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["source"], "dsh")
            self.assertEqual(payload["matched_sessions"], 1)
            self.assertTrue(payload["session_files"][0].endswith("session.jsonl.zstd"))
            texts = [turn["text"] for turn in payload["turns"]]
            self.assertIn("zvec盲测 dsh 候选", texts)
            self.assertIn("DSH 支持完成", texts)


if __name__ == "__main__":
    unittest.main()
