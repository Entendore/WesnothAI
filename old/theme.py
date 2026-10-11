"""Shared constants, quality presets, and dark stylesheet for WesnothAI GUI."""

import os
import sys
from dataclasses import dataclass, field
from typing import List

# ---------------------------------------------------------------------------
# Script directory – ensures relative imports work regardless of cwd
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


# ---------------------------------------------------------------------------
# Quality presets
# ---------------------------------------------------------------------------
@dataclass
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
# Dark QSS stylesheet
# ---------------------------------------------------------------------------
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