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


class PassdownExtractorTest(unittest.TestCase):
    def run_main_json(self, argv):
        stdout = StringIO()
        stderr = StringIO()
        with mock.patch.object(sys, "argv", [str(SCRIPT)] + argv):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = extract_handoff.main()
        return code, stdout.getvalue(), stderr.getvalue()

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


if __name__ == "__main__":
    unittest.main()
