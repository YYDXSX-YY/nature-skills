#!/usr/bin/env python3
"""Create a minimal pulse-recovery width-distribution line figure from data/133.xlsx.

The script deliberately uses only Python's standard library so the figure can be
regenerated in lean execution environments without changing the source Excel file.
"""

from __future__ import annotations

import html
import math
import re
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "133.xlsx"
OUT_FILE = ROOT / "figures" / "pulse_recovery.svg"

SS_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"a": SS_NS, "r": REL_NS}


def _column_index(cell_ref: str) -> int:
    """Return a zero-based column index from an Excel cell reference."""
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        raise ValueError(f"Cannot parse cell reference: {cell_ref}")
    index = 0
    for char in match.group(1):
        index = index * 26 + ord(char) - ord("A") + 1
    return index - 1


def _read_shared_strings(zf: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    strings: list[str] = []
    for item in root.findall("a:si", NS):
        text = "".join(
            node.text or ""
            for node in item.iter(f"{{{SS_NS}}}t")
        )
        strings.append(text)
    return strings


def _sheet_path_by_name(zf: ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels
    }
    sheets = workbook.find("a:sheets", NS)
    if sheets is None:
        raise ValueError("Workbook does not contain any sheets")
    for sheet in sheets:
        if sheet.attrib.get("name") == sheet_name:
            rid = sheet.attrib[f"{{{REL_NS}}}id"]
            target = rid_to_target[rid]
            return "xl/" + target.lstrip("/")
    raise ValueError(f"Sheet not found: {sheet_name}")


def _read_sheet_rows(path: Path, sheet_name: str) -> list[list[str]]:
    with ZipFile(path) as zf:
        shared_strings = _read_shared_strings(zf)
        sheet_path = _sheet_path_by_name(zf, sheet_name)
        root = ET.fromstring(zf.read(sheet_path))
        rows: list[list[str]] = []
        for row in root.findall(".//a:sheetData/a:row", NS):
            values: list[str] = []
            for cell in row.findall("a:c", NS):
                idx = _column_index(cell.attrib["r"])
                while len(values) <= idx:
                    values.append("")
                value_node = cell.find("a:v", NS)
                value = ""
                if value_node is not None:
                    value = value_node.text or ""
                    if cell.attrib.get("t") == "s":
                        value = shared_strings[int(value)]
                values[idx] = value
            rows.append(values)
        return rows


def _to_float(value: str) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def load_width_distribution(path: Path = DATA_FILE) -> list[dict[str, float | str]]:
    """Load binned width percentages from the workbook's exported-count sheet."""
    rows = _read_sheet_rows(path, "导出计数")
    distribution: list[dict[str, float | str]] = []
    for row in rows[2:]:
        if len(row) < 14:
            continue
        interval = row[7].strip()
        before_pct = _to_float(row[12])
        after_pct = _to_float(row[13])
        before_count = _to_float(row[8])
        after_count = _to_float(row[9])
        if not interval or before_pct is None or after_pct is None:
            continue
        distribution.append(
            {
                "interval": interval,
                "before_pct": before_pct,
                "after_pct": after_pct,
                "before_count": before_count or 0.0,
                "after_count": after_count or 0.0,
            }
        )
    return distribution


def _polyline(points: Iterable[tuple[float, float]], color: str, width: float = 2.2) -> str:
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round" />'


def _circle(x: float, y: float, color: str) -> str:
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.4" fill="white" stroke="{color}" stroke-width="1.8" />'


def draw_svg(distribution: list[dict[str, float | str]], out_file: Path = OUT_FILE) -> None:
    if not distribution:
        raise ValueError("No width-distribution rows were found in data/133.xlsx")

    out_file.parent.mkdir(parents=True, exist_ok=True)

    width, height = 860, 520
    margin_left, margin_right, margin_top, margin_bottom = 78, 34, 58, 118
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    x_count = len(distribution)
    x_step = plot_w / max(x_count - 1, 1)
    ymax = max(
        max(float(item["before_pct"]), float(item["after_pct"]))
        for item in distribution
    )
    y_axis_max = math.ceil((ymax + 2) / 10) * 10

    def x_pos(i: int) -> float:
        return margin_left + i * x_step

    def y_pos(value: float) -> float:
        return margin_top + plot_h - (value / y_axis_max) * plot_h

    before_points = [(x_pos(i), y_pos(float(item["before_pct"]))) for i, item in enumerate(distribution)]
    after_points = [(x_pos(i), y_pos(float(item["after_pct"]))) for i, item in enumerate(distribution)]
    before_total = int(sum(float(item["before_count"]) for item in distribution))
    after_total = int(sum(float(item["after_count"]) for item in distribution))

    grid_parts: list[str] = []
    tick_step = 10
    for tick in range(0, int(y_axis_max) + 1, tick_step):
        y = y_pos(tick)
        grid_parts.append(f'<line x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}" stroke="#e7e7e7" stroke-width="1" />')
        grid_parts.append(f'<text x="{margin_left - 10}" y="{y + 4:.2f}" text-anchor="end" class="tick">{tick}</text>')

    label_parts: list[str] = []
    for i, item in enumerate(distribution):
        x = x_pos(i)
        interval = html.escape(str(item["interval"]))
        label_parts.append(f'<line x1="{x:.2f}" y1="{margin_top + plot_h}" x2="{x:.2f}" y2="{margin_top + plot_h + 5}" stroke="#333" stroke-width="1" />')
        label_parts.append(f'<text x="{x:.2f}" y="{margin_top + plot_h + 18}" text-anchor="end" transform="rotate(-45 {x:.2f},{margin_top + plot_h + 18})" class="tick">{interval}</text>')

    before_color = "#376795"
    after_color = "#d07f2c"
    marker_parts = [
        _circle(x, y, before_color) for x, y in before_points
    ] + [
        _circle(x, y, after_color) for x, y in after_points
    ]

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">Pulse-recovery width distribution</title>
  <desc id="desc">Line chart comparing before- and after-recovery width-bin percentages from data/133.xlsx.</desc>
  <style>
    text {{ font-family: Arial, Helvetica, DejaVu Sans, sans-serif; fill: #1f1f1f; }}
    .title {{ font-size: 18px; font-weight: 700; }}
    .subtitle {{ font-size: 12px; fill: #555; }}
    .axis {{ font-size: 12px; font-weight: 700; }}
    .tick {{ font-size: 10px; fill: #444; }}
    .legend {{ font-size: 12px; }}
  </style>
  <rect width="100%" height="100%" fill="white" />
  <text x="{margin_left}" y="27" class="title">Pulse-recovery crack-width distribution</text>
  <text x="{margin_left}" y="45" class="subtitle">Export-count sheet; line chart selected for a two-condition binned table</text>
  {''.join(grid_parts)}
  <line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" stroke="#222" stroke-width="1.2" />
  <line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{width - margin_right}" y2="{margin_top + plot_h}" stroke="#222" stroke-width="1.2" />
  {''.join(label_parts)}
  {_polyline(before_points, before_color)}
  {_polyline(after_points, after_color)}
  {''.join(marker_parts)}
  <text x="{margin_left + plot_w / 2}" y="{height - 22}" text-anchor="middle" class="axis">Width interval</text>
  <text x="18" y="{margin_top + plot_h / 2}" text-anchor="middle" transform="rotate(-90 18,{margin_top + plot_h / 2})" class="axis">Share of observations (%)</text>
  <line x1="{width - 260}" y1="31" x2="{width - 225}" y2="31" stroke="{before_color}" stroke-width="2.4" />
  <circle cx="{width - 242}" cy="31" r="3.4" fill="white" stroke="{before_color}" stroke-width="1.8" />
  <text x="{width - 215}" y="35" class="legend">Before recovery (n={before_total})</text>
  <line x1="{width - 260}" y1="50" x2="{width - 225}" y2="50" stroke="{after_color}" stroke-width="2.4" />
  <circle cx="{width - 242}" cy="50" r="3.4" fill="white" stroke="{after_color}" stroke-width="1.8" />
  <text x="{width - 215}" y="54" class="legend">After recovery (n={after_total})</text>
</svg>
'''
    out_file.write_text(svg, encoding="utf-8")


def main() -> None:
    distribution = load_width_distribution(DATA_FILE)
    draw_svg(distribution, OUT_FILE)
    print(f"Wrote {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
