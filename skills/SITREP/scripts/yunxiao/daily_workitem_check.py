#!/usr/bin/env python3
"""每天 10:00 检查云效待办工作项（仅通知新增），发钉钉消息。"""

import json, os, subprocess, sys, urllib.request
from datetime import datetime
from pathlib import Path

API_BASE = "https://openapi-rdc.aliyuncs.com"
MY_USER_ID = "16455842823636252"
YUNXIAO_USER = "623ae63b5330d45819d7c8e7"
ORG_ID = "5f3f374f6207a1a8b17f933f"
STATE_FILE = Path.home() / ".agents" / "work-reports" / ".yunxiao" / "known_items.json"

ACTIVE_PROJECTS = [
    "18b0183e0ad89566dbefb41390",  # OASIS SIM场景仿真软件
    "35f7f4b4135610740adc881d7c",  # 北汽云仿真
]


def yunxiao_token():
    token = os.environ.get("YUNXIAO_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("YUNXIAO_ACCESS_TOKEN is required")
    return token


def api_call(path, body):
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-yunxiao-token", yunxiao_token())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        raise RuntimeError(f"Yunxiao API failed: {path}") from e


def search_workitems(space_id):
    conditions = json.dumps({
        "conditionGroups": [[{
            "fieldIdentifier": "assignedTo",
            "operator": "CONTAINS", "value": [YUNXIAO_USER],
            "className": "user", "format": "multiList",
        }]]
    })
    result = api_call(f"/oapi/v1/projex/organizations/{ORG_ID}/workitems:search", {
        "category": "Req,Bug", "conditions": conditions,
        "spaceId": space_id, "spaceType": "Project",
        "page": 1, "perPage": 30,
    })
    if isinstance(result, list):
        items = result
    else:
        items = result.get("items", [])
    # 只保留匹配的状态：需求=开发_方案评审，缺陷=待处理
    filtered = []
    for i in items:
        cat = i.get("categoryId", "")
        st = i.get("status", {}).get("name", "") or i.get("status", {}).get("displayName", "")
        if cat == "Req" and "开发_方案评审" in st:
            filtered.append(i)
        elif cat == "Bug" and "待处理" in st:
            filtered.append(i)
    return filtered


def fmt_msg(show_items, total):
    if not show_items:
        return "## 云效待办\n\n无待处理工作项"
    lines = [f"## 云效待办 · {datetime.now():%-m/%-d}", ""]
    by_project = {}
    for it in show_items:
        by_project.setdefault(it.get("space", {}).get("name", "?"), []).append(it)
    for space, its in by_project.items():
        lines.append(f"### {space}（{len(its)}项）")
        for it in its:
            sn = it.get("serialNumber", "?")
            subj = it.get("subject", "?")[:55]
            st = it.get("status", {}).get("displayName", "?")
            wt = it.get("workitemType", {}).get("name", "")
            lines.append(f"- **{sn}** [{wt}] {subj} · _{st}_")
        lines.append("")
    lines.append(f"共 {total} 项待处理")
    return "\n".join(lines)


def send_msg(text):
    subprocess.run([
        "dws", "chat", "message", "send",
        "--user", MY_USER_ID, "--title", "云效待办",
        "--text", text, "--format", "json",
    ], capture_output=True, text=True)


def load_state():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()).get("ids", []))
    return set()


def save_state(ids):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"ids": list(ids), "updated": datetime.now().isoformat()}))


def main():
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    print(f"[yunxiao-check] {datetime.now():%Y-%m-%d %H:%M:%S}")

    all_items = []
    for pid in ACTIVE_PROJECTS:
        items = search_workitems(pid)
        active = items
        all_items.extend(active)

    current_ids = {i["id"] for i in all_items}
    known_ids = load_state()

    if not known_ids or force:
        msg = fmt_msg(all_items, len(all_items))
        print(msg)
        if not dry_run:
            send_msg(msg)
            save_state(current_ids)
            print("已发送 ✓")
        return

    new_ids = current_ids - known_ids
    if not new_ids:
        still = len([i for i in all_items if i["id"] in known_ids])
        print(f"无新工作项，当前 {still} 项。跳过。")
        return

    new_items = [i for i in all_items if i["id"] in new_ids]
    msg = fmt_msg(new_items, len(all_items))
    print(msg)
    if not dry_run:
        send_msg(msg)
        save_state(current_ids)
        print(f"已发送（新增 {len(new_items)} 项）✓")


if __name__ == "__main__":
    main()
