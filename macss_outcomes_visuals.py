from __future__ import annotations

"""
Per-cell PNG & SVG assets:
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
- a composite page preview (PNG)
- a simple output manifest (JSON)

Dependencies:
pip install matplotlib pillow numpy cairosvg
"""

from dataclasses import dataclass
from pathlib import Path
import json
import math
import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.lines import Line2D
from PIL import Image, ImageDraw, ImageFont

#==========config==========#

OUTPUT_DIR = Path("macss_outcomes_assets")
OUTPUT_DIR.mkdir(exist_ok=True)

DPI = 200

# palette
MAROON = "#7b1e1e"
MAROON_SOFT = "#9c3a3a"
INK = "#1d1d1f"
MUTED = "#555555"
LINE = "#d9d2c8"
CREAM = "#efe8df"
PAPER = "#f4eee7"
PANEL = "#e9e1d8"
TRACK = "#e3d9cf"
WHITE = "#ffffff"

# matplotlib defaults
plt.rcParams.update({
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    "font.family": "DejaVu Serif",
    "text.color": INK,
    "axes.edgecolor": LINE,
})

#==========data==========#

SNAPSHOT_METRICS = [
    ("Known Outcomes", 87.0, "87%"),
    ("Placement ≤ 9 Months", 100.0, "100%"),
    ("PhD Funding Acceptance", 92.3, "92.3%"),
]

PHD_CORE_FIELDS = [
    ("Economics", 58.8, "10 / 17", "58.8%"),
    ("Political Science", 100.0, "4 / 4", "100%"),
    ("Psychology", 100.0, "5 / 5", "100%"),
    ("Sociology", 66.7, "8 / 12", "66.7%"),
    ("Business", 85.0, "17 / 20", "85%"),
]

OTHER_DISCIPLINES = [
    ("Communication", "University of Pennsylvania"),
    ("Technology & Social Behavior", "Northwestern"),
    ("Computer Science", "Toronto, EPFL, UCL, Northwestern, BU"),
    ("Information Science", "Cornell, Washington, Indiana"),
    ("Public Policy / Related", "Columbia, Cornell"),
]

PHD_PLACEMENTS_SUBTLE = (
    "MACSS graduates have been admitted to leading doctoral programs across the "
    "United States and internationally, including:"
)
PHD_PLACEMENTS = [
    "Princeton University · Stanford University · Yale University",
    "Harvard University · Massachusetts Institute of Technology · University of Chicago",
    "Northwestern University · University of Pennsylvania · University of Michigan",
]

PROFESSIONAL = {
    "Applied Research": [
        "Becker Friedman Institute; Columbia; Duke; MIT; Northwestern",
        "Princeton; Stanford; UChicago; Urban Institute; Yale",
    ],
    "Consulting": [
        "BCG; Charles River; Cornerstone; Guidehouse",
        "McKinsey; RCF Economic & Financial",
    ],
    "Data Science / Analytics": [
        "Accenture; Amazon; Apple; Microsoft; Oracle",
        "Comscore; Haver; Stax; TransUnion; Walmart",
    ],
    "Finance": [
        "AIG; Capital One; Goldman Sachs; HSBC",
        "Invesco; JPMorgan; Morgan Stanley; Voya",
    ],
    "Startups / Tech": [
        "AbbVie; Alibaba; Amazon; ByteDance; Etsy",
        "Facebook/Meta; Google; Morningstar; PayPal; Wayfair; X",
    ],
    "Other Sectors": [
        "Government — Cook County; Library of Congress; NOAA; USFS",
        "Nonprofit — LEAP; Nature Conservancy; Translators without Borders",
        "Healthcare/Insurance — HCSC; Samsung Life; Zurich NA",
    ],
}

#==========font helpers==========#

def get_font(size: int, bold: bool = False):
    candidates = []
    if bold:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
        ]
    else:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        ]
    for path in candidates:
        p = Path(path)
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()

FONT_TITLE = get_font(42, bold=True)
FONT_H3 = get_font(30, bold=True)
FONT_BODY = get_font(21, bold=False)
FONT_BODY_BOLD = get_font(21, bold=True)
FONT_SMALL = get_font(18, bold=False)
FONT_BIG = get_font(88, bold=True)
FONT_LABEL = get_font(28, bold=False)

#==========utility drawing helpers==========#

def rounded_box(draw: ImageDraw.ImageDraw, xy, radius=22, fill=PAPER, outline=LINE, width=2):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def left_rail(draw: ImageDraw.ImageDraw, xy, color=MAROON, width=8, radius=22):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle((x0, y0, x0 + width, y1), radius=radius, fill=color)


def draw_wrapped_text(draw, text, xy, font, fill, max_width, line_spacing=6):
    x, y = xy
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, y), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing
    return y


def save_pil(img: Image.Image, stem: str):
    png_path = OUTPUT_DIR / f"{stem}.png"
    img.save(png_path)
    return {"png": str(png_path)}


def save_fig(fig: plt.Figure, stem: str):
    png_path = OUTPUT_DIR / f"{stem}.png"
    svg_path = OUTPUT_DIR / f"{stem}.svg"
    fig.savefig(png_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(svg_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return {"png": str(png_path), "svg": str(svg_path)}

#==========matplotlib card/charts==========#

def add_card_background(ax, face=PAPER, rail=True):
    ax.set_facecolor("none")
    card = FancyBboxPatch(
        (0, 0), 1, 1,
        boxstyle="round,pad=0.012,rounding_size=0.05",
        transform=ax.transAxes,
        linewidth=1.2,
        edgecolor=LINE,
        facecolor=face,
        zorder=-10,
        clip_on=False,
    )
    ax.add_patch(card)
    if rail:
        rail_patch = FancyBboxPatch(
            (0, 0), 0.02, 1,
            boxstyle="round,pad=0.0,rounding_size=0.05",
            transform=ax.transAxes,
            linewidth=0,
            facecolor=MAROON,
            zorder=-9,
            clip_on=False,
        )
        ax.add_patch(rail_patch)


def create_bar_card(title: str, rows, stem: str, width=8.0, height=4.8):
    fig, ax = plt.subplots(figsize=(width, height), facecolor=PAPER)
    add_card_background(ax, face=PAPER, rail=True)

    labels = [r[0] for r in rows][::-1]
    values = [r[1] for r in rows][::-1]
    mids = [r[2] for r in rows][::-1]
    rights = [r[3] if len(r) > 3 else r[2] for r in rows][::-1]
    ypos = list(range(len(rows)))

    ax.barh(ypos, [100] * len(rows), color=TRACK, height=0.38, edgecolor="none", zorder=1)
    ax.barh(ypos, values, color=MAROON, height=0.38, edgecolor="none", zorder=2)

    for y, lab, mid, right, val in zip(ypos, labels, mids, rights, values):
        ax.text(0, y + 0.34, lab, va="bottom", ha="left", fontsize=12.5, color=INK, fontweight="medium")
        ax.text(100, y + 0.34, mid, va="bottom", ha="right", fontsize=11.5, color=MUTED)
        ax.text(102.2, y, right, va="center", ha="left", fontsize=12, color=MAROON, fontweight="bold")
        ax.add_line(Line2D([0, 100], [y - 0.52, y - 0.52], lw=0.5, color="#ebe2d8", zorder=0))

    ax.text(0, len(rows) - 0.1 + 0.7, title, ha="left", va="bottom", fontsize=17, fontweight="bold", color=INK)

    ax.set_xlim(0, 116)
    ax.set_ylim(-0.8, len(rows) + 0.6)
    ax.axis("off")
    return save_fig(fig, stem)


def create_big_stat_card(value: str, label: str, stem: str, width=5.8, height=4.8):
    fig, ax = plt.subplots(figsize=(width, height), facecolor=PAPER)
    ax.set_facecolor("none")
    card = FancyBboxPatch(
        (0, 0), 1, 1,
        boxstyle="round,pad=0.012,rounding_size=0.05",
        transform=ax.transAxes,
        linewidth=1.8,
        edgecolor=MAROON,
        facecolor=PAPER,
        zorder=-10,
        clip_on=False,
    )
    ax.add_patch(card)

    inner = FancyBboxPatch(
        (0.06, 0.08), 0.88, 0.84,
        boxstyle="round,pad=0.015,rounding_size=0.05",
        transform=ax.transAxes,
        linewidth=1.1,
        edgecolor=LINE,
        facecolor="#eadfd3",
        zorder=-9,
        clip_on=False,
    )
    ax.add_patch(inner)

    ax.text(0.5, 0.62, value, ha="center", va="center", fontsize=48, color=MAROON, fontweight="bold", transform=ax.transAxes)
    wrapped = "\n".join(textwrap.wrap(label, width=28))
    ax.text(0.5, 0.33, wrapped, ha="center", va="center", fontsize=16, color=INK, transform=ax.transAxes)
    ax.axis("off")
    return save_fig(fig, stem)

#==========PIL list cards==========#

def create_list_card(title: str, items: list[str], stem: str, subtle: str | None = None, width=980, height=600):
    img = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(img)

    rounded_box(draw, (4, 4, width - 4, height - 4), radius=26, fill=PAPER, outline=LINE, width=2)
    draw.rounded_rectangle((4, 4, 16, height - 4), radius=26, fill=MAROON, outline=None)

    x_pad = 42
    y = 32
    draw.text((x_pad, y), title, font=FONT_H3, fill=INK)
    y += 52

    if subtle:
        y = draw_wrapped_text(draw, subtle, (x_pad, y), FONT_SMALL, MUTED, width - 2 * x_pad - 10, line_spacing=5)
        y += 10

    item_box_height = 86 if len(items) <= 3 else 74
    for item in items:
        rounded_box(draw, (x_pad, y, width - x_pad, y + item_box_height), radius=18, fill="#f0e8de", outline=LINE, width=2)
        draw_wrapped_text(draw, item, (x_pad + 16, y + 14), FONT_BODY, INK, width - 2 * x_pad - 32, line_spacing=5)
        y += item_box_height + 14

    return save_pil(img, stem)


def create_other_disciplines_card(stem: str):
    img = Image.new("RGB", (980, 660), PAPER)
    draw = ImageDraw.Draw(img)

    rounded_box(draw, (4, 4, 976, 656), radius=26, fill=PAPER, outline=LINE, width=2)
    draw.rounded_rectangle((4, 4, 16, 656), radius=26, fill=MAROON, outline=None)

    x_pad = 42
    y = 32
    draw.text((x_pad, y), "Other Disciplines", font=FONT_H3, fill=INK)
    y += 52

    for label, detail in OTHER_DISCIPLINES:
        box_h = 92
        rounded_box(draw, (x_pad, y, 938, y + box_h), radius=18, fill="#f0e8de", outline=LINE, width=2)
        draw.text((x_pad + 16, y + 14), label, font=FONT_BODY_BOLD, fill=MAROON)
        draw_wrapped_text(draw, f"— {detail}", (x_pad + 16, y + 44), FONT_BODY, INK, 938 - x_pad - 32, line_spacing=5)
        y += box_h + 12

    return save_pil(img, stem)

#==========composite preview==========#

def load_png(path_dict):
    return Image.open(path_dict["png"]).convert("RGB")


def make_composite_preview(assets: dict[str, dict[str, str]], stem="macss_outcomes_preview"):
    page_w = 2200
    page_h = 2800
    page = Image.new("RGB", (page_w, page_h), CREAM)
    draw = ImageDraw.Draw(page)

    # header
    draw.text((110, 70), "MASTER OF ARTS PROGRAM IN COMPUTATIONAL SOCIAL SCIENCE", font=get_font(24, True), fill=MAROON)
    draw.text((110, 120), "MACSS Career Outcomes", font=get_font(64, True), fill=INK)
    intro = (
        "Customized learning and possible career trajectories based on an individual's interests are key benefits "
        "of interdisciplinary study. Given that breadth and depth, MACSS graduates accept positions across a diversity "
        "of positions, organizations, and industries. MACSS places more graduates in data and research, in both for-profit "
        "and not-for-profit sectors, than any other field."
    )
    draw_wrapped_text(draw, intro, (110, 210), get_font(24), MUTED, 1500, line_spacing=8)
    draw.line((110, 335, 2090, 335), fill=MAROON, width=3)

    def panel_box(x, y, w, h):
        rounded_box(draw, (x, y, x + w, y + h), radius=26, fill=PANEL, outline=MAROON, width=2)

    # snapshot
    draw.text((110, 390), "Class of 2024 Snapshot", font=get_font(42, True), fill=MAROON)
    draw_wrapped_text(draw, "87% known outcomes; 100% employed or in doctoral programs within 9 months; 92.3% of PhD applicants accepted with full funding.", (1320, 402), get_font(20), MUTED, 760)
    panel_box(110, 470, 1980, 520)
    card1 = load_png(assets["snapshot_key_metrics"]).resize((1030, 420))
    card2 = load_png(assets["snapshot_big_stat"]).resize((820, 420))
    page.paste(card1, (150, 520))
    page.paste(card2, (1210, 520))

    # phd
    draw.text((110, 1060), "PhD Outcomes by Field", font=get_font(42, True), fill=MAROON)
    draw_wrapped_text(draw, "Acceptance rates derived from reported applicants and admits.", (1510, 1072), get_font(20), MUTED, 580)
    panel_box(110, 1140, 1980, 760)
    p1 = load_png(assets["phd_core_fields"]).resize((620, 620))
    p2 = load_png(assets["phd_other_disciplines"]).resize((620, 620))
    p3 = load_png(assets["phd_placements"]).resize((620, 620))
    page.paste(p1, (150, 1200))
    page.paste(p2, (790, 1200))
    page.paste(p3, (1430, 1200))

    # professional
    draw.text((110, 1980), "Professional Outcomes (2018–2023)", font=get_font(42, True), fill=MAROON)
    draw_wrapped_text(draw, "Representative employers by common industry.", (1530, 1992), get_font(20), MUTED, 560)
    panel_box(110, 2060, 1980, 620)
    keys = [
        "professional_applied_research",
        "professional_consulting",
        "professional_data_science_analytics",
        "professional_finance",
        "professional_startups_tech",
        "professional_other_sectors",
    ]
    coords = [(150, 2110), (790, 2110), (1430, 2110), (150, 2390), (790, 2390), (1430, 2390)]
    for key, (x, y) in zip(keys, coords):
        img = load_png(assets[key]).resize((620, 240))
        page.paste(img, (x, y))

    page.save(OUTPUT_DIR / f"{stem}.png")
    return {"png": str(OUTPUT_DIR / f"{stem}.png")}

#==========main==========#

def main():
    manifest: dict[str, dict[str, str]] = {}

    manifest["snapshot_key_metrics"] = create_bar_card(
        "Key Metrics",
        [(a, b, c, c) for a, b, c in SNAPSHOT_METRICS],
        "snapshot_key_metrics",
        width=8.6,
        height=4.8,
    )
    manifest["snapshot_big_stat"] = create_big_stat_card(
        "100%",
        "Employment or Doctoral Placement within 9 Months",
        "snapshot_big_stat",
    )
    manifest["phd_core_fields"] = create_bar_card(
        "Core Fields",
        PHD_CORE_FIELDS,
        "phd_core_fields",
        width=7.6,
        height=6.2,
    )
    manifest["phd_other_disciplines"] = create_other_disciplines_card("phd_other_disciplines")
    manifest["phd_placements"] = create_list_card(
        "PhD Placements",
        PHD_PLACEMENTS,
        "phd_placements",
        subtle=PHD_PLACEMENTS_SUBTLE,
        width=980,
        height=660,
    )

    professional_stems = {
        "Applied Research": "professional_applied_research",
        "Consulting": "professional_consulting",
        "Data Science / Analytics": "professional_data_science_analytics",
        "Finance": "professional_finance",
        "Startups / Tech": "professional_startups_tech",
        "Other Sectors": "professional_other_sectors",
    }
    for title, items in PROFESSIONAL.items():
        manifest[professional_stems[title]] = create_list_card(
            title,
            items,
            professional_stems[title],
            width=980,
            height=380,
        )

    manifest["preview"] = make_composite_preview(manifest)

    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved assets to: {OUTPUT_DIR.resolve()}")
    print(f"Manifest: {manifest_path.resolve()}")


if __name__ == "__main__":
    main()
