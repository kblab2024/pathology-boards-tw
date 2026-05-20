from __future__ import annotations

import argparse
import io
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.render"

# Force UTF-8 stdout on Windows so chapter titles can include CJK + middle-dot.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in {"utf-8", "utf8"}:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from pypdf import PdfReader, PdfWriter

from . import config as cfg
from . import html_template as tpl
from .csv_to_html import render_cheatsheet_csv
from .markdown_to_html import audit_path_references, render_markdown_file
from .pdf_engine import PageSpec, render_html_batch


def _build_chapter_body(chapter: dict) -> tuple[str, list[tuple[int, str, str]]]:
    src = cfg.HANDBOOK_DIR / chapter["source"]
    if chapter["kind"] == "csv":
        body = render_cheatsheet_csv(src)
        outline: list[tuple[int, str, str]] = [(1, chapter["title_zh"], f"ch-{chapter['num']}-top")]
    else:
        doc = render_markdown_file(src)
        body = doc.body_html
        outline = doc.outline
    return body, outline


def _assert_clean(html: str, label: str) -> None:
    leaks = audit_path_references(html)
    if leaks:
        sample = ", ".join(sorted(set(leaks))[:8])
        raise RuntimeError(f"{label}: leaked file path reference(s): {sample}")


def _spec_for_section(section: str, chapter: dict | None = None) -> PageSpec:
    """Section: cover, colophon, toc, divider, body, back_cover."""
    if section in {"cover", "back_cover", "divider"}:
        return PageSpec(
            landscape=False,
            margin_mm=(0, 0, 0, 0),
            display_header_footer=False,
        )
    if section in {"colophon", "toc"}:
        return PageSpec(
            landscape=False,
            margin_mm=(18, 16, 18, 16),
            display_header_footer=True,
            header_html=tpl.empty_header(),
            footer_html=tpl.footer_template(None),
        )
    if section == "body":
        assert chapter is not None
        landscape = chapter["orient"] == "landscape"
        return PageSpec(
            landscape=landscape,
            margin_mm=(22, 16, 22, 16),
            display_header_footer=True,
            header_html=tpl.header_template(chapter),
            footer_html=tpl.footer_template(chapter),
        )
    raise ValueError(f"unknown section: {section}")


def _merge_pdfs(paths: list[Path], target: Path) -> int:
    writer = PdfWriter()
    total = 0
    for p in paths:
        reader = PdfReader(str(p))
        for pg in reader.pages:
            writer.add_page(pg)
            total += 1
    writer.write(str(target))
    writer.close()
    return total


def _count_pages(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


def render_one(num: str) -> Path:
    chapter = cfg.chapter_by_num(num)
    body_html, _outline = _build_chapter_body(chapter)

    divider_html = tpl.render_divider(chapter, mode="single")
    body_full_html = tpl.render_body(chapter, body_html)

    _assert_clean(divider_html, f"chapter {num} divider")
    _assert_clean(body_full_html, f"chapter {num} body")

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        divider_pdf = td_path / f"ch{num}_divider.pdf"
        body_pdf = td_path / f"ch{num}_body.pdf"
        jobs = [
            (divider_html, divider_pdf, _spec_for_section("divider")),
            (body_full_html, body_pdf, _spec_for_section("body", chapter)),
        ]
        render_html_batch(jobs)
        target = cfg.output_path(num)
        _merge_pdfs([divider_pdf, body_pdf], target)

    size_kb = target.stat().st_size // 1024
    pages = _count_pages(target)
    print(f"  wrote {target.relative_to(cfg.REPO_ROOT)}  ({size_kb} KiB, {pages} pages)")
    return target


def render_master_edition() -> Path:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        cover_pdf = td_path / "cover.pdf"
        colophon_pdf = td_path / "colophon.pdf"
        back_cover_pdf = td_path / "back_cover.pdf"
        chapter_pdfs: list[tuple[str, Path, Path]] = []  # (num, divider_pdf, body_pdf)

        cover_html = tpl.render_cover("master")
        colophon_html = tpl.render_colophon()
        back_cover_html = tpl.render_back_cover()
        _assert_clean(cover_html, "cover")
        _assert_clean(colophon_html, "colophon")
        _assert_clean(back_cover_html, "back_cover")

        jobs: list[tuple[str, Path, PageSpec]] = [
            (cover_html, cover_pdf, _spec_for_section("cover")),
            (colophon_html, colophon_pdf, _spec_for_section("colophon")),
            (back_cover_html, back_cover_pdf, _spec_for_section("back_cover")),
        ]

        for ch in cfg.CHAPTERS:
            body_html, _outline = _build_chapter_body(ch)
            divider_html = tpl.render_divider(ch, mode="master")
            body_full_html = tpl.render_body(ch, body_html)
            _assert_clean(divider_html, f"master ch{ch['num']} divider")
            _assert_clean(body_full_html, f"master ch{ch['num']} body")

            divider_pdf = td_path / f"ch{ch['num']}_divider.pdf"
            body_pdf = td_path / f"ch{ch['num']}_body.pdf"
            jobs.append((divider_html, divider_pdf, _spec_for_section("divider")))
            jobs.append((body_full_html, body_pdf, _spec_for_section("body", ch)))
            chapter_pdfs.append((ch["num"], divider_pdf, body_pdf))

        print(f"  rendering {len(jobs)} section PDFs via Chromium ...")
        render_html_batch(jobs)

        page_offsets: dict[str, int] = {}
        running = _count_pages(cover_pdf) + _count_pages(colophon_pdf) + 1  # +1 reserves TOC slot
        for num, div_pdf, body_pdf in chapter_pdfs:
            page_offsets[num] = running
            running += _count_pages(div_pdf) + _count_pages(body_pdf)

        toc_entries = [
            {
                "num": ch["num"],
                "title_zh": ch["title_zh"],
                "title_en": ch["title_en"],
                "page": page_offsets[ch["num"]],
                "accent": cfg.CHAPTER_ACCENT[ch["num"]],
            }
            for ch in cfg.CHAPTERS
        ]
        toc_html = tpl.render_toc(toc_entries)
        _assert_clean(toc_html, "toc")
        toc_pdf = td_path / "toc.pdf"
        render_html_batch([(toc_html, toc_pdf, _spec_for_section("toc"))])

        merged_paths = [cover_pdf, colophon_pdf, toc_pdf]
        for _num, div_pdf, body_pdf in chapter_pdfs:
            merged_paths.append(div_pdf)
            merged_paths.append(body_pdf)
        merged_paths.append(back_cover_pdf)

        target = cfg.MASTER_OUTPUT
        total_pages = _merge_pdfs(merged_paths, target)

    size_kb = target.stat().st_size // 1024
    print(f"  wrote {target.relative_to(cfg.REPO_ROOT)}  ({size_kb} KiB, {total_pages} pages)")
    return target


def render_all_chapters() -> list[Path]:
    paths: list[Path] = []
    for ch in cfg.CHAPTERS:
        print(f"chapter {ch['num']} — {ch['title_zh']}")
        paths.append(render_one(ch["num"]))
    return paths


def clean_rendered() -> None:
    if cfg.RENDERED_DIR.exists():
        for p in cfg.RENDERED_DIR.glob("*.pdf"):
            p.unlink()
    cfg.RENDERED_DIR.mkdir(parents=True, exist_ok=True)
    (cfg.RENDERED_DIR / ".gitkeep").touch(exist_ok=True)
    print(f"cleaned {cfg.RENDERED_DIR}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render handbook to PDF")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="render every chapter + master edition")
    group.add_argument("--file", metavar="NN", help="render one chapter by two-digit number")
    group.add_argument("--master", action="store_true", help="render only the master edition")
    group.add_argument("--clean", action="store_true", help="wipe rendered/*.pdf")
    args = parser.parse_args(argv)

    if args.clean:
        clean_rendered()
        return 0

    cfg.RENDERED_DIR.mkdir(parents=True, exist_ok=True)

    if args.file:
        print(f"rendering chapter {args.file}")
        render_one(args.file)
        return 0

    if args.master:
        print("rendering master edition")
        render_master_edition()
        return 0

    if args.all:
        print("rendering all chapters")
        render_all_chapters()
        print("rendering master edition")
        render_master_edition()
        print("done.")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
