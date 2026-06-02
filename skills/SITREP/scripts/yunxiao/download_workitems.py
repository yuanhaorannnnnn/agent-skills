#!/usr/bin/env python3
"""Phase 0: 需求抓取与预处理。下载工作项到本地存档（含图片、PRD、UX、参数表）。
通过 OpenAPI 获取签名 URL 后直接下载 OSS 文件。
"""

import hashlib, json, re, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

API_BASE = "https://openapi-rdc.aliyuncs.com"
TOKEN = "pt-yaK0iLa8SZasNlLZ6pYSCZBZ_48cb5651-11a3-4df6-b5a0-80dcb5c033f4"
ORG_ID = "5f3f374f6207a1a8b17f933f"
YUNXIAO_USER = "623ae63b5330d45819d7c8e7"

PROJECTS = {"18b0183e0ad89566dbefb41390": "OASIS_SIM", "35f7f4b4135610740adc881d7c": "BEIQI"}
OUT_DIR = Path("/media/yhr/2T/yunxiao")
# 筛选条件：需求=开发_方案评审，缺陷=待处理
STATUS_FILTER = {"Req": ["开发_方案评审"], "Bug": ["待处理"]}


def api(path, body=None, method="POST"):
    url = f"{API_BASE}{path}"
    if method == "GET":
        req = urllib.request.Request(url, method="GET")
    else:
        data = json.dumps(body or {}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
    req.add_header("x-yunxiao-token", TOKEN)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception:
            if attempt == 2: return {}
            time.sleep(1)


def search(space_id, category):
    """搜索分配给我的指定状态工作项。"""
    conditions = json.dumps({"conditionGroups": [[{
        "fieldIdentifier": "assignedTo", "operator": "CONTAINS",
        "value": [YUNXIAO_USER], "className": "user", "format": "multiList",
    }]]})
    result = api(f"/oapi/v1/projex/organizations/{ORG_ID}/workitems:search",
                 {"category": category, "conditions": conditions,
                  "spaceId": space_id, "spaceType": "Project", "page": 1, "perPage": 50})
    items = result if isinstance(result, list) else result.get("items", [])
    # 按类型筛选指定状态
    keywords = STATUS_FILTER.get(category, [])
    if keywords:
        items = [i for i in items if any(
            kw in i.get("status", {}).get("name", "") or
            kw in i.get("status", {}).get("displayName", "")
            for kw in keywords)]
    return items


def html_to_text(html):
    if not html: return ""
    t = re.sub(r'<[^>]+>', '', str(html))
    for e, c in [('&nbsp;',' '),('&lt;','<'),('&gt;','>'),('&amp;','&')]:
        t = t.replace(e, c)
    return t.strip()


def extract_file_ids(html):
    if not html: return []
    return list(dict.fromkeys(re.findall(r'fileIdentifier=([a-f0-9]+)', str(html))))


def download_oss(url, save_dir, fname):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            (save_dir / fname).write_bytes(resp.read())
        return True
    except Exception:
        return False


def classify_doc(content, node_id, url):
    """判断文档类型：prd / ux / builtin_params / 通用。"""
    c = (content or "").lower()
    params = url.lower()
    # 表格 → builtin_params.csv
    if 'sheet_range' in params:
        return 'builtin_params', '.csv'
    # UX 关键词
    ux_kw = ['ux', '原型', '设计稿', '蓝湖', 'lanhu', '交互', 'ui ', '界面', 'figma', '高保真', '低保真']
    if any(kw in c[:2000] for kw in ux_kw):
        return 'ux', '.md'
    # PRD 关键词
    prd_kw = ['需求', 'prd', '规格', '参数', '配置', '功能', '接口', '模块', '方案', 'spec', 'requirement', 'feature']
    if any(kw in c[:2000] for kw in prd_kw):
        return 'prd', '.md'
    # 默认用 node_id
    return node_id[:40], '.md'


def download_linked_docs(html, save_dir):
    """下载钉钉文档和表格，返回 prd/ux/params 路径。"""
    import subprocess
    result = {"prd": "", "ux": [], "builtin_params": ""}
    alidoc_urls = list(dict.fromkeys(re.findall(r'(https?://alidocs\.dingtalk\.com/[^\s"<>]+)', str(html))))
    for url in alidoc_urls:
        node_id = url.split('/')[-1].split('?')[0]
        content = ''
        # 先试文档
        r = subprocess.run(['dws', 'doc', 'read', '--node', node_id, '--format', 'json'],
                          capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            try: content = json.loads(r.stdout).get('markdown', '')
            except: pass
        # 失败则试表格
        if not content:
            r2 = subprocess.run(['dws', 'sheet', 'range', 'read', '--node', node_id, '--format', 'json'],
                               capture_output=True, text=True, timeout=30)
            if r2.returncode == 0:
                try:
                    rows = json.loads(r2.stdout).get('displayValues', [])
                    content = '\n'.join(' | '.join(str(v) for v in (row or [])) for row in rows)
                except: pass
        if not content:
            continue

        dtype, ext = classify_doc(content, node_id, url)
        fname = f"{dtype}{ext}"
        (save_dir / fname).write_text(content, encoding='utf-8')

        if dtype == 'prd':
            result['prd'] = str(save_dir / fname)
        elif dtype == 'ux':
            result['ux'].append(str(save_dir / fname))
        elif dtype == 'builtin_params':
            result['builtin_params'] = str(save_dir / fname)
        print('d', end='', flush=True)
    return result


def process_item(item, subdir, force=False):
    sn = item.get("serialNumber", "?")
    iid = item["id"]
    d = OUT_DIR / subdir / sn

    if (d / "state.json").exists():
        st = json.loads((d / "state.json").read_text())
        if st.get("phase") == "done" and not force:
            print(f"  {sn} (done)")
            return
        if not force:
            print(f"  {sn} (skip)")
            return

    d.mkdir(parents=True, exist_ok=True)
    print(f"  {sn}...", end=" ", flush=True)

    detail = api(f"/oapi/v1/projex/organizations/{ORG_ID}/workitems/{iid}", method="GET")
    comments = api(f"/oapi/v1/projex/organizations/{ORG_ID}/workitems/{iid}/comments", method="GET")

    # 解析描述 HTML
    desc_html = detail.get("description", "")
    if isinstance(desc_html, str) and desc_html.startswith("{"):
        try: desc_html = json.loads(desc_html).get("htmlValue", "")
        except: pass

    # 下载关联文档
    linked = download_linked_docs(desc_html, d)

    # 下载附件图片
    all_ids = extract_file_ids(desc_html)
    clist = comments if isinstance(comments, list) else comments.get("comments", [])
    for c in clist:
        ch = c.get("content", "")
        if isinstance(ch, str) and ch.startswith("{"):
            try: ch = json.loads(ch).get("htmlValue", "")
            except: pass
        all_ids.extend(extract_file_ids(ch))

    for fid in dict.fromkeys(all_ids):
        url = api(f"/oapi/v1/projex/organizations/{ORG_ID}/workitems/{iid}/files/{fid}", method="GET").get("url", "")
        if not url: continue
        info = api(f"/oapi/v1/projex/organizations/{ORG_ID}/workitems/{iid}/files/{fid}", method="GET")
        orig_name = info.get("name", f"{fid[:8]}.png")
        if download_oss(url, d, orig_name):
            print(".", end="", flush=True)

    # 元数据
    trackers = detail.get("trackers") or item.get("trackers") or []
    participants = detail.get("participants") or item.get("participants") or []
    now_str = datetime.now().isoformat()

    # state.json
    existing_state = {}
    if (d / "state.json").exists():
        try: existing_state = json.loads((d / "state.json").read_text())
        except: pass

    state = {
        "demand_id": sn,
        "title": item.get("subject", ""),
        "type": item.get("workitemType", {}).get("name", ""),
        "status": item.get("status", {}).get("displayName", ""),
        "project": dict(PROJECTS).get(item.get("space", {}).get("id", ""), ""),
        "creator": item.get("creator", {}).get("name", ""),
        "assignee": item.get("assignedTo", {}).get("name", ""),
        "participants": [p.get("name", "") for p in participants],
        "cc": [t.get("name", "") for t in trackers],
        "phase": existing_state.get("phase", "new"),
        "created_at": existing_state.get("created_at", now_str),
        "updated_at": now_str,
        "local_dir": str(d),
        "prd_doc_path": linked["prd"] or existing_state.get("prd_doc_path", ""),
        "ux_doc_paths": linked["ux"] or existing_state.get("ux_doc_paths", []),
        "builtin_params_path": linked["builtin_params"] or existing_state.get("builtin_params_path", ""),
        "design_doc_path": existing_state.get("design_doc_path", ""),
        "knowledge_doc_url": existing_state.get("knowledge_doc_url", ""),
        "calendar_event_id": existing_state.get("calendar_event_id", ""),
        "deliverable_url": existing_state.get("deliverable_url", ""),
    }
    (d / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # detail.md
    lines = [
        f"# {sn} · {item.get('subject','?')}",
        "",
        f"| 字段 | 内容 |", f"|------|------|",
        f"| 类型 | {state['type']} |",
        f"| 状态 | {state['status']} |",
        f"| 创建人 | {state['creator']} |",
        f"| 负责人 | {state['assignee']} |",
        f"| 项目 | {state['project']} |",
    ]
    if participants: lines.append(f"| 参与人 | {', '.join(p.get('name','?') for p in participants)} |")
    if trackers: lines.append(f"| 抄送 | {', '.join(t.get('name','?') for t in trackers)} |")
    lines.append("")
    lines.append("## 描述"); lines.append(html_to_text(desc_html) or "（无描述）"); lines.append("")
    lines.append("## 评论")
    if clist:
        for c in clist:
            user = c.get("user", {}).get("name", "?")
            ts = c.get("gmtCreate", 0)
            ts_str = datetime.fromtimestamp(ts/1000).strftime("%m-%d %H:%M") if ts else "?"
            ct = c.get("content", "")
            if isinstance(ct, str) and ct.startswith("{"):
                try: ct = json.loads(ct).get("htmlValue", "")
                except: pass
            text = html_to_text(ct)
            lines.append(f"> **{user}** _{ts_str}_")
            for cl in text.split("\n")[:5]: lines.append(f"> {cl}")
            lines.append("")
    else:
        lines.append("（无评论）")
        lines.append("")
    (d / "detail.md").write_text("\n".join(lines), encoding="utf-8")
    print("✓")


def send_msg(text):
    import subprocess
    subprocess.run([
        "dws", "chat", "message", "send",
        "--user", "16455842823636252", "--title", "云效存档",
        "--text", text, "--format", "json",
    ], capture_output=True, text=True)


def main():
    force = "--force" in sys.argv
    dry_run = "--dry-run" in sys.argv
    stats = []

    for pid, pname in PROJECTS.items():
        for cat, subdir in [("Req", "requirements"), ("Bug", "bugs")]:
            items = search(pid, cat)
            new_items = 0
            for item in items:
                sn = item.get("serialNumber", "?")
                d = OUT_DIR / subdir / sn
                already = (d / "state.json").exists()
                if not already or force:
                    process_item(item, subdir, force=force)
                    new_items += 1
            if new_items:
                stats.append(f"{pname} {cat}: {new_items} 项")

    print("\n完成")
    if stats and not dry_run:
        send_msg("## 云效存档\n\n" + "\n".join(f"- {s}" for s in stats))


if __name__ == "__main__":
    main()
