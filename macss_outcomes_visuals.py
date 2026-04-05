from __future__ import annotations

"""
Generalized HTML-to-assets exporter for the MACSS outcomes pages.

What this version fixes:
- does NOT rely on rigid nth-of-type selectors
- finds sections by their actual headings / labels
- tolerates style-only HTML variants (font, radius, color changes, etc.)
- can usually survive modest wrapper/layout changes as long as the content labels remain

Outputs:
- full-page preview PNG + PDF
- hero PNG
- section PNGs
- card PNGs

Dependencies:
pip install playwright
python -m playwright install chromium
"""

from pathlib import Path
from typing import Iterable, Sequence

from playwright.sync_api import Page, Locator, sync_playwright

#==========config==========#

HTML_PATH = Path("macss_outcomes_example_3.html") # swap for desired html path
OUTPUT_DIR = Path("macss_outcomes_assets_3") # swap for desired output path
OUTPUT_DIR.mkdir(exist_ok=True)

VIEWPORT_WIDTH = 1600
VIEWPORT_HEIGHT = 3600
DEVICE_SCALE_FACTOR = 2
PAGE_BG = "#efe8df"

# output stems to semantic identifiers
SECTION_LABELS = {
    "snapshot_section": "Class of 2024 Snapshot",
    "phd_section": "PhD Outcomes by Field",
    "professional_section": "Professional Outcomes (2018–2023)",
}

CARD_LABELS = {
    "snapshot_key_metrics": "Key Metrics",
    "snapshot_big_stat": "Employment or Doctoral Placement within 9 Months",
    "phd_core_fields": "Core Fields",
    "phd_other_disciplines": "Other Disciplines",
    "phd_placements": "PhD Placements",
    "professional_applied_research": "Applied Research",
    "professional_consulting": "Consulting",
    "professional_data_science_analytics": "Data Science / Analytics",
    "professional_finance": "Finance",
    "professional_startups_tech": "Startups / Tech",
    "professional_other_sectors": "Other Sectors",
}

#==========html handling==========#

def _read_html(html_path: Path) -> str:
    if not html_path.exists():
        raise FileNotFoundError(
            f"Could not find HTML file: {html_path.resolve()}\n"
            "Put the exported HTML in the same directory as this script, or change HTML_PATH."
        )
    return html_path.read_text(encoding="utf-8")


def _write_temp_html(html_text: str, out_dir: Path) -> Path:
    temp_html = out_dir / "_render_source.html"
    temp_html.write_text(html_text, encoding="utf-8")
    return temp_html


def _normalize_html_for_export(html_text: str) -> str:
    inject = f"""
<style id="export-overrides">
  html, body {{
    margin: 0 !important;
    padding: 0 !important;
    background: {PAGE_BG} !important;
  }}
  body {{
    -webkit-font-smoothing: antialiased;
    text-rendering: geometricPrecision;
  }}
  .wrap {{
    max-width: 1200px !important;
    margin: 0 auto !important;
  }}
  .card, .panel, .big-stat, .list .item {{
    overflow: hidden !important;
  }}
  .bar-track {{
    overflow: hidden !important;
  }}
  @media print {{
    body {{ background: {PAGE_BG} !important; }}
  }}
</style>
"""
    if "</head>" in html_text:
        return html_text.replace("</head>", inject + "</head>")
    return inject + html_text

#==========locator helpers==========#

def _first_existing(page: Page, selector_candidates: Sequence[str]) -> Locator:
    for selector in selector_candidates:
        loc = page.locator(selector)
        if loc.count() > 0:
            return loc.first
    raise ValueError(
        "None of the selector candidates matched:\n" + "\n".join(f"- {s}" for s in selector_candidates)
    )


def _locator_with_text(page: Page, base_selector: str, text: str) -> Locator:
    """
    Robust text-based locator:
    - exact text in semantic containers first
    - generic text fallback second
    """
    candidates = [
        f'{base_selector}:has-text("{text}")',
        f':text("{text}")',
    ]
    return _first_existing(page, candidates)


def _ancestor_card(locator: Locator) -> Locator:
    candidates = [
        "xpath=ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' card ')][1]",
        "xpath=ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' big-stat ')][1]",
        "xpath=ancestor::div[1]",
    ]
    for selector in candidates:
        loc = locator.locator(selector)
        if loc.count() > 0:
            return loc.first
    return locator


def _ancestor_section(locator: Locator) -> Locator:
    candidates = [
        "xpath=ancestor::section[1]",
        "xpath=ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' section ')][1]",
    ]
    for selector in candidates:
        loc = locator.locator(selector)
        if loc.count() > 0:
            return loc.first
    return locator


def _hero_locator(page: Page) -> Locator:
    return _first_existing(page, ["header.hero", ".hero", "header:has(h1)"])


def _find_section_by_heading(page: Page, heading_text: str) -> Locator:
    heading = _first_existing(page, [
        f'h2:has-text("{heading_text}")',
        f'h1:has-text("{heading_text}")',
        f':text("{heading_text}")',
    ])
    return _ancestor_section(heading)


def _find_card_by_label(page: Page, label_text: str) -> Locator:
    # strongest candidates first: headings or labels inside known card-like blocks
    anchor = _first_existing(page, [
        f'h3:has-text("{label_text}")',
        f'h2:has-text("{label_text}")',
        f'.label:has-text("{label_text}")',
        f'.bar-meta:has-text("{label_text}")',
        f'.list .item:has-text("{label_text}")',
        f'.subtle:has-text("{label_text}")',
        f':text("{label_text}")',
    ])
    return _ancestor_card(anchor)

#==========export helpers==========#

def _screenshot_locator(locator: Locator, path: Path) -> None:
    locator.scroll_into_view_if_needed()
    locator.screenshot(path=str(path), animations="disabled", scale="device")


def _pdf_page(page: Page, path: Path) -> None:
    page.pdf(
        path=str(path),
        print_background=True,
        width="1400px",
        height="2200px",
        margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"},
    )

#==========export pipeline==========#

def export_assets(html_path: Path = HTML_PATH) -> None:
    html_text = _normalize_html_for_export(_read_html(html_path))
    temp_html = _write_temp_html(html_text, OUTPUT_DIR)
    file_url = temp_html.resolve().as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            device_scale_factor=DEVICE_SCALE_FACTOR,
        )
        page = context.new_page()
        page.goto(file_url, wait_until="networkidle")
        page.evaluate("window.scrollTo(0, 0)")

        # full-page exports
        page.screenshot(
            path=str(OUTPUT_DIR / "macss_outcomes_preview.png"),
            full_page=True,
            animations="disabled",
            scale="device",
        )
        _pdf_page(page, OUTPUT_DIR / "macss_outcomes_preview.pdf")

        # hero export
        _screenshot_locator(_hero_locator(page), OUTPUT_DIR / "hero.png")

        # section-level exports
        for stem, heading_text in SECTION_LABELS.items():
            section_loc = _find_section_by_heading(page, heading_text)
            _screenshot_locator(section_loc, OUTPUT_DIR / f"{stem}.png")

        # card-level exports
        for stem, label_text in CARD_LABELS.items():
            card_loc = _find_card_by_label(page, label_text)
            _screenshot_locator(card_loc, OUTPUT_DIR / f"{stem}.png")

        browser.close()

#==========runner==========#

def main() -> None:
    export_assets(HTML_PATH)
    print(f"Saved assets to: {OUTPUT_DIR.resolve()}")

#==========entry==========#

if __name__ == "__main__":
    main()
