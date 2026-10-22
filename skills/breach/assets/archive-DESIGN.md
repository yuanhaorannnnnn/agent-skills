---
version: 2
name: Physical Dossier — Reference Reconstruction
description: 苏联卷宗封面定构图，影视卷宗定材料组织，CIA文书定阅读形态。封套、摊卷、抽页三个场景；不沿用三栏网页。
---

# Archive visual contract

本规范仅属于Archive。模板正本是同目录archive.html。先看 [精选原图](../references/archive-visual/index.md)；[出处与hash](../references/archive-visual/sources.json)随skill离线保存。改构图时必须用相同视角把原图与新稿并排比较，检查形态与信息组织，不以“包含同类CSS元素”宣称已对齐。

## 三个场景与参照

| 场景 | 具体参照 | 构图与材料机制 |
|---|---|---|
| 独立封套 | [苏联封面](../references/archive-visual/soviet-jacket.jpg) | 竖向约0.69宽高比；深灰布脊占宽8%；灰米色纸板；偏淡的旧印刷双框；上方机构抬头、中段大标题、下方手填字段；较新的灰绿归档签倾斜覆盖底部旧框和字段。原印、紫色登记印、手写档号与贴签分别成层，不排成整齐UI卡片。 |
| 摊开卷宗 | [Fallout团队卷宗](../references/archive-visual/fallout-team-file.jpg) | 封套打开成左右纸板，左侧夹住一张白色卷内目录；右侧材料各自保持纸页身份，轻微错位、搭叠，有夹子与纸边。点击材料是“抽出”，不是切换三栏内容。缩略页来自同一dossier实际材料，不能填示例照片。 |
| 抽出阅读 | [CIA电报](../references/archive-visual/user-cia-cable.png)、[评估正文](../references/archive-visual/cia-iraq-p06.png) | 单张白/灰白纸居中；粗细规则线、档号/材料号、居中抬头、框内主题、正文与底部来源。正文用宋体/衬线文字，英文代码用等宽；没有左右信息栏。来源/缺口可单独调阅。 |

补充的[证件](../references/archive-visual/user-identity-card.png)和[正式文书](../references/archive-visual/user-soviet-decree.png)用于照片/字段和签署区分工；只有上游确有这些材料才呈现。用户图最初发布来源未独立核实。纸页背后的相邻材料轻度失焦；[Cold War](../references/archive-visual/cold-war-evidence.png)只参考聚焦关系，不复制游戏菜单或图标。

## Tokens / proportions

```yaml
colors:
  desk: '#292c2b'
  jacket: '#c9ad72'
  cloth: '#4f5551'
  registry-label: '#dedfd3'
  paper: '#fbfbf9'
  ink: '#323431'
  faded-print: '#606756'
  stamp: '#73617d'
geometry:
  closed-jacket: max-width 530px; min-height 735px; rotation -1.3deg
  cloth-spine: 43px desktop; 30px mobile
  later-label: bottom 28px; left 49px; right 63px; rotation -3.5deg
  open-folder: max-width 1160px; left 40%; gap 45px
  withdrawn-sheet: max-width 790px; padding 31px 49px 45px
  material-thumbnails: 2 columns; 320px height desktop; 195px mobile; rotations +2/-3/-1deg
text:
  closed-title: 36px serif; mobile 29px
  subject: 17px serif
  registry-id: 41px monospace; mobile 34px
  document-body: 16px serif; line-height 1.95
  document-title: 25px serif; mobile 22px
  document-metadata: 10–11px monospace
focus:
  adjacent-material: blur 1.7px desktop / 1.3px mobile
  thumbnail-copy: blur 0.65px; inert; aria-hidden
  selected-original: aged scan by default; clear-copy toggle removes filters
```

## 内容与质感边界

- 封套与贴签的id/scope/as_of/count全来自标准dossier。同一信息重复出现在原字段和新签可以形成物理层次；不编造登记年份、调阅次数、机构密级、签名或历史事件。
- “卷宗登记”“来源登记”表示当前已有登记，不表示官方批准/全部来源已读。缺口保持完整，来源read_status不因预览升级。
- 封套的旧感集中于褪色印刷、灰米纸板、布脊、折线和标签覆盖。模板使用程序纸纹，不把带有原案号/人物身份的历史图当背景。
- 当前白纸正文不整体泛黄；默认按用户要求呈现扫描失焦、复印颗粒与墨迹扩散，可切清晰版。实际原件已有遮黑/印章则保持；没有遮黑字段，不制造装饰黑条。
- 摊卷的缩略页和背后失焦页都是真实panel的只读视觉副本，inert且aria-hidden；抽出时始终显示原始panel。无照片的档案不塞历史照片。
- 不使用dashboard、侧栏、徽章KPI、霓虹、玻璃卡片或终端绿替代文书形态。控制按钮位于材料外缘，不包装成业务内容。

## 对照与验收

交付时保留原图/新稿并排对照，至少包含：苏联封套vs新封套、CIA电报vs新内页；同时给出实际打开卷宗的画面。核对封套整体比例、框/章/签的不对称关系；内页是否真实以白纸和文书抬头组织，而非网页加米色背景。

每个artifact revision做一次desktop1440×1000/mobile390×844批量检查：调阅封套→摊卷、目录与六材料卡片、抽出每份材料、放回、合卷、来源、缺口、图片fixture、键盘、低动效、横向溢出。逐个核对原始article内容和输入hash保持。

测试仅证明行为/内容边界；主agent必须查看截图并与原图比较。最终审美由用户判断，不以测试数量代替。

## Paper and surrounding scene — 2026-10-21

用户要求主动加强纸张质感与阅读背景的故事感。当前白纸增加低对比纤维、局部压折、边缘磨损、右上小折角、装订孔和细微墨迹差异。痕迹属于物理材质，不伪造签名、历史或内容遮蔽。实际原图不经滤镜。

抽页时，桌面暖灰光照；同一份已打开卷宗作为固定背景，包含真实目录与材料缩略页，失焦2.8px且略压暗。背景inert/aria-hidden，不能操作；放回时恢复原卷宗。桌边一支铅笔作为空间线索，不构造额外档案材料。白纸默认扫描效果，清晰版可切换；抽页有280ms轻微提起动效；系统/手动减少动效时停用。移动端背景缩放至690px且blur2px，不引起横向溢出。

## User correction: actual scanned content — 2026-10-21

用户明确指出希望正文和图像本身具有参考中的旧扫描效果，而不只是背景或失焦纸页。本条覆盖此前“当前正文/原图不加blur”的视觉限制。默认抽页：整张文书blur .62px（mobile .45px）、contrast1.16，印刷内容opacity .88与轻微重影、纸纹颗粒增强；图片灰度/contrast1.25/blur .85px。资料文字、出处、图片字节不变。工具栏“查看清晰版”移除这些显示滤镜，便于对照与阅读；“返回扫描效果”恢复。图片放大弹窗保留原图。用户要求的是扫描件的视觉体验，不代表源文件损坏或真的发生过扫描/解密事件。

## Strong scan distress — 2026-10-21

用户进一步要求倾斜、模糊、涂抹和错行更激进。按材料序号固定scanner-feed skewY(-.75至+.85deg)，避免长文档旋转产生巨大横向溢出。默认正文blur .9px/mobile .65px、contrast1.3；段落/短语有不均匀重影、失焦、1–3px行位偏差。沿标点拆分只为视觉位移，textContent不变，代码/按钮/链接不拆。三处半透明拖墨蹭污为inert/aria-hidden叠层；不是遮密条，不代表内容缺失。清晰版同时移除倾斜/错位/涂抹/失焦。效果固定，刷新不随机，不制造新的事实。

## Typewriter typography — 2026-10-21

用户于2026-10-21认可朝华打字机（特里王，Version1.001）实排选型。离线内嵌完整字库WOFF2，由原始TTF压缩，不按当前档案裁字；包含32465个Unicode映射，中文、英文、数字均来自该字体，罕见缺字才使用系统fallback。英文字母并非严格等宽，数字等宽；不宣称完全复刻机械字距。正文16px、字距.035em、行高2；清晰版保留该字体。作者许可允许嵌入、分发与修改，禁止将字体文件单独或打包作为字体/素材出售；许可与来源随HTML嵌入并纳入render inputs hash。选型依据：[作者发布说明](https://www.maoken.com/eyes/business/27716.html)；文件镜像BH1PHL/ttf-terrywang-typewriter-fonts，固定commit 0f49da55ecf4c1648d658c17d2e8d2633c385d0f。字体固有不规则轮廓与已有扫描模糊、错行、涂黑叠加，后者仍可由清晰版撤销。

## User-requested simulated black marker — 2026-10-21

用户明确要求加入涂黑，覆盖此前不做装饰遮黑的限制。默认扫描版在少量已有文字短语上叠加墨量不均、边缘略粗糙的黑色马克笔条；黑条随原句换行，不改变文字和来源身份。工具栏注明“模拟涂黑”，不把视觉遮挡标记为原件真实密级/删节。清晰版移除涂黑并显示原文；此效果不是真实保密处理，不能用于隐藏数据。

## Local wear and uneven stacks — 2026-10-21

用户认可视觉评议并授权优化。摊卷保留DOM与目录顺序，以六份为周期改变纸页宽度、高度和旋转；局部搭叠、不同纸边厚度，仅部分材料带夹子。移动端降低搭叠，保留每份标题与点击区；hover/focus提起到最上层。参照仍为Fallout材料形态，不增加虚构附件。

此条覆盖此前整页 .9px/.65px blur：baseline desktop .16px/mobile .12px，局部段落 .55px、短语 .8px，加局部墨量衰减/重影与已有拖擦。朝华字体自身的不规则笔画保留。清晰版移除全部呈现劣化；源字节和textContent不变。模拟涂黑使用不齐上下边缘、透墨细纹与非规则圆角，仍随句换行，不假装原件删节。封套折痕改为低对比暗谷/亮边，磨损集中边缘，避免贯穿整面的白色装饰线。

## Warm yellow jacket — 2026-10-22

用户指出封套相比原图不够黄，要求改色。封套底色#c9ad72、受光面#e0c590，边缘和布脊附近叠黄褐色磨损；归档签维持#dedfd3，内页维持白纸。仅封闭封套色彩更新；用户已认可的搭叠、局部扫描效果与清晰切换不变。

## Worn jacket — 2026-10-22

封套降低黄底饱和度至#c5af7e，叠加固定seed的粗细两级斑驳；右下分叉压皱、磨白边和毛边轮廓；印刷框线与紫章采用不同尺度局部缺墨mask，贴签破边、底缘积污并与封套形成新旧差异。SVG仅生成材质，无历史文字/事件；所有文字仍是真实DOM。只编辑既有HTML的CSS，保留原材料快照及历史render receipt，额外记录增量hash。内页和交互不改。

## CIA documented inner sheets — 2026-10-22

参照新增5张精选扫描页（见archive-visual/index.md）：备忘录与周恩来人物简报用于白纸、深墨、首行缩进与较窄行距；grading sheet用于无填色表头/细黑框。正文16px/1.8，桌面左右页边62px，手机23px；第一标题左对齐、单下划线，材料元数据另列。保留朝华字库、局部失焦、用户要求的模拟涂黑和清晰版，不添加CIA标志、密级、签名或解密批准文案。官方附件跳回首页，镜像身份与读取范围明确记录。封套不改。
