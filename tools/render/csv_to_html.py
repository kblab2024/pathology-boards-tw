from __future__ import annotations

import csv
import html
from pathlib import Path


COL_WIDTHS_PCT = [9, 12, 11, 26, 16, 16, 10]


def render_cheatsheet_csv(csv_path: Path) -> str:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return "<p>(empty)</p>"

    header = rows[0]
    data = rows[1:]
    col_count = len(header)

    parts: list[str] = ['<table class="cheatsheet">']
    parts.append("<colgroup>")
    for i in range(col_count):
        w = COL_WIDTHS_PCT[i] if i < len(COL_WIDTHS_PCT) else 100 // col_count
        parts.append(f'<col style="width: {w}%;">')
    parts.append("</colgroup>")

    parts.append("<thead><tr>")
    for h in header:
        parts.append(f"<th>{html.escape(h.strip())}</th>")
    parts.append("</tr></thead>")

    parts.append("<tbody>")
    last_group: str | None = None
    for row in data:
        row = (row + [""] * col_count)[:col_count]
        group = row[0].strip()
        if group != last_group:
            parts.append(
                f'<tr class="group-row"><td colspan="{col_count}">'
                f"<span class=\"group-label\">{html.escape(group)}</span>"
                f"</td></tr>"
            )
            last_group = group

        parts.append("<tr>")
        for idx, cell in enumerate(row):
            cell_text = cell.strip()
            if idx == 0:
                parts.append('<td class="cat-cell">' + html.escape(cell_text) + "</td>")
                continue
            if ";" in cell_text and len(cell_text) > 24:
                items = [x.strip() for x in cell_text.split(";") if x.strip()]
                inner = "".join(f"<li>{html.escape(it)}</li>" for it in items)
                parts.append(f'<td><ul class="multi">{inner}</ul></td>')
            else:
                parts.append(f"<td>{html.escape(cell_text)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")

    return "".join(parts)
