# Automation execution and delivery contract

任务 prompt 持有业务范围、收件人、预算和执行时刻；本文件只定义共享机制，不授予任何新增发送或写入权限。所有业务日期、周/月窗口和用户指定时刻统一 Asia/Shanghai（UTC+08:00）。不能把服务器UTC小时当北京时间。调度变更通过 automation_update，并将实际 next_run_nominal_at/next_run_at 转为东八区核验；不直接改 scheduler 数据库。

## 本地状态与业务结果

工具位于本文件所属 agent-skills 仓库的 scripts 目录：`python3 <agent-skills-repo>/scripts/automation_state.py --directory <CODEX_HOME>/automations/<id> <action> --input <JSON文件>`。状态继续使用现有 reliability-state.json；不迁移或清空旧items/issues/months/facts。输入用JSON文件，禁止把HTML或业务文本拼进shell命令。

原任务模型前置门禁优先；门禁前不读业务数据、不写状态。未知实际模型视为blocked，不凭配置替代实际运行模型。通过后，以实际run/thread ID为key使用run action，分别记录：
- business_status：running / completed / no_op / partial / blocked / failed。
- notification_status：not_needed / pending / reported_in_chat / confirmed / unverified / failed。
- 可选gate、artifact、updated_at；只存最小诊断，禁止凭据或无关业务正文。

开始可记running/pending，完成写实际业务结果。业务未完成不能因为工具正常返回或PENDING_REVIEW而记completed。未验证用户端通知时记unverified；只有实际通知回执才能confirmed。reported_in_chat只表示已有可核验聊天输出，不表示系统推送。先保存结果，再输出明确结果或阻塞及产物路径；若工具支持且确知本轮thread ID，可标未读，仍不算系统推送确认。不写scheduler状态，不发送额外失败邮件。

item只记录各工作项，completed事实与失败gate分开；facts仅接受成功分析结果，失败不能覆盖last_analyzed。状态写失败停止后续外部副作用。无变化/无行动的业务按其原通知约定处理。

## 邮件投递（仅适用于原任务已授权的邮件）

所有投递以issues为唯一防重账本；消费进度与投递状态分开。收件人me先解析为已连接本人实际邮箱；固定收件人沿原任务授权，不从本协议推导地址。

1. 首次prepare前读取任务既有回执和Gmail Sent。拆分/迁移任务还要检查原任务的同一期回执；发现已发送就不再发送，不因新状态为空重发。
2. issue key包括业务类型、原始期次（Asia/Shanghai）和实际收件人；分part业务另加part。恢复保持原期次，不使用恢复当天替换。
3. prepare提交实际HTML body、recipient、subject、date和manifest。保存prepared artifact路径与SHA-256；同key返回旧issue，必须复用其artifact/manifest，不重选或重写正文。
4. posting只接受prepared，持久化成功才调用Gmail。send返回非空message ID立即receipt。实际发送最多一次。
5. posting跨轮或超时先recover为maybe_sent，禁止盲发。用实际收件人、原issue日期、完整subject查Sent，读取实际MIME解码HTML；仅唯一匹配的message ID、路由字段和body hash才能补receipt。没有body、日期不明、多候选或查无结果均保留maybe_sent并报告人工核对。
6. hash统一为解码后字符串CRLF/CR转LF，再UTF-8 SHA-256；其他内容不改。Gmail没有hash字段。发送后按任务预算做两次独立核对，保存证据；receipt本身不证明核对已完成。

X Likes的pending.json负责条目/part消费；issues负责邮件发送。每个part先按本协议完成receipt及核对，再以同一个message ID执行mark-sent；mark-sent失败时恢复只重做本地消费确认，不重发邮件。旧pending/mark-sent回执作为防重证据保留。Harness的mail-receipt.json同理兼容，不能与issues各自发送一次。

## 预算与恢复

预算由原任务给出。普通连接器调用尽可能45秒超时；只有瞬时网络失败允许一次重试，认证、权限、余额失败停止该来源。Harness case/grade沿runner自己的240/300秒，不套45秒。调用层不能硬限时时如实记录，返回后检查总预算，不宣称已强制中断。
开始、每条/part后和远端调用前检查总时长；到限保存partial/remaining。恢复读取事实checkpoint，已完成不回滚，未完成项保留精确gate。共享state.py不代替scheduler，也不提供系统推送保证。
