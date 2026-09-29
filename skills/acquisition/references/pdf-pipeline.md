# Acquisition route: pdf pipeline

## PDF 管线

### Step P1: 获取 PDF

**远程 URL**：curl 下载
```bash
curl -sL "PDF_URL" -o /media/yhr/2T/files/wiki/raw/papers/<slug>.pdf --connect-timeout 15
```

**本地文件**：直接使用已有路径。

### Step P2: 提取文本

```bash
python3 -c "
import fitz
doc = fitz.open('/media/yhr/2T/files/wiki/raw/papers/<slug>.pdf')
for page in doc:
    print(page.get_text())
" > /media/yhr/2T/files/wiki/raw/papers/<slug>.txt
```

依赖 `pymupdf`（`pip install pymupdf`）。

### Step P3: 蒸馏 → 结构化笔记

读取 `raw/papers/<slug>.txt`，按 [蒸馏规则](../SKILL.md#蒸馏规则) 生成笔记 → `queries/<YYYYMMDD>-<slug>.md`。

PDF 通常篇幅较长（10-50 页），蒸馏时注意：
- 先通读全文提取核心论点框架，再填充细节
- 保留原文的关键数据/表格/数字
- 示例代码完整保留
