# Automation execution and delivery contract

任务 prompt 持有业务范围、收件人、预算和执行时刻；本文件只定义共享机制，不授予任何新增发送或写入权限。所有业务日期、周/月窗口和用户指定时刻统一 Asia/Shanghai（UTC+08:00）。不能把服务器UTC小时当北京时间。调度变更通过 automation_update，并将实际 next_run_nominal_at/next_run_at 转为东八区核验；不直接改 scheduler 数据库。

## 本地状态与业务结果

工具位于本文件所属 agent-skills 仓库的 scripts 目录：`python3 <agent-skills-repo>/scripts/automation_state.py --directory <CODEX_HOME>/automations/<id> <action> --input <JSON文件>`。状态继续使用现有 reliability-state.json；不迁移或清空旧items/issues/months/facts。输入用JSON文件，禁止把HTML或业务文本拼进shell命令。

模型由任务或所属会话配置决定，直接执行任务业务，不进行运行前模型/provider检查，不因无法自证模型身份而中止。历史prompt、运行记忆中的模型前置条件已于2026-10-24取消；业务授权、来源校验、内容安全和投递防重仍按原任务执行。以实际run/thread ID为key使用run action，分别记录：
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

## 按任务启用的完成邮件

此约定覆盖用户明确要求“这个任务完成后邮件给我”等一次性交付，不因任务耗时长、生成了文件或安装了插件而自动启用。沿用该任务已有收件人授权；当前聊天仍保留简短结果。邮件仅作单向交付，回复邮件不代表 agent 已收到指令。

- 正文按结果、关键限制、成果入口、待用户修改或决定的事项组织；未定稿醒目标注“草稿”，partial/blocked 不写成完成。没有新成果时不为通知而发信。
- 手机入口沿用已授权可访问的 HTTPS 链接；本地文件优先用合适的可阅读附件。工具不支持附件且无远端入口时，在正文给足核心结果，明确完整文件仅本机可用；不得自动公开上传或扩大共享权限，本机路径只能作代码定位说明。
- 复用上面的投递协议。一次性任务将账本放在该任务持久 artifact 目录的 mail-delivery 子目录，issue key 使用 task ID + 交付版本 + 实际邮箱；恢复沿用同一 key。授权不明确时先交当前聊天成果，不臆造收件人或发送授权。
- 准备、posting、receipt、maybe_sent 和回执核对继续使用现有 helper，不增加新服务或独立发送器。一次发送后最多两次回执核对；不能核验时保留 unverified，不为取得成功状态而重发。
- 不自动发送工作周报：仍保留钉钉私有草稿供人工修改。普通维护成功、版本更新不新增邮件；旅行等待具体出行安排。研究工具只处理明确题目，不因周报或邮件需求启动无界搜索、付费补额或全年监测。

## 预算与恢复

预算由原任务给出。普通连接器调用尽可能45秒超时；只有瞬时网络失败允许一次重试，认证、权限、余额失败停止该来源。Harness case/grade沿runner自己的240/300秒，不套45秒。调用层不能硬限时时如实记录，返回后检查总预算，不宣称已强制中断。
开始、每条/part后和远端调用前检查总时长；到限保存partial/remaining。恢复读取事实checkpoint，已完成不回滚，未完成项保留精确gate。共享state.py不代替scheduler，也不提供系统推送保证。
