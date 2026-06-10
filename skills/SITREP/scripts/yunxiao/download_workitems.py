#!/usr/bin/env python3
"""Phase 0: 需求抓取与预处理。下载工作项到本地存档（含图片、PRD、UX、参数表）。
通过 OpenAPI 获取签名 URL 后直接下载 OSS 文件。
"""

import hashlib, json, os, re, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

API_BASE = "https://openapi-rdc.aliyuncs.com"
ORG_ID = "5f3f374f6207a1a8b17f933f"
YUNXIAO_USER = "623ae63b5330d45819d7c8e7"

PROJECTS = {"18b0183e0ad89566dbefb41390": "OASIS_SIM", "35f7f4b4135610740adc881d7c": "BEIQI"}
OUT_DIR = Path("/media/yhr/2T/yunxiao")
# 筛选条件：需求=开发_方案评审，缺陷=待处理
STATUS_FILTER = {"Req": ["开发_方案评审"], "Bug": ["待处理"]}


def yunxiao_token():
    token = os.environ.get("YUNXIAO_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("YUNXIAO_ACCESS_TOKEN is required")
    return token


def api(path, body=None, method="POST"):
    url = f"{API_BASE}{path}"
    if method == "GET":
        req = urllib.request.Request(url, method="GET")
    else:
        data = json.dumps(body or {}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
    req.add_header("x-yunxiao-token", yunxiao_token())
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1)
    raise RuntimeError(f"Yunxiao API failed after 3 attempts: {path}") from last_error


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


def get_item_status(workitem_id):
    """查询单个工作项的 displayName 状态。"""
    path = f"/oapi/v1/projex/organizations/{ORG_ID}/workitems/{workitem_id}"
    item = api(path, method="GET")
    return item.get("status", {}).get("displayName", "")


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


def _comment_count_from_md(path: Path) -> int:
    """Count existing comments in detail.md by counting '> **' lines."""
    if not path.exists():
        return 0
    content = path.read_text(encoding="utf-8")
    return len(re.findall(r'^> \*\*.*?\*\* _', content, re.MULTILINE))


def process_item(item, subdir):
    sn = item.get("serialNumber", "?")
    iid = item["id"]
    d = OUT_DIR / subdir / sn

    # Determine first-time vs incremental
    existing_state = {}
    if (d / "state.json").exists():
        try:
            existing_state = json.loads((d / "state.json").read_text())
        except Exception:
            pass

    is_new = not existing_state
    d.mkdir(parents=True, exist_ok=True)

    if is_new:
        print(f"  {sn}...", end=" ", flush=True)
    else:
        print(f"  {sn} (update)...", end=" ", flush=True)

    detail = api(f"/oapi/v1/projex/organizations/{ORG_ID}/workitems/{iid}", method="GET")
    comments = api(f"/oapi/v1/projex/organizations/{ORG_ID}/workitems/{iid}/comments", method="GET")

    # 解析描述 HTML
    desc_html = detail.get("description", "")
    if isinstance(desc_html, str) and desc_html.startswith("{"):
        try: desc_html = json.loads(desc_html).get("htmlValue", "")
        except: pass

    clist = comments if isinstance(comments, list) else comments.get("comments", [])
    trackers = detail.get("trackers") or item.get("trackers") or []
    participants = detail.get("participants") or item.get("participants") or []
    now_str = datetime.now().isoformat()

    # ── Attachments: download new files (both first-time and update) ──
    all_ids = extract_file_ids(desc_html)
    for c in clist:
        ch = c.get("content", "")
        if isinstance(ch, str) and ch.startswith("{"):
            try: ch = json.loads(ch).get("htmlValue", "")
            except: pass
        all_ids.extend(extract_file_ids(ch))

    seen_names = set(f.name for f in d.iterdir() if f.is_file())  # skip existing
    for idx, fid in enumerate(dict.fromkeys(all_ids), 1):
        if fid in seen_names:
            continue
        url = api(f"/oapi/v1/projex/organizations/{ORG_ID}/workitems/{iid}/files/{fid}", method="GET").get("url", "")
        if not url: continue
        info = api(f"/oapi/v1/projex/organizations/{ORG_ID}/workitems/{iid}/files/{fid}", method="GET")
        orig_name = info.get("name", f"{fid[:8]}.png")
        if orig_name in seen_names:
            stem, ext = orig_name.rsplit(".", 1) if "." in orig_name else (orig_name, "png")
            orig_name = f"{stem}_{idx}.{ext}"
        seen_names.add(orig_name)
        if download_oss(url, d, orig_name):
            print(".", end="", flush=True)

    attachments = api(f"/oapi/v1/projex/organizations/{ORG_ID}/workitems/{iid}/attachments", method="GET")
    for att in (attachments if isinstance(attachments, list) else []):
        fname = att.get("fileName", f"attachment_{att.get('fileId','')[:8]}")
        if fname in seen_names:
            continue
        oss_url = att.get("url", "")
        seen_names.add(fname)
        if oss_url and download_oss(oss_url, d, fname):
            print("a", end="", flush=True)

    # ── First-time: download linked docs ──
    linked = {}
    if is_new:
        linked = download_linked_docs(desc_html, d)

    # ── detail.md: rewrite if new, append if comments changed ──
    detail_path = d / "detail.md"
    new_comment_count = len(clist)
    old_comment_count = _comment_count_from_md(detail_path) if not is_new else 0

    if is_new or new_comment_count > old_comment_count:
        if is_new:
            # Full write
            lines = [
                f"# {sn} · {item.get('subject','?')}",
                "",
                f"| 字段 | 内容 |", f"|------|------|",
                f"| 类型 | {item.get('workitemType',{}).get('name','')} |",
                f"| 状态 | {item.get('status',{}).get('displayName','')} |",
                f"| 创建人 | {item.get('creator',{}).get('name','')} |",
                f"| 负责人 | {item.get('assignedTo',{}).get('name','')} |",
                f"| 项目 | {dict(PROJECTS).get(item.get('space',{}).get('id',''),'')} |",
            ]
            if participants: lines.append(f"| 参与人 | {', '.join(p.get('name','?') for p in participants)} |")
            if trackers: lines.append(f"| 抄送 | {', '.join(t.get('name','?') for t in trackers)} |")
            lines.append("")
            lines.append("## 描述"); lines.append(html_to_text(desc_html) or "（无描述）"); lines.append("")
            lines.append("## 评论")
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
            if not clist:
                lines.append("（无评论）")
                lines.append("")
            detail_path.write_text("\n".join(lines), encoding="utf-8")
        else:
            # Append new comments only
            new_comments = clist[old_comment_count:]
            with open(detail_path, "a", encoding="utf-8") as f:
                for c in new_comments:
                    user = c.get("user", {}).get("name", "?")
                    ts = c.get("gmtCreate", 0)
                    ts_str = datetime.fromtimestamp(ts/1000).strftime("%m-%d %H:%M") if ts else "?"
                    ct = c.get("content", "")
                    if isinstance(ct, str) and ct.startswith("{"):
                        try: ct = json.loads(ct).get("htmlValue", "")
                        except: pass
                    text = html_to_text(ct)
                    f.write(f"> **{user}** _{ts_str}_\n")
                    for cl in text.split("\n")[:5]: f.write(f"> {cl}\n")
                    f.write("\n")
            print(f"+{new_comment_count-old_comment_count}c", end="", flush=True)

    # ── state.json: always update ──
    state = {
        "demand_id": sn,
        "workitem_id": iid,
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
        "prd_doc_path": linked.get("prd") or existing_state.get("prd_doc_path", ""),
        "ux_doc_paths": linked.get("ux") or existing_state.get("ux_doc_paths", []),
        "builtin_params_path": linked.get("builtin_params") or existing_state.get("builtin_params_path", ""),
        "design_doc_path": existing_state.get("design_doc_path", ""),
        "knowledge_doc_url": existing_state.get("knowledge_doc_url", ""),
        "calendar_event_id": existing_state.get("calendar_event_id", ""),
        "deliverable_url": existing_state.get("deliverable_url", ""),
    }
    (d / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✓")


def send_msg(text):
    import subprocess
    result = subprocess.run([
        "dws", "chat", "message", "send",
        "--user", "16455842823636252", "--title", "云效存档",
        "--text", text, "--format", "json",
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "DingTalk message send failed: "
            f"stdout={result.stdout.strip()} stderr={result.stderr.strip()}"
        )

def main():
    dry_run = "--dry-run" in sys.argv
    stats = []
    status_changes = []

    for pid, pname in PROJECTS.items():
        for cat, subdir in [("Req", "requirements"), ("Bug", "bugs")]:
            items = search(pid, cat)
            updated = 0
            for item in items:
                sn = item.get("serialNumber", "?")
                d = OUT_DIR / subdir / sn

                # Track status changes
                if (d / "state.json").exists():
                    try:
                        old_st = json.loads((d / "state.json").read_text())
                        old_status = old_st.get("status", "")
                    except Exception:
                        old_status = ""
                else:
                    old_status = ""

                if dry_run:
                    print(f"  {sn} ({subdir}, dry-run)")
                else:
                    process_item(item, subdir)

                # Check for status change
                new_status = item.get("status", {}).get("displayName", "")
                if old_status and new_status and old_status != new_status:
                    status_changes.append((sn, old_status, new_status))
                updated += 1
            if updated:
                stats.append(f"{pname} {cat}: {updated} 项")

    changed_sns = {sn for sn, _, _ in status_changes}

    # List all active items
    all_active = []
    inbox_count = 0
    for sf in OUT_DIR.glob("*/**/state.json"):
        try:
            st = json.loads(sf.read_text())
            if st.get("phase") != "done":
                all_active.append(st)
                if st.get("phase") == "new":
                    inbox_count += 1
        except: pass

    print(f"\n完成 | 列表: {len(all_active)} | inbox: {inbox_count}")
    if status_changes:
        print(f"  状态变更: {len(status_changes)} 项")

    if not dry_run:
        now_str = datetime.now().strftime("%-m/%-d")
        run_time = datetime.now().strftime("%H:%M:%S")
        lines = [f"## 今日云效待办 · {now_str}", ""]
        lines.append(f"✅ 定时任务已执行：{run_time}")
        if stats:
            lines.append(f"📦 本次扫描：{', '.join(stats)}")
        else:
            lines.append("📦 本次扫描：未发现符合筛选条件的云效工作项")
        lines.append("")

        by_project = {}
        for it in all_active:
            by_project.setdefault(it.get("project", "?"), []).append(it)
        if by_project:
            for proj, its in by_project.items():
                lines.append(f"### {proj}（{len(its)}项）")
                for it in its:
                    type_icon = "📋" if "需求" in it['type'] else "🐛"
                    st = it['status']
                    if "待处理" in st or "挂起" in st: st_icon = "⏳"
                    elif "进行中" in st or "开发" in st or "修复" in st: st_icon = "🔄"
                    elif "方案" in st: st_icon = "📝"
                    else: st_icon = "📌"
                    chg = "⚡" if it['demand_id'] in changed_sns else ""
                    lines.append(f"- {type_icon} **{it['demand_id']}** {it['title'][:55]} · {st_icon} **{it['status']}** {chg}")
                lines.append("")
        else:
            lines.append("暂无待处理项。")
            lines.append("")

        lines.append(f"📥 Inbox: {inbox_count} 项待处理")
        lines.append("")
        if status_changes:
            lines.append(f"🔄 状态变更: {len(status_changes)} 项")
            for sn, old, new in status_changes:
                lines.append(f"- **{sn}** {old} → {new}")
        else:
            lines.append("🔄 状态变更：无")

        # --- Clear-ready scan (phase=integration, 集成测试中→回归验证) ---
        clear_ready = []
        bugs_root = OUT_DIR / "bugs"
        if bugs_root.exists():
            for bug_dir in sorted(bugs_root.iterdir()):
                if not bug_dir.is_dir():
                    continue
                sp = bug_dir / "state.json"
                if not sp.exists():
                    continue
                try:
                    st = json.loads(sp.read_text())
                except Exception:
                    continue
                if st.get("phase") != "integration":
                    continue
                if st.get("status") != "集成测试中":
                    continue
                wid = st.get("workitem_id", "")
                if not wid:
                    continue
                yunxiao_status = get_item_status(wid)
                if yunxiao_status == "回归验证":
                    clear_ready.append((bug_dir.name, st.get("title", ""), st.get("fix_branch", "")))

        if clear_ready:
            lines.append("")
            lines.append(f"🧹 Clear Ready: {len(clear_ready)} 项")
            for bug_id, title, branch in clear_ready:
                lines.append(f"- **{bug_id}** {title[:50]} · `/Repair Clear {bug_id}`")
        # --- end Clear scan ---

        send_msg("\n".join(lines))

if __name__ == "__main__":
    main()
