# 会话接续归属

同一项工作由一种机制负责接续。`session_handoff_scan.py`只读取原生`session_meta.thread_source`、明确的接续设置和既有后继关联，不读取标题/消息内容来猜来源，也不降低原压缩、空闲、活动或项目检查条件。

| 来源/状态 | 通用交接动作 |
| --- | --- |
| `automation` | 默认`scheduler`：保留源对话，由该自动化后续运行读取自身持久任务状态，不创建交接对话 |
| `user`、`agent_created_thread` | 默认`handoff`：达到原阈值后继续原安全检查与后继验证 |
| 已登记后继 | 沿交接关联继承原接续方式；不会因后继标记为agent创建而丢失automation来源 |
| 已有`successor_created`且有ID | 仅恢复/验证该后继，禁止再创建；完成记录和源对话均保留 |
| 用户明确取消既有交接 | 记录`cancelled`，保留原后继ID与前状态；源/后继均不再自动创建或恢复交接，不改Heartbeat绑定 |
| `subagent` | 保留；子agent不作为用户长期对话自动交接 |
| 来源缺失/冲突、父关联缺失/冲突/循环 | 保留并报告`unresolved`原因，不猜、不创建 |

扫描JSON保留`candidates`，增加`skipped`，每项附`continuation_mode`、`continuation_reason`，候选另有`action=handoff|recover-existing`。`skipped`不占每轮最多3个真实候选；未知归属须在运行结果列明，不能称全部无事。`--include-handled`仅用于只读核验，不重新打开已完成交接。

定时运行自身须按已有业务契约及时保存用户决定、检查点和未完成项。通用交接任务不写其他任务业务文件、不代替它们补造检查点，也不把“未新建聊天”称为业务已经完成。自动化关联信息或持久状态不足时，由该任务实际续接时明确报告缺口。

用户明确把某次运行转为长期人工推进时，可在原交接状态中设置覆盖：

```bash
python3 /home/yhr/.agents/repos/agent-skills/scripts/session_handoff_scan.py \
  --set-continuation <完整session-id> --mode handoff --reason '<用户明确指令依据>'
```

`--mode scheduler`可将跨轮接续归回调度器。覆盖仅由明确用户决定设置，不依据聊天长度或模型猜测自动切换；设置不删除既有完成/后继事实。已经交接的源对话不再生成第二个后继；需要人工长期推进时在当前后继设置。写入沿用`~/.agents/session-handoff/state.json`，锁定读改写，保留其他记录，无新增状态服务。

固定聊天中的定时续办可使用已有聊天上下文；轮换聊天后，其定时目标绑定仍需另外实际更新并回读验证。本路由修改不自动迁移这些绑定，不声称具备该能力。

用户明确要求取消交接、归档后继并继续原对话时，先读原指令及当前归档/绑定状态，再用`--mark-cancelled <source-id> --reason '<用户决定的thread/turn依据>'`保存到既有交接账本。仅凭等待审批、暂时失败或未回复不能取消。扫描返回`handoff-cancelled-by-user`属于有依据的保留，不是完成交接，也不是未解决来源冲突。不得取消归档、唤醒后继、迁移定时绑定或重开取消记录；后续重新交接需新的明确用户决定。

解析rollout时，首个本会话原生ID持有文件归属。子agent首头明确声明父session_id时，后续继承的父session_meta不能覆盖本会话ID或来源；不符合该明确父关联的不同ID继续标冲突，不凭文件名或正文猜测。
