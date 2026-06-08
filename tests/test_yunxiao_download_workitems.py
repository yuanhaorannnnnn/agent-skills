from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "skills" / "SITREP" / "scripts" / "yunxiao" / "download_workitems.py"


def load_module():
    spec = importlib.util.spec_from_file_location("download_workitems_under_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DownloadWorkitemsTests(unittest.TestCase):
    def test_dry_run_does_not_process_or_write_items(self) -> None:
        module = load_module()
        fake_items = [{"serialNumber": "JHBN-1", "id": "item-1"}]

        with patch.object(sys, "argv", ["download_workitems.py", "--dry-run"]),              patch.object(module, "PROJECTS", {"project-1": "OASIS_SIM"}),              patch.object(module, "search", return_value=fake_items),              patch.object(module, "process_item") as process_item,              patch.object(module, "send_msg") as send_msg:
            module.main()

        process_item.assert_not_called()
        send_msg.assert_not_called()

    def test_api_raises_after_retries_instead_of_returning_empty_dict(self) -> None:
        module = load_module()

        with patch("urllib.request.urlopen", side_effect=TimeoutError("network down")),              patch.object(module.time, "sleep"):
            with self.assertRaises(RuntimeError):
                module.api("/broken", method="GET")


if __name__ == "__main__":
    unittest.main()
