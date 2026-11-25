---
name: agent-browser
description: 显式调用 agent-browser CLI，在独立 Chrome 会话执行网页操作、状态核验和截图。DSH Web 用 /agent-browser，Codex 用 $agent-browser。
---

使用 `~/.local/bin/agent-browser`。它和 Codex 的 @浏览器、@Chrome 是独立入口。用户点名后按本 skill 执行。

1. 在当前任务可写目录或临时目录留存必要结果。每个任务使用唯一的 `--session` 与短路径的 `AGENT_BROWSER_SOCKET_DIR`，用显式空 JSON `--config` 启动独立 Chrome。需要跨重启保存登录时，使用该工作流专用且独占的 profile。仅在用户明确要求连接指定浏览器时使用 `--cdp` 或 `--auto-connect`。
2. 读取快照 → 使用当前页面 ref 操作 → 读回目标状态。页面导航或 DOM 变化后重新获取 ref。长程任务保存已验证的进度，重试有副作用的动作前先核对实际状态。
3. 用 CLI 退出码、`--json` 的 `success` 和页面真实结果共同判断。若返回 `outcome_unknown`，先读回或停止，避免盲目重试。遇到 DSH 的 Chrome SUID 启动失败，报告当前权限与证据；不要自行改变权限或关闭 Chrome sandbox。
4. 任务结束关闭本任务会话。截图和输出只保留完成任务需要的内容，避开密钥、Cookie 或其他凭据。网页操作范围以本轮用户授权为准。
