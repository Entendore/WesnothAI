"""
WesnothAI - AI Movie Renderer for Battle for Wesnoth
=====================================================
2 tabs (Record, Builder). Auto-scanned addons. Auto-detected Wesnoth.

Files: main.py, gui_app.py, scenarios.py, addon_generator.py,
       wesnoth_bridge.py, video_encoder.py, npc_database.py
"""

import os
import sys
import json
import time
import platform
import threading
import queue
import shutil
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, field

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QSlider, QTextEdit, QLineEdit, QListWidget, QListWidgetItem, QTabWidget,
    QGroupBox, QFileDialog, QMessageBox, QSplitter, QScrollArea, QGridLayout,
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QFont, QPixmap

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from scenarios import ScenarioDef
from wesnoth_bridge import WesnothBridge, RecordingConfig, WesnothPaths, AddonScanner, AddonUnit, DiscoveredAddon
from addon_generator import WesnothAddonGenerator


# =============================================================================
# QUALITY PRESETS
# =============================================================================

class QualityPreset:
    name: str
    resolution: str
    fps: int
    codec: str
    preset: str
    crf: int
    audio_bitrate: str
    description: str
    icon: str


QUALITY_PRESETS: List[QualityPreset] = [
    QualityPreset(
        name="YouTube 1080p",
        resolution="1920x1080",
        fps=30,
        codec="libx264",
        preset="medium",
        crf=23,
        audio_bitrate="192k",
        description="Recommended for YouTube uploads. Good quality at reasonable file size.",
        icon="[YT]",
    ),
    QualityPreset(
        name="YouTube 720p",
        resolution="1280x720",
        fps=30,
        codec="libx264",
        preset="medium",
        crf=23,
        audio_bitrate="128k",
        description="Smaller file for YouTube. Good for longer battles.",
        icon="[YT]",
    ),
    QualityPreset(
        name="Discord Share",
        resolution="1280x720",
        fps=24,
        codec="libx264",
        preset="fast",
        crf=28,
        audio_bitrate="128k",
        description="Optimized for Discord's 25MB file limit for short clips.",
        icon="[DC]",
    ),
    QualityPreset(
        name="High Quality",
        resolution="1920x1080",
        fps=30,
        codec="libx264",
        preset="slow",
        crf=18,
        audio_bitrate="192k",
        description="Best visual quality. Larger files, slower encoding.",
        icon="[HQ]",
    ),
    QualityPreset(
        name="Archive Master",
        resolution="1920x1080",
        fps=30,
        codec="libx264",
        preset="veryslow",
        crf=15,
        audio_bitrate="256k",
        description="Maximum quality for archiving. Very slow encoding.",
        icon="[AR]",
    ),
    QualityPreset(
        name="Fast Preview",
        resolution="1024x576",
        fps=24,
        codec="libx264",
        preset="ultrafast",
        crf=30,
        audio_bitrate="96k",
        description="Quick preview. Low quality but very fast encoding.",
        icon="[Q]",
    ),
    QualityPreset(
        name="4K Ultra HD",
        resolution="2560x1440",
        fps=30,
        codec="libx264",
        preset="slow",
        crf=20,
        audio_bitrate="192k",
        description="Ultra HD for high-end displays. Requires powerful machine.",
        icon="[4K]",
    ),
    QualityPreset(
        name="H.265 Compact",
        resolution="1280x720",
        fps=24,
        codec="libx265",
        preset="medium",
        crf=28,
        audio_bitrate="128k",
        description="H.265/HEVC codec. Much smaller files, very slow encoding.",
        icon="[H5]",
    ),
    QualityPreset(
        name="Custom",
        resolution="1280x720",
        fps=30,
        codec="libx264",
        preset="medium",
        crf=23,
        audio_bitrate="128k",
        description="Use your own settings below.",
        icon="[--]",
    ),
]


def get_preset_by_name(name: str) -> QualityPreset:
    """Return the preset whose *name* matches, falling back to the 'Custom' preset."""
    for p in QUALITY_PRESETS:
        if p.name == name:
            return p
    return QUALITY_PRESETS[8]


def get_preset_menu_items() -> List[str]:
    """Return display strings for a combo-box / menu (icon + name)."""
    return [f"{p.icon} {p.name}" for p in QUALITY_PRESETS]


PRESET_NAMES: List[str] = [p.name for p in QUALITY_PRESETS]


# ---------------------------------------------------------------------------


# =============================================================================
# DARK STYLESHEET
# =============================================================================

DARK_QSS = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Segoe UI", "Noto Sans", sans-serif;
    font-size: 10pt;
}

QGroupBox {
    border: 1px solid #2a3a5c;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 14px;
    font-weight: bold;
    color: #e94560;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}

QPushButton {
    background-color: #1e2a4a;
    color: #e0e0e0;
    border: 1px solid #2a3a5c;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: bold;
    font-size: 10pt;
}
QPushButton:hover {
    background-color: #e94560;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #533483;
}

QPushButton[accent="true"] {
    background-color: #e94560;
    color: #ffffff;
    font-size: 11pt;
}
QPushButton[accent="true"]:hover {
    background-color: #ff6b81;
}

QPushButton[stop="true"] {
    background-color: #e74c3c;
    color: #ffffff;
    font-size: 11pt;
}
QPushButton[stop="true"]:hover {
    background-color: #ff6b6b;
}

QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #1e2a4a;
    color: #e0e0e0;
    border: 1px solid #2a3a5c;
    border-radius: 3px;
    padding: 3px 6px;
    font-size: 10pt;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #e94560;
}

QComboBox {
    background-color: #1e2a4a;
    color: #e0e0e0;
    border: 1px solid #2a3a5c;
    border-radius: 3px;
    padding: 3px 6px;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #1e2a4a;
    color: #e0e0e0;
    selection-background-color: #e94560;
    border: 1px solid #2a3a5c;
}

QListWidget {
    background-color: #1e2a4a;
    color: #e0e0e0;
    border: 1px solid #2a3a5c;
    border-radius: 3px;
    outline: none;
    font-size: 11pt;
}
QListWidget::item {
    padding: 4px 8px;
}
QListWidget::item:selected {
    background-color: #e94560;
    color: #ffffff;
}

QTextEdit {
    background-color: #0d1117;
    color: #8b949e;
    border: 1px solid #2a3a5c;
    border-radius: 3px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 9pt;
}

QTabWidget::pane {
    border: 1px solid #2a3a5c;
    border-radius: 3px;
    background-color: #1a1a2e;
}
QTabBar::tab {
    background-color: #1e2a4a;
    color: #8090a0;
    padding: 8px 18px;
    border: 1px solid #2a3a5c;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #e94560;
    color: #ffffff;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #1e2a4a;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #e94560;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background: #e94560;
    border-radius: 3px;
}

QCheckBox {
    color: #e0e0e0;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #2a3a5c;
    border-radius: 3px;
    background-color: #1e2a4a;
}
QCheckBox::indicator:checked {
    background-color: #e94560;
    border-color: #e94560;
}

QScrollArea {
    border: none;
    background-color: #1a1a2e;
}

QScrollBar:vertical {
    background: #1a1a2e;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #2a3a5c;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #3a4a6c;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QStatusBar {
    background-color: #16213e;
    color: #8090a0;
    font-size: 9pt;
}
"""


# =============================================================================
# MAP PREVIEW RENDERER
# =============================================================================

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


# =============================================================================
# REUSABLE WIDGETS
# =============================================================================

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


# =============================================================================
# RECORD PANEL (scenario browser + batch queue)
# =============================================================================

class RecordPanel(QWidget):
    """Main recording tab: scenario browser + batch queue."""

    # Signals the main window connects to
    scenario_selected = Signal(object)  # emits ScenarioDef or None
    batch_changed = Signal(int)         # emits batch count

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filtered_scenarios: List[ScenarioDef] = list(ALL_SCENARIOS)
        self._batch_scenarios: List[ScenarioDef] = []
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Vertical)
        outer.addWidget(splitter)

        # === Top: Scenario browser ===
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Left: category filter + scenario list
        left_panel = QVBoxLayout()
        left_panel.setContentsMargins(0, 0, 0, 0)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Category:"))
        self.scenario_filter_combo = QComboBox()
        self.scenario_filter_combo.addItems([
            "All Scenarios", "Single Unit", "Wave Attack",
            "King of the Hill", "Multi-Faction",
        ])
        self.scenario_filter_combo.currentTextChanged.connect(self._on_scenario_filter)
        filter_row.addWidget(self.scenario_filter_combo, stretch=1)
        left_panel.addLayout(filter_row)

        self.scenario_list = QListWidget()
        self.scenario_list.currentRowChanged.connect(self._on_scenario_select)
        left_panel.addWidget(self.scenario_list)
        top_layout.addLayout(left_panel, stretch=3)

        # Right: scenario details + map preview
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(0, 0, 0, 0)

        # Scenario details group
        details_group = QGroupBox("Scenario Details")
        details_layout = QVBoxLayout(details_group)
        details_layout.setSpacing(4)

        self.scenario_name_label = QLabel("Select a scenario")
        self.scenario_name_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.scenario_name_label.setWordWrap(True)
        self.scenario_name_label.setStyleSheet("color: #e94560; background: transparent;")
        details_layout.addWidget(self.scenario_name_label)

        self.scenario_desc = QLabel("")
        self.scenario_desc.setWordWrap(True)
        self.scenario_desc.setStyleSheet("color: #c0c0c0; background: transparent; font-size: 9pt;")
        details_layout.addWidget(self.scenario_desc)

        # Info grid
        info_grid = QHBoxLayout()
        self.info_labels = {}
        for key in ("Factions", "Map Size", "Weather", "Turns"):
            lbl = QLabel(f"{key}: --")
            lbl.setStyleSheet("color: #8090a0; background: transparent; font-size: 9pt;")
            info_grid.addWidget(lbl)
            self.info_labels[key] = lbl
        details_layout.addLayout(info_grid)

        # Map preview
        self.map_preview = MapPreviewLabel(self, width=420, height=200)
        details_layout.addWidget(self.map_preview, stretch=1)

        right_panel.addWidget(details_group, stretch=1)
        top_layout.addLayout(right_panel, stretch=4)

        splitter.addWidget(top_widget)

        # === Bottom: Batch queue ===
        batch_widget = QWidget()
        batch_layout = QVBoxLayout(batch_widget)
        batch_layout.setContentsMargins(0, 0, 0, 0)

        batch_header = QHBoxLayout()
        batch_title = QLabel("Batch Queue")
        batch_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        batch_title.setStyleSheet("color: #e94560; background: transparent;")
        batch_header.addWidget(batch_title)

        self.batch_count_label = QLabel("(0 scenarios)")
        self.batch_count_label.setStyleSheet("color: #8090a0; background: transparent;")
        batch_header.addWidget(self.batch_count_label)
        batch_header.addStretch()

        self.add_batch_btn = QPushButton("  Add to Batch  ")
        self.add_batch_btn.clicked.connect(self._add_to_batch)
        batch_header.addWidget(self.add_batch_btn)

        self.clear_batch_btn = QPushButton("  Clear Batch  ")
        self.clear_batch_btn.clicked.connect(self._clear_batch)
        batch_header.addWidget(self.clear_batch_btn)

        batch_layout.addLayout(batch_header)

        self.batch_list = QListWidget()
        self.batch_list.setMaximumHeight(120)
        batch_layout.addWidget(self.batch_list)

        splitter.addWidget(batch_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        # Populate scenarios after all widgets exist
        self._populate_scenario_list()

    def _populate_scenario_list(self):
        """Fill scenario list widget. Must be called after widgets exist."""
        self.scenario_list.blockSignals(True)
        self.scenario_list.clear()
        for s in self._filtered_scenarios:
            factions = " vs ".join(side.faction for side in s.sides)
            self.scenario_list.addItem(f"{s.name}  ({factions})")
        if self._filtered_scenarios:
            self.scenario_list.setCurrentRow(0)
        self.scenario_list.blockSignals(False)
        # Trigger selection manually
        if self._filtered_scenarios:
            self._on_scenario_select(0)

    def _on_scenario_filter(self, category: str):
        self._filtered_scenarios = []
        if category == "All Scenarios":
            self._filtered_scenarios = list(ALL_SCENARIOS)
        else:
            for s in ALL_SCENARIOS:
                cats = get_scenario_categories(s)
                if category in cats:
                    self._filtered_scenarios.append(s)
        self._populate_scenario_list()

    def _on_scenario_select(self, row: int):
        if row < 0 or row >= len(self._filtered_scenarios):
            self.scenario_selected.emit(None)
            return
        scenario = self._filtered_scenarios[row]
        self._show_scenario_details(scenario)
        self.scenario_selected.emit(scenario)

    def _show_scenario_details(self, s: ScenarioDef):
        self.scenario_name_label.setText(s.name)
        self.scenario_desc.setText(s.description)
        factions = " vs ".join(side.faction for side in s.sides)
        self.info_labels["Factions"].setText(f"Factions: {factions}")
        self.info_labels["Map Size"].setText(f"Map: {s.width}x{s.height}")
        self.info_labels["Weather"].setText(f"Weather: {s.weather.value}")
        self.info_labels["Turns"].setText(f"Turns: {s.turns_to_record}/{s.max_turns}")
        if s.map_data:
            self.map_preview.render_map(s.map_data)
        else:
            self.map_preview.setText("No map data")

    def _add_to_batch(self):
        row = self.scenario_list.currentRow()
        if 0 <= row < len(self._filtered_scenarios):
            scenario = self._filtered_scenarios[row]
            self._batch_scenarios.append(scenario)
            factions = " vs ".join(side.faction for side in scenario.sides)
            self.batch_list.addItem(f"{scenario.name}  ({factions})")
            self.batch_count_label.setText(f"({len(self._batch_scenarios)} scenarios)")
            self.batch_changed.emit(len(self._batch_scenarios))

    def _clear_batch(self):
        self._batch_scenarios.clear()
        self.batch_list.clear()
        self.batch_count_label.setText("(0 scenarios)")
        self.batch_changed.emit(0)

    def get_selected_scenario(self) -> Optional[ScenarioDef]:
        row = self.scenario_list.currentRow()
        if 0 <= row < len(self._filtered_scenarios):
            return self._filtered_scenarios[row]
        return None

    def get_batch_scenarios(self) -> List[ScenarioDef]:
        return list(self._batch_scenarios)


# =============================================================================
# RECORDING PANEL (merged from panels/recording_panel.py)
# =============================================================================

"""Recording Panel — Quality config, record controls, and log output."""

import os
import sys
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSpinBox, QSlider, QTextEdit, QLineEdit, QFileDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# QUALITY_PRESETS and get_preset_menu_items defined above in this file


# =============================================================================
# RECORDING PANEL (quality config + controls + log)
# =============================================================================

class RecordingPanel(QWidget):
    """Bottom panel: Wesnoth path, quality preset, record/batch/stop buttons, log."""

    # Signals
    record_single = Signal()
    record_batch = Signal()
    stop_recording = Signal()
    open_output = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_recording = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)

        # === Row 1: Wesnoth path + Output dir ===
        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        path_row.addWidget(QLabel("Wesnoth:"))
        self.wesnoth_path_label = QLabel("Not detected")
        self.wesnoth_path_label.setStyleSheet(
            "color: #e74c3c; background: #1e2a4a; padding: 2px 8px; "
            "border: 1px solid #2a3a5c; border-radius: 3px; font-size: 9pt;"
        )
        self.wesnoth_path_label.setWordWrap(False)
        path_row.addWidget(self.wesnoth_path_label, stretch=2)

        self.wesnoth_browse_btn = QPushButton("Browse")
        self.wesnoth_browse_btn.clicked.connect(self._browse_wesnoth)
        path_row.addWidget(self.wesnoth_browse_btn)

        path_row.addWidget(QLabel("Output:"))
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("Select output directory...")
        self.output_dir_input.setText(os.path.join(SCRIPT_DIR, "output"))
        path_row.addWidget(self.output_dir_input, stretch=2)
        self.output_browse_btn = QPushButton("...")
        self.output_browse_btn.setFixedWidth(30)
        self.output_browse_btn.clicked.connect(self._browse_output)
        path_row.addWidget(self.output_browse_btn)

        layout.addLayout(path_row)

        # === Row 2: Quality settings ===
        quality_row = QHBoxLayout()
        quality_row.setSpacing(8)

        quality_row.addWidget(QLabel("Preset:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(get_preset_menu_items())
        self.quality_combo.setCurrentIndex(0)
        self.quality_combo.currentIndexChanged.connect(self._on_preset_change)
        quality_row.addWidget(self.quality_combo)

        quality_row.addWidget(QLabel("Resolution:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["1920x1080", "1280x720", "1024x576", "854x480", "2560x1440"])
        self.resolution_combo.setCurrentText("1280x720")
        quality_row.addWidget(self.resolution_combo)

        quality_row.addWidget(QLabel("FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(10, 60)
        self.fps_spin.setValue(30)
        quality_row.addWidget(self.fps_spin)

        quality_row.addWidget(QLabel("CRF:"))
        self.crf_slider = QSlider(Qt.Horizontal)
        self.crf_slider.setRange(0, 51)
        self.crf_slider.setValue(23)
        self.crf_slider.setMaximumWidth(120)
        self.crf_slider.valueChanged.connect(self._on_crf_change)
        quality_row.addWidget(self.crf_slider)
        self.crf_label = QLabel("23")
        self.crf_label.setStyleSheet("color: #e94560; background: transparent; font-weight: bold; min-width: 24px;")
        quality_row.addWidget(self.crf_label)

        quality_row.addStretch()
        layout.addLayout(quality_row)

        # === Row 3: Action buttons ===
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.record_btn = QPushButton("  Record  ")
        self.record_btn.setProperty("accent", True)
        self.record_btn.clicked.connect(self.record_single.emit)
        btn_row.addWidget(self.record_btn)

        self.batch_btn = QPushButton("  Record Batch  ")
        self.batch_btn.clicked.connect(self.record_batch.emit)
        btn_row.addWidget(self.batch_btn)

        self.stop_btn = QPushButton("  Stop  ")
        self.stop_btn.setProperty("stop", True)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_recording.emit)
        btn_row.addWidget(self.stop_btn)

        self.open_btn = QPushButton("  Open Output  ")
        self.open_btn.clicked.connect(self.open_output.emit)
        btn_row.addWidget(self.open_btn)

        btn_row.addStretch()

        self.recording_status = QLabel("Ready")
        self.recording_status.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.recording_status.setStyleSheet("color: #2ecc71; background: transparent;")
        btn_row.addWidget(self.recording_status)

        layout.addLayout(btn_row)

        # === Log area ===
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(140)
        self.log_text.setStyleSheet(
            "background-color: #0d1117; color: #8b949e; "
            "border: 1px solid #2a3a5c; border-radius: 3px; "
            "font-family: 'Consolas', 'Courier New', monospace; font-size: 9pt;"
        )
        layout.addWidget(self.log_text)

        # Initialize preset defaults
        self._on_preset_change(0)

    # --- Preset ---

    def _on_preset_change(self, index: int):
        if index < 0 or index >= len(QUALITY_PRESETS):
            return
        preset = QUALITY_PRESETS[index]
        if preset.name == "Custom":
            return

        for w in (self.resolution_combo, self.fps_spin, self.crf_slider):
            w.blockSignals(True)
        self.resolution_combo.setCurrentText(preset.resolution)
        self.fps_spin.setValue(preset.fps)
        self.crf_slider.setValue(preset.crf)
        self.crf_label.setText(str(preset.crf))
        for w in (self.resolution_combo, self.fps_spin, self.crf_slider):
            w.blockSignals(False)

    def _on_crf_change(self, value: int):
        self.crf_label.setText(str(value))

    # --- Browse ---

    def _browse_wesnoth(self):
        filt = "Executables (*.exe);;All Files (*)" if sys.platform == "win32" else "All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select Wesnoth Binary", "", filt)
        if path:
            self.wesnoth_path_label.setText(path)
            self.wesnoth_path_label.setStyleSheet(
                "color: #2ecc71; background: #1e2a4a; padding: 2px 8px; "
                "border: 1px solid #2a3a5c; border-radius: 3px; font-size: 9pt;"
            )

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.output_dir_input.setText(path)

    # --- Public API ---

    def set_recording_state(self, is_recording: bool):
        self._is_recording = is_recording
        self.record_btn.setEnabled(not is_recording)
        self.batch_btn.setEnabled(not is_recording)
        self.stop_btn.setEnabled(is_recording)
        if is_recording:
            self.recording_status.setText("Recording...")
            self.recording_status.setStyleSheet("color: #e94560; background: transparent;")
        else:
            self.recording_status.setText("Ready")
            self.recording_status.setStyleSheet("color: #2ecc71; background: transparent;")

    def set_wesnoth_path(self, path: str, found: bool = True):
        self.wesnoth_path_label.setText(path or "Not detected")
        color = "#2ecc71" if found else "#e74c3c"
        self.wesnoth_path_label.setStyleSheet(
            f"color: {color}; background: #1e2a4a; padding: 2px 8px; "
            "border: 1px solid #2a3a5c; border-radius: 3px; font-size: 9pt;"
        )

    def set_addon_dir(self, path: str):
        """No-op in new design. Addon dirs are auto-scanned, not displayed here."""
        pass

    def append_log(self, message: str, tag: str = ""):
        color = {"error": "#e74c3c", "success": "#2ecc71", "warning": "#f39c12",
                 "warn": "#f39c12", "info": "#3498db"}.get(tag, "#e0e0e0")
        self.log_text.append(f'<span style="color: {color}">{message}</span>')
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def get_config_dict(self) -> dict:
        res_text = self.resolution_combo.currentText()
        w, h = res_text.split("x")
        idx = self.quality_combo.currentIndex()
        return {
            "resolution": (int(w), int(h)),
            "fps": self.fps_spin.value(),
            "crf": self.crf_slider.value(),
            "preset_name": QUALITY_PRESETS[idx].name,
            "codec": QUALITY_PRESETS[idx].codec,
            "preset": QUALITY_PRESETS[idx].preset,
            "audio_bitrate": QUALITY_PRESETS[idx].audio_bitrate,
            "output_dir": self.output_dir_input.text(),
        }

    def get_wesnoth_path(self) -> str:
        text = self.wesnoth_path_label.text()
        return "" if text in ("Not detected", "") else text


# =============================================================================
# BUILDER PANEL (custom scenario builder)
# =============================================================================

class BuilderPanel(QWidget):
    """Custom scenario builder tab with all build modes."""

    scenario_generated = Signal(object)   # emits ScenarioDef
    custom_added = Signal(object)         # emits ScenarioDef (added to main list)
    log_message = Signal(str, str)        # (message, tag)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_scenario: Optional[ScenarioDef] = None
        self._addon_unit_ids: List[str] = []
        self._setup_ui()

    def _setup_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter)

        # === Left: Configuration (scrollable) ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setSpacing(6)

        # --- Builder Type ---
        type_group = QGroupBox("  Builder Type  ")
        type_layout = QVBoxLayout(type_group)
        self.builder_type_combo = QComboBox()
        self.builder_type_combo.addItems([
            "Standard (2 Factions)", "Multi-Faction (3+)", "Wave Attack", "King of the Hill",
        ])
        self.builder_type_combo.currentTextChanged.connect(self._on_builder_type_change)
        type_layout.addWidget(self.builder_type_combo)

        # Name + seed row
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self.custom_name_edit = QLineEdit("Custom Battle")
        name_row.addWidget(self.custom_name_edit, stretch=1)
        name_row.addWidget(QLabel("Seed:"))
        self.custom_seed_spin = QSpinBox()
        self.custom_seed_spin.setRange(1, 99999)
        self.custom_seed_spin.setValue(42)
        name_row.addWidget(self.custom_seed_spin)
        type_layout.addLayout(name_row)

        # Gold + units + turns row
        param_row = QHBoxLayout()
        param_row.addWidget(QLabel("Gold:"))
        self.custom_gold_spin = QSpinBox()
        self.custom_gold_spin.setRange(50, 500)
        self.custom_gold_spin.setSingleStep(25)
        self.custom_gold_spin.setValue(150)
        param_row.addWidget(self.custom_gold_spin)
        param_row.addWidget(QLabel("Units/Side:"))
        self.custom_units_spin = QSpinBox()
        self.custom_units_spin.setRange(2, 12)
        self.custom_units_spin.setValue(4)
        param_row.addWidget(self.custom_units_spin)
        param_row.addWidget(QLabel("Turns:"))
        self.custom_turns_spin = QSpinBox()
        self.custom_turns_spin.setRange(5, 60)
        self.custom_turns_spin.setSingleStep(5)
        self.custom_turns_spin.setValue(25)
        param_row.addWidget(self.custom_turns_spin)
        type_layout.addLayout(param_row)

        left.addWidget(type_group)

        # --- Random Matchup ---
        rand_group = QGroupBox("  Random Matchup  ")
        rand_layout = QHBoxLayout(rand_group)
        self.random_btn = QPushButton("  Generate Random Matchup  ")
        self.random_btn.setProperty("accent", True)
        self.random_btn.clicked.connect(self._on_random_matchup)
        rand_layout.addWidget(self.random_btn)
        left.addWidget(rand_group)

        # --- Side 1 Config ---
        self.side1_group = QGroupBox("  Side 1 — Red  ")
        self.side1_group.setStyleSheet("QGroupBox { color: #e74c3c; }")
        s1_layout = QGridLayout(self.side1_group)
        s1_layout.setSpacing(4)

        s1_layout.addWidget(QLabel("Faction:"), 0, 0)
        self.faction_a_combo = QComboBox()
        self.faction_a_combo.addItems(list(FACTION_INFO.keys()))
        self.faction_a_combo.currentTextChanged.connect(self._on_s1_faction_change)
        s1_layout.addWidget(self.faction_a_combo, 0, 1)

        s1_layout.addWidget(QLabel("Leader:"), 1, 0)
        self.s1_leader = QComboBox()
        s1_layout.addWidget(self.s1_leader, 1, 1)

        s1_layout.addWidget(QLabel("Gold:"), 2, 0)
        self.s1_gold = QSpinBox()
        self.s1_gold.setRange(50, 1000)
        self.s1_gold.setValue(200)
        self.s1_gold.setSingleStep(25)
        s1_layout.addWidget(self.s1_gold, 2, 1)

        s1_layout.addWidget(QLabel("Units:"), 3, 0)
        self.s1_units = QSpinBox()
        self.s1_units.setRange(1, 20)
        self.s1_units.setValue(5)
        s1_layout.addWidget(self.s1_units, 3, 1)

        left.addWidget(self.side1_group)

        # --- Side 2 Config ---
        self.side2_group = QGroupBox("  Side 2 — Blue  ")
        self.side2_group.setStyleSheet("QGroupBox { color: #3498db; }")
        s2_layout = QGridLayout(self.side2_group)
        s2_layout.setSpacing(4)

        s2_layout.addWidget(QLabel("Faction:"), 0, 0)
        self.faction_b_combo = QComboBox()
        self.faction_b_combo.addItems(list(FACTION_INFO.keys()))
        self.faction_b_combo.setCurrentIndex(1)
        self.faction_b_combo.currentTextChanged.connect(self._on_s2_faction_change)
        s2_layout.addWidget(self.faction_b_combo, 0, 1)

        s2_layout.addWidget(QLabel("Leader:"), 1, 0)
        self.s2_leader = QComboBox()
        s2_layout.addWidget(self.s2_leader, 1, 1)

        s2_layout.addWidget(QLabel("Gold:"), 2, 0)
        self.s2_gold = QSpinBox()
        self.s2_gold.setRange(50, 1000)
        self.s2_gold.setValue(200)
        self.s2_gold.setSingleStep(25)
        s2_layout.addWidget(self.s2_gold, 2, 1)

        s2_layout.addWidget(QLabel("Units:"), 3, 0)
        self.s2_units = QSpinBox()
        self.s2_units.setRange(1, 20)
        self.s2_units.setValue(5)
        s2_layout.addWidget(self.s2_units, 3, 1)

        left.addWidget(self.side2_group)

        # --- Specific Unit Mode ---
        self.specific_unit_cb = QCheckBox("Use specific unit only (e.g. Vampire Bat Swarm)")
        self.specific_unit_cb.setStyleSheet("color: #f39c12; background: transparent;")
        self.specific_unit_cb.setToolTip(
            "When checked, ALL extra units on Side 1 will be the same type."
        )
        left.addWidget(self.specific_unit_cb)

        spec_row = QHBoxLayout()
        spec_row.addWidget(QLabel("Unit Type:"))
        self.specific_unit_combo = QComboBox()
        self.specific_unit_combo.setEditable(True)
        self.specific_unit_combo.setMinimumWidth(200)
        all_known_units = set()
        for units in FACTION_UNIT_POOLS.values():
            all_known_units.update(units)
        for uid in sorted(all_known_units):
            self.specific_unit_combo.addItem(uid)
        spec_row.addWidget(self.specific_unit_combo, stretch=1)
        left.addLayout(spec_row)

        # --- Map Config ---
        map_group = QGroupBox("  Map Configuration  ")
        map_layout = QGridLayout(map_group)
        map_layout.setSpacing(4)

        map_layout.addWidget(QLabel("Template:"), 0, 0)
        self.map_template = QComboBox()
        self.map_template.addItems(list(MAP_TEMPLATES.keys()))
        self.map_template.currentTextChanged.connect(self._on_template_change)
        map_layout.addWidget(self.map_template, 0, 1)

        map_layout.addWidget(QLabel("Width:"), 1, 0)
        self.map_width = QSpinBox()
        self.map_width.setRange(10, 40)
        self.map_width.setValue(20)
        map_layout.addWidget(self.map_width, 1, 1)

        map_layout.addWidget(QLabel("Height:"), 2, 0)
        self.map_height = QSpinBox()
        self.map_height.setRange(8, 30)
        self.map_height.setValue(14)
        map_layout.addWidget(self.map_height, 2, 1)

        left.addWidget(map_group)

        # --- Multi-Faction Panel (hidden by default) ---
        self.multi_faction_group = QGroupBox("  Factions  ")
        mf_layout = QVBoxLayout(self.multi_faction_group)
        mf_layout.setSpacing(3)

        self.faction_list_widget = QListWidget()
        self.faction_list_widget.setMaximumHeight(120)
        for fname in list(FACTION_INFO.keys()):
            self.faction_list_widget.addItem(fname)
        for i in range(min(3, self.faction_list_widget.count())):
            self.faction_list_widget.item(i).setSelected(True)
        mf_layout.addWidget(self.faction_list_widget)

        mf_btn_row = QHBoxLayout()
        mf_add_btn = QPushButton("+ Add")
        mf_add_btn.clicked.connect(self._mf_add_faction)
        mf_remove_btn = QPushButton("- Remove")
        mf_remove_btn.clicked.connect(self._mf_remove_faction)
        mf_btn_row.addWidget(mf_add_btn)
        mf_btn_row.addWidget(mf_remove_btn)
        self._mf_count_label = QLabel("Selected: 3")
        self._mf_count_label.setStyleSheet("color: #8090a0; background: transparent;")
        mf_btn_row.addWidget(self._mf_count_label)
        mf_btn_row.addStretch()
        mf_layout.addLayout(mf_btn_row)

        self.multi_faction_group.setVisible(False)
        left.addWidget(self.multi_faction_group)

        # --- Wave Attack Panel (hidden by default) ---
        self.wave_group = QGroupBox("  Wave Settings  ")
        wave_layout = QGridLayout(self.wave_group)
        wave_layout.setSpacing(4)

        wave_layout.addWidget(QLabel("Attacker:"), 0, 0, Qt.AlignRight)
        self.wave_attacker_combo = QComboBox()
        self.wave_attacker_combo.addItems(list(FACTION_INFO.keys()))
        self.wave_attacker_combo.setCurrentText("Undead")
        wave_layout.addWidget(self.wave_attacker_combo, 0, 1)

        wave_layout.addWidget(QLabel("Defender:"), 1, 0, Qt.AlignRight)
        self.wave_defender_combo = QComboBox()
        self.wave_defender_combo.addItems(list(FACTION_INFO.keys()))
        self.wave_defender_combo.setCurrentText("Loyalists")
        wave_layout.addWidget(self.wave_defender_combo, 1, 1)

        wave_layout.addWidget(QLabel("Wave Interval:"), 2, 0, Qt.AlignRight)
        self.wave_interval_spin = QSpinBox()
        self.wave_interval_spin.setRange(2, 8)
        self.wave_interval_spin.setValue(3)
        wave_layout.addWidget(self.wave_interval_spin, 2, 1, Qt.AlignLeft)

        wave_layout.addWidget(QLabel("Num Waves:"), 3, 0, Qt.AlignRight)
        self.wave_count_spin = QSpinBox()
        self.wave_count_spin.setRange(3, 15)
        self.wave_count_spin.setValue(6)
        wave_layout.addWidget(self.wave_count_spin, 3, 1, Qt.AlignLeft)

        wave_layout.addWidget(QLabel("Units/Wave:"), 4, 0, Qt.AlignRight)
        self.wave_size_spin = QSpinBox()
        self.wave_size_spin.setRange(2, 12)
        self.wave_size_spin.setValue(4)
        wave_layout.addWidget(self.wave_size_spin, 4, 1, Qt.AlignLeft)

        self.wave_group.setVisible(False)
        left.addWidget(self.wave_group)

        # --- KotH Panel (hidden by default) ---
        self.koth_group = QGroupBox("  King of the Hill  ")
        koth_layout = QGridLayout(self.koth_group)
        koth_layout.setSpacing(4)

        koth_layout.addWidget(QLabel("Factions:"), 0, 0, Qt.AlignRight)
        self.koth_faction_spin = QSpinBox()
        self.koth_faction_spin.setRange(3, 9)
        self.koth_faction_spin.setValue(4)
        koth_layout.addWidget(self.koth_faction_spin, 0, 1, Qt.AlignLeft)

        koth_hint = QLabel("Uses the faction list above")
        koth_hint.setStyleSheet("color: #8090a0; background: transparent; font-size: 8pt;")
        koth_layout.addWidget(koth_hint, 1, 0, 1, 2)

        self.koth_group.setVisible(False)
        left.addWidget(self.koth_group)

        # --- Action buttons ---
        btn_row = QHBoxLayout()
        self.generate_btn = QPushButton("  Generate & Preview  ")
        self.generate_btn.setProperty("accent", True)
        self.generate_btn.clicked.connect(self._on_generate)
        btn_row.addWidget(self.generate_btn)

        self.add_to_list_btn = QPushButton("  Add to Scenario List  ")
        self.add_to_list_btn.clicked.connect(self._on_add_to_list)
        btn_row.addWidget(self.add_to_list_btn)
        left.addLayout(btn_row)

        left.addStretch()
        scroll.setWidget(left_widget)
        splitter.addWidget(scroll)

        # === Right: Map preview + addon units ===
        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(6)

        # Preview
        preview_group = QGroupBox("  Preview  ")
        preview_layout = QVBoxLayout(preview_group)

        self.custom_preview_label = QLabel("Build a scenario and click Generate & Preview")
        self.custom_preview_label.setStyleSheet("color: #8090a0; background: transparent;")
        preview_layout.addWidget(self.custom_preview_label)

        self.builder_map_preview = MapPreviewLabel(self, width=500, height=300)
        preview_layout.addWidget(self.builder_map_preview, stretch=1)

        self.builder_info = QLabel("")
        self.builder_info.setWordWrap(True)
        self.builder_info.setStyleSheet("color: #8090a0; background: transparent; font-size: 9pt;")
        preview_layout.addWidget(self.builder_info)

        right.addWidget(preview_group, stretch=3)

        # Addon Units section
        addon_group = QGroupBox("  Addon Units  ")
        addon_layout = QVBoxLayout(addon_group)
        addon_layout.setContentsMargins(8, 16, 8, 6)
        addon_layout.setSpacing(4)

        addon_splitter = QSplitter(Qt.Horizontal)
        addon_layout.addWidget(addon_splitter, stretch=1)

        # Addon list
        addon_left = QWidget()
        addon_left_layout = QVBoxLayout(addon_left)
        addon_left_layout.setContentsMargins(0, 0, 0, 0)
        addon_list_label = QLabel("Discovered Addons:")
        addon_list_label.setStyleSheet("color: #e94560; background: transparent; font-weight: bold;")
        addon_left_layout.addWidget(addon_list_label)
        self.addon_list = QListWidget()
        addon_left_layout.addWidget(self.addon_list, stretch=1)
        addon_splitter.addWidget(addon_left)

        # Unit list
        addon_right = QWidget()
        addon_right_layout = QVBoxLayout(addon_right)
        addon_right_layout.setContentsMargins(0, 0, 0, 0)
        unit_list_label = QLabel("Units in Selected Addon:")
        unit_list_label.setStyleSheet("color: #e94560; background: transparent; font-weight: bold;")
        addon_right_layout.addWidget(unit_list_label)
        self.addon_unit_list = QListWidget()
        addon_right_layout.addWidget(self.addon_unit_list, stretch=1)
        addon_splitter.addWidget(addon_right)
        addon_splitter.setSizes([300, 400])

        # Addon buttons
        addon_btn_row = QHBoxLayout()
        self.addon_status_label = QLabel("No addons scanned yet.")
        self.addon_status_label.setStyleSheet("color: #8090a0; background: transparent;")
        addon_btn_row.addWidget(self.addon_status_label)
        addon_btn_row.addStretch()
        self.use_addon_units_btn = QPushButton("Add All to Builder")
        self.use_addon_units_btn.clicked.connect(self._add_addon_units_to_builder)
        addon_btn_row.addWidget(self.use_addon_units_btn)
        addon_layout.addLayout(addon_btn_row)

        right.addWidget(addon_group, stretch=2)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])

        # Initialize faction leader combos
        self._on_s1_faction_change(self.faction_a_combo.currentText())
        self._on_s2_faction_change(self.faction_b_combo.currentText())
        self._on_template_change(self.map_template.currentText())

    # =========================================================================
    # FACTION HELPERS
    # =========================================================================

    def _on_s1_faction_change(self, faction: str):
        self.s1_leader.blockSignals(True)
        self.s1_leader.clear()
        leader = get_leader_for_faction(faction)
        units = get_recruitable_units(faction)
        self.s1_leader.addItems([leader] + units)
        self.s1_leader.blockSignals(False)

    def _on_s2_faction_change(self, faction: str):
        self.s2_leader.blockSignals(True)
        self.s2_leader.clear()
        leader = get_leader_for_faction(faction)
        units = get_recruitable_units(faction)
        self.s2_leader.addItems([leader] + units)
        self.s2_leader.blockSignals(False)

    def _on_template_change(self, template_name: str):
        tpl = MAP_TEMPLATES.get(template_name)
        if tpl:
            self.map_width.blockSignals(True)
            self.map_height.blockSignals(True)
            self.map_width.setValue(tpl["w"])
            self.map_height.setValue(tpl["h"])
            self.map_width.blockSignals(False)
            self.map_height.blockSignals(False)

    # =========================================================================
    # BUILDER TYPE SWITCHING
    # =========================================================================

    def _on_builder_type_change(self, btype: str):
        is_standard = "Standard" in btype
        is_multi = "Multi-Faction" in btype
        is_wave = "Wave" in btype
        is_koth = "Hill" in btype

        self.multi_faction_group.setVisible(is_multi)
        self.wave_group.setVisible(is_wave)
        self.koth_group.setVisible(is_koth)

        self.side1_group.setVisible(is_standard or is_wave)
        self.side2_group.setVisible(is_standard)

        if is_wave:
            self.custom_name_edit.setText("Wave Attack")
        elif is_multi:
            self.custom_name_edit.setText("Multi-Faction Battle")
        elif is_koth:
            self.custom_name_edit.setText("King of the Hill")
        else:
            self.custom_name_edit.setText("Custom Battle")

    # =========================================================================
    # MULTI-FACTION HELPERS
    # =========================================================================

    def _mf_add_faction(self):
        current = self.faction_list_widget.count()
        selected = sum(1 for i in range(current) if self.faction_list_widget.item(i).isSelected())
        for i in range(current):
            if not self.faction_list_widget.item(i).isSelected():
                self.faction_list_widget.item(i).setSelected(True)
                selected += 1
                break
        self._mf_count_label.setText(f"Selected: {selected}")

    def _mf_remove_faction(self):
        current = self.faction_list_widget.count()
        selected_indices = [i for i in range(current) if self.faction_list_widget.item(i).isSelected()]
        if selected_indices:
            self.faction_list_widget.item(selected_indices[-1]).setSelected(False)
        selected = sum(1 for i in range(current) if self.faction_list_widget.item(i).isSelected())
        self._mf_count_label.setText(f"Selected: {selected}")

    def _get_selected_factions(self) -> List[str]:
        factions = []
        for i in range(self.faction_list_widget.count()):
            if self.faction_list_widget.item(i).isSelected():
                factions.append(self.faction_list_widget.item(i).text())
        return factions

    # =========================================================================
    # RANDOM MATCHUP
    # =========================================================================

    def _on_random_matchup(self):
        a, b = get_random_matchup()
        self.faction_a_combo.setCurrentText(a)
        self.faction_b_combo.setCurrentText(b)
        self.custom_seed_spin.setValue(random.randint(1, 99999))
        self.log_message.emit(f"Random matchup: {a} vs {b}", "info")

    # =========================================================================
    # GENERATE
    # =========================================================================

    def _on_generate(self):
        from PySide6.QtWidgets import QMessageBox

        try:
            btype = self.builder_type_combo.currentText()
            specific_unit = None
            if self.specific_unit_cb.isChecked():
                specific_unit = self.specific_unit_combo.currentText().strip()
                if not specific_unit:
                    QMessageBox.warning(self, "Warning", "Enter or select a unit type!")
                    return

            name = self.custom_name_edit.text()
            template = self.map_template.currentText()
            seed = self.custom_seed_spin.value()
            turns = self.custom_turns_spin.value()
            ups = self.custom_units_spin.value()

            if "Wave" in btype:
                scenario = build_wave_scenario(
                    name=name,
                    attacker_faction=self.wave_attacker_combo.currentText(),
                    defender_faction=self.wave_defender_combo.currentText(),
                    template=template,
                    gold_attacker=300, gold_defender=200,
                    income_attacker=5, income_defender=3,
                    max_turns=40, record_turns=turns,
                    wave_interval=self.wave_interval_spin.value(),
                    num_waves=self.wave_count_spin.value(),
                    units_per_wave=self.wave_size_spin.value(),
                    seed=seed,
                )
            elif "Multi-Faction" in btype:
                factions = self._get_selected_factions()
                if len(factions) < 3:
                    QMessageBox.warning(self, "Warning", "Select at least 3 factions for multi-faction!")
                    return
                scenario = build_multi_faction_scenario(
                    name=name, factions=factions,
                    template=template,
                    gold=120, income=1,
                    max_turns=35, record_turns=turns,
                    units_per_side=ups, seed=seed,
                )
            elif "Hill" in btype:
                factions = self._get_selected_factions()
                n_factions = self.koth_faction_spin.value()
                if len(factions) < n_factions:
                    QMessageBox.warning(self, "Warning", f"Select at least {n_factions} factions!")
                    return
                factions = factions[:n_factions]
                scenario = build_koth_scenario(
                    name=name, factions=factions,
                    template=template,
                    gold=130, income=1,
                    max_turns=30, record_turns=turns,
                    units_per_side=ups, seed=seed,
                )
            else:
                # Standard 2-faction
                scenario = build_custom_scenario(
                    name=name,
                    faction1=self.faction_a_combo.currentText(),
                    faction2=self.faction_b_combo.currentText(),
                    leader1=self.s1_leader.currentText(),
                    leader2=self.s2_leader.currentText(),
                    gold1=self.s1_gold.value(),
                    gold2=self.s2_gold.value(),
                    units1=self.s1_units.value(),
                    units2=self.s2_units.value(),
                    template_name=template,
                    width=self.map_width.value(),
                    height=self.map_height.value(),
                    seed=seed,
                    specific_unit=specific_unit,
                    addon_units=self._addon_unit_ids,
                )

            if scenario and scenario.map_data:
                self._last_scenario = scenario
                self.builder_map_preview.render_map(scenario.map_data)

                tmpl = MAP_TEMPLATES.get(template, {})
                factions_str = " vs ".join(s.faction for s in scenario.sides)
                extra = ""
                if scenario.turn_events and any(e.get("action") == "reinforcements" for e in scenario.turn_events):
                    wave_count = sum(1 for e in scenario.turn_events if e.get("action") == "reinforcements")
                    extra = f" | Waves: {wave_count}"
                self.builder_info.setText(
                    f"Map: {scenario.width}x{scenario.height} | "
                    f"Factions ({len(scenario.sides)}): {factions_str} | "
                    f"Terrain: {tmpl.get('description', 'N/A')}{extra}"
                )
                self.custom_preview_label.setText(f"'{scenario.name}' generated successfully!")
                self.custom_preview_label.setStyleSheet("color: #2ecc71; background: transparent;")
                self.log_message.emit(
                    f"Custom scenario generated: {scenario.name} ({scenario.width}x{scenario.height})",
                    "success",
                )
                self.scenario_generated.emit(scenario)
            else:
                self.builder_info.setText("Failed to generate scenario.")
                self.log_message.emit("Failed to generate scenario.", "error")

        except Exception as e:
            self.log_message.emit(f"Error building custom scenario: {e}", "error")
            from PySide6.QtWidgets import QMessageBox as MB
            MB.critical(self, "Error", f"Failed to build scenario:\n{e}")

    def _on_add_to_list(self):
        if not self._last_scenario:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Warning", "Generate a scenario first!")
            return
        self.custom_added.emit(self._last_scenario)
        self.log_message.emit(f"Added custom scenario: {self._last_scenario.name}", "success")

    # =========================================================================
    # ADDON UNITS
    # =========================================================================

    def set_discovered_addons(self, addons, addon_units):
        """Called from main window to populate addon lists."""
        self._discovered_addons = addons
        self._addon_units = addon_units

        self.addon_list.clear()
        if not addons:
            self.addon_status_label.setText("No addons with custom units found.")
            return

        total_units = sum(a.unit_count for a in addons)
        self.addon_status_label.setText(
            f"Found {len(addons)} addon(s) with {total_units} custom unit(s)."
        )
        for addon in addons:
            display = f"{addon.name}  ({addon.unit_count} units)"
            self.addon_list.addItem(display)
        if addons:
            self.addon_list.setCurrentRow(0)

    def _on_addon_select(self, row: int):
        self.addon_unit_list.clear()
        if row < 0 or row >= len(getattr(self, '_discovered_addons', [])):
            return
        addon = self._discovered_addons[row]
        for unit in addon.units:
            hp_str = f"HP:{unit.hp}" if unit.hp > 0 else ""
            faction_str = f"[{unit.faction}] " if unit.faction else ""
            display = f"{unit.unit_id}  -  {faction_str}{unit.name}  {hp_str}"
            self.addon_unit_list.addItem(display)

    def _add_addon_units_to_builder(self):
        if not self._addon_unit_ids:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Warning", "No addon units discovered yet. Scan addons first!")
            return
        count = len(self._addon_unit_ids)
        self.log_message.emit(
            f"Added {count} addon unit(s) to available pool for Custom Builder.",
            "success",
        )
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Units Available",
            f"{count} addon unit(s) are now available in the Custom Builder.\n\n"
            f"Use them in the 'Specific Unit' field when building a scenario."
        )

    def set_addon_unit_ids(self, unit_ids: List[str]):
        """Set the list of addon unit IDs available for specific unit mode."""
        self._addon_unit_ids = list(unit_ids)
        # Add them to the specific unit combo if not already there
        for uid in unit_ids:
            if self.specific_unit_combo.findText(uid) < 0:
                self.specific_unit_combo.addItem(uid)

    def get_generated_scenario(self) -> Optional[ScenarioDef]:
        return self._last_scenario


# =============================================================================


# =============================================================================
# SCENARIO BUILDER LOGIC
# =============================================================================

# =============================================================================

"""
Custom Scenario Builder — Create custom Wesnoth scenarios from the GUI.
Provides faction/unit selection, map template choices, and parameter tuning.
"""

import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from scenarios import (
    ScenarioDef, SideConfig, FACTION_UNIT_POOLS,
    TimeOfDay, WeatherType,
    _fill, _place_castle, _place_villages, _draw_road,
    _set_terrain, _draw_terrain_rect,
)


# Faction metadata
FACTION_INFO = {
    "Loyalists": {"leader": "General", "color": "blue", "alignment": "lawful"},
    "Rebels": {"leader": "Elvish Captain", "color": "green", "alignment": "liminal"},
    "Northerners": {"leader": "Orcish Warlord", "color": "red", "alignment": "chaotic"},
    "Undead": {"leader": "Ancient Lich", "color": "purple", "alignment": "chaotic"},
    "Drakes": {"leader": "Drake Flare", "color": "red", "alignment": "chaotic"},
    "Knalgan Alliance": {"leader": "Dwarvish Lord", "color": "brown", "alignment": "lawful"},
    "Merfolk": {"leader": "Merfolk Diviner", "color": "teal", "alignment": "liminal"},
    "Outlaws": {"leader": "Outlaw", "color": "orange", "alignment": "chaotic"},
    "Saurians": {"leader": "Saurian Oracle", "color": "green", "alignment": "neutral"},
}

# Map template definitions
MAP_TEMPLATES = {
    "Open Field": {"w": 20, "h": 14, "base": "Gg", "villages": 8,
                   "forests": 10, "hills": 8, "description": "Open grassland"},
    "Forest": {"w": 22, "h": 16, "base": "Gg^Fp", "villages": 6,
               "forests": 40, "hills": 4, "description": "Dense forest"},
    "Mountains": {"w": 22, "h": 14, "base": "Hh", "villages": 6,
                   "forests": 5, "hills": 15, "description": "Mountain terrain"},
    "Swamp": {"w": 20, "h": 14, "base": "St", "villages": 7,
              "forests": 8, "hills": 2, "description": "Swamp and marshland"},
    "River Valley": {"w": 24, "h": 16, "base": "Gg", "villages": 10,
                     "forests": 12, "hills": 6, "description": "River with bridges"},
    "Island": {"w": 18, "h": 14, "base": "Gg", "villages": 5,
               "forests": 6, "hills": 3, "description": "Small island"},
    "Fortress": {"w": 20, "h": 14, "base": "Gg", "villages": 6,
                 "forests": 8, "hills": 4, "description": "Castle-focused"},
    "Mixed": {"w": 24, "h": 16, "base": "Gg", "villages": 12,
              "forests": 15, "hills": 10, "description": "Varied terrain mix"},
}


def get_random_matchup() -> Tuple[str, str]:
    """Generate a random faction matchup, avoiding mirrors."""
    factions = list(FACTION_INFO.keys())
    a = random.choice(factions)
    b = random.choice([f for f in factions if f != a])
    return a, b


def get_leader_for_faction(faction: str) -> str:
    """Get the default leader unit type for a faction."""
    info = FACTION_INFO.get(faction, {})
    return info.get("leader", "General")


def get_recruitable_units(faction: str, max_units: int = 7) -> List[str]:
    """Get a list of recruitable unit types for a faction."""
    pool = FACTION_UNIT_POOLS.get(faction, [])
    if not pool:
        return ["Spearman"]  # Fallback
    # Return a mix of low-level units (first entries tend to be base units)
    recruits = [u for u in pool if not any(x in u for x in ["Lord", "Sovereign",
              "Grand", "High", "Ancient", "Master", "Champion", "Blademaster",
              "Hurricane", "Pathfinder", "Tyrant", "Siren", "Dragonguard"])]
    if not recruits:
        recruits = pool[:5]
    return recruits[:max_units]


def get_faction_color(faction: str) -> str:
    """Get the display color for a faction."""
    return FACTION_INFO.get(faction, {}).get("color", "blue")


def build_custom_scenario(
    name: str,
    faction_a: str,
    faction_b: str,
    template: str = "Open Field",
    gold: int = 150,
    income: int = 2,
    max_turns: int = 30,
    record_turns: int = 25,
    units_per_side: int = 4,
    seed: Optional[int] = None,
    description: str = "",
    specific_unit: Optional[str] = None,
    addon_units: Optional[List[str]] = None,
) -> ScenarioDef:
    """
    Build a custom ScenarioDef from user parameters.

    Args:
        name: Scenario name
        faction_a: Side 1 faction name
        faction_b: Side 2 faction name
        template: Map template name
        gold: Starting gold per side
        income: Base income per side
        max_turns: Maximum game turns
        record_turns: Turns to record before ending
        units_per_side: Extra pre-placed units per side
        seed: Random seed (None for random)
        description: Scenario description

    Returns:
        Complete ScenarioDef ready for addon generation.
    """
    rng = random.Random(seed)

    # Get template
    tmpl = MAP_TEMPLATES.get(template, MAP_TEMPLATES["Open Field"])
    W, H = tmpl["w"], tmpl["h"]
    base_terrain = tmpl["base"]

    # Generate map
    m = _fill(base_terrain, W, H)

    # Add terrain features based on template
    if template == "River Valley":
        # Add a river through the middle
        from scenarios import _draw_river
        river_y = H // 2
        bridge_width = 2
        bridges = [(W // 4 - bridge_width, W // 4 + bridge_width),
                    (W // 2 - bridge_width, W // 2 + bridge_width),
                    (3 * W // 4 - bridge_width, 3 * W // 4 + bridge_width)]
        m = _draw_river(m, river_y, bridges, "Ss")
        # Second row of deep water
        for x in range(W):
            for b_start, b_end in bridges:
                if not (b_start <= x <= b_end):
                    m = _set_terrain(m, x, river_y + 1, "Ww")
    elif template == "Island":
        # Surround with water
        for x in range(W):
            m = _set_terrain(m, x, 0, "Ss")
            m = _set_terrain(m, x, H - 1, "Wo")
            if x < 3 or x >= W - 3:
                for y in range(H):
                    if x < 2 or x >= W - 2:
                        m = _set_terrain(m, x, y, "Wo")
                    else:
                        m = _set_terrain(m, x, y, "Ss")
        for y in range(H):
            m = _set_terrain(m, 0, y, "Wo")
            m = _set_terrain(m, 1, y, "Ss")
            m = _set_terrain(m, W - 1, y, "Wo")
            m = _set_terrain(m, W - 2, y, "Ss")
    elif template == "Fortress":
        # Add mountains as fortress walls
        for x in range(4, W - 4):
            m = _set_terrain(m, x, 2, "Mm")
            m = _set_terrain(m, x, H - 3, "Mm")

    # Scatter forests
    forest_count = tmpl["forests"]
    for _ in range(forest_count):
        fx = rng.randint(1, W - 2)
        fy = rng.randint(1, H - 2)
        # Don't place on castles
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Scatter hills
    hill_count = tmpl["hills"]
    for _ in range(hill_count):
        hx = rng.randint(1, W - 2)
        hy = rng.randint(1, H - 2)
        m = _set_terrain(m, hx, hy, "Hh")

    # Place villages
    village_positions = []
    attempts = 0
    while len(village_positions) < tmpl["villages"] and attempts < 200:
        vx = rng.randint(2, W - 3)
        vy = rng.randint(2, H - 3)
        # Avoid castle areas
        if abs(vx - 3) > 3 or abs(vy - H // 2) > 3:
            if abs(vx - (W - 4)) > 3 or abs(vy - H // 2) > 3:
                if (vx, vy) not in village_positions:
                    village_positions.append((vx, vy))
        attempts += 1
    m = _place_villages(m, village_positions)

    # Road between keeps
    m = _draw_road(m, [(3, H // 2), (W // 2, H // 2), (W - 4, H // 2)])

    # Place castles
    m = _place_castle(m, 3, H // 2, 1)
    m = _place_castle(m, W - 4, H // 2, 2)

    # Build side configs
    info_a = FACTION_INFO.get(faction_a, {})
    info_b = FACTION_INFO.get(faction_b, {})

    recruits_a = get_recruitable_units(faction_a)
    recruits_b = get_recruitable_units(faction_b)

    # Add addon units to recruit pools if provided
    if addon_units:
        addon_set = set(addon_units)
        recruits_a = recruits_a + [u for u in addon_units if u not in set(recruits_a)]
        recruits_b = recruits_b + [u for u in addon_units if u not in set(recruits_b)]

    # Generate extra units for side A
    extra_a = []
    for i in range(units_per_side):
        ux = rng.choice([2, 4]) + rng.randint(-1, 1)
        uy = (H // 2) + rng.choice([-1, 1]) + rng.randint(-1, 1)
        ux = max(0, min(W - 1, ux))
        uy = max(0, min(H - 1, uy))
        # Specific unit mode: all side A units are the same type
        if specific_unit:
            unit_type = specific_unit
        else:
            unit_type = rng.choice(recruits_a) if recruits_a else "Spearman"
        extra_a.append({"type": unit_type, "x": ux, "y": uy})

    # Generate extra units for side B
    extra_b = []
    for i in range(units_per_side):
        ux = (W - 4) + rng.choice([-1, 1]) + rng.randint(-1, 1)
        uy = (H // 2) + rng.choice([-1, 1]) + rng.randint(-1, 1)
        ux = max(0, min(W - 1, ux))
        uy = max(0, min(H - 1, uy))
        unit_type = rng.choice(recruits_b) if recruits_b else "Orcish Grunt"
        extra_b.append({"type": unit_type, "x": ux, "y": uy})

    side_a = SideConfig(
        side_number=1,
        faction=faction_a,
        color=info_a.get("color", "blue"),
        gold=gold,
        income=income,
        can_recruit=[specific_unit] if specific_unit else recruits_a,
        leader_type=info_a.get("leader", "General"),
        leader_x=3,
        leader_y=H // 2,
        ai_aggression=0.55,
        ai_caution=0.25,
        extra_units=extra_a,
    )

    side_b = SideConfig(
        side_number=2,
        faction=faction_b,
        color=info_b.get("color", "red"),
        gold=gold,
        income=income,
        can_recruit=recruits_b,
        leader_type=info_b.get("leader", "Orcish Warlord"),
        leader_x=W - 4,
        leader_y=H // 2,
        ai_aggression=0.55,
        ai_caution=0.25,
        extra_units=extra_b,
    )

    # Pick weather based on terrain
    weather = WeatherType.CLEAR
    if template == "Swamp":
        weather = WeatherType.FOG
    elif template == "Mountains":
        weather = WeatherType.CLEAR
    elif template == "Island":
        weather = WeatherType.CLEAR

    # Generate description if not provided
    if not description:
        if specific_unit:
            description = (
                f"A swarm of {specific_unit}s descends upon the "
                f"{tmpl['description'].lower()} battlefield. "
                f"{faction_a} deploys only {specific_unit}s against a "
                f"{faction_b} army. Chaos ensues as the skies and fields "
                f"fill with {specific_unit}s."
            )
        else:
            description = (
                f"Custom battle on a {tmpl['description'].lower()} map. "
                f"{faction_a} forces face off against {faction_b} "
                f"in a procedurally generated engagement."
            )

    scenario_id = name.lower().replace(" ", "_").replace("'", "")[:30]
    if seed is not None:
        scenario_id += f"_s{seed}"

    return ScenarioDef(
        id=scenario_id,
        name=name,
        description=description,
        map_data=m,
        sides=[side_a, side_b],
        max_turns=max_turns,
        turns_to_record=record_turns,
        time_of_day=TimeOfDay.MIDDAY,
        weather=weather,
        camera_pacing="cinematic",
        camera_zoom=1.0,
    )


# =============================================================================
# MULTI-FACTION BUILDER
# =============================================================================

# Color palette for sides 1-9
SIDE_COLORS = ["blue", "red", "green", "purple", "orange", "teal", "brown", "white", "magenta"]


def build_multi_faction_scenario(
    name: str,
    factions: List[str],
    template: str = "Open Field",
    gold: int = 120,
    income: int = 1,
    max_turns: int = 35,
    record_turns: int = 25,
    units_per_side: int = 3,
    seed: Optional[int] = None,
    description: str = "",
) -> ScenarioDef:
    """
    Build a multi-faction scenario with N sides (3 to 9).

    Sides are placed around the map perimeter, evenly spaced.
    The map uses a larger template to accommodate more factions.
    """
    rng = random.Random(seed)
    n_sides = len(factions)

    # Use a larger map for more factions
    tmpl = MAP_TEMPLATES.get(template, MAP_TEMPLATES["Mixed"])
    W = max(tmpl["w"], 18 + n_sides * 2)
    H = max(tmpl["h"], 14 + n_sides)

    # Generate map
    m = _fill(tmpl["base"], W, H)

    # Calculate castle positions around perimeter
    # Distribute sides around the edges
    castle_positions = []
    margin_x = max(3, W // (n_sides + 1))
    margin_y = max(3, H // (n_sides + 1))

    # Place sides: some on left, some on right, some on top/bottom
    left_count = (n_sides + 1) // 2
    right_count = n_sides - left_count

    # Left side castles
    for i in range(left_count):
        cy = int((i + 1) * H / (left_count + 1))
        castle_positions.append((3, cy))

    # Right side castles
    for i in range(right_count):
        cy = int((i + 1) * H / (right_count + 1))
        castle_positions.append((W - 4, cy))

    # Place castles
    for i, (cx, cy) in enumerate(castle_positions):
        m = _place_castle(m, cx, cy, i + 1)

    # Scatter terrain features
    forest_count = tmpl.get("forests", 12)
    for _ in range(forest_count):
        fx = rng.randint(1, W - 2)
        fy = rng.randint(1, H - 2)
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    hill_count = tmpl.get("hills", 8)
    for _ in range(hill_count):
        hx = rng.randint(1, W - 2)
        hy = rng.randint(1, H - 2)
        m = _set_terrain(m, hx, hy, "Hh")

    # Villages — more for more factions, cluster toward center
    n_villages = max(tmpl.get("villages", 8), n_sides * 3)
    village_positions = []
    attempts = 0
    while len(village_positions) < n_villages and attempts < 300:
        vx = rng.randint(max(4, W // 4), min(W - 5, 3 * W // 4))
        vy = rng.randint(max(2, H // 4), min(H - 3, 3 * H // 4))
        if (vx, vy) not in village_positions:
            village_positions.append((vx, vy))
        attempts += 1
    m = _place_villages(m, village_positions)

    # Roads connecting adjacent castles through center
    cx, cy = W // 2, H // 2
    for i, (ax, ay) in enumerate(castle_positions):
        m = _draw_road(m, [(ax, ay), (cx, cy)])

    # Build side configs
    sides = []
    faction_names = " vs ".join(factions)

    for i, (faction, (cx, cy)) in enumerate(zip(factions, castle_positions)):
        info = FACTION_INFO.get(faction, {})
        color = SIDE_COLORS[i % len(SIDE_COLORS)]
        recruits = get_recruitable_units(faction)

        # Generate extra units
        extra = []
        for _ in range(units_per_side):
            ux = cx + rng.choice([-1, 1]) + rng.randint(-1, 1)
            uy = cy + rng.choice([-1, 1]) + rng.randint(-1, 1)
            ux = max(0, min(W - 1, ux))
            uy = max(0, min(H - 1, uy))
            unit_type = rng.choice(recruits) if recruits else "Spearman"
            extra.append({"type": unit_type, "x": ux, "y": uy})

        side = SideConfig(
            side_number=i + 1,
            faction=faction,
            color=color,
            gold=gold,
            income=income,
            can_recruit=recruits,
            leader_type=info.get("leader", "General"),
            leader_x=cx,
            leader_y=cy,
            ai_aggression=0.55 + rng.random() * 0.15,
            ai_caution=0.2 + rng.random() * 0.15,
            extra_units=extra,
        )
        sides.append(side)

    if not description:
        description = (
            f"A {n_sides}-way battle on a {tmpl.get('description', 'varied').lower()} map. "
            f"{faction_names} — all factions converge from their corners "
            f"in a chaotic multi-front war."
        )

    scenario_id = name.lower().replace(" ", "_").replace("'", "")[:30]
    if seed is not None:
        scenario_id += f"_s{seed}"

    return ScenarioDef(
        id=scenario_id,
        name=name,
        description=description,
        map_data=m,
        sides=sides,
        max_turns=max_turns,
        turns_to_record=record_turns,
        time_of_day=TimeOfDay.MIDDAY,
        weather=WeatherType.CLEAR,
        camera_pacing="follow_action",
        camera_zoom=max(0.6, 1.0 - n_sides * 0.08),
    )


# =============================================================================
# WAVE SCENARIO BUILDER
# =============================================================================

def build_wave_scenario(
    name: str,
    attacker_faction: str,
    defender_faction: str,
    template: str = "Open Field",
    gold_attacker: int = 300,
    gold_defender: int = 200,
    income_attacker: int = 5,
    income_defender: int = 3,
    max_turns: int = 40,
    record_turns: int = 30,
    wave_interval: int = 3,
    num_waves: int = 6,
    units_per_wave: int = 4,
    seed: Optional[int] = None,
    description: str = "",
) -> ScenarioDef:
    """
    Build a wave attack scenario.

    The attacker gets periodic reinforcements (waves) that grow in strength.
    The defender has a fortified position and must survive.
    """
    rng = random.Random(seed)
    tmpl = MAP_TEMPLATES.get(template, MAP_TEMPLATES["Open Field"])
    W, H = tmpl["w"], tmpl["h"]

    m = _fill(tmpl["base"], W, H)

    # Attacker castle on the left
    m = _place_castle(m, 3, H // 2, 1)
    # Defender castle on the right
    m = _place_castle(m, W - 4, H // 2, 2)

    # Add some defensive terrain near defender (hills/mountains as walls)
    for y in range(max(0, H // 2 - 3), min(H, H // 2 + 4)):
        m = _set_terrain(m, W - 7, y, "Hh")
        if y % 2 == 0:
            m = _set_terrain(m, W - 8, y, "Mm")

    # Terrain features
    for _ in range(tmpl.get("forests", 8)):
        fx = rng.randint(5, W - 10)
        fy = rng.randint(1, H - 2)
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    for _ in range(tmpl.get("hills", 5)):
        hx = rng.randint(5, W - 10)
        hy = rng.randint(1, H - 2)
        m = _set_terrain(m, hx, hy, "Hh")

    # Villages — more for defender
    villages = []
    attempts = 0
    while len(villages) < tmpl.get("villages", 8) and attempts < 200:
        vx = rng.randint(max(4, W // 2), W - 5)
        vy = rng.randint(2, H - 3)
        if (vx, vy) not in villages:
            villages.append((vx, vy))
        attempts += 1
    # Also some villages in the middle
    for _ in range(3):
        vx = rng.randint(W // 4, 3 * W // 4)
        vy = rng.randint(2, H - 3)
        if (vx, vy) not in villages:
            villages.append((vx, vy))
    m = _place_villages(m, villages)

    # Road
    m = _draw_road(m, [(4, H // 2), (W // 2, H // 2), (W - 5, H // 2)])

    # Build attacker side config
    atk_info = FACTION_INFO.get(attacker_faction, {})
    atk_recruits = get_recruitable_units(attacker_faction, max_units=10)

    side_a = SideConfig(
        side_number=1,
        faction=attacker_faction,
        color=atk_info.get("color", "red"),
        gold=gold_attacker,
        income=income_attacker,
        can_recruit=atk_recruits,
        leader_type=atk_info.get("leader", "General"),
        leader_x=3,
        leader_y=H // 2,
        ai_aggression=0.7,
        ai_caution=0.15,
        extra_units=[
            {"type": rng.choice(atk_recruits) if atk_recruits else "Spearman",
             "x": 2 + rng.randint(-1, 1), "y": (H // 2) + rng.choice([-1, 1])}
            for _ in range(3)
        ],
    )

    # Build defender side config
    def_info = FACTION_INFO.get(defender_faction, {})
    def_recruits = get_recruitable_units(defender_faction, max_units=10)

    side_b = SideConfig(
        side_number=2,
        faction=defender_faction,
        color=def_info.get("color", "blue"),
        gold=gold_defender,
        income=income_defender,
        can_recruit=def_recruits,
        leader_type=def_info.get("leader", "General"),
        leader_x=W - 4,
        leader_y=H // 2,
        ai_aggression=0.4,
        ai_caution=0.5,
        extra_units=[
            {"type": rng.choice(def_recruits) if def_recruits else "Spearman",
             "x": (W - 4) + rng.randint(-1, 1), "y": (H // 2) + rng.choice([-1, 1])}
            for _ in range(5)
        ],
    )

    # Generate wave events
    wave_events = []
    spawn_xs = [1, 2, 4, 5, 3, 6]
    spawn_y_offsets = [-2, -1, 0, 1, 2, -3, 3]

    for wave_num in range(num_waves):
        turn = (wave_num + 1) * wave_interval
        # Each wave gets more units and better types
        wave_size = units_per_wave + wave_num
        pool = atk_recruits if atk_recruits else ["Spearman"]

        # Mix base and advanced units
        wave_unit_types = []
        for i in range(wave_size):
            # Later waves include stronger units
            if wave_num >= 2 and i < wave_num:
                idx = min(len(pool) - 1, len(pool) // 2 + i)
                wave_unit_types.append(pool[idx])
            else:
                wave_unit_types.append(rng.choice(pool[:max(3, len(pool) // 2)]))

        # Wave message
        wave_names = ["first", "second", "third", "fourth", "fifth", "sixth",
                       "seventh", "eighth", "ninth", "tenth"]
        wave_name = wave_names[wave_num] if wave_num < len(wave_names) else f"wave {wave_num + 1}"
        wave_events.append({
            "turn": turn,
            "action": "message",
            "side": 1,
            "text": f"The {wave_name} wave attacks!",
        })

        # Spawn units
        units_to_spawn = []
        for i, utype in enumerate(wave_unit_types):
            sx = spawn_xs[i % len(spawn_xs)]
            sy = (H // 2) + spawn_y_offsets[i % len(spawn_y_offsets)]
            sy = max(0, min(H - 1, sy))
            units_to_spawn.append({"type": utype, "x": sx, "y": sy})

        wave_events.append({
            "turn": turn,
            "action": "reinforcements",
            "side": 1,
            "units": units_to_spawn,
        })

    if not description:
        description = (
            f"Wave attack: {attacker_faction} sends {num_waves} waves of reinforcements "
            f"against a fortified {defender_faction} position. Each wave is stronger "
            f"than the last. The defender must hold out or be overwhelmed."
        )

    scenario_id = name.lower().replace(" ", "_").replace("'", "")[:30]
    if seed is not None:
        scenario_id += f"_s{seed}"

    return ScenarioDef(
        id=scenario_id,
        name=name,
        description=description,
        map_data=m,
        sides=[side_a, side_b],
        max_turns=max_turns,
        turns_to_record=record_turns,
        time_of_day=TimeOfDay.MIDDAY,
        weather=WeatherType.CLEAR,
        camera_pacing="cinematic",
        camera_zoom=0.9,
        turn_events=wave_events,
    )


# =============================================================================
# KING OF THE HILL BUILDER
# =============================================================================

def build_koth_scenario(
    name: str,
    factions: List[str],
    template: str = "Open Field",
    gold: int = 130,
    income: int = 1,
    max_turns: int = 30,
    record_turns: int = 22,
    units_per_side: int = 3,
    seed: Optional[int] = None,
    description: str = "",
) -> ScenarioDef:
    """
    Build a King of the Hill scenario with N factions.

    All factions start from the edges and race to control the central
    hill/objective area.
    """
    rng = random.Random(seed)
    n_sides = len(factions)

    tmpl = MAP_TEMPLATES.get(template, MAP_TEMPLATES["Mixed"])
    W = max(tmpl["w"], 18 + n_sides * 2)
    H = max(tmpl["h"], 14 + n_sides)

    m = _fill(tmpl["base"], W, H)

    # Central hill — villages forming a cluster
    cx, cy = W // 2, H // 2
    center_villages = [(cx - 1, cy), (cx, cy - 1), (cx + 1, cy), (cx, cy + 1), (cx, cy)]
    m = _place_villages(m, center_villages)

    # Ring of hills around center
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if abs(dx) + abs(dy) == 3 or abs(dx) + abs(dy) == 4:
                hx, hy = cx + dx, cy + dy
                if 0 <= hx < W and 0 <= hy < H:
                    m = _set_terrain(m, hx, hy, "Hh")

    # Castle positions around perimeter
    castle_positions = []
    for i in range(n_sides):
        angle = 2 * 3.14159 * i / n_sides
        # Place at ~80% from center
        dist_x = int((W // 2 - 3) * 0.85)
        dist_y = int((H // 2 - 3) * 0.85)
        px = int(cx + dist_x * __import__("math").cos(angle))
        py = int(cy + dist_y * __import__("math").sin(angle))
        px = max(3, min(W - 4, px))
        py = max(3, min(H - 4, py))
        castle_positions.append((px, py))

    for i, (cpx, cpy) in enumerate(castle_positions):
        m = _place_castle(m, cpx, cpy, i + 1)

    # Villages between castles and center
    for i in range(n_sides):
        ax, ay = castle_positions[i]
        vx = (ax + cx) // 2
        vy = (ay + cy) // 2
        m = _place_villages(m, [(vx, vy)])

    # More scattered villages
    for _ in range(n_sides * 2):
        vx = rng.randint(2, W - 3)
        vy = rng.randint(2, H - 3)
        m = _place_villages(m, [(vx, vy)])

    # Forests for tactical cover
    for _ in range(12):
        fx = rng.randint(1, W - 2)
        fy = rng.randint(1, H - 2)
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Roads from each castle to center
    for cpx, cpy in castle_positions:
        m = _draw_road(m, [(cpx, cpy), (cx, cy)])

    # Build sides
    sides = []
    faction_names_str = " vs ".join(factions)

    for i, (faction, (cpx, cpy)) in enumerate(zip(factions, castle_positions)):
        info = FACTION_INFO.get(faction, {})
        color = SIDE_COLORS[i % len(SIDE_COLORS)]
        recruits = get_recruitable_units(faction)

        extra = []
        for _ in range(units_per_side):
            ux = cpx + rng.choice([-1, 1]) + rng.randint(-1, 1)
            uy = cpy + rng.choice([-1, 1]) + rng.randint(-1, 1)
            ux = max(0, min(W - 1, ux))
            uy = max(0, min(H - 1, uy))
            unit_type = rng.choice(recruits) if recruits else "Spearman"
            extra.append({"type": unit_type, "x": ux, "y": uy})

        side = SideConfig(
            side_number=i + 1,
            faction=faction,
            color=color,
            gold=gold,
            income=income,
            can_recruit=recruits,
            leader_type=info.get("leader", "General"),
            leader_x=cpx,
            leader_y=cpy,
            ai_aggression=0.6,
            ai_caution=0.25,
            extra_units=extra,
        )
        sides.append(side)

    # KotH narrative events
    koth_events = [
        {"turn": 1, "action": "message", "text": "Seize the central hill to dominate the battlefield!"},
        {"turn": max_turns // 3, "action": "message", "text": "The fight for the hill intensifies!"},
        {"turn": 2 * max_turns // 3, "action": "message", "text": "The final struggle for the hill begins!"},
    ]

    if not description:
        description = (
            f"King of the Hill: {n_sides} factions — {faction_names_str} — "
            f"race to control the central hill. The faction holding the center "
            f"controls the battlefield."
        )

    scenario_id = name.lower().replace(" ", "_").replace("'", "")[:30]
    if seed is not None:
        scenario_id += f"_s{seed}"

    return ScenarioDef(
        id=scenario_id,
        name=name,
        description=description,
        map_data=m,
        sides=sides,
        max_turns=max_turns,
        turns_to_record=record_turns,
        time_of_day=TimeOfDay.AFTERNOON,
        weather=WeatherType.CLEAR,
        camera_pacing="follow_action",
        camera_zoom=max(0.6, 1.0 - n_sides * 0.08),
        turn_events=koth_events,
    )


# =============================================================================
# MAIN WINDOW
# =============================================================================

class WesnothAIRendererApp(QMainWindow):
    """Main window - 2 tabs: Record and Builder. Addons auto-scanned."""

    def __init__(self):
        super().__init__()

        # --- State ---
        self.wesnoth_paths: Optional[WesnothPaths] = None
        self._log_queue: queue.Queue = queue.Queue()
        self._log_signal = LogSignalEmitter()
        self._log_signal.log_line.connect(self._append_log_line)
        self._recording_thread: Optional[threading.Thread] = None
        self._is_recording = False
        self._current_bridge: Optional[WesnothBridge] = None
        self._history = RecordingHistory()
        self._last_custom_scenario: Optional[ScenarioDef] = None
        self._addon_scanner = AddonScanner()

        # --- Window ---
        self.setWindowTitle("WesnothAI - Battle for Wesnoth Recorder")
        self.resize(1200, 820)
        self.setMinimumSize(960, 680)

        self._build_ui()
        self._connect_signals()
        self._start_log_poller()

        # Center on screen
        geo = self.screen().availableGeometry()
        self.move((geo.width() - self.width()) // 2, (geo.height() - self.height()) // 2)

    def run(self):
        self.show()
        QTimer.singleShot(300, self._auto_detect_wesnoth)

    # =========================================================================
    # UI CONSTRUCTION
    # =========================================================================

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        # --- Title bar ---
        title_row = QHBoxLayout()
        root.addLayout(title_row)

        title = QLabel("WesnothAI")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #e94560; background: transparent;")
        title_row.addWidget(title)

        sub = QLabel("Battle for Wesnoth | github.com/wesnoth/wesnoth")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color: #8090a0; background: transparent; margin-left: 12px;")
        title_row.addWidget(sub)
        title_row.addStretch()

        self.wesnoth_badge = QLabel("Detecting...")
        self.wesnoth_badge.setFont(QFont("Segoe UI", 9))
        self.wesnoth_badge.setStyleSheet(
            "background-color: #1e2a4a; color: #8090a0; padding: 2px 8px; border-radius: 3px;"
        )
        title_row.addWidget(self.wesnoth_badge)

        self.addon_badge = QLabel("Addons: --")
        self.addon_badge.setFont(QFont("Segoe UI", 9))
        self.addon_badge.setStyleSheet(
            "background-color: #1e2a4a; color: #8090a0; padding: 2px 8px; border-radius: 3px;"
        )
        title_row.addWidget(self.addon_badge)

        # --- Tabs: Record / Builder ---
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, stretch=1)

        tab_record = QWidget()
        tab_builder = QWidget()
        self.tabs.addTab(tab_record, "  Record  ")
        self.tabs.addTab(tab_builder, "  Builder  ")

        # Record tab: scenario browser on top, recording controls + log on bottom        self.record_panel = RecordPanel()        self.recording_panel = RecordingPanel()

        rec_layout = QVBoxLayout(tab_record)
        rec_layout.setContentsMargins(0, 0, 0, 0)
        rec_layout.addWidget(self.record_panel, stretch=1)
        rec_layout.addWidget(self.recording_panel)

        # Builder tab        self.builder_panel = BuilderPanel()
        bld_layout = QVBoxLayout(tab_builder)
        bld_layout.setContentsMargins(0, 0, 0, 0)
        bld_layout.addWidget(self.builder_panel, stretch=1)

    # =========================================================================
    # SIGNALS
    # =========================================================================

    def _connect_signals(self):
        self.recording_panel.record_single.connect(self._start_recording)
        self.recording_panel.record_batch.connect(self._start_batch_recording)
        self.recording_panel.stop_recording.connect(self._stop_recording)
        self.recording_panel.open_output.connect(self._open_output_folder)
        self.recording_panel.wesnoth_browse_btn.clicked.connect(self._browse_wesnoth)
        self.builder_panel.scenario_generated.connect(self._on_custom_generated)
        self.builder_panel.log_message.connect(lambda msg, tag: self._log(msg, tag))

    # =========================================================================
    # AUTO-DETECT (runs on startup)
    # =========================================================================

    def _start_log_poller(self):
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_log_queue)
        self._poll_timer.start(100)

    def _auto_detect_wesnoth(self):
        """Background: detect Wesnoth + scan addons."""
        def _detect():
            deps = WesnothBridge.check_dependencies()
            found = WesnothBridge.find_wesnoth()
            # Scan addons
            self._addon_scanner.scan()
            addon_count = len(self._addon_scanner._discovered)
            unit_count = len(self._addon_scanner._all_units)
            QTimer.singleShot(0, lambda: self._on_detect_done(deps, found, addon_count, unit_count))
        threading.Thread(target=_detect, daemon=True).start()

    def _on_detect_done(self, deps, found, addon_count, unit_count):
        # Update Wesnoth badge
        if found:
            self.wesnoth_paths = found
            ver = found.version if found.version and found.version != "unknown" else ""
            self.wesnoth_badge.setText(f"Wesnoth {ver}".strip() or "Wesnoth Found")
            self.wesnoth_badge.setStyleSheet(
                "background-color: #1a3a1a; color: #2ecc71; padding: 2px 8px; border-radius: 3px;"
            )
            self.recording_panel.set_wesnoth_path(found.wesnoth_binary, found=True)
            self._log(f"Wesnoth: {found.wesnoth_binary}", "success")
            if found.addon_dir:
                self.recording_panel.set_addon_dir(found.addon_dir)
        else:
            self.wesnoth_badge.setText("Wesnoth NOT Found")
            self.wesnoth_badge.setStyleSheet(
                "background-color: #3a1a1a; color: #e74c3c; padding: 2px 8px; border-radius: 3px;"
            )
            self.recording_panel.set_wesnoth_path("Not detected", found=False)

        # Update addon badge + feed builder panel
        if addon_count > 0:
            self.addon_badge.setText(f"Addons: {addon_count} ({unit_count} units)")
            self.addon_badge.setStyleSheet(
                "background-color: #1a2a3a; color: #3498db; padding: 2px 8px; border-radius: 3px;"
            )
            # Pass discovered addons to builder panel
            self.builder_panel.set_discovered_addons(
                self._addon_scanner._discovered,
                self._addon_scanner._all_units,
            )
        else:
            self.addon_badge.setText("Addons: 0")
            self.addon_badge.setStyleSheet(
                "background-color: #1e2a4a; color: #8090a0; padding: 2px 8px; border-radius: 3px;"
            )
            self.builder_panel.set_discovered_addons([], [])

        # Set addon unit IDs for the builder's specific-unit mode
        if self._addon_scanner._all_units:
            self.builder_panel.set_addon_unit_ids(self._addon_scanner.get_unit_ids())

        # Log deps
        self._log("Dependencies:")
        for name, ok in deps.items():
            self._log(f"  {'OK' if ok else 'MISSING':>8} {name}", "success" if ok else "warning")

        if not found:
            self._log("")
            self._log("Wesnoth not found. Install:", "error")
            if platform.system() == "Windows":
                self._log("  Steam: store.steampowered.com/app/366920", "warn")
                self._log("  Or download: wesnoth.org", "warn")
            else:
                self._log("  sudo apt install wesnoth", "warn")
                self._log("  Or: flatpak install flathub org.wesnoth.Wesnoth", "warn")

        self._log(f"Addons scanned: {addon_count} addon(s), {unit_count} unit type(s)", "info")

    # =========================================================================
    # WESNOTH PATH
    # =========================================================================

    def _browse_wesnoth(self):
        if sys.platform == "win32":
            filt = "Executables (*.exe);;All Files (*)"
        else:
            filt = "All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select Wesnoth Binary", "", filt)
        if path:
            self.recording_panel.set_wesnoth_path(path, found=True)
            self._log(f"Wesnoth path set: {path}", "success")

    def _ensure_wesnoth_path(self) -> Optional[str]:
        """Return a valid Wesnoth binary path, auto-detecting if needed."""
        path = self.recording_panel.get_wesnoth_path()
        if path and (os.path.isfile(path) or path.startswith("flatpak")):
            return path
        if path:
            self._log(f"Wesnoth path invalid: {path}. Re-detecting...", "warning")

        found = WesnothBridge.find_wesnoth()
        if found and found.wesnoth_binary:
            self.wesnoth_paths = found
            self.recording_panel.set_wesnoth_path(found.wesnoth_binary, found=True)
            if found.addon_dir:
                self.recording_panel.set_addon_dir(found.addon_dir)
            self._log(f"Auto-detected: {found.wesnoth_binary}", "success")
            return found.wesnoth_binary

        if platform.system() == "Windows":
            QMessageBox.critical(
                self, "Wesnoth Not Found",
                "Cannot find wesnoth.exe.\n\n"
                "1. Install via Steam: store.steampowered.com/app/366920\n"
                "2. Download from wesnoth.org\n"
                "3. Click 'Browse' to locate wesnoth.exe manually"
            )
        else:
            QMessageBox.critical(
                self, "Wesnoth Not Found",
                "Cannot find wesnoth binary.\n\n"
                "  sudo apt install wesnoth\n"
                "  Or: flatpak install flathub org.wesnoth.Wesnoth\n"
                "  Or click 'Browse' to locate it manually."
            )
        return None

    # =========================================================================
    # RECORDING
    # =========================================================================

    def _start_recording(self):
        scenario = self.record_panel.get_selected_scenario()
        if not scenario:
            if self._last_custom_scenario:
                scenario = self._last_custom_scenario
                self._log(f"Using last built scenario: {scenario.name}", "info")
            else:
                QMessageBox.warning(self, "No Scenario", "Select a scenario first.")
                return

        wesnoth_bin = self._ensure_wesnoth_path()
        if not wesnoth_bin:
            return

        cfg = self.recording_panel.get_config_dict()
        w, h = cfg["resolution"]
        output_dir = cfg["output_dir"]
        os.makedirs(output_dir, exist_ok=True)
        output = os.path.join(output_dir, f"{scenario.id}.mp4")

        addon_dir = tempfile.mkdtemp(prefix="wesnoth_addon_")
        self._log(f"Recording: {scenario.name} ({w}x{h} @ {cfg['fps']}fps)")

        try:
            gen = WesnothAddonGenerator({"addon_name": "ai_movie_renderer", "output_dir": addon_dir})
            gen.generate_single_scenario(scenario)
        except Exception as e:
            self._log(f"Addon generation failed: {e}", "error")
            QMessageBox.critical(self, "Error", str(e))
            shutil.rmtree(addon_dir, ignore_errors=True)
            return

        rec_cfg = RecordingConfig(
            wesnoth_path=wesnoth_bin,
            scenario_id=scenario.id,
            addon_path=addon_dir,
            resolution=(w, h),
            fps=cfg["fps"],
            output_path=output,
            video_crf=cfg["crf"],
            video_preset=cfg["preset"],
        )

        self._is_recording = True
        self.recording_panel.set_recording_state(True)

        self._current_bridge = WesnothBridge(rec_cfg)
        self._current_bridge.set_log_callback(self._on_bridge_log)

        self._recording_thread = threading.Thread(
            target=self._recording_worker,
            args=(self._current_bridge, addon_dir, scenario),
            daemon=True,
        )
        self._recording_thread.start()

    def _recording_worker(self, bridge: WesnothBridge, addon_dir: str, scenario: ScenarioDef):
        try:
            success = bridge.run_recording(self._on_bridge_log)

            def on_done():
                self._is_recording = False
                self._current_bridge = None
                self.recording_panel.set_recording_state(False)
                if success:
                    info = bridge.get_recording_info()
                    dur = info.get("duration_seconds", "?")
                    size = info.get("file_size_mb", "?")
                    self._log(f"Saved: {info['output']} ({size} MB, {dur}s)", "success")
                    self._history.add(scenario.name, scenario.id, info["output"],
                                      str(dur), str(size))
                    # Auto-open
                    if os.path.isfile(info["output"]):
                        try:
                            if platform.system() == "Windows":
                                os.startfile(info["output"])
                            elif platform.system() == "Darwin":
                                subprocess.Popen(["open", info["output"]],
                                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            else:
                                subprocess.Popen(["xdg-open", info["output"]],
                                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except Exception:
                            pass
                else:
                    self._log("Recording failed.", "error")
                shutil.rmtree(addon_dir, ignore_errors=True)

            QTimer.singleShot(0, on_done)
        except Exception as e:
            self._log(f"Recording error: {e}", "error")
            QTimer.singleShot(0, lambda: self.recording_panel.set_recording_state(False))

    def _start_batch_recording(self):
        batch = self.record_panel.get_batch_scenarios()
        if not batch:
            QMessageBox.warning(self, "Empty Queue", "Add scenarios to the batch queue first.")
            return

        wesnoth_bin = self._ensure_wesnoth_path()
        if not wesnoth_bin:
            return

        cfg = self.recording_panel.get_config_dict()
        output_dir = cfg["output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        self._is_recording = True
        self.recording_panel.set_recording_state(True)

        t = threading.Thread(
            target=self._batch_worker,
            args=(batch, wesnoth_bin, output_dir, cfg),
            daemon=True,
        )
        t.start()

    def _batch_worker(self, scenarios, wesnoth_bin, out_dir, cfg):
        total = len(scenarios)
        ok_count = 0
        w, h = cfg["resolution"]

        for i, scenario in enumerate(scenarios):
            self._log(f"Batch {i+1}/{total}: {scenario.name}", "info")
            output = os.path.join(out_dir, f"{scenario.id}.mp4")
            addon_dir = tempfile.mkdtemp(prefix="wesnoth_batch_")
            try:
                gen = WesnothAddonGenerator({"addon_name": "ai_movie_renderer", "output_dir": addon_dir})
                gen.generate_single_scenario(scenario)

                rec_cfg = RecordingConfig(
                    wesnoth_path=wesnoth_bin, scenario_id=scenario.id,
                    addon_path=addon_dir, resolution=(w, h),
                    fps=cfg["fps"], output_path=output,
                    video_crf=cfg["crf"], video_preset=cfg["preset"],
                )
                bridge = WesnothBridge(rec_cfg)
                bridge.set_log_callback(self._on_bridge_log)
                if bridge.run_recording(self._on_bridge_log):
                    ok_count += 1
                    info = bridge.get_recording_info()
                    self._history.add(scenario.name, scenario.id, output,
                                      str(info.get("duration_seconds", "")),
                                      str(info.get("file_size_mb", "")))
                    self._log(f"  Done: {scenario.name}", "success")
                else:
                    self._log(f"  FAILED: {scenario.name}", "error")
            except Exception as e:
                self._log(f"  ERROR: {scenario.name}: {e}", "error")
            finally:
                shutil.rmtree(addon_dir, ignore_errors=True)

        def on_done():
            self._is_recording = False
            self.recording_panel.set_recording_state(False)
            self._log(f"Batch complete: {ok_count}/{total} succeeded", "success")

        QTimer.singleShot(0, on_done)

    def _stop_recording(self):
        if self._current_bridge:
            self._current_bridge.cancel()
        self._is_recording = False
        self.recording_panel.set_recording_state(False)

    def _open_output_folder(self):
        output_dir = self.recording_panel.get_config_dict()["output_dir"]
        os.makedirs(output_dir, exist_ok=True)
        try:
            if platform.system() == "Windows":
                os.startfile(output_dir)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", output_dir],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["xdg-open", output_dir],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self._log(f"Could not open folder: {e}", "warning")

    # =========================================================================
    # BUILDER
    # =========================================================================

    def _on_custom_generated(self, scenario: ScenarioDef):
        self._last_custom_scenario = scenario
        self._log(f"Built: {scenario.name} ({scenario.width}x{scenario.height})", "success")

    # =========================================================================
    # LOGGING
    # =========================================================================

    def _on_bridge_log(self, msg: str):
        self._log_queue.put(msg)

    def _poll_log_queue(self):
        try:
            while True:
                msg = self._log_queue.get_nowait()
                tag = "info"
                if "ERROR" in msg or "FATAL" in msg:
                    tag = "error"
                elif "WARNING" in msg:
                    tag = "warning"
                elif any(w in msg.lower() for w in ("ok", "success", "complete", "saved")):
                    tag = "success"
                self._log(msg, tag)
        except queue.Empty:
            pass

    def _append_log_line(self, msg: str, tag: str):
        self.recording_panel.append_log(msg, tag)

    def _log(self, msg: str, tag: str = "info"):
        if hasattr(self, "recording_panel"):
            self.recording_panel.append_log(msg, tag)

    # =========================================================================
    # CLOSE
    # =========================================================================

    def closeEvent(self, event):
        if self._is_recording:
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "Recording in progress. Stop and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            self._stop_recording()
            time.sleep(1)
        event.accept()
