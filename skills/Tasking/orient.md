# Orient — 情报分析与方案生成

## 预检

1. 确认当前在项目代码仓库根目录下
2. 确认 `/media/yhr/2T/yunxiao/requirements/<demand-id>/` 存在且包含 `state.json` 和 `detail.md`

## 分支管理

| 参数 | 行为 |
|------|------|
| (无) | `git checkout -b feature/<demand-id>` 从默认主分支 |
| `--base <branch>` | `git checkout -b feature/<demand-id>` 从指定分支 |
| `--branch <name>` | `git checkout <name>` 使用已有分支 |

从 `state.json` 读取需求标题作 commit 上下文。

## 情报收集

### Step 1: 加载需求文档

按顺序读取：
1. `state.json` — 获取结构化元数据（参与人、抄送人、项目、状态）
2. `detail.md` — 需求描述和全部评论历史
3. `prd.md` — PRD 文档（如有）
4. `builtin_params.csv` — 内置参数表（如有）
5. `ux_doc_paths` 指向的 UI/UX 文件（如有）

### Step 2: 分析代码库

以需求描述中的关键词为线索，在当前分支代码库中定位受影响的模块：
- 用 Overwatch 拉远看整体结构
- 定位需要修改的具体文件和函数
- 识别接口边界和依赖关系

### Step 3: 输出情报摘要

用 Markdown 输出分析结果：

```markdown
## 需求摘要
[一段话概括需求目标]

## 受影响模块
- `path/to/module1`: [改动内容]
- `path/to/module2`: [改动内容]

## 接口影响
[API/配置文件/SDK 方法变更点]

## 待确认
- [不确定的点 1]
- [不确定的点 2]
```

**关键原则**: 不确定的点必须列出来等你确认，不要自行假设后直接推进。

## 方案生成

用户确认情报摘要后，调用 CONOPS 生成技术方案：

1. 将情报摘要 + state.json 中的需求元数据传递给 CONOPS
2. CONOPS 输出到 `.proposal/<demand-id>/design.md`（默认路径）
3. 更新 `state.json`:
   - `phase`: `new` → `plan`
   - `design_doc_path`: 方案文件绝对路径
   - `participants` / `cc`: 从需求单读取（如果 Phase 0 未写入）

## 完成检查

- [ ] 分支已创建/切换
- [ ] 需求文档已全部读取
- [ ] 代码分析已完成
- [ ] 待确认清单已获用户确认
- [ ] CONOPS 方案文档已生成
- [ ] state.json 已更新
