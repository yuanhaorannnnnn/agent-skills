---
name: software-study
description: |
  深入学习一个软件、仓库、开发工具、平台或产品，建立可持续更新的 Study Hub，
  用官方文档、源码实现和本机运行三类证据回答"它是什么、怎么工作、问题在哪"。
  触发于"深入学习 X"、"系统了解 X"、"建立 X 的学习路线"、"study this repo/product"、
  "帮我搞懂这个工具"。
  不用于单篇文章/论文/课程/知识库摄入（用 acquisition），不用于一次性问题或直接改代码（用 execute）。
metadata:
  version: "0.1.0"
---

# Software Study

把"软件"当成有版本、有源码、有运行时的可操作对象来学，而不是把官网页面归档一遍。

核心产物是一个持续更新的 Study Hub，连接：官方来源地图、版本边界、架构模型、源码证据、实践证据和掌握矩阵。

## 与 acquisition 的边界

| 对象 | 使用 | 产物 |
|---|---|---|
| 文章、论文、课程、知识库、资料合集 | `acquisition` | raw + query + collection Hub |
| 软件、仓库、开发工具、平台、产品 | `software-study` | Study Hub + 来源/版本清单 + 架构模型 + 源码证据 + 实践证据 |

判断依据不是"输入是不是很多网页"，而是学习目标：网页是内容主体，还是软件的其中一层证据。

## 六类状态

1. **学习目标** — 使用 / 理解架构 / 二次开发 / 性能调优 / 长期维护。目标决定深度和要读的源码。
2. **官方来源地图** — 官网文档、repository、examples、API reference、architecture docs、release notes、issues。第三方材料只用于解释和发现线索，不作为规范性结论。
3. **版本边界** — 本机版本、官方文档时间点、源码 commit/branch。版本变化时更新清单，不把当前结论无条件外推。
4. **Study Hub** — 整体架构、资料规模、阅读顺序、各模块状态、子 query 链接、未解问题。
5. **证据等级** — 官方文档=产品主张；源码=实际实现；示例/测试=预期行为；本机实验=当前环境可复现证据。四类分开记账。
6. **掌握 Gate** — 能画出系统结构、能解释核心数据流、能定位关键代码、能运行最小示例、能修改一个行为并验证、能说明适用边界和主要失败模式。

## 工作流

### 1. 钉住版本与范围

先确认本机版本、官方仓库 commit、文档时间点，写进来源清单。范围不明时先问清学习目标。

### 2. 盘点官方来源

优先官方 sitemap、docs、repository、examples。用 `acquisition` 的脚本做来源身份检查和 raw 归档，不复制一套抓取实现：

```bash
python ~/.agents/skills/acquisition/scripts/source_identity.py --wiki-root <wiki-root> --url "<url>"
python ~/.agents/skills/acquisition/scripts/extract_article.py "<url>" --save-raw --wiki-root <wiki-root>
```

### 3. 建模对象

先回答组件、状态所有权、关键生命周期，再整理功能清单。不要从功能列表倒推架构。

### 4. docs → source → runtime 三角验证

对每个关键结论标注证据来源。缺运行时证据时标记 pending，不用官方宣传替代。

### 5. 能力矩阵

记录"会用、会解释、会诊断、会扩展"分别到哪一步，并给出下一步证据。

### 6. 按需拆专题

只在真实问题出现时拆 `queries/YYYYMMDD-<software>-<topic>.md`，避免把全部官方文档机械改写。

## 产物

```text
queries/YYYYMMDD-<software>-study-hub.md               # 主 Hub
raw/collections/YYYYMMDD-<software>-study-sources.json # 来源/版本清单
raw/articles/...                                        # 官方页面归档
queries/YYYYMMDD-<software>-<topic>.md                  # 按需专题
.research/<software-study>/                             # 实践证据（命令、结果、截图）
```

Hub 最小结构：

```markdown
---
title: "<software> 软件学习 Hub"
created: <date>
type: query
sources: [<raw refs>]
source_url: "<official home>"
confidence: <high|medium|low>
---

## 学习目标
## 一句话模型
## 版本边界
## 官方文档规模
## 文档到源码映射
## 当前环境边界
## 学习进度 / 掌握矩阵
## 阅读讨论
## 来源
```

来源清单记录：`subject`、`study_type`、`official_home`、`official_repository`、`installed_version`、`source_snapshot`（commit/version/文件数）、`documentation_inventory`、`archived_official_pages`、`evidence_state`。

## 完成标准

- Hub 存在且钉住版本、commit、文档时间点。
- 关键结论有 docs/source 证据标注，runtime 证据区分已验证与 pending。
- 掌握矩阵有明确状态和下一步证据。
- 链接、索引、日志、catalog 通过 wiki 门禁。

## 边界

- 不把"资料读完"当作"学会了"。
- 不把官方宣传或第三方转述当作源码/运行事实。
- 不在未获授权时修改、编译或运行目标软件；先给只读证据和最小 PoC 计划。
- 大站点先建立来源规模清单和导航，不先全量下载。
