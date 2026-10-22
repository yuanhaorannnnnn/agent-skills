# 材料包与索引

此契约用于建档模式的新建、人物分支沿原ID补充，以及更新模式的修改。调档保持源包与身份索引只读，默认展示的 HTML/渲染回执写在包外。旧版档案仍可读取，不强制迁移；不满足 Archive 输入契约时返回原档并说明展示限制。

## 包结构

```text
<id>/
  dossier.md       可独立阅读的入口，指向材料、附件、来源与缺口
  manifest.json    身份、有序材料与来源定位
  materials/      按需生成的整理稿/摘录；原始附件可留在原位置
```

入口与材料文档不强制上述文件名，但必须由 manifest 显式引用。来源只读；整理稿与原件清楚区分。核心结论在正文附 source ID/定位；manifest 不承担事实正文。

## 主题覆盖记录

建档需要新建或沿原ID补充时，先在入口或已有材料中形成覆盖表；仅复用返回既有档案时不补写。交付前按 `SKILL.md` 的覆盖复核更新；表不是固定分类模板，也不增加 manifest 必填字段。

| 主题面/工作线 | 来源线索与实际读取范围 | 已收材料或证据缺口 | 未纳入理由（若有） |
|---|---|---|---|
| 按初检发现的实际工作线填写 | 来源 ID/位置；区分已读、部分读取与仅线索 | 材料 ID/可调阅位置，或仍缺何种原件 | 例如用户限定范围；不以“非技术核心”为默认排除理由 |

来源与材料定位复用 manifest 的 ID，不复制事实正文。初检尚未读取的候选可先记线索，复核时不得算作已覆盖证据。重要未读线索仍未处置时，记录待补查与覆盖限制，不给完整覆盖结论。

表旁记录复核所对照的索引/关联任务/目录范围、结果及未覆盖项；若有单独覆盖材料，按普通 material 引用。已存在的 `gaps` 同步保留证据缺口；范围外项说明理由，不伪装成缺失原件。结构 gate 的 pass 与覆盖复核结果独立。局部更新只维护受影响项；只读调档不创建/补写本表，旧卷不因新增约定而自动迁移。

## Manifest 示例

```json
{
  "schema_version": 1,
  "id": "lidar-weather",
  "scope": "simulation/lidar-weather",
  "title": "激光雷达天气模型",
  "aliases": ["LiDAR雨雪雾", "MEMS天气建模"],
  "as_of": "2026-10-20",
  "entry": "dossier.md",
  "materials": [
    {"id": "M01", "title": "决策记录", "kind": "thread", "path": "materials/decisions.md", "sources": ["S01"]}
  ],
  "sources": [
    {"id": "S01", "path": "/resolved/source/report.md", "locator": "lines 15-60", "evidence": "original", "read_status": "read", "read_at": "2026-10-20"}
  ],
  "gaps": []
}
```

- `id`：库内唯一，lowercase kebab-case，建立后不因改名而变化。
- `scope`：稳定的语义范围。由流程判断同义/重叠，不按每次问法另起范围。
- `as_of`：本包整理截面，不能替代各材料事件日期。
- `entry`/材料 `path`：包内相对路径，禁止越出包目录；外部附件使用 `source_ref`，不能伪装包内文件。
- 每份材料含 `id/title/kind/sources`，以及 `path` 或 `source_ref` 二选一。kind 可用 brief/thread/tree/graph/excerpt/report/image/open-items 等，按内容选择。
- 来源含 `path` 或 `url` 二选一；保留可定位的页码、行号、消息 ID 或图表标识。机器绝对路径仅写实际产物，不能写入公开 skill 仓库。
- `evidence`：original / derived；`read_status`：read / partial / unread / missing。read/partial 时含 `read_at`。远程来源不由 gate 自动抓取。
- 本地 missing 来源保留身份并列入 gaps；其他已声明可用的本地路径必须存在。未读或二手来源不能支持“原件已核实”。
- `sha256` 可选，说明绑定的读取截面；不把当前 hash 说成历史签名。
- `gaps` 必须显式列出，允许空列表。关系可放在正文或按需扩展 manifest，每条边注明语义和证据，不要求统一画图。

## 身份索引

```json
{
  "schema_version": 1,
  "dossiers": [
    {"id": "lidar-weather", "scope": "simulation/lidar-weather", "title": "激光雷达天气模型", "aliases": ["LiDAR雨雪雾"], "path": "/resolved/package/manifest.json"}
  ]
}
```

旧版条目 `path` 可指向现有入口 Markdown，不必先做 manifest。ID 全库唯一；相同 scope 内标题/alias 归一化冲突必须先复用或消歧。不同 scope 的同名对象可以并存，但检索时必须展示范围。Gate 的 NFKC/casefold/空白归一化只捕获确定冲突，不能证明语义上不存在重复。

只读调档可以直接使用 Canon 原有 artifact index。专用身份索引尚不存在不阻止查找已有主题页，也不授予创建空索引或迁移权限。
