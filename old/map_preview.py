"""
Hex Map Preview - Renders Wesnoth WML map data as QPixmap (via Pillow -> QPixmap).
Uses authentic Wesnoth terrain codes with proper hex grid layout.
No custom renderer - just a lightweight preview for the GUI.
"""

import math
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from PySide6.QtGui import QImage, QPixmap


# Wesnoth terrain code -> display color (authentic-ish palette)
TERRAIN_COLORS = {
    "Gg":  "#5b8c3e",   # Grass
    "Gg^Fp": "#2d5a1e", # Forest on grass
    "Gg^Fm": "#6b9c4e", # Flower meadow
    "Re":  "#c4a868",   # Road
    "Hh":  "#9e8c6a",   # Hills
    "Hh^Fp": "#5a7a3a", # Forest on hills
    "Mm":  "#8a8a8a",   # Mountains
    "Mm^Xm": "#aaaaaa", # Snow-capped peak
    "Ms":  "#4a4a4a",   # Impassable mountain
    "Ds":  "#d4b870",   # Desert/sand
    "Ss":  "#4a8ab0",   # Shallow water
    "Ww":  "#2a5a8a",   # Deep water / reef
    "Wo":  "#1a3a6a",   # Ocean
    "Wt":  "#3a6a3a",   # Swamp water
    "St":  "#4a5a2a",   # Swamp
    "Ur":  "#6a5a4a",   # Cave floor
    "Cv":  "#7a7a7a",   # Castle
    "Kh":  "#b8960c",   # Keep
    "Vv":  "#c8a040",   # Village
    "Ha":  "#d8e8f0",   # Snow
    "Ai":  "#a0c0e0",   # Anc ice
    "Xos": "#3a7a3a",   # Oasis
}

HEX_W = 18  # Default hex width


def _parse_terrain_code(code: str) -> str:
    """Parse a WML terrain code and return the base terrain type."""
    code = code.strip()
    for prefix in ["1 ", "2 ", "3 ", "4 ", "5 ", "6 ", "7 ", "8 ", "9 "]:
        if code.startswith(prefix):
            code = code[len(prefix):]
            break
    if code in TERRAIN_COLORS:
        return code
    if "^" in code:
        base = code.split("^")[0]
        if base in TERRAIN_COLORS:
            return base
    return "Gg"


def _get_terrain_color(code: str) -> str:
    """Get the hex color string for a terrain code."""
    parsed = _parse_terrain_code(code)
    return TERRAIN_COLORS.get(parsed, TERRAIN_COLORS["Gg"])


def _hex_corners(cx: float, cy: float, size: float) -> List[Tuple[float, float]]:
    """Get the 6 corner points of a flat-top hexagon centered at (cx, cy)."""
    corners = []
    for i in range(6):
        angle = math.radians(60 * i)
        corners.append((cx + size * math.cos(angle), cy + size * math.sin(angle)))
    return corners


def render_map_to_pixmap(
    map_data: List[str],
    width: int = 420,
    height: int = 280,
    show_grid: bool = True,
    show_legend: bool = True,
) -> QPixmap:
    """
    Render a Wesnoth WML map to a QPixmap using Pillow for rendering.

    Args:
        map_data: List of strings, each a comma-separated row of terrain codes
        width: Output width in pixels
        height: Output height in pixels
        show_grid: Whether to draw hex grid lines
        show_legend: Whether to draw the terrain legend overlay

    Returns:
        QPixmap with the rendered hex map
    """
    img = Image.new("RGBA", (width, height), "#0d1117")
    draw = ImageDraw.Draw(img)

    if not map_data:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except Exception:
            font = ImageFont.load_default()
        draw.text((width // 2 - 40, height // 2 - 8), "No map data", fill="#8090a0", font=font)
        return _pil_to_qpixmap(img)

    map_h = len(map_data)
    map_w = len(map_data[0].split(",")) if map_data[0] else 0
    if map_w == 0 or map_h == 0:
        return _pil_to_qpixmap(img)

    # Calculate hex size to fit
    hex_w_max = (width - 20) / (map_w * 0.75 + 0.25)
    hex_h_max = (height - 20) / (map_h * math.sqrt(3) / 2 + math.sqrt(3) / 2 + 0.5)
    hex_size = min(hex_w_max, hex_h_max, HEX_W)
    hex_size = max(hex_size, 4)

    # Offset to center the map
    total_w = hex_size * 2 + (map_w - 1) * hex_size * 1.5 + hex_size
    total_h = (math.sqrt(3) * hex_size) * map_h + math.sqrt(3) * hex_size * 0.5
    offset_x = max(0, (width - total_w) / 2) + hex_size
    offset_y = max(0, (height - total_h) / 2) + math.sqrt(3) * hex_size * 0.5

    grid_color = "#1a1a2e"

    # Draw hexes
    for row_idx, row_str in enumerate(map_data):
        cells = row_str.split(",")
        for col_idx, cell in enumerate(cells):
            cell = cell.strip()
            if not cell:
                continue

            color = _get_terrain_color(cell)

            w = hex_size * 2
            h = math.sqrt(3) * hex_size
            cx = offset_x + col_idx * w * 0.75
            cy = offset_y + row_idx * h + (col_idx % 2) * h * 0.5

            corners = _hex_corners(cx, cy, hex_size)

            outline = grid_color if show_grid else None
            draw.polygon(corners, fill=color, outline=outline)

    # Draw legend
    if show_legend:
        _draw_legend_pil(draw, map_data, width, height)

    return _pil_to_qpixmap(img)


def _draw_legend_pil(
    draw: ImageDraw.ImageDraw,
    map_data: List[str],
    canvas_w: int,
    canvas_h: int,
):
    """Draw a small terrain legend in the corner using Pillow."""
    terrain_counts: Dict[str, int] = {}
    for row_str in map_data:
        for cell in row_str.split(","):
            cell = cell.strip()
            if cell:
                parsed = _parse_terrain_code(cell)
                terrain_counts[parsed] = terrain_counts.get(parsed, 0) + 1

    if not terrain_counts:
        return

    sorted_terrains = sorted(terrain_counts.items(), key=lambda x: -x[1])[:6]
    if not sorted_terrains:
        return

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 7)
    except Exception:
        try:
            font = ImageFont.load_default(size=7)
        except Exception:
            font = ImageFont.load_default()

    x_start = canvas_w - 100
    y_start = 8
    line_h = 15
    box_h = len(sorted_terrains) * line_h + 6

    # Semi-transparent background
    overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [x_start - 5, y_start - 3, canvas_w - 3, y_start + box_h],
        radius=3, fill=(26, 26, 46, 200), outline=(42, 58, 92, 255),
    )
    # Composite overlay
    from PIL import Image as PILImage
    img_alpha = draw.im  # type: ignore
    overlay_img = PILImage.alpha_composite(
        PILImage.new("RGBA", img_alpha.size, (0, 0, 0, 0)),
        overlay,
    )
    # We need to paste the overlay onto the main image
    # Since we don't have access to the parent Image, we'll draw directly
    # with an opaque approximation instead
    draw.rounded_rectangle(
        [x_start - 5, y_start - 3, canvas_w - 3, y_start + box_h],
        radius=3, fill="#1a1a2e", outline="#2a3a5c",
    )

    for i, (terrain, count) in enumerate(sorted_terrains):
        y = y_start + i * line_h
        color = TERRAIN_COLORS.get(terrain, "#5b8c3e")
        draw.rectangle([x_start, y, x_start + 10, y + 10], fill=color)
        short = terrain.split("^")[0]
        draw.text((x_start + 14, y + 1), f"{short} ({count})", fill="#8090a0", font=font)


def _pil_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    """Convert a PIL Image to a QPixmap."""
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")
    w, h = pil_image.size
    data = pil_image.tobytes("raw", "RGBA", 0, -1)
    qimg = QImage(data, w, h, w * 4, QImage.Format_ARGB32)
    return QPixmap.fromImage(qimg.copy())


def get_terrain_summary(map_data: List[str]) -> Dict[str, int]:
    """Get a summary of terrain types in a map."""
    terrain_counts: Dict[str, int] = {}
    for row_str in map_data:
        for cell in row_str.split(","):
            cell = cell.strip()
            if cell:
                parsed = _parse_terrain_code(cell)
                terrain_counts[parsed] = terrain_counts.get(parsed, 0) + 1
    return terrain_counts


# =============================================================================
# REUSABLE WIDGETS (merged from widgets/__init__.py)
# =============================================================================

"""Reusable widgets and helpers for WesnothAI GUI."""

import os
import sys
import json
import queue
from datetime import datetime
from typing import List, Dict, Optional

from PySide6.QtWidgets import QLabel, QWidget, QListWidget
from PySide6.QtCore import Qt, Signal, QObject

# render_map_to_pixmap is in this file


class MapPreviewLabel(QLabel):
    """A QLabel that displays a rendered hex map pixmap."""
    def __init__(self, parent=None, width=420, height=280):
        super().__init__(parent)
        self._width = width
        self._height = height
        self.setMinimumSize(200, 150)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #0d1117; border: 1px solid #2a3a5c; border-radius: 3px;")
        self.setText("No map data")

    def render_map(self, map_data: List[str]):
        if not map_data:
            self.setText("No map data")
            return
        pixmap = render_map_to_pixmap(map_data, self._width, self._height)
        self.setPixmap(pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.pixmap():
            self.setPixmap(self.pixmap().scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))


class LogSignalEmitter(QObject):
    """Emits log lines across thread boundaries via Qt signals."""
    log_line = Signal(str, str)  # (message, tag)


class RecordingHistory:
    """Tracks completed recordings for the session."""
    def __init__(self, path: str = ""):
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        self.path = path or os.path.join(SCRIPT_DIR, "recording_history.json")
        self.records: List[Dict] = []
        self._load()

    def _load(self):
        try:
            if os.path.isfile(self.path):
                with open(self.path, "r") as f:
                    self.records = json.load(f)
        except Exception:
            self.records = []

    def _save(self):
        try:
            with open(self.path, "w") as f:
                json.dump(self.records[-50:], f, indent=2)
        except Exception:
            pass

    def add(self, scenario_name: str, scenario_id: str, output_path: str,
            duration: str = "", file_size: str = ""):
        record = {
            "timestamp": datetime.now().isoformat(),
            "scenario_name": scenario_name,
            "scenario_id": scenario_id,
            "output_path": output_path,
            "duration": duration,
            "file_size": file_size,
        }
        self.records.append(record)
        self._save()
        return record

    def get_last(self, n: int = 5) -> List[Dict]:
        return self.records[-n:]