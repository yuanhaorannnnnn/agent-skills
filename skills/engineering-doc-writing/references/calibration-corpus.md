# Technical Writing Calibration Corpus

## 用途

这是一组用于校准技术文档结构、信息密度、证据关系和作者判断的原文。它不是语言风格模板，也不是“名人文章摘抄”。

每次由 skill 路由到本目录时，选择与当前文档任务、读者和技术深度相近的 1—2 个样本。抽取可观察的写作行为，再回到当前项目事实中重写；不要复制句子、口头禅、标题形式或作者的个人经历。

## 选择规则

1. 先按文档任务选样本，再按作者名气选样本。
2. 优先使用原作者、官方团队或原始项目页面；转载只用于发现线索。
3. 每次校准只选择少量样本。混合过多文体会把差异误判为通用规则。
4. 记录样本的适用文体和不可迁移部分。博客文章可以有个人口吻，客户报告不必复制这种口吻。
5. 参考文档只校准组织方式和判断方式，不替代当前项目的事实、数据、接口和证据。

## 按文档任务选择

| 当前任务 | 优先样本 | 观察重点 |
|---|---|---|
| 机制说明 | 阮一峰 DNS、Julia Evans debugging | 从具体现象或命令进入；逐步建立模型；让抽象概念落到可观察行为 |
| 评价 / 验证 | CoolShell 性能测试、Brendan Gregg methodology | 先定义问题和边界；指标服务于问题；区分测量、解释和行动；明确何时停止或继续 |
| 设计 / 架构 | 美团无人车引擎、Martin Kleppmann logs | 由真实约束引出方案；用系统演化解释复杂度；把取舍写成因果关系 |
| 事故 / 复盘 | Cloudflare postmortem、Google SRE postmortem culture | 分开预期设计和实际行为；按时间和证据组织；标记推测；行动项针对系统缺口 |
| 工程变更 / 发布 | Simon Willison feature、release notes | 把 issue、实现、测试、文档和发布关联起来；给读者可执行入口和可追踪证据 |

## 中文样本

### CoolShell / 陈皓：由 12306.cn 谈谈网站性能技术

原文：[coolshell.cn/articles/6470.html](https://coolshell.cn/articles/6470.html)

适合校准评价和性能分析。文章先从订票业务的访问模式、一致性要求和峰值负载解释问题，再进入前端、后端和数据层。可迁移的规律是：性能结论必须绑定 workload 和业务约束；方案按瓶颈位置展开；数字用于说明量级和因果，而不是装饰结论。

不要迁移的部分：文章是基于个人经验的公开讨论，部分数据和判断需要按原文语境理解，不能当作当前项目的实测证据。

### CoolShell / 陈皓：性能测试应该怎么做？

原文：[coolshell.cn/articles/17381.html](https://coolshell.cn/articles/17381.html)

适合校准测试报告和指标解释。文章先指出平均值、吞吐量、响应时间和成功率之间的断裂，再提出更严谨的测试组织方式。可迁移的规律是：先指出指标为什么不能单独回答问题，再说明指标之间的关系和测试条件。

不要迁移的部分：作者的批评性口吻和具体测试标准不能自动成为所有项目的验收标准。

### 美团技术团队：美团无人车引擎在仿真中的实践

原文：[tech.meituan.com/2020/11/27/self-driving-in-simulation-system.html](https://tech.meituan.com/2020/11/27/self-driving-in-simulation-system.html)

适合校准系统设计和仿真实践。文章先区分车载环境与离线仿真的运行条件，再提出无人车引擎作为隔离差异的系统边界，后续设计围绕这个问题展开。可迁移的规律是：不要从组件名或技术热词开始；先写运行环境之间的差异，再写设计如何吸收差异。

不要迁移的部分：行业背景、公司规模和具体架构不能移植到没有相同约束的项目。

### 阮一峰：DNS 查询原理详解

原文：[ruanyifeng.com/blog/2022/08/dns-query.html](https://www.ruanyifeng.com/blog/2022/08/dns-query.html)

适合校准机制说明。文章用一个域名和 `dig` 命令作为主线，从用户可见操作逐步展开到根域名、TLD、权威服务器和递归服务器。可迁移的规律是：保持一个贯穿全文的具体对象；每引入一个抽象名词，都说明它在当前过程中的作用；示例必须能验证前文。

不要迁移的部分：面向入门读者的完整背景铺垫不适合直接放进面向专家的设计或验证报告。

## English samples

### Martin Kleppmann: Using logs to build a solid data infrastructure

原文：[martin.kleppmann.com/2015/05/27/logs-for-data-infrastructure.html](https://martin.kleppmann.com/2015/05/27/logs-for-data-infrastructure.html)

适合校准架构推理。文章从简单的 web app 和 database 开始，随着缓存、搜索、图索引和消息队列的加入展示复杂度如何产生，最后提出 log 作为数据同步边界。可迁移的规律是：让方案由问题的演化自然推出；用简单模型建立共同起点；每个设计选择都对应一个已暴露的失败模式。

不要迁移的部分：博客中的“我认为”和个人偏好不是项目决策；观点不能替代本项目的约束和验证。

### Brendan Gregg: Performance Analysis Methodology

原文：[brendangregg.com/methodology.html](https://www.brendangregg.com/methodology.html)

适合校准性能分析、实验设计和验证报告。文章把问题陈述、workload、指标、实验、分析和停止条件组织成方法，并同时展示常见的反方法。可迁移的规律是：定义系统边界和问题，再选指标和实验；不要从 dashboard 或结果表倒推问题；分析应有收敛条件。

不要迁移的部分：USE、RED、TSA 等方法属于性能分析工具箱，不是所有技术文档都要出现的章节或术语。

### Cloudflare: Post mortem on the Cloudflare Control Plane and Analytics Outage

原文：[blog.cloudflare.com/post-mortem-on-cloudflare-control-plane-and-analytics-outage](https://blog.cloudflare.com/post-mortem-on-cloudflare-control-plane-and-analytics-outage/)

适合校准事故报告和可靠性复盘。文章先写 intended design，再对照实际故障、依赖关系、影响、恢复和改进；对未确认部分明确标记为 informed speculation。可迁移的规律是：预期行为和观察行为分开；事实、推断和行动分层；改进项对应具体系统缺口。

不要迁移的部分：公开事故报告的道歉、客户沟通和组织语境，不应机械加入普通技术报告。

### Google SRE：Postmortem Culture

原文：[sre.google/workbook/postmortem-culture](https://sre.google/workbook/postmortem-culture/)

适合校准事故文档的读者对象和长期价值。Google 把 postmortem 定义为写给未来团队成员的信，要求记录影响、响应过程、做得好的地方、改进点和可执行的 action items。可迁移的规律是：复盘不是为事故写一个结论，而是让后来的人能够理解系统如何失效、当时如何判断以及哪些措施会改变下一次结果。

不要迁移的部分：Google 的组织文化和 SRE 术语不是所有团队的强制流程；只保留适合当前读者和事故范围的内容。

### Julia Evans: How I got better at debugging

原文：[jvns.ca/blog/2015/11/22/how-i-got-better-at-debugging](https://jvns.ca/blog/2015/11/22/how-i-got-better-at-debugging/)

适合校准面向工程师的解释和经验总结。文章用具体 bug、工具和观察描述如何形成排查习惯，而不是先给一套抽象方法论。可迁移的规律是：用一个真实问题承载观点；让工具、观察和判断连续出现；承认不知道什么以及什么证据改变了判断。

不要迁移的部分：个人经历、幽默和第一人称口吻适合博客，不代表客户交付文档应该口语化。

### Simon Willison: How I build a feature

原文：[simonwillison.net/2022/Jan/12/how-i-build-a-feature](https://simonwillison.net/2022/Jan/12/how-i-build-a-feature/)

适合校准工程变更、开发记录和可追踪交付。文章把 issue、开发环境、测试、实现、文档、commit、release 和 demo 串成一条可回溯链路，并展示测试如何先失败再通过。可迁移的规律是：文档不是开发结束后的装饰；每个结论都尽量有对应的代码、测试、issue 或可运行结果。

不要迁移的部分：个人工作习惯不自动成为团队流程；只保留当前读者确实需要的追踪信息。

## 抽取表

阅读样本时只记录以下内容：

| 观察项 | 要问的问题 |
|---|---|
| 入口 | 作者从读者已经遇到的什么问题、现象或决定开始？ |
| 对象 | 全文真正的主语是什么？有没有被参数、工具或指标替代？ |
| 关系 | 内容按因果、时序、对比、层级还是证据关系展开？ |
| 证据 | 哪些是观察，哪些是推断，哪些是判断？作者如何标记它们？ |
| 粒度 | 何时给数字、代码、图、公式或例子？何时停止解释？ |
| 取舍 | 方案放弃了什么，代价是什么，为什么仍然选择它？ |
| 结尾 | 读者最后得到的是结论、操作、决策、验证门槛还是开放问题？ |

最终只把跨样本、能改变写作决策的规律写回 Skill。不要把样本中的章节数量、禁词、语气或个人习惯变成新模板。
