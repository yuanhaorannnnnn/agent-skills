# Archive mode

`$breach --archive <manifest.json>` 或“把这份材料包做成档案调阅页”进入 `archive` 路由。只有当前上下文唯一、明确的材料包时可省路径；没有输入或有多个候选时请用户指定，不自动调用dossier建档、检索或补证。“调取XX的档案”先由dossier只读定位，随后默认把已登记manifest、索引及包外输出路径交给本路由展示；用户要求仅原文/路径时不渲染。Breach不自行定位、更新或注册原档。

## 输入与职责

读取 [dossier材料契约](../../dossier/references/material-contract.md) 的 v1 manifest：身份、入口、有序materials、sources、gaps。原文内容与已有Thread/Tree/Graph关系归上游所有。不得新造结论、补材料、改顺序的语义、制造密级/遮黑/照片。

**唯一输入是由dossier登记、并通过dossier gate的标准材料包。** 不接普通Markdown、任意JSON、临时材料清单或仅伪装成manifest的文件。旧版卷宗也必须先由dossier完成标准化更新与登记；breach不能自行转换、补字段、迁移、注册或绕过检查。

renderer必须显式接收上游身份索引`--catalog`，调用dossier自己的只读gate，核对ID、scope、标题/aliases、manifest精确路径与材料/来源引用。Skill入口从已有dossier交付确定manifest和索引；缺少任一项时停在选择输入，不自行搜索/建立档案。这个validator是工具依赖，不是调用dossier重新建档。

## 确定性渲染

需已安装同仓库dossier（只使用其validator），以及已有Python包 `markdown-it-py`（Markdown解析，禁用raw HTML）。缺失时明确报告依赖；不静默改用自由摘要或新增解析器。

```bash
python3 <skill-dir>/scripts/render_archive.py --archive /absolute/package/manifest.json \
  --catalog /absolute/canon/artifacts/dossier-index.json \
  -o .proposal/archive/<dossier-id>/index.html
```

`--archive`是skill模式参数，也是本renderer的真实CLI参数。其他模式继续走原入口；它们不因新增archive而改变。

先读 [Archive视觉规范](../assets/archive-DESIGN.md) 和随skill保存的 [精选样图](archive-visual/index.md)，再用 `assets/archive.html` 确定性渲染。默认封套依据用户认可的苏联卷宗：布脊、双框、后贴归档签与淡紫登记印迹；内页依据真实文书的阅读层级。模板使用独立封套→摊开卷宗/材料缩略页→抽出单张文书的三个场景，不采用三栏网页。保留原图放大、来源登记、证据缺口、键盘与低动效。正文16px，默认扫描效果作用于文字/图片的页面呈现，提供清晰版切换；原图字节与源文件不变。不新造密级、历史登记事件或人物照片；用户明确要求的模拟涂黑只属于可撤销视觉层，工具栏标明，清晰版恢复原文，不冒充原件删节。

此路由读取自己的bundled视觉规范，不走General page的layout/style自由选择，不覆盖项目DESIGN.md。改模板时同步更新视觉规范的参数和对应原图依据，并重新验收；渲染回执同时记录规范hash。

Markdown保留标题、列表、表格、引用和代码；Mermaid/Graph代码先完整可读保留，不将代码块冒充已绘制的关系图。代码/JSON/文本附件保持原文；安全raster图片原字节嵌入。其他附件显示身份/路径，不伪装为已预览。远程资源只显示链接，renderer不联网抓取。

## 读取与输出边界

- 源包与索引只读。包内路径不能越界；包外只读取manifest显式登记、被材料引用的source，Markdown中的任意链接不会扩大文件读取范围。
- 拒绝重名材料/来源ID、悬空引用、未登记的越界读取与损坏schema。被实际嵌入的来源有sha256时必须匹配；不匹配交回上游更新，不刷新hash。
- missing/unread来源显示状态，不读取正文。partial来源显式显示登记的读取范围；完整文档预览不自动更改其历史证据状态。
- 输出必须在材料包之外，不能覆盖输入文件；生成独立HTML与相邻`.render.json`清单，记录manifest、上游索引、dossier gate结果、template与实际读取文件hash。原始来源保留位置。
- HTML无运行时第三方依赖；外部链接需用户点击；本地链接展示路径，不声称浏览器已打开原件。不把任意输入作为脚本或可执行HTML。

## 验证与交付

运行renderer相关测试；对每次实际artifact revision做一次desktop/mobile浏览器检查，覆盖开/收封套、全部材料、来源、缺口、图片（有则检查）、键盘、低动效和溢出。核对源包前后hash一致。最终交付HTML与限制；来源内容不作重新写作时paperwork=skipped。

provenance记录`route=archive`、manifest/template路径和hash；telemetry用`route=archive`，`style=archive-template`，`prose=faithful`，实际填写render/visual-check状态。语义缺失交给上游，不由renderer补全。
