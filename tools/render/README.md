# tools/render/ — 渲染管線

> Python 工具鏈：把 `handbook/*.md` 與 `handbook/*.csv` 渲染成補習班參考書風格 PDF。

## 結構

| 檔案 | 職責 |
|------|------|
| [`config.py`](config.py) | 章節版式表、配色、字型路徑、輸出目錄 |
| [`markdown_to_html.py`](markdown_to_html.py) | markdown-it-py + 引用剝除正則 + 路徑洩漏 audit |
| [`csv_to_html.py`](csv_to_html.py) | CSV → 分組寬版表格 HTML（給章節 01 用） |
| [`html_template.py`](html_template.py) | Jinja2 模板組裝（封面/colophon/divider/toc/body/back） |
| [`pdf_engine.py`](pdf_engine.py) | Playwright (headless Chromium) PDF 渲染 wrapper |
| [`render.py`](render.py) | CLI 入口，整體編排與 pypdf 合併 |
| [`requirements.txt`](requirements.txt) | 5 個 pip 依賴 |

## 安裝

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r tools/render/requirements.txt
python -m playwright install chromium
```

## 使用

```powershell
python tools/render/render.py --all        # 9 個章節 + master edition
python tools/render/render.py --file 03    # 單章節
python tools/render/render.py --master     # 只 render master
python tools/render/render.py --clean      # 清空 rendered/*.pdf
```

## 為何選 Playwright

| 選項 | 為何不選 |
|------|---------|
| WeasyPrint | 需要安裝 GTK3 系統 DLL（Windows 上 friction 大） |
| Pandoc + wkhtmltopdf | 兩個外部執行檔，wkhtmltopdf 已停止維護 |
| Pandoc + LaTeX | TeX 安裝 1-2 GB，CJK 字體配置複雜 |
| pyppeteer | 已停止維護 |
| **Playwright** | ✅ 純 pip 安裝、Chromium 自動下載、CJK 系統字體自然支援、CSS Paged Media 多數可用 |

## 渲染流程

```
1. handbook/<chapter>.md ─→ markdown_to_html.render_markdown_file
                              │
                              ├─ 引用剝除（regex 移除 "source:", "[L42]", "(出處: ...)"）
                              └─ markdown-it-py 渲染 → HTML body

2. handbook/01-*.csv ─→ csv_to_html.render_cheatsheet_csv
                              │
                              └─ 依分類欄分組 + 多值欄拆 <ul> → <table> HTML

3. HTML body + Jinja templates ─→ html_template.render_<section>
                              │
                              └─ 包入 cover / colophon / divider / body / back HTML

4. 完整 HTML doc ─→ markdown_to_html.audit_path_references
                              │
                              └─ 在 <body> 內掃路徑模式；命中即 raise

5. 通過 audit 的 HTML ─→ pdf_engine.render_html_batch
                              │
                              └─ Playwright (Chromium) print to PDF

6. 個別 section PDF ─→ render._merge_pdfs (pypdf)
                              │
                              └─ 合併成單一 chapter PDF 或 master edition
```

## 修改指引

| 想做的事 | 改哪 |
|---------|------|
| 換 PDF 配色 | `config.py:PALETTE` 與 `CHAPTER_ACCENT` + 對應 CSS |
| 改字型 | `assets/styles/02_typography.css` 的 `@font-face` |
| 改頁眉/頁腳 | `html_template.py:header_template` / `footer_template`（**不是** CSS @page）|
| 新加引用剝除 pattern | `markdown_to_html.py:CITATION_*_PATTERNS` |
| 新章節 | 在 `config.py:CHAPTERS` 追加 entry + `CHAPTER_ACCENT` 加色 |
| 改章節的橫直版 | `config.py` 該 chapter 的 `orient` 欄改 `"landscape"` 或 `"portrait"` |

## 已知限制

- **Chromium 不支援 CSS @page 的 @top-left / @bottom-right 之類規則。** 頁眉頁腳用 Playwright 的 `headerTemplate`/`footerTemplate` 帶 HTML 字串實作。
- **pypdf 對 Chromium subset embedded font 的文字抽取會亂碼**（特別是章節 01 大量 CJK），這是 pypdf 限制，PDF 本身顯示是對的。
- **CSS `target-counter()` 不支援。** TOC 頁碼是 render 流程中先 render 個別章節 → 用 pypdf 數頁 → 再 render TOC HTML。

## 路徑洩漏 audit

最重要的安全網。`markdown_to_html.audit_path_references(html)` 會：

1. 拿掉 `<head>`、`<style>`、`<link>` 區塊（避免誤判 CSS link）
2. 拿掉 `<code>`、`<pre>` 區塊（避免誤判技術範例）
3. 對剩下的部分跑正則：`(handbook|tools/render|assets|data|rendered)/...` 或單一 `*.md/*.json/*.csv` 檔名

命中就回傳 list；`render.py:_assert_clean` 任何非空 list 都 raise `RuntimeError`。

**保留**：`104-1`、`115-1-87`、`114-2` 等國考代碼不會被誤判（正則僅針對含副檔名或目錄前綴的字串）。
