from __future__ import annotations

"""
Per-cell PNG assets (rendered directly from HTML):
- snapshot_key_metrics
- snapshot_big_stat
- phd_core_fields
- phd_other_disciplines
- phd_placements
- professional_applied_research
- professional_consulting
- professional_data_science_analytics
- professional_finance
- professional_startups_tech
- professional_other_sectors

As well as:
- section-level exports
- full-page preview (PNG + PDF)

Dependencies:
pip install playwright
python -m playwright install chromium
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

#==========config==========#

HTML_PATH = Path("macss_outcomes_example.html")
OUTPUT_DIR = Path("macss_outcomes_assets")
OUTPUT_DIR.mkdir(exist_ok=True)

VIEWPORT_WIDTH = 1600
VIEWPORT_HEIGHT = 3200
DEVICE_SCALE_FACTOR = 2
PAGE_BG = "#efe8df"

#==========selectors==========#

CARD_SELECTORS = {
    "snapshot_key_metrics": "section:nth-of-type(1) .grid-2 > .card:nth-of-type(1)",
    "snapshot_big_stat": "section:nth-of-type(1) .grid-2 > .card:nth-of-type(2)",
    "phd_core_fields": "section:nth-of-type(2) .grid-3 > .card:nth-of-type(1)",
    "phd_other_disciplines": "section:nth-of-type(2) .grid-3 > .card:nth-of-type(2)",
    "phd_placements": "section:nth-of-type(2) .grid-3 > .card:nth-of-type(3)",
    "professional_applied_research": "section:nth-of-type(3) .grid-3 > .card:nth-of-type(1)",
    "professional_consulting": "section:nth-of-type(3) .grid-3 > .card:nth-of-type(2)",
    "professional_data_science_analytics": "section:nth-of-type(3) .grid-3 > .card:nth-of-type(3)",
    "professional_finance": "section:nth-of-type(3) .grid-3 > .card:nth-of-type(4)",
    "professional_startups_tech": "section:nth-of-type(3) .grid-3 > .card:nth-of-type(5)",
    "professional_other_sectors": "section:nth-of-type(3) .grid-3 > .card:nth-of-type(6)",
}

SECTION_SELECTORS = {
    "hero": "header.hero",
    "snapshot_section": "section:nth-of-type(1)",
    "phd_section": "section:nth-of-type(2)",
    "professional_section": "section:nth-of-type(3)",
}

#==========html handling==========#

def _read_html(html_path: Path) -> str:
    if not html_path.exists():
        raise FileNotFoundError(
            f"Could not find HTML file: {html_path.resolve()}"
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

#==========export helpers==========#

def _screenshot_locator(locator, path: Path) -> None:
    locator.scroll_into_view_if_needed()
    locator.screenshot(path=str(path), animations="disabled", scale="device")


def _pdf_page(page, path: Path) -> None:
    page.pdf(
        path=str(path),
        print_background=True,
        width="1400px",
        height="2200px",
        margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"},
    )


def _export_group(page, selectors: dict[str, str]) -> None:
    for stem, selector in selectors.items():
        locator = page.locator(selector).first
        if locator.count() == 0:
            raise ValueError(f"Selector did not match anything: {selector}")

        png_path = OUTPUT_DIR / f"{stem}.png"
        _screenshot_locator(locator, png_path)

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

        # section-level exports
        for stem, selector in SECTION_SELECTORS.items():
            locator = page.locator(selector).first
            if locator.count() == 0:
                raise ValueError(f"Section selector did not match anything: {selector}")

            _screenshot_locator(locator, OUTPUT_DIR / f"{stem}.png")

        # card-level exports
        _export_group(page, CARD_SELECTORS)

        browser.close()

#==========runner==========#

def main() -> None:
    export_assets(HTML_PATH)
    print(f"Saved assets to: {OUTPUT_DIR.resolve()}")

#==========entry==========#

if __name__ == "__main__":
    main()