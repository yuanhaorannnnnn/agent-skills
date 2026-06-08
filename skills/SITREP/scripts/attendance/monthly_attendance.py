#!/usr/bin/env python3
"""月末出勤统计：最后一个工作日 17:30 触发，发钉钉消息告知实际出勤天数。

公式: 实际出勤 = 当月周一至周五天数 - 法定假日调休天数 - 请假天数
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

MY_USER_ID = "16455842823636252"
MY_NAME = "袁浩然"

# 法定节假日（国务院 2026 年放假安排：国办发明电〔2025〕7号）
HOLIDAYS_2026 = {
    # 元旦 1/1-1/3（3天）
    "2026-01-01", "2026-01-02",
    # 春节 2/15-2/23（9天）
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20", "2026-02-23",
    # 清明 4/4-4/6（3天，不调休）
    "2026-04-06",
    # 劳动节 5/1-5/5（5天）
    "2026-05-01", "2026-05-04", "2026-05-05",
    # 端午 6/19-6/21（3天，不调休）
    "2026-06-19",
    # 中秋 9/25-9/27（3天，不调休）
    "2026-09-25",
    # 国庆+中秋连休 10/1-10/7（7天）
    "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07",
}

# 调休补班日（周末上班）
MAKEUP_WORKDAYS_2026 = {
    "2026-01-04",  # 元旦调休（周日上班）
    "2026-02-14",  # 春节调休（周六上班）
    "2026-02-28",  # 春节调休（周六上班）
    "2026-05-09",  # 劳动节调休（周六上班）
    "2026-09-20",  # 国庆调休（周日上班）
    "2026-10-10",  # 国庆调休（周六上班）
}


def _is_working_day(d: datetime) -> bool:
    """判断某天是否为工作日（考虑周末、法定假、调休补班）。"""
    ds = d.strftime("%Y-%m-%d")
    if ds in HOLIDAYS_2026:
        return False
    if ds in MAKEUP_WORKDAYS_2026:
        return True
    return d.weekday() < 5


def last_working_day_of_month() -> datetime:
    """返回当月最后一个工作日。"""
    today = datetime.now()
    if today.month == 12:
        first_of_next = datetime(today.year + 1, 1, 1)
    else:
        first_of_next = datetime(today.year, today.month + 1, 1)
    last_day = first_of_next - timedelta(days=1)

    cursor = last_day
    while True:
        if _is_working_day(cursor):
            return cursor
        cursor -= timedelta(days=1)


def count_working_days(year: int, month: int) -> int:
    """统计当月工作日天数（周一至周五 - 法定假 + 调休补班）。"""
    first = datetime(year, month, 1)
    if month == 12:
        last = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = datetime(year, month + 1, 1) - timedelta(days=1)

    count = 0
    cursor = first
    while cursor <= last:
        if _is_working_day(cursor):
            count += 1
        cursor += timedelta(days=1)
    return count


def _json_loads_checked(stdout: str, context: str) -> dict:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{context} 返回非 JSON: {exc}") from exc


def _approval_instances_page(process_code: str, start: str, end: str, next_token: int) -> tuple[list[dict], int | None]:
    r = subprocess.run([
        "dws", "oa", "approval", "list-initiated",
        "--process-code", process_code,
        "--start", start, "--end", end,
        "--max-results", "20", "--next-token", str(next_token), "--format", "json",
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"查询请假审批失败: {r.stderr or r.stdout}")

    data = _json_loads_checked(r.stdout, "查询请假审批")
    result = data.get("result", {})
    instances = result.get("processInstanceList", []) or result.get("list", []) or []
    token = result.get("nextToken", result.get("next_token"))
    try:
        token = int(token) if token not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        token = None
    return instances, token


def _approval_detail(instance_id: str) -> dict:
    r = subprocess.run([
        "dws", "oa", "approval", "detail",
        "--instance-id", instance_id,
        "--format", "json",
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"读取请假审批详情失败 {instance_id}: {r.stderr or r.stdout}")
    return _json_loads_checked(r.stdout, f"请假审批详情 {instance_id}")


def _numbers_from_value(value) -> list[float]:
    if value is None:
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    text = str(value)
    results = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*天", text):
        results.append(float(m.group(1)))
    if results:
        return results
    if re.fullmatch(r"\s*\d+(?:\.\d+)?\s*", text):
        return [float(text)]
    return []


def _extract_leave_days_from_detail(detail: dict, instance_id: str) -> float:
    """Extract leave duration from approval detail; fail if ambiguous."""
    candidates: list[float] = []
    keywords = ("请假天数", "请假时长", "休假天数", "休假时长", "天数", "时长", "duration", "days")

    def walk(obj, context: str = ""):
        if isinstance(obj, dict):
            names = []
            for key in ("name", "label", "title", "componentName", "bizAlias", "id", "key"):
                if obj.get(key) is not None:
                    names.append(str(obj.get(key)))
            local_context = " ".join([context, *names])
            for key in ("value", "extValue", "text", "content"):
                if key in obj and any(k.lower() in local_context.lower() for k in keywords):
                    candidates.extend(_numbers_from_value(obj.get(key)))
            for k, v in obj.items():
                walk(v, f"{local_context} {k}")
        elif isinstance(obj, list):
            for item in obj:
                walk(item, context)

    walk(detail)
    positive = [v for v in candidates if v > 0]
    if not positive:
        raise RuntimeError(f"无法从请假审批详情解析请假天数: {instance_id}")
    # If several fields repeat the same duration, use the max to avoid double counting duplicates.
    return max(positive)


def count_leave_days(year: int, month: int) -> float:
    """从 OA 审批获取当月请假天数。失败时抛错，避免把未知当 0。"""
    start = f"{year}-{month:02d}-01T00:00:00+08:00"
    if month == 12:
        end = f"{year+1}-01-01T00:00:00+08:00"
    else:
        end = f"{year}-{month+1:02d}-01T00:00:00+08:00"

    process_code = "PROC-69CDA25A-3952-47AA-AD0C-746BCF066B92"
    next_token = 0
    instances: list[dict] = []
    while True:
        page, next_token_or_none = _approval_instances_page(process_code, start, end, next_token)
        instances.extend(page)
        if next_token_or_none is None:
            break
        next_token = next_token_or_none

    leave_days = 0.0
    for inst in instances:
        if inst.get("processInstanceStatus") not in ("COMPLETED", "AGREE"):
            continue
        instance_id = inst.get("processInstanceId") or inst.get("process_instance_id") or inst.get("id")
        if not instance_id:
            raise RuntimeError(f"请假审批缺少 instance id: {inst}")
        detail = _approval_detail(instance_id)
        leave_days += _extract_leave_days_from_detail(detail, instance_id)
    return leave_days


def send_message(text: str):
    """给自己发钉钉消息。"""
    r = subprocess.run([
        "dws", "chat", "message", "send",
        "--user", MY_USER_ID,
        "--title", f"月出勤统计",
        "--text", text,
        "--format", "json",
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"发送出勤统计失败: {r.stderr or r.stdout}")


def parse_month() -> tuple[int, int]:
    """解析 --month YYYY-MM 或返回当前月。"""
    for i, a in enumerate(sys.argv):
        if a == "--month" and i + 1 < len(sys.argv):
            parts = sys.argv[i + 1].split("-")
            return int(parts[0]), int(parts[1])
    now = datetime.now()
    return now.year, now.month


def main():
    year, month = parse_month()
    # 用该月 15 号作为参考日
    ref_date = datetime(year, month, 15)

    # 只在最后一个工作日触发（--force / --month 可强制）
    forced = "--force" in sys.argv or "--month" in sys.argv
    today = datetime.now()
    lwd = last_working_day_of_month()
    if not forced and today.date() != lwd.date():
        print(f"今天 {today:%Y-%m-%d} 不是月末最后一个工作日 ({lwd:%Y-%m-%d})，跳过。")
        return

    print(f"计算出勤: {year}年{month}月...")

    total = count_working_days(year, month)
    leave = count_leave_days(year, month)
    actual = total - leave

    msg = (
        f"## {MY_NAME} {month}月出勤统计\n\n"
        f"- 应出勤：**{total}** 天（工作日 - 法定假 + 调休补班）\n"
        f"- 请假：**{leave:g}** 天\n"
        f"- 实际出勤：**{actual:g}** 天"
    )

    print(msg)
    if "--dry-run" not in sys.argv:
        send_message(msg)
        print("已发送 ✓")


if __name__ == "__main__":
    main()
