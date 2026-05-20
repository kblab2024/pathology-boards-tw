# handbook/ — 教學教材原始檔

> _本目錄的所有檔案皆由 Claude Code (Anthropic) AI 整理產生。醫學內容請對照 Robbins / WHO 標準教科書查證使用。_

## 教材清單

| 章 | 檔名 | 用途 | 渲染版式 |
|----|------|------|---------|
| 00 | [`00-overview.md`](00-overview.md) | 全套導覽、教學流程、驗收標準、AI 揭露 | 直版 |
| 01 | [`01-molecular-cheatsheet.csv`](01-molecular-cheatsheet.csv) | ~150 分子標記 → 疾病 → 治療意涵速查 | **橫版** |
| 02 | [`02-mock-exam-blank.md`](02-mock-exam-blank.md) | 50 題模擬考空白卷 (114-2 + 115-1) | 直版 |
| 03 | [`03-mock-exam-key.md`](03-mock-exam-key.md) | 50 題模擬考詳解版 | 直版 |
| 04 | [`04-confusion-pairs.md`](04-confusion-pairs.md) | 30 張易混淆對比題卡 | 直版 |
| 05 | [`05-12week-syllabus.md`](05-12week-syllabus.md) | 12 週教學大綱 | 直版 |
| 06 | [`06-high-frequency-diseases.md`](06-high-frequency-diseases.md) | 歷年高頻疾病清單 + Top 30 教學優先序 | 直版 |
| 07 | [`07-ihc-marker-cheatsheet.md`](07-ihc-marker-cheatsheet.md) | IHC marker 雙向速查 + 必背口訣 | **橫版** |
| 08 | [`08-buzzword-cheatsheet.md`](08-buzzword-cheatsheet.md) | 150+ 經典 buzzword → 疾病 | 直版 |
| 09 | [`09-weak-spot-cards.md`](09-weak-spot-cards.md) | 14 張弱點補強題卡 | 直版 |

## 編輯規範

1. **必保留**：每份檔案 H1 標題下方第一個 blockquote 是 AI 揭露聲明，**不要刪除**。
2. **不要在內文新增**：`foo.md`、`(出處: bar.json)`、`[L42]` 等檔案路徑引用 — 渲染管線會擋下並 raise。
3. **可以保留**：`104-1`、`115-1-87`、`114-2` 等國考代碼 — 那是合法的題目編號。
4. **CSV 格式**：第一欄為「分類」，渲染時用作分組依據；逗號內有逗號的儲存格請用標準 CSV 引號 escape。
5. **新增章節**：依序給下一個編號（如 `10-foo.md`），然後到 [`tools/render/config.py`](../tools/render/config.py) 註冊 chapter。

## 渲染成 PDF

```powershell
python tools/render/render.py --all
# 或單檔
python tools/render/render.py --file 03
```

PDF 輸出到 [`../rendered/`](../rendered/)。
