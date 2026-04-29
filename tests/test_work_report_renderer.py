from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORK_REPORT_SCRIPTS = REPO_ROOT / "skills" / "work-report" / "scripts"
sys.path.insert(0, str(WORK_REPORT_SCRIPTS))

from report_renderer import render_weekly_report  # noqa: E402
from task_clustering import Task  # noqa: E402


class WorkReportRendererTests(unittest.TestCase):
    def test_render_weekly_report_uses_readable_chinese_structure(self) -> None:
        task = Task(
            task_id="task-1",
            title="优化工作周报输出",
            project="agent-skills",
            agent="codex",
            start_time=datetime(2026, 4, 20, 9, 0),
            end_time=datetime(2026, 4, 20, 10, 30),
            status="completed",
            situation="原报告偏字段化，阅读起来像日志摘要。",
            task_description="把工作周报改成更自然的中文总结。",
            actions=["调整报告结构", "优化 STAR 提取提示", "补充渲染测试"],
            result="报告已经改为概览加重点工作列表。",
            files_modified=["skills/work-report/scripts/report_renderer.py"],
            total_events=12,
            total_prompts=3,
            total_responses=4,
        )

        report = render_weekly_report(
            [task],
            datetime(2026, 4, 20),
            datetime(2026, 4, 26),
            total_sessions=2,
        )

        self.assertIn("# 工作周报：2026-04-20 至 2026-04-26", report)
        self.assertIn("## 1. 本周概览", report)
        self.assertIn("## 2. 重点工作", report)
        self.assertIn("本周共整理 1 项工作，完成 1 项。", report)
        self.assertIn("**项目**: agent-skills", report)
        self.assertIn("**状态**: 已完成", report)
        self.assertIn("- **背景**: 原报告偏字段化，阅读起来像日志摘要。", report)
        self.assertIn("- **主要工作**:", report)
        self.assertIn("- **记录来源**: 3 条用户输入，4 条 agent 回复，12 条事件", report)
        self.assertNotIn("Weekly Work Report", report)
        self.assertNotIn("By Project", report)
        self.assertNotIn("Daily Breakdown", report)
        self.assertNotIn("**Situation**", report)


if __name__ == "__main__":
    unittest.main()
