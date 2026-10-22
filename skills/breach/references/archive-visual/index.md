# Archive visual references

Archive模式的精选视觉参考，随Breach一起保存。修改封套先看苏联卷宗与Fallout图；修改内页先看CIA报告正文与用户电报；涉及照片/身份字段时再看证件。确定性渲染直接使用模板，无需每次重新搜索图片。

| 本地样图 | 观察重点 |
|---|---|
| [soviet-jacket.jpg](soviet-jacket.jpg) | 封套主参考：布脊、双框、后贴签、淡紫印迹 |
| [fallout-team-file.jpg](fallout-team-file.jpg) | 封套与内页形成统一材料包 |
| [cold-war-evidence.png](cold-war-evidence.png) | 材料背景与当前对象的聚焦关系 |
| [cia-iraq-p01.png](cia-iraq-p01.png) | 报告封面：编号、标题、页边登记 |
| [cia-iraq-p06.png](cia-iraq-p06.png) | 白纸正文：层级、留白、页码 |
| [user-cia-cable.png](user-cia-cable.png) | 黑白电报：规则线、文字密度、批注 |
| [user-identity-card.png](user-identity-card.png) | 证件：照片、印刷字段、手写字段与骑缝印 |
| [user-soviet-decree.png](user-soviet-decree.png) | 正式文书：抬头、留白、签署区 |

## 使用边界与维护

- 用户明确认可苏联封套的补贴签与长期调阅层次；当前正文用白/灰白纸。外观偏好不能升级为档案事实。
- 先看相关原图，再对照 [archive-DESIGN.md](../../assets/archive-DESIGN.md) 修改 [archive.html](../../assets/archive.html)。样图仅作为参照，不直接混入业务材料。
- 三张`user-*`是用户提供的原图，最初发布来源未独立核实；CIA两页是原PDF渲染，其余图保留下载原字节。
- 出处URL、用途、SHA256、PDF页码与派生关系统一见 [sources.json](sources.json)。来源图片不代表授予再利用许可。
- 更换参考时同步来源清单、设计规范的对应依据，验证本地文件/hash和相对链接。修改模板才需重新做视觉验收。
- 完整PDF、候选资料与调研过程由原Wiki调研目录保留，位置可从Canon的`breach-archive`任务追溯；它们不是skill运行或修改模板的必需依赖。精选图通过复制归入，原始调研文件没有删除。

## CIA Reading Room 原件参考 — 2026-10-22

官方附件本次均跳回首页，以下PDF从Internet Archive对应Reading Room记录取得。文档编号经扫描页核对；不宣称与当前官方文件字节一致。完整PDF保存在Wiki调研目录，精选页随skill离线保存。只参考文书形态，不移植机构、密级、签名、删节理由或历史事实。

- [cia-memo-p01.png](cia-memo-p01.png) — CIA-RDP80B01676R001300080017-4，PDF第1页；备忘录：左对齐主题、窄行距、较宽页边。
- [cia-lightning-p01.png](cia-lightning-p01.png) — CIA-RDP79B01709A002100070003-0，PDF第1页；字段行与正文分层，删节有留白框。
- [cia-grading-p01.png](cia-grading-p01.png) — CIA-RDP78-04864A000100060013-0，PDF第1页；表单：无填色细黑框、独立字段、边缘扫描噪点。
- [cia-zhou-cover.png](cia-zhou-cover.png) — C06928140，PDF第1页；周恩来人物报告封面：标题层级与留白。
- [cia-zhou-brief.png](cia-zhou-brief.png) — C06928140，PDF第4页；人物简报：首行缩进、窄行距、灰色复制底纹。
