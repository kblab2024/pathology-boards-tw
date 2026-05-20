---
description: Render every handbook chapter to PDF + the Master Edition, then audit for path leaks
---

執行完整 render：

1. 確認 venv 存在；若沒有，建立並安裝依賴：
   ```
   py -3.11 -m venv .venv
   .venv\Scripts\python.exe -m pip install -r tools/render/requirements.txt
   .venv\Scripts\python.exe -m playwright install chromium
   ```

2. 跑全 render：
   ```
   .venv\Scripts\python.exe tools/render/render.py --all
   ```

3. 驗證 `rendered/` 有 11 個 PDF（00 至 09 + master edition）。

4. 對 master edition 做路徑洩漏 audit：
   ```
   .venv\Scripts\python.exe -c "from pypdf import PdfReader; import re; r=PdfReader('rendered/00-master-edition.pdf'); t='\n'.join(p.extract_text() or '' for p in r.pages); leaks=re.findall(r'(?:handbook|tools/render|assets/styles|data/)[\w./-]*|[\w-]+\.(?:md|json|csv)(?![\w])', t); print('LEAKS:' , leaks[:5] if leaks else 'NONE — OK')"
   ```

5. 報告各 PDF 頁數、總大小，並指出若 audit 有 leak。

最後提示使用者可以打開 `rendered/00-master-edition.pdf` 視覺檢查。
