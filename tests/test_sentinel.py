from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "Sentinel" / "scripts" / "sentinel.sh"


class SentinelTests(unittest.TestCase):
    def run_tool(self, args, root: Path, check: bool = False) -> subprocess.CompletedProcess:
        env = {**os.environ, "SENTINEL_ROOT": str(root)}
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            cwd=REPO_ROOT,
            env=env,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_start_wait_records_success_state_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "monitor"
            work = Path(tmp) / "work"
            work.mkdir()

            result = self.run_tool(
                [
                    "start",
                    "--id", "success-build",
                    "--title", "Success Build",
                    "--cwd", str(work),
                    "--no-terminal",
                    "--wait",
                    "--",
                    "bash", "-lc", "echo hello-monitor",
                ],
                root,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((root / "success-build" / "state.json").read_text())
            self.assertEqual(state["status"], "succeeded")
            self.assertEqual(state["exit_code"], 0)
            self.assertEqual(state["cwd"], str(work))
            self.assertEqual(state["command"], ["bash", "-lc", "echo hello-monitor"])
            self.assertIn("hello-monitor", (root / "success-build" / "build.log").read_text())
            self.assertIn("EXIT_CODE=0", (root / "success-build" / "build.log").read_text())

    def test_failure_records_failed_status_and_errors_command_finds_log_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "monitor"
            work = Path(tmp) / "work"
            work.mkdir()

            result = self.run_tool(
                [
                    "start",
                    "--id", "failed-build",
                    "--cwd", str(work),
                    "--no-terminal",
                    "--wait",
                    "--",
                    "bash", "-lc", "echo 'fatal: broken build' >&2; exit 7",
                ],
                root,
            )

            self.assertEqual(result.returncode, 7, result.stderr)
            state = json.loads((root / "failed-build" / "state.json").read_text())
            self.assertEqual(state["status"], "failed")
            self.assertEqual(state["exit_code"], 7)

            errors = self.run_tool(["errors", "--id", "failed-build"], root)
            self.assertEqual(errors.returncode, 0, errors.stderr)
            self.assertIn("fatal: broken build", errors.stdout)

    def test_env_injection_is_available_to_monitored_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "monitor"
            work = Path(tmp) / "work"
            work.mkdir()

            result = self.run_tool(
                [
                    "start",
                    "--id", "env-build",
                    "--cwd", str(work),
                    "--env", "MONITOR_TEST_VALUE=from-env",
                    "--no-terminal",
                    "--wait",
                    "--",
                    "bash", "-lc", "printf '%s\\n' \"$MONITOR_TEST_VALUE\"",
                ],
                root,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            log = (root / "env-build" / "build.log").read_text()
            self.assertIn("from-env", log)

    def test_status_and_tail_read_existing_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "monitor"
            work = Path(tmp) / "work"
            work.mkdir()

            self.run_tool(
                [
                    "start", "--id", "tail-build", "--cwd", str(work),
                    "--no-terminal", "--wait", "--",
                    "bash", "-lc", "printf 'line1\\nline2\\nline3\\n'",
                ],
                root,
                check=True,
            )

            status = self.run_tool(["status", "--id", "tail-build"], root)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertEqual(json.loads(status.stdout)["status"], "succeeded")

            tail = self.run_tool(["tail", "--id", "tail-build", "--lines", "3"], root)
            self.assertEqual(tail.returncode, 0, tail.stderr)
            self.assertNotIn("line1", tail.stdout)
            self.assertIn("line2", tail.stdout)
            self.assertIn("line3", tail.stdout)
            self.assertIn("EXIT_CODE=0", tail.stdout)

    def test_async_start_can_be_stopped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "monitor"
            work = Path(tmp) / "work"
            work.mkdir()

            result = self.run_tool(
                [
                    "start", "--id", "stop-build", "--cwd", str(work),
                    "--no-terminal", "--",
                    "bash", "-lc", "echo started; sleep 30",
                ],
                root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            state_path = root / "stop-build" / "state.json"
            for _ in range(50):
                state = json.loads(state_path.read_text())
                if state["status"] == "running":
                    break
                import time
                time.sleep(0.05)
            else:
                self.fail("monitor task did not reach running state")

            stop = self.run_tool(["stop", "--id", "stop-build"], root)
            self.assertEqual(stop.returncode, 0, stop.stderr)
            state = json.loads(state_path.read_text())
            self.assertEqual(state["status"], "stopped")

    def test_conda_activation_tolerates_unset_variables_in_activate_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "monitor"
            work = Path(tmp) / "work"
            work.mkdir()
            conda_sh = Path(tmp) / "conda.sh"
            conda_sh.write_text(
                "conda() {\n"
                "  if [ \"$1\" = \"activate\" ]; then\n"
                "    : \"${MKL_INTERFACE_LAYER}\"\n"
                "  fi\n"
                "}\n"
            )

            result = self.run_tool(
                [
                    "start", "--id", "conda-build", "--cwd", str(work),
                    "--conda-env", "py38", "--conda-sh", str(conda_sh),
                    "--no-terminal", "--wait", "--",
                    "bash", "-lc", "echo conda-ok",
                ],
                root,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((root / "conda-build" / "state.json").read_text())
            self.assertEqual(state["status"], "succeeded")
            self.assertIn("conda-ok", (root / "conda-build" / "build.log").read_text())

    def test_run_starts_and_waits_until_success_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "monitor"
            work = Path(tmp) / "work"
            work.mkdir()

            result = self.run_tool(
                [
                    "run", "--id", "run-build", "--cwd", str(work),
                    "--no-terminal", "--lines", "5", "--",
                    "bash", "-lc", "echo run-ok",
                ],
                root,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("STATUS=succeeded", result.stdout)
            self.assertIn("EXIT_CODE=0", result.stdout)
            self.assertIn("run-ok", result.stdout)
            state = json.loads((root / "run-build" / "state.json").read_text())
            self.assertEqual(state["status"], "succeeded")

    def test_run_waits_until_failure_and_returns_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "monitor"
            work = Path(tmp) / "work"
            work.mkdir()

            result = self.run_tool(
                [
                    "run", "--id", "run-failed", "--cwd", str(work),
                    "--no-terminal", "--lines", "5", "--",
                    "bash", "-lc", "echo 'error: run failed' >&2; exit 9",
                ],
                root,
            )

            self.assertEqual(result.returncode, 9)
            self.assertIn("STATUS=failed", result.stdout)
            self.assertIn("EXIT_CODE=9", result.stdout)
            self.assertIn("error: run failed", result.stdout)


if __name__ == "__main__":
    unittest.main()
