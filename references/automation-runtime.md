# Automation execution and delivery contract

任务 prompt 持有业务范围、收件人、预算和执行时刻；本文件只定义共享机制，不授予任何新增发送或写入权限。所有业务日期、周/月窗口和用户指定时刻统一 Asia/Shanghai（UTC+08:00）。不能把服务器UTC小时当北京时间。调度变更通过 automation_update，并将实际 next_run_nominal_at/next_run_at 转为东八区核验；不直接改 scheduler 数据库。

## 定期视觉成果

仅当任务实际需要视觉设计时，沿用用户选定的系列方向和具体参考；新建系列先选并观察一个适合内容与媒介的真实参考，整体学习其构图、字级和节奏，记录来源与适配，不强制把版式和风格拆开混搭。具体规则由 Cover / Breach 或该成果的生成 skill 承担；适配邮件客户端与实际内容，渲染和设备未验证时明确记录。视觉改版只影响新产物，不更改已经冻结的 prepared/pending，也不构成发送或恢复暂停任务的授权。

## 本地状态与业务结果

调度唤醒时间与名义时间可能不同。先核对本次调用的实际期次、适用日和防重状态；已确认属于本期的提前唤醒不应仅因未到整点就记 no_op 并退出，也不能假定整点还会再次触发。先推进独立准备；如果任务要求外部动作不得早于指定时刻，在同一轮内等到该时刻再执行，等待计入原预算。无法在原预算内完成时保留产物与具体原因，不新增唤醒任务、不改排期，也不因此绕过原验收或重发。

### 本地预览的启动顺序

适用于普通对话和自动任务。恢复契约版本：`iab-owner-route-v2`（2026-11-12）。

`Browser is not available: iab` 表示当前调用未发现内置浏览器，不能直接判断为权限拒绝或永久不可用。已观察到工具调用早于该对话的窗口归属绑定；2026-11-12 一例缺少绑定约197秒，窗口侧同步后后端仅用2毫秒就绪。时间经过本身不建立绑定；不能承诺固定等待即可修复。`Local browser access is unavailable for this chat`、站点拒绝和协议拒绝分别处理，不用本流程绕过。

1. 用当前官方浏览器入口检查 inventory；没有入口时记录工具缺失，不假称调用失败。缺少 iab 时继续原任务内独立内容准备，保存实际产物和防重状态。
2. 已有待验收产物时，可用 `open_in_codex` 在**调用对话自身**打开已授权且仍存活的本地 HTTP 预览，再用同一官方浏览器入口有限复查一次。该调用是正式打开请求，不是保证成功的初始化接口；`queued` 可能一直等待对话在原窗口显示。不得借用别的对话身份或后台 socket，不能把 queued、别的对话成功或日志中的 ready 当本任务验收。
3. iab 出现后打开本任务实际页面，完成原定关键交互。分别记录 inventory、页面打开、交互结果；若出现 `Frame with the given id was not found` 等后续错误，单独记录页面/帧故障，不回写成 iab 未注册。仍不可用则保留产物及精确 gate，停止机械重试，保留原验收与预算。
4. 后续自然续跑或新的实质恢复证据允许再次有限核验，不等用户重复提醒。治理侧按问题、版本与目标记录发送/接收/采用/效果；同版无新证据不催促，不恢复暂停/归档任务。

OMP 备用补充（`omp-browser-fallback-v1`，2026-11-13）：正式浏览器入口缺失或暂不可用，且上述有限恢复仍失败时，在当前任务已授权范围内按 [OMP 浏览器备用入口](omp-browser-fallback.md) 切换，不等用户再次提醒；明确访问拒绝、站点或协议拒绝不适用。保留原产物验收、预算和防重，记录实际调用版本、模式、工具事件、原任务结果与清理证据；备用任务成功不代表 Codex 原故障修复。用户已选择扩展保持启用，relay 仅任务期间运行；busy 不抢占。没有适用故障时等待自然工作，不制造测试或恢复旧业务。

排查时按同一 session 的失败、owner sync/captured route、backend startup ready 及最终工具回执关联。浏览器发现会探测其他会话的后端，单独一条 `No ChatGPT browser route...` 可能只是未匹配候选；成功 inventory 之后不能据此断言复发。应用侧根治需要在具有可信窗口归属的任务启动/接管路径完成绑定并等待就绪，保留会话隔离与权限检查；当前工作流只缓解提前退出，不代表客户端已修复。证据见 Canon `raw/update-cards/20261105-cross-thread-friction-pilot.md` 的 2026-11-12 根因续查。

工具位于本文件所属 agent-skills 仓库的 scripts 目录：`python3 <agent-skills-repo>/scripts/automation_state.py --directory <CODEX_HOME>/automations/<id> <action> --input <JSON文件>`。状态继续使用现有 reliability-state.json；不迁移或清空旧items/issues/months/facts。输入用JSON文件，禁止把HTML或业务文本拼进shell命令。

先在该 automation 的本轮产物目录实际写入输入 JSON，并回读确认可解析，再调用 `--input`；不要只在命令中引用尚未创建的 `/tmp/*.json`。运行状态写入失败时，保存原业务错误与写入错误，修复本地输入后只补记同一 run 的真实状态；不得因此重复 API 请求、发送、消费进度或其他业务副作用。

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

## 钉钉文档交付终点

所有已授权的钉钉文档输出遵循 `/home/yhr/.agents/repos/agent-skills/references/dingtalk-delivery-routing.md`：先按实际协作范围选择“我的文档”或“OASIS仿真产品开发”知识库，再在目标内查找合适目录和已有文档。不是固定放个人空间，也不限两个业务目录。明确私有的周报草稿与只读同步保持原约束；路由本身不授权新增发送、通知或历史批量迁移。保留原有防重、人工内容和链接，逐份核验目标受众与权限。

## 直接付费调用

所有可能产生现金、预付或可购买额度消耗的自动任务，先执行 `paid-usage-policy.md`。本协议不新增付费授权。平台账期/本地日历月分别计算；冻结issue保持同一预算身份，分页与重试累计。余额/账单查询优先免费只读接口；不可用不以付费业务请求探测。
