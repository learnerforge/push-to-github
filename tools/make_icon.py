"""Build assets/urgithub.ico and assets/urgithub.png from assets/urgithub.svg.

Pure Python standard library only — no third-party packages (matches the
project's zero-dependency rule).

Usage:  python tools/make_icon.py
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from iconwrite import write_ico, write_png  # noqa: E402
from svgsub import (  # noqa: E402
    Shape,
    SVG_VIEW,
    circle_points,
    parse_color,
    parse_path,
    render,
    rounded_rect_points,
)

ROOT = Path(__file__).resolve().parent.parent
SVG_FILE = ROOT / "assets" / "urgithub.svg"
OUT_ICO = ROOT / "assets" / "urgithub.ico"
OUT_PNG = ROOT / "assets" / "urgithub.png"

SIZES = (16, 24, 32, 48, 64, 128, 256)
DEFAULT_STROKE_WIDTH = 9.0
NS = "http://www.w3.org/2000/svg"


def build_shapes(root_el):
    shapes = []

    def make():
        return Shape()

    def walk(el, stroke, stroke_width, fill):
        tag = el.tag.split("}")[-1]
        local = {"stroke": stroke, "stroke_width": stroke_width, "fill": fill}
        if "stroke" in el.attrib:
            local["stroke"] = el.attrib["stroke"]
        if "stroke-width" in el.attrib:
            local["stroke_width"] = el.attrib["stroke-width"]
        if "fill" in el.attrib:
            local["fill"] = el.attrib["fill"]

        if tag == "path":
            subpaths, closed = parse_path(el.attrib["d"])
            sh = make()
            sh.polylines = subpaths
            sh.closed = closed
            sh.stroke_color = parse_color(local["stroke"])
            sh.fill_color = parse_color(local["fill"])
            sh.stroke_width = float(local["stroke_width"])
            shapes.append(sh)
        elif tag == "rect":
            x = float(el.attrib["x"])
            y = float(el.attrib["y"])
            w = float(el.attrib["width"])
            h = float(el.attrib["height"])
            rx = float(el.attrib.get("rx", 0.0))
            ry = float(el.attrib.get("ry", rx))
            sh = make()
            sh.polylines = [rounded_rect_points(x, y, w, h, rx, ry)]
            sh.closed = [True]
            sh.stroke_color = parse_color(local["stroke"])
            sh.fill_color = parse_color(local["fill"])
            sh.stroke_width = float(local["stroke_width"])
            shapes.append(sh)
        elif tag == "circle":
            cx = float(el.attrib["cx"])
            cy = float(el.attrib["cy"])
            r = float(el.attrib["r"])
            sh = make()
            sh.polylines = [circle_points(cx, cy, r)]
            sh.closed = [True]
            sh.stroke_color = parse_color(local["stroke"])
            sh.fill_color = parse_color(local["fill"])
            sh.stroke_width = float(local["stroke_width"])
            shapes.append(sh)
        elif tag in ("g", "svg"):
            for child in el:
                walk(child, local["stroke"], float(local["stroke_width"]), local["fill"])

    walk(root_el, "none", DEFAULT_STROKE_WIDTH, "none")
    return shapes


def preview(size, rgba):
    chars = " .:-=+*#%@"
    lines = []
    stride = size * 4
    for y in range(0, size, max(1, size // 32)):
        row = []
        for x in range(0, size, max(1, size // 64)):
            alpha = rgba[y * stride + x * 4 + 3]
            row.append(chars[min(9, (alpha * 10) // 256)])
        lines.append("".join(row))
    return "\n".join(lines)


def verify(size, rgba):
    covered = sum(1 for i in range(0, len(rgba), 4) if rgba[i + 3])
    total = size * size
    return covered, covered * 100.0 / total


def main():
    tree = ET.parse(SVG_FILE)
    root_el = tree.getroot()
    shapes = build_shapes(root_el)
    print(f"Parsed {len(shapes)} shapes from {SVG_FILE.name}")

    png_rgba = render(256, shapes)
    write_png(OUT_PNG, 256, png_rgba)
    print(f"Wrote {OUT_PNG.name} ({OUT_PNG.stat().st_size} bytes)")

    images = [(s, render(s, shapes)) for s in SIZES]
    write_ico(OUT_ICO, images)
    print(f"Wrote {OUT_ICO.name} ({OUT_ICO.stat().st_size} bytes)")

    print("\nSize coverage check:")
    for size, rgba in images:
        covered, pct = verify(size, rgba)
        print(f"  {size:>3}px  {covered:>6} px covered  ({pct:5.1f}%)")

    print("\nPreview (256px):")
    print(preview(256, png_rgba))


if __name__ == "__main__":
    main()
