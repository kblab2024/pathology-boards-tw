from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.attrs import attrs_plugin
from mdit_py_plugins.deflist import deflist_plugin
from mdit_py_plugins.footnote import footnote_plugin


CITATION_LINE_PATTERNS = [
    re.compile(r"^\s*>\s*(來源|資料來源|出處|source)\s*[:：].*$", re.IGNORECASE),
    re.compile(r"^\s*[-*]\s*(來源|資料來源|出處|source)\s*[:：].*$", re.IGNORECASE),
    re.compile(r"^\s*🤖.*$"),
    re.compile(r"^\s*Co-Authored-By:.*Claude.*$", re.IGNORECASE),
]

CITATION_INLINE_PATTERNS = [
    re.compile(r"\(\s*source\s*[:：][^)]+\)", re.IGNORECASE),
    re.compile(r"\[\s*源\s*[:：][^\]]+\]"),
    re.compile(r"\(\s*出處\s*[:：][^)]*\.(md|csv|json)[^)]*\)"),
    re.compile(r"\[L\d+(-L?\d+)?\]"),
    re.compile(r"（L\d+(-\d+)?）"),
    re.compile(r"\s*—\s*see\s+[^\s]+\.(md|csv|json)\b", re.IGNORECASE),
]

PATH_AUDIT_PATTERN = re.compile(
    r"(?<![\w-])(?:handbook|tools/render|assets|data|rendered)/[\w./-]+|"
    r"(?<![\w-])[\w\-]+\.(?:md|json|csv)(?![\w])",
    re.IGNORECASE,
)

CODE_BLOCK_PATTERN = re.compile(r"<(code|pre)\b[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
HEAD_BLOCK_PATTERN = re.compile(r"<head\b[^>]*>.*?</head>", re.DOTALL | re.IGNORECASE)
STYLE_BLOCK_PATTERN = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
LINK_TAG_PATTERN = re.compile(r"<link\b[^>]*>", re.DOTALL | re.IGNORECASE)


@dataclass
class HtmlDoc:
    body_html: str
    outline: list[tuple[int, str, str]]


def _strip_citations(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    kept: list[str] = []
    for line in lines:
        if any(p.match(line) for p in CITATION_LINE_PATTERNS):
            continue
        cleaned = line
        for pat in CITATION_INLINE_PATTERNS:
            cleaned = pat.sub("", cleaned)
        kept.append(cleaned.rstrip())
    text = "\n".join(kept)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _build_md() -> MarkdownIt:
    md = (
        MarkdownIt("commonmark", {"html": False, "breaks": False, "linkify": True})
        .enable("table")
        .enable("strikethrough")
        .use(anchors_plugin, min_level=1, max_level=4, permalink=False, slug_func=_slug)
        .use(attrs_plugin)
        .use(deflist_plugin)
        .use(footnote_plugin)
    )
    return md


def _slug(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[\s]+", "-", text)
    text = re.sub(r"[^\w一-鿿-]", "", text)
    return text or "section"


def _extract_outline(md: MarkdownIt, source: str) -> list[tuple[int, str, str]]:
    tokens = md.parse(source)
    outline: list[tuple[int, str, str]] = []
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open" and tok.tag in {"h1", "h2", "h3"}:
            inline = tokens[i + 1]
            text = inline.content.strip()
            anchor = tok.attrs.get("id") if tok.attrs else None
            if not anchor:
                anchor = _slug(text)
            level = int(tok.tag[1])
            outline.append((level, text, anchor))
    return outline


def render_markdown_file(md_path: Path) -> HtmlDoc:
    raw = md_path.read_text(encoding="utf-8")
    cleaned = _strip_citations(raw)
    md = _build_md()
    outline = _extract_outline(md, cleaned)
    body_html = md.render(cleaned)
    return HtmlDoc(body_html=body_html, outline=outline)


def audit_path_references(html: str) -> list[str]:
    # Audit only user-visible content, not the document head / inline stylesheets.
    stripped = HEAD_BLOCK_PATTERN.sub("", html)
    stripped = STYLE_BLOCK_PATTERN.sub("", stripped)
    stripped = LINK_TAG_PATTERN.sub("", stripped)
    stripped = CODE_BLOCK_PATTERN.sub("", stripped)
    matches = PATH_AUDIT_PATTERN.findall(stripped)
    flat: list[str] = []
    for m in matches:
        if isinstance(m, tuple):
            flat.extend(x for x in m if x)
        else:
            flat.append(m)
    return [m for m in flat if m]
