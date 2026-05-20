from __future__ import annotations

import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from playwright.sync_api import sync_playwright

from . import config as cfg


@dataclass
class PageSpec:
    landscape: bool = False
    margin_mm: tuple[float, float, float, float] = (20, 16, 22, 16)  # top, right, bottom, left
    display_header_footer: bool = False
    header_html: str = ""
    footer_html: str = ""


def _mm(value: float) -> str:
    return f"{value}mm"


def _stage_html(html_str: str) -> Path:
    """Drop the HTML into a temp file beneath the repo so file:// font and
    stylesheet URLs share an origin with the loaded page."""
    stage_dir = cfg.REPO_ROOT / ".render-stage"
    stage_dir.mkdir(exist_ok=True)
    path = stage_dir / f"{uuid.uuid4().hex}.html"
    path.write_text(html_str, encoding="utf-8")
    return path


def _pdf_kwargs(spec: PageSpec) -> dict:
    top, right, bottom, left = spec.margin_mm
    kwargs: dict = {
        "format": "A4",
        "landscape": spec.landscape,
        "margin": {
            "top": _mm(top),
            "right": _mm(right),
            "bottom": _mm(bottom),
            "left": _mm(left),
        },
        "print_background": True,
    }
    if spec.display_header_footer:
        kwargs["display_header_footer"] = True
        kwargs["header_template"] = spec.header_html
        kwargs["footer_template"] = spec.footer_html
    else:
        kwargs["display_header_footer"] = False
    return kwargs


def render_html_to_pdf(html_str: str, target: Path, spec: PageSpec) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = _stage_html(html_str)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--allow-file-access-from-files"],
            )
            try:
                page = browser.new_page()
                page.emulate_media(media="print")
                page.goto(stage.as_uri(), wait_until="networkidle")
                page.pdf(path=str(target), **_pdf_kwargs(spec))
            finally:
                browser.close()
    finally:
        stage.unlink(missing_ok=True)


def render_html_batch(jobs: Iterable[tuple[str, Path, PageSpec]]) -> None:
    """Render multiple HTML strings to PDFs sharing one browser process."""
    staged: list[Path] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--allow-file-access-from-files"],
            )
            try:
                for html_str, target, spec in jobs:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    stage = _stage_html(html_str)
                    staged.append(stage)
                    page = browser.new_page()
                    page.emulate_media(media="print")
                    page.goto(stage.as_uri(), wait_until="networkidle")
                    page.pdf(path=str(target), **_pdf_kwargs(spec))
                    page.close()
            finally:
                browser.close()
    finally:
        for stage in staged:
            stage.unlink(missing_ok=True)
        stage_dir = cfg.REPO_ROOT / ".render-stage"
        if stage_dir.exists():
            try:
                stage_dir.rmdir()
            except OSError:
                pass
