#!/usr/bin/env python3
"""将 SITREP 生成的 Markdown 工作周报通过 LLM 提取后提交为钉钉周报。

用法:
  python3 submit_dingtalk_report.py --report <周报markdown路径> [--dry-run]
"""

import argparse
import json
import os
import re
import subprocess
import sys

from anthropic import Anthropic

TEMPLATE_NAME = "周报"

# OASIS SIM 产品开发群成员。
# dws report create 当前不会自动继承模板接收人，template detail 也不暴露 receiver IDs，
# 所以提交脚本必须带默认接收人，避免手动补跑或 cron 环境漏 env 后接收人为空。
DEFAULT_REPORT_RECEIVERS = (
    "1629077236740667,12365829611219204,16677841294378345,"
    "16630305268849065,17113372241822640,16454069611218832,"
    "1642554671495110,16935374573524248,17119352041538685,"
    "1753665012576918,16092186407543021,16455842823636252"
)

SYSTEM_PROMPT = """你是一个技术周报助手。根据 SITREP 自动采集的 coding agent 工作记录，生成一份简洁的钉钉周报。

要求：
1. 每个字段输出格式为编号列表（1. xxx / 2. xxx），每项 1-2 句话，中文
2. 过滤噪音：忽略系统命令、meta 对话、纯工具调用的记录
3. 合并同类：同一主题的多条记录合并为一项
4. 语义归纳：用自然中文描述做了什么，而不是照搬原始 prompt
5. 风格参考：
   本周完成工作: "1. 升级开发环境\n2. 差速小车动力学模型代码审查和交接"
   下周工作计划: "1. 解决宝时德项目动力学的遗留问题\n2. 完成 physics-Anything 的复现"

输出严格的 JSON 格式，不要有任何其他文本：
{"本周完成工作": "...", "下周工作计划": "...", "需协调与帮助": "..."}"""


def read_report(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def extract_via_llm(md: str) -> dict:
    """用 LLM 从工作周报中提取钉钉周报三个字段。"""
    if os.environ.get("SITREP_SKIP_LLM") == "1":
        print("跳过 LLM 提取，使用基础提取")
        return _basic_extract(md)

    # 截取报告主体（去掉过长内容，保护 token）
    overview = _section(md, "本周概览") or ""
    highlights = _section(md, "重点工作") or md

    # 限制内容长度，重点工作取前 15000 字符
    highlights = highlights[:15000]
    content = f"## 本周概览\n\n{overview}\n\n## 重点工作\n\n{highlights}"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # 尝试从文件加载
        for keyfile in [
            os.path.expanduser("~/.anthropic_api_key"),
            os.path.expanduser("~/.config/anthropic/api_key"),
        ]:
            if os.path.exists(keyfile):
                with open(keyfile) as f:
                    api_key = f.read().strip()
                break
    if not api_key:
        print("未找到 API key，降级为基础提取")
        return _basic_extract(md)

    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
    model = os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro[1m]")

    client = Anthropic(api_key=api_key, base_url=base_url, timeout=60.0)

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=2000,
            temperature=0.3,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        # 跳过 thinking block，取第一个文本块
        text = ""
        for block in resp.content:
            if hasattr(block, "text") and block.text:
                text = block.text
                break
        # 清理可能的 markdown 代码块包裹
        text = re.sub(r"^```(?:json)?\s*", "", text.strip())
        text = re.sub(r"\s*```$", "", text.strip())
        return json.loads(text)
    except Exception as e:
        print(f"LLM 提取失败: {e}，降级为基础提取")
        return _basic_extract(md)


def _section(md: str, heading: str) -> str:
    """提取 markdown 中指定二级标题下的内容。"""
    pattern = rf"##\s+\d+\.\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s+\d+\.|$)"
    m = re.search(pattern, md, re.DOTALL)
    return m.group(1).strip() if m else ""


def _basic_extract(md: str) -> dict:
    """无 LLM 时的降级提取。

    Rendered weekly reports already carry user-confirmed task status. Split
    completed items into this week's work and unfinished items into next week's
    plan instead of emitting a placeholder.
    """
    tasks = _parse_report_tasks(md)
    done = [t["title"] for t in tasks if t["status"] == "已完成"][:20]
    next_plan = [t["title"] for t in tasks if t["status"] in {"进行中", "受阻"}][:10]
    return {
        "本周完成工作": "\n".join(f"{i}. {t}" for i, t in enumerate(done, 1)) if done else "（无记录）",
        "下周工作计划": "\n".join(f"{i}. {t}" for i, t in enumerate(next_plan, 1)) if next_plan else "暂无需延续事项。",
        "需协调与帮助": "",
    }


def _parse_report_tasks(md: str) -> list[dict]:
    blocks = re.split(r"(?=^###\s+\d+\.\d+\.\s+)", md, flags=re.MULTILINE)
    tasks = []
    for block in blocks:
        title_match = re.search(r"^###\s+\d+\.\d+\.\s+(.+?)\s*$", block, re.MULTILINE)
        if not title_match:
            continue
        status_match = re.search(r"\*\*状态\*\*:\s*([^|\n]+)", block)
        title = title_match.group(1).strip()
        status = status_match.group(1).strip() if status_match else ""
        if title:
            tasks.append({"title": title, "status": status})
    return tasks


def get_template_fields() -> tuple[str, list[dict]]:
    r = subprocess.run(
        ["dws", "report", "template", "detail", "--name", TEMPLATE_NAME, "--format", "json"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"获取模版失败: {r.stderr}")
        sys.exit(1)
    data = json.loads(r.stdout)
    return data["result"]["report_template_id"], data["result"]["report_template_fields"]


def build_contents(fields: list[dict], data: dict) -> str:
    contents = []
    for f in fields:
        name = f["field_name"]
        ftype = f["field_type"]
        if ftype != 1:
            continue
        # 模糊匹配 LLM 输出 key（处理 "与"/"和" 等差异）
        val = ""
        for k, v in data.items():
            if _fuzzy_match(name, k):
                val = v
                break
        contents.append({
            "key": name,
            "sort": str(f["field_sort"]),
            "content": val,
            "contentType": "markdown",
            "type": str(ftype),
        })
    return json.dumps(contents, ensure_ascii=False)


def _fuzzy_match(field_name: str, llm_key: str) -> bool:
    """模糊匹配模版字段名和 LLM 输出 key。"""
    # 精确匹配
    if field_name == llm_key:
        return True
    # 去除"与"/"和"差异后匹配
    a = field_name.replace("与", "和").replace("及", "和").strip()
    b = llm_key.replace("与", "和").replace("及", "和").strip()
    return a == b
    return json.dumps(contents, ensure_ascii=False)


def submit(template_id: str, contents_json: str, dry_run: bool) -> bool:
    cmd = [
        "dws", "report", "create",
        "--template-id", template_id,
        "--contents", contents_json,
        "--format", "json",
    ]
    receivers = os.environ.get("REPORT_RECEIVERS_OVERRIDE") or DEFAULT_REPORT_RECEIVERS
    if receivers:
        cmd.extend(["--to-user-ids", receivers])
    if dry_run:
        print(f"\n[dry-run] 将执行: dws report create ...")
        print(f"[dry-run] receivers: {len([r for r in receivers.split(',') if r.strip()])}")
        print(f"[dry-run] contents:")
        for item in json.loads(contents_json):
            if item["type"] == "1":
                print(f"  [{item['key']}]")
                print(f"  {item['content'][:300]}")
                print()
        return True

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"提交失败: {r.stderr}")
        return False
    result = json.loads(r.stdout)
    if result.get("success"):
        print("钉钉周报提交成功 ✓")
        return True
    print(f"提交失败: {result}")
    return False


def main():
    parser = argparse.ArgumentParser(description="将 SITREP 周报提交为钉钉周报")
    parser.add_argument("--report", required=True, help="SITREP 生成的 Markdown 周报路径")
    parser.add_argument("--dry-run", action="store_true", help="预览不实际提交")
    args = parser.parse_args()

    if not os.path.exists(args.report):
        print(f"周报文件不存在: {args.report}")
        sys.exit(1)

    md = read_report(args.report)

    print("通过 LLM 提取关键内容...")
    data = extract_via_llm(md)

    for key in ["本周完成工作", "下周工作计划", "需协调与帮助"]:
        val = data.get(key, "")
        print(f"  [{key}]: {val[:80]}{'...' if len(val) > 80 else ''}")

    tid, fields = get_template_fields()
    contents_json = build_contents(fields, data)

    success = submit(tid, contents_json, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
