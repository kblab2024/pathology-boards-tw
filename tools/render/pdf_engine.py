from __future__ import annotations

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


def render_html_to_pdf(html_str: str, target: Path, spec: PageSpec) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    top, right, bottom, left = spec.margin_mm

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(html_str, wait_until="networkidle")
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
                "prefer_css_page_size": False,
            }
            if spec.display_header_footer:
                kwargs["display_header_footer"] = True
                kwargs["header_template"] = spec.header_html
                kwargs["footer_template"] = spec.footer_html
            else:
                kwargs["display_header_footer"] = False
            page.emulate_media(media="print")
            page.pdf(path=str(target), **kwargs)
        finally:
            browser.close()


def render_html_batch(jobs: Iterable[tuple[str, Path, PageSpec]]) -> None:
    """Render multiple HTML strings to PDFs sharing one browser process."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for html_str, target, spec in jobs:
                target.parent.mkdir(parents=True, exist_ok=True)
                page = browser.new_page()
                page.emulate_media(media="print")
                page.set_content(html_str, wait_until="networkidle")
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
                page.pdf(path=str(target), **kwargs)
                page.close()
        finally:
            browser.close()
