"""
WesnothAI - AI Movie Renderer for Battle for Wesnoth
Single-file PySide6 GUI. All features included.

Usage:  python wesnothai.py
        python wesnothai.py --check-deps
        python wesnothai.py --list-scenarios

Based on: https://github.com/wesnoth/wesnoth
"""

import os, sys, time, math, json, queue, random, platform, re
import signal, shutil, subprocess, tempfile, threading, struct, configparser
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QMessageBox, QFileDialog,
    QComboBox, QSpinBox, QSlider, QTextEdit, QLineEdit,
    QListWidget, QSplitter, QGroupBox, QFrame, QGridLayout,
    QCheckBox, QScrollArea,
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QFont, QImage, QPixmap
from PIL import Image, ImageDraw, ImageFont

# =========================================================================
# THEME - Dark stylesheet and quality presets
# =========================================================================

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

# =========================================================================
# NPC DATABASE - Unit stats
# =========================================================================



class TerrainType(Enum):
    GRASS = "grass"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    HILLS = "hills"
    WATER = "water"
    SWAMP = "swamp"
    SAND = "sand"
    CASTLE = "castle"
    VILLAGE = "village"
    CAVE = "cave"
    SNOW = "snow"
    FROZEN = "frozen"
    DESERT = "desert"


class AttackType(Enum):
    BLADE = "blade"
    PIERCE = "pierce"
    IMPACT = "impact"
    FIRE = "fire"
    COLD = "cold"
    ARCANE = "arcane"
    LIGHTNING = "lightning"


class Alignment(Enum):
    LAWFUL = "lawful"
    NEUTRAL = "neutral"
    CHAOTIC = "chaotic"
    LIMINAL = "liminal"


@dataclass
class Attack:
    name: str
    type: AttackType
    damage: int
    strikes: int
    range: str  # "melee" or "ranged"
    special: Optional[str] = None


@dataclass
class UnitDef:
    id: str
    name: str
    race: str
    faction: str
    level: int
    hp: int
    cost: int
    movement: int
    vision: int
    alignment: Alignment
    attacks: List[Attack]
    advances_to: List[str] = field(default_factory=list)
    # Visual profile for pixel-art rendering
    primary_color: str = "#FFFFFF"
    secondary_color: str = "#808080"
    accent_color: str = "#404040"
    body_type: str = "humanoid"  # humanoid, beast, flying, undead, aquatic
    has_cape: bool = False
    has_wings: bool = False
    has_helm: bool = False
    has_shield: bool = False
    has_staff: bool = False
    has_bow: bool = False
    size: int = 1  # 1=normal, 2=large


# ============================================================
# FACTION DEFINITIONS — All NPCs organized by faction
# ============================================================

def _build_database() -> Dict[str, UnitDef]:
    db = {}

    # ===================== LOYALISTS =====================
    db["Fencer"] = UnitDef(
        id="Fencer", name="Fencer", race="human", faction="Loyalists",
        level=1, hp=28, cost=14, movement=6, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Sword", AttackType.BLADE, 5, 3, "melee")],
        advances_to=["Fencer II", "Master at Arms"],
        primary_color="#3366CC", secondary_color="#CC3333", accent_color="#DAA520",
        body_type="humanoid", has_helm=True,
    )
    db["Fencer II"] = UnitDef(
        id="Fencer_II", name="Fencer", race="human", faction="Loyalists",
        level=2, hp=36, cost=22, movement=6, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 7, 4, "melee"),
            Attack("Crossbow", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        advances_to=["Master at Arms"],
        primary_color="#3366CC", secondary_color="#CC3333", accent_color="#FFD700",
        body_type="humanoid", has_helm=True,
    )
    db["Master at Arms"] = UnitDef(
        id="Master_at_Arms", name="Master at Arms", race="human", faction="Loyalists",
        level=3, hp=44, cost=36, movement=6, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 9, 4, "melee", "firststrike"),
            Attack("Crossbow", AttackType.PIERCE, 6, 3, "ranged"),
        ],
        primary_color="#2850A8", secondary_color="#B22222", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_cape=True,
    )
    db["Heavy Infantryman"] = UnitDef(
        id="Heavy_Infantryman", name="Heavy Infantryman", race="human", faction="Loyalists",
        level=1, hp=40, cost=19, movement=4, vision=3,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Mace", AttackType.IMPACT, 8, 2, "melee")],
        advances_to=["Infantry General", "Shock Trooper"],
        primary_color="#555555", secondary_color="#888888", accent_color="#3366CC",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Infantry General"] = UnitDef(
        id="Infantry_General", name="Infantry General", race="human", faction="Loyalists",
        level=2, hp=52, cost=30, movement=4, vision=3,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Mace", AttackType.IMPACT, 10, 3, "melee"),
            Attack("Javelin", AttackType.PIERCE, 7, 2, "ranged"),
        ],
        advances_to=["Grand Marshal"],
        primary_color="#444444", secondary_color="#777777", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Shock Trooper"] = UnitDef(
        id="Shock_Trooper", name="Shock Trooper", race="human", faction="Loyalists",
        level=2, hp=48, cost=30, movement=5, vision=3,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Mace", AttackType.IMPACT, 11, 3, "melee")],
        primary_color="#666666", secondary_color="#999999", accent_color="#CC3333",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Grand Marshal"] = UnitDef(
        id="Grand_Marshal", name="Grand Marshal", race="human", faction="Loyalists",
        level=3, hp=60, cost=50, movement=5, vision=3,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Mace", AttackType.IMPACT, 12, 3, "melee", "charge"),
            Attack("Javelin", AttackType.PIERCE, 8, 3, "ranged"),
        ],
        primary_color="#333333", secondary_color="#666666", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Spearman"] = UnitDef(
        id="Spearman", name="Spearman", race="human", faction="Loyalists",
        level=1, hp=28, cost=14, movement=5, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Spear", AttackType.PIERCE, 5, 3, "melee")],
        advances_to=["Pikeman", "Javelineer"],
        primary_color="#339966", secondary_color="#CC3333", accent_color="#DAA520",
        body_type="humanoid", has_helm=True,
    )
    db["Pikeman"] = UnitDef(
        id="Pikeman", name="Pikeman", race="human", faction="Loyalists",
        level=2, hp=38, cost=23, movement=5, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Pike", AttackType.PIERCE, 8, 3, "melee")],
        advances_to=["Halberdier"],
        primary_color="#228B22", secondary_color="#B22222", accent_color="#DAA520",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Halberdier"] = UnitDef(
        id="Halberdier", name="Halberdier", race="human", faction="Loyalists",
        level=3, hp=50, cost=40, movement=5, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Halberd", AttackType.BLADE, 10, 3, "melee", "charge")],
        primary_color="#006400", secondary_color="#8B0000", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Javelineer"] = UnitDef(
        id="Javelineer", name="Javelineer", race="human", faction="Loyalists",
        level=2, hp=30, cost=22, movement=5, vision=5,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Spear", AttackType.PIERCE, 6, 2, "melee"),
            Attack("Javelin", AttackType.PIERCE, 7, 2, "ranged"),
        ],
        primary_color="#339966", secondary_color="#CC6633", accent_color="#DAA520",
        body_type="humanoid", has_helm=True,
    )
    db["Bowman"] = UnitDef(
        id="Bowman", name="Bowman", race="human", faction="Loyalists",
        level=1, hp=24, cost=14, movement=5, vision=5,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Bow", AttackType.PIERCE, 5, 3, "ranged")],
        advances_to=["Longbowman", "Master Bowman"],
        primary_color="#228B22", secondary_color="#8B4513", accent_color="#DAA520",
        body_type="humanoid", has_bow=True,
    )
    db["Longbowman"] = UnitDef(
        id="Longbowman", name="Longbowman", race="human", faction="Loyalists",
        level=2, hp=32, cost=24, movement=5, vision=6,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Longbow", AttackType.PIERCE, 7, 4, "ranged")],
        advances_to=["Master Bowman"],
        primary_color="#006400", secondary_color="#654321", accent_color="#DAA520",
        body_type="humanoid", has_bow=True,
    )
    db["Master Bowman"] = UnitDef(
        id="Master_Bowman", name="Master Bowman", race="human", faction="Loyalists",
        level=3, hp=38, cost=40, movement=5, vision=7,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Master Bow", AttackType.PIERCE, 9, 4, "ranged", "marksman")],
        primary_color="#004D00", secondary_color="#3E2723", accent_color="#FFD700",
        body_type="humanoid", has_bow=True, has_cape=True,
    )
    db["Cavalryman"] = UnitDef(
        id="Cavalryman", name="Cavalryman", race="human", faction="Loyalists",
        level=1, hp=34, cost=19, movement=8, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Sword", AttackType.BLADE, 6, 3, "melee")],
        advances_to=["Knight", "Lancer", "Dragoon"],
        primary_color="#3366CC", secondary_color="#8B4513", accent_color="#DAA520",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Knight"] = UnitDef(
        id="Knight", name="Knight", race="human", faction="Loyalists",
        level=2, hp=46, cost=28, movement=8, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 8, 3, "melee", "charge"),
            Attack("Lance", AttackType.PIERCE, 9, 1, "melee"),
        ],
        advances_to=["Paladin", "Grand Knight"],
        primary_color="#2850A8", secondary_color="#8B4513", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Paladin"] = UnitDef(
        id="Paladin", name="Paladin", race="human", faction="Loyalists",
        level=3, hp=56, cost=46, movement=8, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Holy Sword", AttackType.ARCANE, 10, 3, "melee", "charge"),
            Attack("Lance", AttackType.PIERCE, 10, 2, "melee"),
        ],
        primary_color="#1A237E", secondary_color="#FFD700", accent_color="#FFFFFF",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Grand Knight"] = UnitDef(
        id="Grand_Knight", name="Grand Knight", race="human", faction="Loyalists",
        level=3, hp=58, cost=44, movement=9, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 10, 4, "melee"),
            Attack("Lance", AttackType.PIERCE, 11, 2, "melee", "charge"),
        ],
        primary_color="#1A237E", secondary_color="#B22222", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Lancer"] = UnitDef(
        id="Lancer", name="Lancer", race="human", faction="Loyalists",
        level=2, hp=44, cost=27, movement=9, vision=5,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Lance", AttackType.PIERCE, 9, 2, "melee", "charge")],
        advances_to=["Paladin", "Grand Knight"],
        primary_color="#3366CC", secondary_color="#8B4513", accent_color="#C0C0C0",
        body_type="humanoid", has_helm=True,
    )
    db["Dragoon"] = UnitDef(
        id="Dragoon", name="Dragoon", race="human", faction="Loyalists",
        level=2, hp=40, cost=25, movement=8, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 7, 3, "melee"),
            Attack("Pistol", AttackType.FIRE, 8, 2, "ranged"),
        ],
        primary_color="#4169E1", secondary_color="#8B4513", accent_color="#DAA520",
        body_type="humanoid", has_helm=True,
    )
    db["Mage"] = UnitDef(
        id="Mage", name="Mage", race="human", faction="Loyalists",
        level=1, hp=22, cost=17, movement=5, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Fireball", AttackType.FIRE, 7, 3, "ranged")],
        advances_to=["White Mage", "Red Mage", "Silver Mage"],
        primary_color="#6633CC", secondary_color="#9966FF", accent_color="#FFD700",
        body_type="humanoid", has_staff=True,
    )
    db["White Mage"] = UnitDef(
        id="White_Mage", name="White Mage", race="human", faction="Loyalists",
        level=2, hp=30, cost=27, movement=5, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Holy Light", AttackType.ARCANE, 9, 3, "ranged", "heal")],
        advances_to=["Arch Mage"],
        primary_color="#EEEEFF", secondary_color="#6633CC", accent_color="#FFD700",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Red Mage"] = UnitDef(
        id="Red_Mage", name="Red Mage", race="human", faction="Loyalists",
        level=2, hp=32, cost=27, movement=5, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Fireball", AttackType.FIRE, 10, 3, "ranged"),
            Attack("Staff", AttackType.IMPACT, 5, 2, "melee"),
        ],
        advances_to=["Arch Mage"],
        primary_color="#CC3333", secondary_color="#FF6633", accent_color="#FFD700",
        body_type="humanoid", has_staff=True,
    )
    db["Silver Mage"] = UnitDef(
        id="Silver_Mage", name="Silver Mage", race="human", faction="Loyalists",
        level=2, hp=30, cost=30, movement=5, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Lightning", AttackType.LIGHTNING, 9, 3, "ranged"),
            Attack("Staff", AttackType.IMPACT, 5, 2, "melee"),
        ],
        advances_to=["Arch Mage"],
        primary_color="#C0C0C0", secondary_color="#6633CC", accent_color="#00BFFF",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Arch Mage"] = UnitDef(
        id="Arch_Mage", name="Arch Mage", race="human", faction="Loyalists",
        level=3, hp=38, cost=46, movement=5, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Meteor", AttackType.FIRE, 12, 3, "ranged"),
            Attack("Staff", AttackType.IMPACT, 6, 2, "melee"),
        ],
        primary_color="#4B0082", secondary_color="#8B00FF", accent_color="#FFD700",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Horseman"] = UnitDef(
        id="Horseman", name="Horseman", race="human", faction="Loyalists",
        level=0, hp=28, cost=15, movement=7, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Sword", AttackType.BLADE, 5, 3, "melee")],
        advances_to=["Cavalryman"],
        primary_color="#3366CC", secondary_color="#8B4513", accent_color="#DAA520",
        body_type="humanoid", has_helm=True,
    )

    # ===================== REBELS (ELVES) =====================
    db["Elvish Fighter"] = UnitDef(
        id="Elvish_Fighter", name="Elvish Fighter", race="elf", faction="Rebels",
        level=1, hp=26, cost=14, movement=6, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Sword", AttackType.BLADE, 5, 3, "melee")],
        advances_to=["Elvish Captain", "Elvish Hero", "Elvish Champion"],
        primary_color="#228B22", secondary_color="#32CD32", accent_color="#8B4513",
        body_type="humanoid",
    )
    db["Elvish Captain"] = UnitDef(
        id="Elvish_Captain", name="Elvish Captain", race="elf", faction="Rebels",
        level=2, hp=36, cost=24, movement=6, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 7, 3, "melee"),
            Attack("Bow", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        advances_to=["Elvish Marshal"],
        primary_color="#1B5E20", secondary_color="#2E7D32", accent_color="#FFD700",
        body_type="humanoid", has_helm=True,
    )
    db["Elvish Hero"] = UnitDef(
        id="Elvish_Hero", name="Elvish Hero", race="elf", faction="Rebels",
        level=2, hp=38, cost=25, movement=6, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Great Sword", AttackType.BLADE, 8, 3, "melee"),
            Attack("Bow", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        advances_to=["Elvish Champion"],
        primary_color="#2E7D32", secondary_color="#43A047", accent_color="#C0C0C0",
        body_type="humanoid",
    )
    db["Elvish Champion"] = UnitDef(
        id="Elvish_Champion", name="Elvish Champion", race="elf", faction="Rebels",
        level=3, hp=48, cost=42, movement=6, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 10, 4, "melee", "firststrike"),
            Attack("Bow", AttackType.PIERCE, 6, 3, "ranged"),
        ],
        primary_color="#1B5E20", secondary_color="#A5D6A7", accent_color="#FFD700",
        body_type="humanoid", has_cape=True,
    )
    db["Elvish Marshal"] = UnitDef(
        id="Elvish_Marshal", name="Elvish Marshal", race="elf", faction="Rebels",
        level=3, hp=46, cost=42, movement=6, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 9, 3, "melee", "leadership"),
            Attack("Bow", AttackType.PIERCE, 6, 3, "ranged"),
        ],
        primary_color="#004D40", secondary_color="#26A69A", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_cape=True,
    )
    db["Elvish Archer"] = UnitDef(
        id="Elvish_Archer", name="Elvish Archer", race="elf", faction="Rebels",
        level=1, hp=22, cost=14, movement=6, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Bow", AttackType.PIERCE, 5, 3, "ranged", "marksman")],
        advances_to=["Elvish Marksman", "Elvish Ranger", "Elvish Avenger"],
        primary_color="#228B22", secondary_color="#8B4513", accent_color="#32CD32",
        body_type="humanoid", has_bow=True,
    )
    db["Elvish Marksman"] = UnitDef(
        id="Elvish_Marksman", name="Elvish Marksman", race="elf", faction="Rebels",
        level=2, hp=28, cost=24, movement=6, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Longbow", AttackType.PIERCE, 8, 4, "ranged", "marksman")],
        advances_to=["Elvish Sharpshooter"],
        primary_color="#1B5E20", secondary_color="#654321", accent_color="#FFD700",
        body_type="humanoid", has_bow=True,
    )
    db["Elvish Sharpshooter"] = UnitDef(
        id="Elvish_Sharpshooter", name="Elvish Sharpshooter", race="elf", faction="Rebels",
        level=3, hp=34, cost=42, movement=6, vision=8,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Master Bow", AttackType.PIERCE, 10, 5, "ranged", "marksman")],
        primary_color="#004D40", secondary_color="#3E2723", accent_color="#FFD700",
        body_type="humanoid", has_bow=True, has_cape=True,
    )
    db["Elvish Ranger"] = UnitDef(
        id="Elvish_Ranger", name="Elvish Ranger", race="elf", faction="Rebels",
        level=2, hp=30, cost=22, movement=6, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 5, 2, "melee"),
            Attack("Bow", AttackType.PIERCE, 7, 3, "ranged"),
        ],
        advances_to=["Elvish Avenger"],
        primary_color="#2E7D32", secondary_color="#1B5E20", accent_color="#8B4513",
        body_type="humanoid", has_bow=True,
    )
    db["Elvish Avenger"] = UnitDef(
        id="Elvish_Avenger", name="Elvish Avenger", race="elf", faction="Rebels",
        level=3, hp=38, cost=40, movement=6, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 7, 3, "melee"),
            Attack("Bow", AttackType.PIERCE, 9, 4, "ranged"),
        ],
        primary_color="#1B5E20", secondary_color="#A5D6A7", accent_color="#FF6347",
        body_type="humanoid", has_bow=True, has_cape=True,
    )
    db["Elvish Shaman"] = UnitDef(
        id="Elvish_Shaman", name="Elvish Shaman", race="elf", faction="Rebels",
        level=1, hp=20, cost=15, movement=5, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Staff", AttackType.IMPACT, 4, 2, "melee", "heal")],
        advances_to=["Elvish Druid", "Elvish Sorceress"],
        primary_color="#9C27B0", secondary_color="#228B22", accent_color="#FFD700",
        body_type="humanoid", has_staff=True,
    )
    db["Elvish Druid"] = UnitDef(
        id="Elvish_Druid", name="Elvish Druid", race="elf", faction="Rebels",
        level=2, hp=28, cost=25, movement=5, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Entangle", AttackType.IMPACT, 5, 3, "ranged", "slow"),
            Attack("Staff", AttackType.IMPACT, 5, 2, "melee", "heal"),
        ],
        advances_to=["Elvish Sylph"],
        primary_color="#6A1B9A", secondary_color="#1B5E20", accent_color="#FFD700",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Elvish Sorceress"] = UnitDef(
        id="Elvish_Sorceress", name="Elvish Sorceress", race="elf", faction="Rebels",
        level=2, hp=28, cost=26, movement=5, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Frost", AttackType.COLD, 9, 3, "ranged"),
            Attack("Staff", AttackType.IMPACT, 5, 2, "melee"),
        ],
        advances_to=["Elvish Enchantress"],
        primary_color="#7B1FA2", secondary_color="#CE93D8", accent_color="#00BFFF",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Elvish Enchantress"] = UnitDef(
        id="Elvish_Enchantress", name="Elvish Enchantress", race="elf", faction="Rebels",
        level=3, hp=36, cost=44, movement=5, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Glacier", AttackType.COLD, 11, 3, "ranged"),
            Attack("Staff", AttackType.IMPACT, 6, 2, "melee"),
        ],
        primary_color="#4A148C", secondary_color="#E1BEE7", accent_color="#00BFFF",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Elvish Sylph"] = UnitDef(
        id="Elvish_Sylph", name="Elvish Sylph", race="elf", faction="Rebels",
        level=3, hp=34, cost=44, movement=6, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Faerie Fire", AttackType.ARCANE, 9, 3, "ranged", "heal"),
            Attack("Staff", AttackType.IMPACT, 6, 2, "melee"),
        ],
        primary_color="#1B5E20", secondary_color="#81C784", accent_color="#FFD700",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Wose"] = UnitDef(
        id="Wose", name="Wose", race="wose", faction="Rebels",
        level=1, hp=42, cost=18, movement=3, vision=2,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Crush", AttackType.IMPACT, 9, 2, "melee")],
        advances_to=["Elder Wose"],
        primary_color="#2E7D32", secondary_color="#5D4037", accent_color="#388E3C",
        body_type="beast", size=2,
    )
    db["Elder Wose"] = UnitDef(
        id="Elder_Wose", name="Elder Wose", race="wose", faction="Rebels",
        level=2, hp=58, cost=30, movement=3, vision=2,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Crush", AttackType.IMPACT, 12, 2, "melee")],
        primary_color="#1B5E20", secondary_color="#3E2723", accent_color="#4CAF50",
        body_type="beast", size=2,
    )
    db["Merman Fighter"] = UnitDef(
        id="Merman_Fighter", name="Merman Fighter", race="merman", faction="Rebels",
        level=1, hp=26, cost=14, movement=5, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 5, 3, "melee")],
        advances_to=["Merman Warrior", "Merman Entangler"],
        primary_color="#006994", secondary_color="#40E0D0", accent_color="#8B4513",
        body_type="aquatic",
    )
    db["Merman Warrior"] = UnitDef(
        id="Merman_Warrior", name="Merman Warrior", race="merman", faction="Rebels",
        level=2, hp=36, cost=23, movement=5, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Trident", AttackType.PIERCE, 8, 3, "melee"),
            Attack("Spear", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        primary_color="#004D6E", secondary_color="#00CED1", accent_color="#B8860B",
        body_type="aquatic",
    )
    db["Merman Entangler"] = UnitDef(
        id="Merman_Entangler", name="Merman Entangler", race="merman", faction="Rebels",
        level=2, hp=34, cost=22, movement=5, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Trident", AttackType.PIERCE, 7, 3, "melee"),
            Attack("Net", AttackType.IMPACT, 4, 2, "ranged", "slow"),
        ],
        primary_color="#006994", secondary_color="#20B2AA", accent_color="#2E8B57",
        body_type="aquatic",
    )

    # ===================== NORTHERNERS (ORCS) =====================
    db["Orcish Grunt"] = UnitDef(
        id="Orcish_Grunt", name="Orcish Grunt", race="orc", faction="Northerners",
        level=1, hp=32, cost=12, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Axe", AttackType.BLADE, 7, 2, "melee")],
        advances_to=["Orcish Warrior", "Orcish Assassin"],
        primary_color="#8B4513", secondary_color="#556B2F", accent_color="#A0522D",
        body_type="humanoid",
    )
    db["Orcish Warrior"] = UnitDef(
        id="Orcish_Warrior", name="Orcish Warrior", race="orc", faction="Northerners",
        level=2, hp=44, cost=21, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Axe", AttackType.BLADE, 10, 3, "melee"),
            Attack("Crossbow", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        advances_to=["Orcish Warlord"],
        primary_color="#5C4033", secondary_color="#556B2F", accent_color="#B22222",
        body_type="humanoid", has_helm=True,
    )
    db["Orcish Warlord"] = UnitDef(
        id="Orcish_Warlord", name="Orcish Warlord", race="orc", faction="Northerners",
        level=3, hp=56, cost=35, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Great Axe", AttackType.BLADE, 12, 3, "melee", "leadership"),
            Attack("Crossbow", AttackType.PIERCE, 6, 2, "ranged"),
        ],
        primary_color="#3E2723", secondary_color="#556B2F", accent_color="#FF4500",
        body_type="humanoid", has_helm=True, has_cape=True,
    )
    db["Orcish Assassin"] = UnitDef(
        id="Orcish_Assassin", name="Orcish Assassin", race="orc", faction="Northerners",
        level=2, hp=36, cost=22, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Dagger", AttackType.BLADE, 6, 4, "melee", "poison"),
            Attack("Throwing Knife", AttackType.BLADE, 5, 2, "ranged", "poison"),
        ],
        primary_color="#333333", secondary_color="#556B2F", accent_color="#00FF00",
        body_type="humanoid",
    )
    db["Orcish Archer"] = UnitDef(
        id="Orcish_Archer", name="Orcish Archer", race="orc", faction="Northerners",
        level=1, hp=26, cost=13, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Bow", AttackType.PIERCE, 6, 2, "ranged")],
        advances_to=["Orcish Crossbowman"],
        primary_color="#8B4513", secondary_color="#556B2F", accent_color="#A0522D",
        body_type="humanoid", has_bow=True,
    )
    db["Orcish Crossbowman"] = UnitDef(
        id="Orcish_Crossbowman", name="Orcish Crossbowman", race="orc", faction="Northerners",
        level=2, hp=34, cost=22, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Crossbow", AttackType.PIERCE, 8, 3, "ranged")],
        primary_color="#5C4033", secondary_color="#556B2F", accent_color="#A0522D",
        body_type="humanoid", has_bow=True,
    )
    db["Orcish Slurbow"] = UnitDef(
        id="Orcish_Slurbow", name="Orcish Slurbow", race="orc", faction="Northerners",
        level=2, hp=30, cost=21, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Slurbow", AttackType.PIERCE, 9, 2, "ranged")],
        primary_color="#5C4033", secondary_color="#8B4513", accent_color="#00FF00",
        body_type="humanoid", has_bow=True,
    )
    db["Troll"] = UnitDef(
        id="Troll", name="Troll", race="troll", faction="Northerners",
        level=1, hp=40, cost=16, movement=4, vision=3,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Club", AttackType.IMPACT, 9, 2, "melee")],
        advances_to=["Troll Warrior", "Troll Rocklobber"],
        primary_color="#6B8E23", secondary_color="#556B2F", accent_color="#8B4513",
        body_type="beast", size=2,
    )
    db["Troll Warrior"] = UnitDef(
        id="Troll_Warrior", name="Troll Warrior", race="troll", faction="Northerners",
        level=2, hp=54, cost=26, movement=4, vision=3,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Great Club", AttackType.IMPACT, 12, 3, "melee")],
        primary_color="#556B2F", secondary_color="#2F4F2F", accent_color="#8B4513",
        body_type="beast", size=2,
    )
    db["Troll Rocklobber"] = UnitDef(
        id="Troll_Rocklobber", name="Troll Rocklobber", race="troll", faction="Northerners",
        level=2, hp=48, cost=24, movement=4, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Club", AttackType.IMPACT, 10, 2, "melee"),
            Attack("Rock", AttackType.IMPACT, 8, 2, "ranged"),
        ],
        primary_color="#6B8E23", secondary_color="#8B8682", accent_color="#A9A9A9",
        body_type="beast", size=2,
    )
    db["Goblin Knight"] = UnitDef(
        id="Goblin_Knight", name="Goblin Knight", race="goblin", faction="Northerners",
        level=1, hp=28, cost=15, movement=8, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Spear", AttackType.PIERCE, 5, 3, "melee")],
        advances_to=["Goblin Pillager", "Goblin Impaler"],
        primary_color="#556B2F", secondary_color="#8B4513", accent_color="#A0522D",
        body_type="humanoid", has_helm=True,
    )
    db["Goblin Pillager"] = UnitDef(
        id="Goblin_Pillager", name="Goblin Pillager", race="goblin", faction="Northerners",
        level=2, hp=36, cost=24, movement=8, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Spear", AttackType.PIERCE, 7, 3, "melee"),
            Attack("Bomb", AttackType.FIRE, 8, 1, "ranged"),
        ],
        primary_color="#2F4F2F", secondary_color="#8B4513", accent_color="#FF4500",
        body_type="humanoid", has_helm=True,
    )
    db["Goblin Impaler"] = UnitDef(
        id="Goblin_Impaler", name="Goblin Impaler", race="goblin", faction="Northerners",
        level=2, hp=34, cost=23, movement=8, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Trident", AttackType.PIERCE, 9, 2, "melee", "charge")],
        primary_color="#33691E", secondary_color="#795548", accent_color="#A0522D",
        body_type="humanoid", has_helm=True,
    )
    db["Naga Fighter"] = UnitDef(
        id="Naga_Fighter", name="Naga Fighter", race="naga", faction="Northerners",
        level=1, hp=30, cost=14, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Trident", AttackType.PIERCE, 6, 3, "melee")],
        advances_to=["Naga Warrior", "Naga Myrmidon"],
        primary_color="#2E8B57", secondary_color="#8B0000", accent_color="#DAA520",
        body_type="aquatic",
    )
    db["Naga Warrior"] = UnitDef(
        id="Naga_Warrior", name="Naga Warrior", race="naga", faction="Northerners",
        level=2, hp=40, cost=22, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Trident", AttackType.PIERCE, 9, 3, "melee"),
            Attack("Spear", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        primary_color="#1B5E20", secondary_color="#B71C1C", accent_color="#FFD700",
        body_type="aquatic",
    )
    db["Naga Myrmidon"] = UnitDef(
        id="Naga_Myrmidon", name="Naga Myrmidon", race="naga", faction="Northerners",
        level=3, hp=52, cost=38, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Trident", AttackType.PIERCE, 11, 3, "melee"),
            Attack("Spear", AttackType.PIERCE, 7, 3, "ranged"),
        ],
        primary_color="#004D40", secondary_color="#880E4F", accent_color="#FFD700",
        body_type="aquatic", has_cape=True,
    )
    db["Wolf Rider"] = UnitDef(
        id="Wolf_Rider", name="Wolf Rider", race="orc", faction="Northerners",
        level=1, hp=26, cost=15, movement=9, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Sword", AttackType.BLADE, 5, 3, "melee")],
        advances_to=["Wolf Raider", "Goblin Rouser"],
        primary_color="#556B2F", secondary_color="#8B4513", accent_color="#A0522D",
        body_type="humanoid",
    )
    db["Wolf Raider"] = UnitDef(
        id="Wolf_Raider", name="Wolf Raider", race="orc", faction="Northerners",
        level=2, hp=36, cost=24, movement=9, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Sword", AttackType.BLADE, 8, 3, "melee")],
        primary_color="#33691E", secondary_color="#5D4037", accent_color="#B22222",
        body_type="humanoid",
    )

    # ===================== UNDEAD =====================
    db["Skeleton"] = UnitDef(
        id="Skeleton", name="Skeleton", race="undead", faction="Undead",
        level=1, hp=22, cost=11, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Sword", AttackType.BLADE, 5, 2, "melee")],
        advances_to=["Skeleton Archer", "Revenant"],
        primary_color="#E8E8E8", secondary_color="#BDBDBD", accent_color="#424242",
        body_type="undead",
    )
    db["Skeleton Archer"] = UnitDef(
        id="Skeleton_Archer", name="Skeleton Archer", race="undead", faction="Undead",
        level=1, hp=18, cost=12, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Bow", AttackType.PIERCE, 5, 3, "ranged")],
        advances_to=["Bone Shooter", "Banebow"],
        primary_color="#E0E0E0", secondary_color="#9E9E9E", accent_color="#424242",
        body_type="undead", has_bow=True,
    )
    db["Bone Shooter"] = UnitDef(
        id="Bone_Shooter", name="Bone Shooter", race="undead", faction="Undead",
        level=2, hp=26, cost=22, movement=5, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Crossbow", AttackType.PIERCE, 7, 3, "ranged")],
        primary_color="#BDBDBD", secondary_color="#757575", accent_color="#333333",
        body_type="undead", has_bow=True,
    )
    db["Banebow"] = UnitDef(
        id="Banebow", name="Banebow", race="undead", faction="Undead",
        level=2, hp=30, cost=23, movement=5, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Longbow", AttackType.PIERCE, 8, 4, "ranged", "poison")],
        primary_color="#9E9E9E", secondary_color="#616161", accent_color="#00FF00",
        body_type="undead", has_bow=True,
    )
    db["Revenant"] = UnitDef(
        id="Revenant", name="Revenant", race="undead", faction="Undead",
        level=2, hp=34, cost=20, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Sword", AttackType.BLADE, 7, 3, "melee"),
            Attack("Cold Touch", AttackType.COLD, 5, 2, "melee"),
        ],
        primary_color="#BDBDBD", secondary_color="#757575", accent_color="#000080",
        body_type="undead",
    )
    db["Death Knight"] = UnitDef(
        id="Death_Knight", name="Death Knight", race="undead", faction="Undead",
        level=3, hp=48, cost=38, movement=7, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Sword", AttackType.BLADE, 9, 3, "melee", "charge"),
            Attack("Cold Touch", AttackType.COLD, 7, 2, "melee"),
        ],
        primary_color="#424242", secondary_color="#BDBDBD", accent_color="#191970",
        body_type="undead", has_helm=True, has_cape=True,
    )
    db["Ghost"] = UnitDef(
        id="Ghost", name="Ghost", race="undead", faction="Undead",
        level=1, hp=16, cost=13, movement=7, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Touch", AttackType.COLD, 6, 3, "melee")],
        advances_to=["Shadow", "Wraith", "Spectre"],
        primary_color="#B0C4DE", secondary_color="#E0E8F0", accent_color="#4169E1",
        body_type="undead",
    )
    db["Shadow"] = UnitDef(
        id="Shadow", name="Shadow", race="undead", faction="Undead",
        level=2, hp=22, cost=23, movement=7, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Claws", AttackType.BLADE, 7, 3, "melee")],
        primary_color="#2F2F4F", secondary_color="#4B4B7A", accent_color="#6A5ACD",
        body_type="undead",
    )
    db["Wraith"] = UnitDef(
        id="Wraith", name="Wraith", race="undead", faction="Undead",
        level=2, hp=26, cost=25, movement=7, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Claws", AttackType.BLADE, 8, 3, "melee"),
            Attack("Cold Aura", AttackType.COLD, 6, 2, "ranged"),
        ],
        primary_color="#1C1C3C", secondary_color="#3C3C6C", accent_color="#483D8B",
        body_type="undead",
    )
    db["Spectre"] = UnitDef(
        id="Spectre", name="Spectre", race="undead", faction="Undead",
        level=3, hp=32, cost=40, movement=7, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Claws", AttackType.BLADE, 9, 4, "melee"),
            Attack("Cold Aura", AttackType.COLD, 7, 2, "ranged"),
        ],
        primary_color="#0D0D2B", secondary_color="#2D2D5B", accent_color="#6A0DAD",
        body_type="undead", has_cape=True,
    )
    db["Vampire Bat"] = UnitDef(
        id="Vampire_Bat", name="Vampire Bat", race="undead", faction="Undead",
        level=1, hp=14, cost=10, movement=8, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Bite", AttackType.BLADE, 4, 3, "melee")],
        advances_to=["Blood Bat", "Dread Bat"],
        primary_color="#4A0E4E", secondary_color="#800080", accent_color="#FF0000",
        body_type="flying", has_wings=True,
    )
    db["Blood Bat"] = UnitDef(
        id="Blood_Bat", name="Blood Bat", race="undead", faction="Undead",
        level=2, hp=22, cost=20, movement=9, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Bite", AttackType.BLADE, 6, 4, "melee", "drain")],
        primary_color="#4A0E4E", secondary_color="#8B0000", accent_color="#FF0000",
        body_type="flying", has_wings=True,
    )
    db["Dread Bat"] = UnitDef(
        id="Dread_Bat", name="Dread Bat", race="undead", faction="Undead",
        level=3, hp=30, cost=35, movement=9, vision=7,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Bite", AttackType.BLADE, 8, 4, "melee", "drain"),
            Attack("Screech", AttackType.IMPACT, 5, 2, "ranged"),
        ],
        primary_color="#2D0033", secondary_color="#4B0082", accent_color="#FF0000",
        body_type="flying", has_wings=True,
    )
    db["Necromancer"] = UnitDef(
        id="Necromancer", name="Necromancer", race="human", faction="Undead",
        level=2, hp=30, cost=26, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Staff", AttackType.COLD, 7, 2, "melee"),
            Attack("Shadow Wave", AttackType.COLD, 9, 2, "ranged"),
        ],
        advances_to=["Dark Sorcerer"],
        primary_color="#2D0033", secondary_color="#4B0082", accent_color="#9400D3",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Dark Sorcerer"] = UnitDef(
        id="Dark_Sorcerer", name="Dark Sorcerer", race="human", faction="Undead",
        level=3, hp=38, cost=44, movement=5, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Staff", AttackType.COLD, 8, 2, "melee"),
            Attack("Shadow Storm", AttackType.COLD, 11, 3, "ranged"),
        ],
        primary_color="#1A0025", secondary_color="#38006B", accent_color="#BF00FF",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Walking Corpse"] = UnitDef(
        id="Walking_Corpse", name="Walking Corpse", race="undead", faction="Undead",
        level=0, hp=18, cost=8, movement=4, vision=3,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Claws", AttackType.BLADE, 4, 2, "melee")],
        primary_color="#8B7355", secondary_color="#6B5B3A", accent_color="#4A3C28",
        body_type="undead",
    )

    # ===================== DRAKES =====================
    db["Drake Clasher"] = UnitDef(
        id="Drake_Clasher", name="Drake Clasher", race="drake", faction="Drakes",
        level=1, hp=36, cost=16, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("War Blade", AttackType.BLADE, 6, 3, "melee")],
        advances_to=["Drake Slasher", "Drake Arbiter"],
        primary_color="#FF8C00", secondary_color="#FFD700", accent_color="#8B0000",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Slash"] = UnitDef(
        id="Drake_Slasher", name="Drake Slasher", race="drake", faction="Drakes",
        level=2, hp=48, cost=28, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Great Blade", AttackType.BLADE, 9, 3, "melee")],
        advances_to=["Drake Blade-master"],
        primary_color="#FF6600", secondary_color="#FFD700", accent_color="#8B0000",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Blade-master"] = UnitDef(
        id="Drake_Blade_master", name="Drake Blade-master", race="drake", faction="Drakes",
        level=3, hp=60, cost=42, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Master Blade", AttackType.BLADE, 12, 4, "melee")],
        primary_color="#E65100", secondary_color="#FFD700", accent_color="#B71C1C",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Arbiter"] = UnitDef(
        id="Drake_Arbiter", name="Drake Arbiter", race="drake", faction="Drakes",
        level=2, hp=46, cost=27, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("War Blade", AttackType.BLADE, 8, 3, "melee", "leadership"),
            Attack("Fire Breath", AttackType.FIRE, 6, 2, "ranged"),
        ],
        advances_to=["Drake Flare-master"],
        primary_color="#FF8C00", secondary_color="#FFD700", accent_color="#B71C1C",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Flare-master"] = UnitDef(
        id="Drake_Flare_master", name="Drake Flare-master", race="drake", faction="Drakes",
        level=3, hp=56, cost=42, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("War Blade", AttackType.BLADE, 9, 3, "melee", "leadership"),
            Attack("Fire Breath", AttackType.FIRE, 9, 3, "ranged"),
        ],
        primary_color="#E65100", secondary_color="#FFD700", accent_color="#FF0000",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Burner"] = UnitDef(
        id="Drake_Burner", name="Drake Burner", race="drake", faction="Drakes",
        level=1, hp=32, cost=16, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Fire Breath", AttackType.FIRE, 7, 2, "ranged")],
        advances_to=["Drake Firestarter", "Drake Flamer"],
        primary_color="#FF4500", secondary_color="#FFD700", accent_color="#FF0000",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Firestarter"] = UnitDef(
        id="Drake_Firestarter", name="Drake Firestarter", race="drake", faction="Drakes",
        level=2, hp=44, cost=28, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Fire Breath", AttackType.FIRE, 10, 3, "ranged"),
            Attack("Claws", AttackType.BLADE, 5, 2, "melee"),
        ],
        primary_color="#FF0000", secondary_color="#FFD700", accent_color="#8B0000",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Fighter"] = UnitDef(
        id="Drake_Fighter", name="Drake Fighter", race="drake", faction="Drakes",
        level=1, hp=34, cost=15, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Claws", AttackType.BLADE, 5, 3, "melee")],
        advances_to=["Drake Warrior", "Drake Glider"],
        primary_color="#FF8C00", secondary_color="#FFA500", accent_color="#8B4513",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Warrior"] = UnitDef(
        id="Drake_Warrior", name="Drake Warrior", race="drake", faction="Drakes",
        level=2, hp=46, cost=26, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Claws", AttackType.BLADE, 8, 3, "melee"),
            Attack("Fire Breath", AttackType.FIRE, 5, 2, "ranged"),
        ],
        primary_color="#FF6600", secondary_color="#FFA500", accent_color="#8B4513",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Glider"] = UnitDef(
        id="Drake_Glider", name="Drake Glider", race="drake", faction="Drakes",
        level=2, hp=40, cost=25, movement=8, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Claws", AttackType.BLADE, 7, 3, "melee")],
        primary_color="#20B2AA", secondary_color="#FFD700", accent_color="#FF8C00",
        body_type="flying", has_wings=True, size=2,
    )

    # ===================== KNALGAN ALLIANCE (DWARVES) =====================
    db["Dwarvish Fighter"] = UnitDef(
        id="Dwarvish_Fighter", name="Dwarvish Fighter", race="dwarf", faction="Knalgan Alliance",
        level=1, hp=34, cost=13, movement=4, vision=3,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Axe", AttackType.BLADE, 6, 3, "melee")],
        advances_to=["Dwarvish Steelclad", "Dwarvish Thunderer", "Dwarvish Berserker"],
        primary_color="#8B4513", secondary_color="#A0522D", accent_color="#B8860B",
        body_type="humanoid", has_helm=True,
    )
    db["Dwarvish Steelclad"] = UnitDef(
        id="Dwarvish_Steelclad", name="Dwarvish Steelclad", race="dwarf", faction="Knalgan Alliance",
        level=2, hp=48, cost=23, movement=4, vision=3,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Axe", AttackType.BLADE, 9, 3, "melee"),
            Attack("Crossbow", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        advances_to=["Dwarvish Lord"],
        primary_color="#654321", secondary_color="#8B4513", accent_color="#DAA520",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Dwarvish Lord"] = UnitDef(
        id="Dwarvish_Lord", name="Dwarvish Lord", race="dwarf", faction="Knalgan Alliance",
        level=3, hp=60, cost=40, movement=4, vision=3,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Great Axe", AttackType.BLADE, 11, 3, "melee", "leadership"),
            Attack("Crossbow", AttackType.PIERCE, 6, 2, "ranged"),
        ],
        primary_color="#4A2C0A", secondary_color="#8B4513", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Dwarvish Thunderer"] = UnitDef(
        id="Dwarvish_Thunderer", name="Dwarvish Thunderer", race="dwarf", faction="Knalgan Alliance",
        level=1, hp=28, cost=16, movement=4, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Musket", AttackType.IMPACT, 9, 2, "ranged")],
        advances_to=["Dwarvish Dragonguard", "Dwarvish Runemaster"],
        primary_color="#8B4513", secondary_color="#696969", accent_color="#FFD700",
        body_type="humanoid", has_helm=True,
    )
    db["Dwarvish Dragonguard"] = UnitDef(
        id="Dwarvish_Dragonguard", name="Dwarvish Dragonguard", race="dwarf", faction="Knalgan Alliance",
        level=2, hp=38, cost=28, movement=4, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Musket", AttackType.IMPACT, 12, 2, "ranged"),
            Attack("Hammer", AttackType.IMPACT, 7, 2, "melee"),
        ],
        advances_to=["Dwarvish Stalwart"],
        primary_color="#654321", secondary_color="#4A4A4A", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Dwarvish Stalwart"] = UnitDef(
        id="Dwarvish_Stalwart", name="Dwarvish Stalwart", race="dwarf", faction="Knalgan Alliance",
        level=3, hp=52, cost=46, movement=4, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Heavy Musket", AttackType.IMPACT, 15, 2, "ranged"),
            Attack("Hammer", AttackType.IMPACT, 9, 2, "melee"),
        ],
        primary_color="#4A2C0A", secondary_color="#333333", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Dwarvish Runemaster"] = UnitDef(
        id="Dwarvish_Runemaster", name="Dwarvish Runemaster", race="dwarf", faction="Knalgan Alliance",
        level=2, hp=36, cost=30, movement=4, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Musket", AttackType.IMPACT, 10, 2, "ranged"),
            Attack("Runed Hammer", AttackType.ARCANE, 7, 2, "melee"),
        ],
        advances_to=["Dwarvish Runesmith"],
        primary_color="#654321", secondary_color="#191970", accent_color="#00BFFF",
        body_type="humanoid", has_helm=True, has_staff=True,
    )
    db["Dwarvish Runesmith"] = UnitDef(
        id="Dwarvish_Runesmith", name="Dwarvish Runesmith", race="dwarf", faction="Knalgan Alliance",
        level=3, hp=44, cost=46, movement=4, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Musket", AttackType.IMPACT, 11, 2, "ranged"),
            Attack("Runed Hammer", AttackType.ARCANE, 9, 3, "melee"),
        ],
        primary_color="#4A2C0A", secondary_color="#0D47A1", accent_color="#00E5FF",
        body_type="humanoid", has_helm=True, has_staff=True, has_cape=True,
    )
    db["Dwarvish Berserker"] = UnitDef(
        id="Dwarvish_Berserker", name="Dwarvish Berserker", race="dwarf", faction="Knalgan Alliance",
        level=2, hp=38, cost=22, movement=5, vision=3,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Axe", AttackType.BLADE, 7, 4, "melee", "berserk")],
        primary_color="#B22222", secondary_color="#8B4513", accent_color="#FFD700",
        body_type="humanoid", has_helm=True,
    )
    db["Gryphon"] = UnitDef(
        id="Gryphon", name="Gryphon", race="gryphon", faction="Knalgan Alliance",
        level=2, hp=38, cost=25, movement=8, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Claws", AttackType.BLADE, 8, 3, "melee")],
        primary_color="#DAA520", secondary_color="#F5DEB3", accent_color="#8B4513",
        body_type="flying", has_wings=True, size=2,
    )
    db["Gryphon Master"] = UnitDef(
        id="Gryphon_Master", name="Gryphon Master", race="gryphon", faction="Knalgan Alliance",
        level=3, hp=50, cost=42, movement=9, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Talon", AttackType.BLADE, 11, 3, "melee")],
        primary_color="#B8860B", secondary_color="#F5DEB3", accent_color="#8B4513",
        body_type="flying", has_wings=True, size=2,
    )

    # ===================== SAURIANS =====================
    db["Saurian Skirmisher"] = UnitDef(
        id="Saurian_Skirmisher", name="Saurian Skirmisher", race="saurian", faction="Saurians",
        level=1, hp=24, cost=12, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Spear", AttackType.PIERCE, 5, 2, "melee")],
        advances_to=["Saurian Fighter", "Saurian Augur"],
        primary_color="#556B2F", secondary_color="#8FBC8F", accent_color="#DAA520",
        body_type="humanoid",
    )
    db["Saurian Fighter"] = UnitDef(
        id="Saurian_Fighter", name="Saurian Fighter", race="saurian", faction="Saurians",
        level=2, hp=34, cost=21, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Spear", AttackType.PIERCE, 7, 3, "melee"),
            Attack("Javelin", AttackType.PIERCE, 6, 2, "ranged"),
        ],
        advances_to=["Saurian Warrior", "Saurian Oracle"],
        primary_color="#4A5D23", secondary_color="#6B8E23", accent_color="#B8860B",
        body_type="humanoid", has_shield=True,
    )
    db["Saurian Warrior"] = UnitDef(
        id="Saurian_Warrior", name="Saurian Warrior", race="saurian", faction="Saurians",
        level=3, hp=44, cost=35, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Spear", AttackType.PIERCE, 9, 3, "melee"),
            Attack("Javelin", AttackType.PIERCE, 8, 2, "ranged"),
        ],
        primary_color="#3B4A1B", secondary_color="#556B2F", accent_color="#DAA520",
        body_type="humanoid", has_shield=True, has_helm=True,
    )
    db["Saurian Augur"] = UnitDef(
        id="Saurian_Augur", name="Saurian Augur", race="saurian", faction="Saurians",
        level=2, hp=28, cost=24, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Cold Bolt", AttackType.COLD, 8, 2, "ranged")],
        advances_to=["Saurian Oracle"],
        primary_color="#2E8B57", secondary_color="#556B2F", accent_color="#00BFFF",
        body_type="humanoid", has_staff=True,
    )
    db["Saurian Oracle"] = UnitDef(
        id="Saurian_Oracle", name="Saurian Oracle", race="saurian", faction="Saurians",
        level=3, hp=36, cost=40, movement=6, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Ice Storm", AttackType.COLD, 11, 3, "ranged")],
        primary_color="#1B5E20", secondary_color="#2E8B57", accent_color="#00E5FF",
        body_type="humanoid", has_staff=True, has_cape=True,
    )

    # ===================== OUTLAWS =====================
    db["Thief"] = UnitDef(
        id="Thief", name="Thief", race="human", faction="Outlaws",
        level=1, hp=22, cost=13, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Dagger", AttackType.BLADE, 4, 3, "melee")],
        advances_to=["Rogue", "Footpad"],
        primary_color="#2F2F2F", secondary_color="#555555", accent_color="#8B4513",
        body_type="humanoid",
    )
    db["Rogue"] = UnitDef(
        id="Rogue", name="Rogue", race="human", faction="Outlaws",
        level=2, hp=30, cost=22, movement=6, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Dagger", AttackType.BLADE, 6, 3, "melee", "backstab"),
            Attack("Throwing Knife", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        advances_to=["Assassin"],
        primary_color="#1A1A1A", secondary_color="#444444", accent_color="#8B0000",
        body_type="humanoid",
    )
    db["Assassin"] = UnitDef(
        id="Assassin", name="Assassin", race="human", faction="Outlaws",
        level=3, hp=38, cost=38, movement=6, vision=7,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Dagger", AttackType.BLADE, 7, 4, "melee", "backstab poison"),
            Attack("Throwing Knife", AttackType.PIERCE, 6, 3, "ranged", "poison"),
        ],
        primary_color="#0D0D0D", secondary_color="#333333", accent_color="#00FF00",
        body_type="humanoid", has_cape=True,
    )
    db["Footpad"] = UnitDef(
        id="Footpad", name="Footpad", race="human", faction="Outlaws",
        level=1, hp=24, cost=11, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Club", AttackType.IMPACT, 5, 2, "melee")],
        advances_to=["Highwayman", "Trapper"],
        primary_color="#5D4037", secondary_color="#795548", accent_color="#8B4513",
        body_type="humanoid",
    )
    db["Highwayman"] = UnitDef(
        id="Highwayman", name="Highwayman", race="human", faction="Outlaws",
        level=2, hp=32, cost=20, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Club", AttackType.IMPACT, 7, 3, "melee"),
            Attack("Crossbow", AttackType.PIERCE, 6, 2, "ranged"),
        ],
        primary_color="#3E2723", secondary_color="#5D4037", accent_color="#B8860B",
        body_type="humanoid",
    )
    db["Trapper"] = UnitDef(
        id="Trapper", name="Trapper", race="human", faction="Outlaws",
        level=2, hp=28, cost=19, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Club", AttackType.IMPACT, 6, 2, "melee"),
            Attack("Net", AttackType.IMPACT, 4, 2, "ranged", "slow"),
        ],
        primary_color="#4A3C28", secondary_color="#6B5B3A", accent_color="#2E8B57",
        body_type="humanoid",
    )
    db["Poacher"] = UnitDef(
        id="Poacher", name="Poacher", race="human", faction="Outlaws",
        level=1, hp=20, cost=11, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Sling", AttackType.IMPACT, 5, 2, "ranged")],
        advances_to=["Huntsman"],
        primary_color="#556B2F", secondary_color="#8B4513", accent_color="#696969",
        body_type="humanoid",
    )
    db["Huntsman"] = UnitDef(
        id="Huntsman", name="Huntsman", race="human", faction="Outlaws",
        level=2, hp=28, cost=20, movement=5, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Sling", AttackType.IMPACT, 7, 3, "ranged"),
            Attack("Dagger", AttackType.BLADE, 4, 2, "melee"),
        ],
        primary_color="#33691E", secondary_color="#5D4037", accent_color="#696969",
        body_type="humanoid",
    )

    # ===================== MERFOLK =====================
    db["Merfolk Diviner"] = UnitDef(
        id="Merfolk_Diviner", name="Merfolk Diviner", race="merman", faction="Merfolk",
        level=1, hp=20, cost=15, movement=5, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 4, 2, "melee"), Attack("Water Bolt", AttackType.COLD, 6, 2, "ranged")],
        advances_to=["Merfolk Enchantress", "Merfolk Priestess"],
        primary_color="#006994", secondary_color="#40E0D0", accent_color="#E040FB",
        body_type="aquatic", has_staff=True,
    )
    db["Merfolk Enchantress"] = UnitDef(
        id="Merfolk_Enchantress", name="Merfolk Enchantress", race="merman", faction="Merfolk",
        level=2, hp=28, cost=25, movement=5, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 5, 2, "melee"), Attack("Tidal Wave", AttackType.COLD, 9, 2, "ranged")],
        advances_to=["Merfolk Siren"],
        primary_color="#004D6E", secondary_color="#00CED1", accent_color="#AA00FF",
        body_type="aquatic", has_staff=True, has_cape=True,
    )
    db["Merfolk Siren"] = UnitDef(
        id="Merfolk_Siren", name="Merfolk Siren", race="merman", faction="Merfolk",
        level=3, hp=36, cost=44, movement=5, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 6, 2, "melee"), Attack("Tsunami", AttackType.COLD, 12, 3, "ranged")],
        primary_color="#003344", secondary_color="#008B8B", accent_color="#D500F9",
        body_type="aquatic", has_staff=True, has_cape=True,
    )
    db["Merfolk Priestess"] = UnitDef(
        id="Merfolk_Priestess", name="Merfolk Priestess", race="merman", faction="Merfolk",
        level=2, hp=26, cost=26, movement=5, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 4, 2, "melee"), Attack("Holy Water", AttackType.ARCANE, 8, 2, "ranged", "heal")],
        primary_color="#1A237E", secondary_color="#40E0D0", accent_color="#FFD700",
        body_type="aquatic", has_staff=True,
    )
    db["Merfolk Netcaster"] = UnitDef(
        id="Merfolk_Netcaster", name="Merfolk Netcaster", race="merman", faction="Merfolk",
        level=1, hp=22, cost=13, movement=5, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 5, 2, "melee"), Attack("Net", AttackType.IMPACT, 3, 2, "ranged", "slow")],
        primary_color="#006994", secondary_color="#2E8B57", accent_color="#DAA520",
        body_type="aquatic",
    )
    db["Merfolk Hoplite"] = UnitDef(
        id="Merfolk_Hoplite", name="Merfolk Hoplite", race="merman", faction="Merfolk",
        level=2, hp=34, cost=22, movement=5, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 8, 3, "melee"), Attack("Spear", AttackType.PIERCE, 5, 2, "ranged")],
        primary_color="#004D6E", secondary_color="#B8860B", accent_color="#DAA520",
        body_type="aquatic", has_shield=True,
    )

    return db


# Module-level singleton
DATABASE: Dict[str, UnitDef] = _build_database()


def get_all_factions() -> List[str]:
    """Return sorted list of all faction names."""
    return sorted(set(u.faction for u in DATABASE.values()))


def get_units_by_faction(faction: str) -> List[UnitDef]:
    """Return all units belonging to a faction, sorted by level then name."""
    units = [u for u in DATABASE.values() if u.faction == faction]
    return sorted(units, key=lambda u: (u.level, u.name))


def get_unit_by_id(unit_id: str) -> Optional[UnitDef]:
    """Look up a unit definition by its id."""
    return DATABASE.get(unit_id)


def get_all_units() -> List[UnitDef]:
    """Return every unit in the database sorted by faction, level, name."""
    return sorted(DATABASE.values(), key=lambda u: (u.faction, u.level, u.name))


def get_faction_color(faction: str) -> str:
    """Return a representative color for each faction."""
    colors = {
        "Loyalists": "#3366CC",
        "Rebels": "#228B22",
        "Northerners": "#8B4513",
        "Undead": "#4B0082",
        "Drakes": "#FF6600",
        "Knalgan Alliance": "#8B4513",
        "Saurians": "#556B2F",
        "Outlaws": "#333333",
        "Merfolk": "#006994",
    }
    return colors.get(faction, "#808080")

# =========================================================================
# SCENARIOS - 8 preset battle definitions
# =========================================================================



# =============================================================================
# Terrain code reference (real Wesnoth terrain codes)
# =============================================================================
# Gg  = Grassland        Gg^Fp = Forest       Gg^Fm = Flower meadow
# Re  = Road             Re^Et = Road (elven)  Ch  = Chasm/cave wall
# Hh  = Hills            Hh^Fp = Hills+forest  Mm  = Mountains
# Mm^Xm = Mountains+peak  Ds  = Desert/sand    Ss  = Shallow water
# Wo  = Deep water       Wo^Dt = Deep water+coast Ww = Reef
# Wt  = Swamp water      St  = Swamp          Ur  = Cave floor
# Cv  = Cave             Cud = Cave (dwarven)  Kha = Keep (allied)
# Khb = Keep (bandit)    Khr = Keep (rebels)   Khu = Keep (undead)
# Chs = Castle (swamp)   Chb = Cave (bat)     Cvb = Cave (bat)
# Cvc = Cave (crystal)   Vv  = Village        Ai  = Anc. ice
# Afa = An. forest       Ha  = Snow           Ms  = Impassable mt.
# Xos = Oasis

class TimeOfDay(Enum):
    """Wesnoth time-of-day schedule."""
    DAWN = "dawn"
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    FIRST_WATCH = "first_watch"
    SECOND_WATCH = "second_watch"
    DEEP_NIGHT = "deep_night"


class WeatherType(Enum):
    """Weather effects (visual via Lua color_adjust)."""
    CLEAR = "clear"
    RAIN = "rain"
    SNOW = "snow"
    FOG = "fog"
    STORM = "storm"


@dataclass
class SideConfig:
    """Configuration for one side in a scenario."""
    side_number: int
    controller: str = "ai"  # "ai" or "human"
    faction: str = ""  # Wesnoth faction name for filtering
    color: str = ""  # Team color palette
    gold: int = 100
    income: int = 0
    can_recruit: List[str] = field(default_factory=list)
    leader_type: str = ""  # Wesnoth unit type ID for leader
    leader_x: int = 0
    leader_y: int = 0
    ai_aggression: float = 0.5  # 0.0 to 1.0
    ai_caution: float = 0.25
    ai_recruitment_ratio: float = 0.5
    # Additional pre-placed units
    extra_units: List[Dict] = field(default_factory=list)


@dataclass
class ScenarioDef:
    """Complete definition of a battle scenario."""
    id: str  # Scenario ID (used in WML [scenario] id=)
    name: str  # Display name
    description: str  # Scenario description
    map_data: List[str]  # WML map lines (comma-separated terrain codes)
    sides: List[SideConfig] = field(default_factory=list)
    max_turns: int = 30
    turns_to_record: int = 20  # Stop recording after this many turns
    victory_condition: str = "kill enemy leader"
    defeat_condition: str = "lose leader"
    time_of_day: TimeOfDay = TimeOfDay.MIDDAY
    weather: WeatherType = WeatherType.CLEAR
    # Lua camera directives
    camera_pacing: str = "cinematic"  # "cinematic", "fast", "follow_action"
    camera_zoom: float = 1.0
    # Turn events (WML [event] blocks)
    turn_events: List[Dict] = field(default_factory=list)
    # Music track (from Wesnoth default)
    music: str = "battle.ogg"
    # Map dimensions (derived from map_data)
    width: int = 0
    height: int = 0

    def __post_init__(self):
        if self.map_data:
            self.height = len(self.map_data)
            self.width = len(self.map_data[0].split(",")) if self.map_data[0] else 0


# =============================================================================
# MAP BUILDER HELPERS
# =============================================================================

def _fill(terrain: str, w: int, h: int) -> List[str]:
    """Create a map filled with a single terrain type."""
    return [",".join([terrain] * w) for _ in range(h)]


def _place_castle(map_lines: List[str], cx: int, cy: int, side: int,
                   castle_terrain: str = "Cv", keep_terrain: str = "Kh"):
    """Place a castle with keep centered at (cx, cy). Returns modified map."""
    m = [line.split(",") for line in map_lines]
    # Castle is 3x2 hex pattern (offset coords)
    positions = [
        (0, 0), (-1, 0), (1, 0),
        (-2, -1), (-1, -1), (0, -1), (1, -1), (2, -1),
    ]
    for dx, dy in positions:
        px, py = cx + dx, cy + dy
        if 0 <= py < len(m) and 0 <= px < len(m[py]):
            if dx == 0 and dy == 0:
                # Keep for this side: prefix with side number
                m[py][px] = f"{side} {keep_terrain}"
            else:
                m[py][px] = castle_terrain
    return [",".join(row) for row in m]


def _place_villages(map_lines: List[str], positions: List[Tuple[int, int]]) -> List[str]:
    """Place villages at given positions."""
    m = [line.split(",") for line in map_lines]
    for x, y in positions:
        if 0 <= y < len(m) and 0 <= x < len(m[y]):
            m[y][x] = "Vv"
    return [",".join(row) for row in m]


def _set_terrain(map_lines: List[str], x: int, y: int, terrain: str) -> List[str]:
    """Set a single hex terrain."""
    m = [line.split(",") for line in map_lines]
    if 0 <= y < len(m) and 0 <= x < len(m[y]):
        m[y][x] = terrain
    return [",".join(row) for row in m]


def _draw_terrain_rect(map_lines: List[str], x1: int, y1: int, x2: int, y2: int,
                        terrain: str) -> List[str]:
    """Fill a rectangular area with terrain."""
    m = [line.split(",") for line in map_lines]
    for y in range(max(0, y1), min(len(m), y2 + 1)):
        for x in range(max(0, x1), min(len(m[y]), x2 + 1)):
            m[y][x] = terrain
    return [",".join(row) for row in m]


def _draw_road(map_lines: List[str], points: List[Tuple[int, int]]) -> List[str]:
    """Draw a road through a series of waypoints."""
    m = [line.split(",") for line in map_lines]
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        steps = max(abs(x2 - x1), abs(y2 - y1), 1)
        for s in range(steps + 1):
            t = s / steps
            x = int(x1 + (x2 - x1) * t)
            y = int(y1 + (y2 - y1) * t)
            if 0 <= y < len(m) and 0 <= x < len(m[y]):
                # Don't overwrite castles/keeps
                if not m[y][x].startswith(("C", "K")):
                    m[y][x] = "Re"
    return [",".join(row) for row in m]


def _draw_river(map_lines: List[str], y_pos: int, gaps: List[Tuple[int, int]] = None,
                 water_terrain: str = "Ww") -> List[str]:
    """Draw a horizontal river with gaps (bridges)."""
    m = [line.split(",") for line in map_lines]
    w = len(m[0]) if m else 0
    gap_ranges = gaps or []
    for x in range(w):
        in_gap = False
        for g_start, g_end in gap_ranges:
            if g_start <= x <= g_end:
                in_gap = True
                break
        if not in_gap and 0 <= y_pos < len(m):
            if 0 <= x < len(m[y_pos]):
                m[y_pos][x] = water_terrain
            if y_pos + 1 < len(m) and 0 <= x < len(m[y_pos + 1]):
                m[y_pos + 1][x] = water_terrain
    return [",".join(row) for row in m]


# =============================================================================
# SCENARIO 1: CLASSIC BATTLEFIELD
# =============================================================================
def create_classic_battlefield() -> ScenarioDef:
    """Two armies face off on an open grassland with scattered villages."""
    W, H = 20, 14
    m = _fill("Gg", W, H)

    # Scatter forests
    random.seed(42)
    forest_positions = [
        (5, 3), (6, 3), (14, 3), (15, 3),
        (3, 7), (4, 7), (16, 7), (17, 7),
        (7, 10), (8, 10), (12, 10), (13, 10),
        (9, 5), (10, 5), (11, 5),
    ]
    for fx, fy in forest_positions:
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Hills along flanks
    for x in range(1, 4):
        m = _set_terrain(m, x, 1, "Hh")
        m = _set_terrain(m, x, 12, "Hh")
        m = _set_terrain(m, W - 1 - x, 1, "Hh")
        m = _set_terrain(m, W - 1 - x, 12, "Hh")

    # Villages in strategic positions
    villages = [
        (10, 4), (9, 7), (10, 10),  # Center column
        (5, 5), (15, 9),             # Flanks
        (7, 3), (13, 11),            # Support
    ]
    m = _place_villages(m, villages)

    # Road connecting the two keeps
    m = _draw_road(m, [(3, 7), (7, 7), (10, 7), (13, 7), (17, 7)])

    # Castles
    m = _place_castle(m, 3, 7, 1)
    m = _place_castle(m, 17, 7, 2)

    side_a = SideConfig(
        side_number=1, faction="Loyalists", color="blue",
        gold=150, income=2,
        leader_type="General",
        leader_x=3, leader_y=7,
        can_recruit=["Spearman", "Bowman", "Cavalryman", "Heavy Infantryman",
                      "Mage", "Fencer", "Horseman"],
        ai_aggression=0.6, ai_caution=0.2,
        extra_units=[
            {"type": "Spearman", "x": 2, "y": 6},
            {"type": "Bowman", "x": 4, "y": 6},
            {"type": "Cavalryman", "x": 2, "y": 8},
            {"type": "Spearman", "x": 4, "y": 8},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Northerners", color="red",
        gold=150, income=2,
        leader_type="Orcish Warlord",
        leader_x=17, leader_y=7,
        can_recruit=["Orcish Grunt", "Orcish Archer", "Orcish Assassin",
                      "Troll", "Goblin Spearman", "Wolf Rider", "Orcish Crossbowman"],
        ai_aggression=0.7, ai_caution=0.15,
        extra_units=[
            {"type": "Orcish Grunt", "x": 16, "y": 6},
            {"type": "Troll", "x": 18, "y": 6},
            {"type": "Wolf Rider", "x": 16, "y": 8},
            {"type": "Orcish Archer", "x": 18, "y": 8},
        ],
    )

    return ScenarioDef(
        id="classic_battlefield",
        name="Classic Battlefield",
        description="Two great armies clash on open grassland. The Loyalist Crown "
                    "forces march against a horde of Northern orcs in a classic "
                    "pitched battle. Villages dot the landscape, offering vital "
                    "resources to whichever side can hold them. A road connects "
                    "the two keeps through the center of the field.",
        map_data=m, sides=[side_a, side_b],
        max_turns=30, turns_to_record=25,
        time_of_day=TimeOfDay.MIDDAY, weather=WeatherType.CLEAR,
        camera_pacing="cinematic", camera_zoom=1.0,
        music="battle.ogg",
    )


# =============================================================================
# SCENARIO 2: CASTLE SIEGE
# =============================================================================
def create_castle_siege() -> ScenarioDef:
    """Defenders hold a large fortress against a besieging army."""
    W, H = 22, 16
    m = _fill("Gg", W, H)

    # Large defender castle complex (side 1) on the left
    # Outer walls (mountains as walls)
    for x in range(2, 9):
        m = _set_terrain(m, x, 2, "Mm")
        m = _set_terrain(m, x, 13, "Mm")
    for y in range(2, 14):
        m = _set_terrain(m, 1, y, "Mm")
        m = _set_terrain(m, 9, y, "Mm")
    # Gate opening
    m = _set_terrain(m, 9, 7, "Re")
    m = _set_terrain(m, 9, 8, "Re")
    # Inner area
    m = _place_castle(m, 5, 8, 1)
    # Inner villages (supplies)
    inner_villages = [(3, 5), (7, 5), (3, 11), (7, 11), (5, 6), (5, 10)]
    m = _place_villages(m, inner_villages)

    # Attacker camps (side 2) on the right
    m = _place_castle(m, 18, 8, 2)

    # Attacker siege positions (hills for archers)
    for y in range(4, 12):
        m = _set_terrain(m, 11, y, "Hh")
    for y in range(5, 11):
        m = _set_terrain(m, 12, y, "Hh")

    # Forests providing cover for approach
    forest_positions = [
        (13, 3), (14, 3), (13, 4),
        (13, 12), (14, 12), (13, 11),
        (15, 6), (15, 7), (15, 8), (15, 9),
    ]
    for fx, fy in forest_positions:
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Outer villages
    outer_villages = [(10, 3), (10, 13), (15, 4), (15, 11)]
    m = _place_villages(m, outer_villages)

    # Road from attacker keep to castle gate
    m = _draw_road(m, [(18, 8), (14, 8), (10, 8), (9, 8)])

    side_a = SideConfig(
        side_number=1, faction="Loyalists", color="blue",
        gold=200, income=4,
        leader_type="Grand Marshal",
        leader_x=5, leader_y=8,
        can_recruit=["Spearman", "Bowman", "Heavy Infantryman",
                      "Longbowman", "Cavalryman", "Mage"],
        ai_aggression=0.3, ai_caution=0.5,  # Defensive
        extra_units=[
            {"type": "Heavy Infantryman", "x": 4, "y": 7},
            {"type": "Heavy Infantryman", "x": 6, "y": 7},
            {"type": "Longbowman", "x": 3, "y": 7},
            {"type": "Longbowman", "x": 7, "y": 7},
            {"type": "Spearman", "x": 4, "y": 9},
            {"type": "Spearman", "x": 6, "y": 9},
            {"type": "Mage", "x": 5, "y": 7},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Undead", color="red",
        gold=200, income=3,
        leader_type="Ancient Lich",
        leader_x=18, leader_y=8,
        can_recruit=["Skeleton", "Skeleton Archer", "Ghost", "Necrophage",
                      "Ghoul", "Dark Adept", "Bone Shooter"],
        ai_aggression=0.6, ai_caution=0.3,
        extra_units=[
            {"type": "Skeleton", "x": 17, "y": 7},
            {"type": "Skeleton", "x": 19, "y": 7},
            {"type": "Skeleton Archer", "x": 17, "y": 9},
            {"type": "Skeleton Archer", "x": 19, "y": 9},
            {"type": "Ghost", "x": 16, "y": 8},
            {"type": "Dark Adept", "x": 20, "y": 8},
        ],
    )

    return ScenarioDef(
        id="castle_siege",
        name="Castle Siege",
        description="A mighty Loyalist fortress stands under siege by an undead "
                    "horde. The defenders must hold their walls while the undead "
                    "legions throw wave after wave of skeletons and dark magic "
                    "against the battlements. Hills provide vantage points for "
                    "the besiegers' archers, while forests offer cover for "
                    "flanking maneuvers.",
        map_data=m, sides=[side_a, side_b],
        max_turns=35, turns_to_record=25,
        time_of_day=TimeOfDay.DUSK, weather=WeatherType.FOG,
        camera_pacing="cinematic", camera_zoom=0.9,
        music="siege_of_laurelmor.ogg",
        turn_events=[
            {"turn": 1, "action": "message", "side": 2,
             "text": "The dead shall claim these walls!"},
            {"turn": 5, "action": "reinforcements", "side": 2,
             "units": [{"type": "Walking Corpse", "x": 12, "y": 4},
                       {"type": "Walking Corpse", "x": 12, "y": 12}]},
            {"turn": 10, "action": "message", "side": 1,
             "text": "Hold the line! Reinforcements are coming!"},
            {"turn": 10, "action": "reinforcements", "side": 1,
             "units": [{"type": "Paladin", "x": 7, "y": 6},
                       {"type": "Cavalryman", "x": 7, "y": 10}]},
        ],
    )


# =============================================================================
# SCENARIO 3: FOREST AMBUSH
# =============================================================================
def create_forest_ambush() -> ScenarioDef:
    """Dense forest map where rebels ambush a marching army."""
    W, H = 22, 16
    m = _fill("Gg^Fp", W, H)  # Mostly forest

    # Clearings
    clearings = [
        (3, 3, 6, 6),    # NW clearing (side 1 start)
        (16, 10, 19, 13), # SE clearing (side 2 start)
        (9, 6, 12, 9),   # Central clearing (battlefield)
        (2, 12, 4, 14),  # SW pond area
        (18, 2, 20, 4),  # NE hills
    ]
    for x1, y1, x2, y2 in clearings:
        m = _draw_terrain_rect(m, x1, y1, x2, y2, "Gg")

    # Paths through forest (roads)
    m = _draw_road(m, [(5, 5), (7, 6), (9, 7), (10, 7)])
    m = _draw_road(m, [(12, 8), (14, 9), (16, 11)])
    m = _draw_road(m, [(10, 7), (10, 5), (10, 3)])

    # Water features (small pond)
    m = _set_terrain(m, 3, 13, "Ww")
    m = _set_terrain(m, 3, 14, "Ww")
    m = _set_terrain(m, 4, 13, "Ss")

    # Hills in NE
    for x in range(18, 21):
        for y in range(2, 5):
            m = _set_terrain(m, x, y, "Hh")

    # Villages hidden in clearings
    villages = [
        (4, 4), (10, 7), (17, 11),
        (5, 8), (16, 7), (10, 3), (11, 11),
    ]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 4, 4, 1)
    m = _place_castle(m, 18, 12, 2)

    side_a = SideConfig(
        side_number=1, faction="Rebels", color="green",
        gold=130, income=2,
        leader_type="Elvish Captain",
        leader_x=4, leader_y=4,
        can_recruit=["Elvish Fighter", "Elvish Archer", "Elvish Scout",
                      "Elvish Shaman", "Wose", "Elvish Druid"],
        ai_aggression=0.5, ai_caution=0.3,
        extra_units=[
            {"type": "Elvish Fighter", "x": 5, "y": 4},
            {"type": "Elvish Archer", "x": 3, "y": 4},
            {"type": "Elvish Fighter", "x": 5, "y": 5},
            {"type": "Elvish Archer", "x": 3, "y": 5},
            {"type": "Wose", "x": 7, "y": 3},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Loyalists", color="red",
        gold=160, income=2,
        leader_type="General",
        leader_x=18, leader_y=12,
        can_recruit=["Spearman", "Bowman", "Cavalryman",
                      "Heavy Infantryman", "Mage", "Fencer"],
        ai_aggression=0.7, ai_caution=0.15,  # Aggressive march
        extra_units=[
            {"type": "Spearman", "x": 17, "y": 11},
            {"type": "Cavalryman", "x": 19, "y": 11},
            {"type": "Spearman", "x": 17, "y": 13},
            {"type": "Bowman", "x": 19, "y": 13},
            {"type": "Heavy Infantryman", "x": 16, "y": 12},
        ],
    )

    return ScenarioDef(
        id="forest_ambush",
        name="Forest Ambush",
        description="Deep in the great Aethenwood, elvish rebels lie in wait "
                    "along forest paths. A Loyalist army, marching to suppress "
                    "the rebellion, must navigate through dense woodland where "
                    "every shadow could conceal an elvish blade. The forest "
                    "favors the defenders — elves move freely through the trees "
                    "while heavy-armored soldiers struggle in the undergrowth.",
        map_data=m, sides=[side_a, side_b],
        max_turns=25, turns_to_record=20,
        time_of_day=TimeOfDay.AFTERNOON, weather=WeatherType.CLEAR,
        camera_pacing="cinematic", camera_zoom=0.95,
        music="elvish_theme.ogg",
    )


# =============================================================================
# SCENARIO 4: RIVER CROSSING
# =============================================================================
def create_river_crossing() -> ScenarioDef:
    """A river divides the map with strategic bridge crossings."""
    W, H = 24, 16
    m = _fill("Gg", W, H)

    # River running horizontally through the middle
    river_y = 7
    bridge_gaps = [(5, 7), (11, 13), (18, 22)]
    m = _draw_river(m, river_y, bridge_gaps, "Ss")
    m = _draw_river(m, river_y + 1, bridge_gaps, "Ww")
    # Make bridges
    for g_start, g_end in bridge_gaps:
        for x in range(g_start, g_end + 1):
            m = _set_terrain(m, x, river_y, "Re")  # Bridge = road on shallow water
            m = _set_terrain(m, x, river_y + 1, "Re")

    # Hills on north bank
    for x in range(2, 6):
        m = _set_terrain(m, x, 5, "Hh")
    for x in range(15, 20):
        m = _set_terrain(m, x, 5, "Hh")

    # Forests near bridges
    forest_positions = [
        (4, 3), (5, 3), (10, 4), (11, 4), (12, 4),
        (17, 3), (18, 3), (19, 3),
        (4, 12), (5, 12), (10, 11), (11, 11), (12, 11),
        (17, 12), (18, 12), (19, 12),
    ]
    for fx, fy in forest_positions:
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Villages near bridges (strategic points)
    villages = [
        (6, 6), (6, 9),    # West bridge
        (10, 6), (13, 9),  # Center bridge
        (19, 6), (19, 9),  # East bridge
        (11, 2), (12, 13), # Far sides
    ]
    m = _place_villages(m, villages)

    # Roads leading to bridges
    m = _draw_road(m, [(4, 4), (6, 6), (6, 9), (4, 12)])
    m = _draw_road(m, [(11, 2), (12, 6), (11, 9), (12, 13)])
    m = _draw_road(m, [(19, 3), (19, 6), (19, 9), (19, 13)])

    # Castles
    m = _place_castle(m, 4, 3, 1)
    m = _place_castle(m, 20, 13, 2)

    side_a = SideConfig(
        side_number=1, faction="Knalgan Alliance", color="brown",
        gold=170, income=3,
        leader_type="Dwarvish Lord",
        leader_x=4, leader_y=3,
        can_recruit=["Dwarvish Fighter", "Dwarvish Thunderer", "Dwarvish Guardsman",
                      "Dwarvish Scout", "Gryphon Rider", "Dwarvish Berserker"],
        ai_aggression=0.5, ai_caution=0.35,
        extra_units=[
            {"type": "Dwarvish Fighter", "x": 3, "y": 3},
            {"type": "Dwarvish Fighter", "x": 5, "y": 3},
            {"type": "Dwarvish Thunderer", "x": 3, "y": 4},
            {"type": "Dwarvish Guardsman", "x": 5, "y": 4},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Drakes", color="red",
        gold=150, income=2,
        leader_type="Drake Flare",
        leader_x=20, leader_y=13,
        can_recruit=["Drake Clasher", "Drake Fighter", "Drake Burner",
                      "Drake Glider", "Drake Scout", "Saurian Skirmisher"],
        ai_aggression=0.7, ai_caution=0.2,
        extra_units=[
            {"type": "Drake Clasher", "x": 19, "y": 12},
            {"type": "Drake Burner", "x": 21, "y": 12},
            {"type": "Saurian Skirmisher", "x": 19, "y": 14},
            {"type": "Drake Glider", "x": 21, "y": 14},
        ],
    )

    return ScenarioDef(
        id="river_crossing",
        name="River Crossing",
        description="The mighty River Arkan divides the land. Three bridges span "
                    "its waters — each a vital crossing point that could decide "
                    "the battle. The Dwarvish Alliance defends the northern bank "
                    "while fire-breathing Drakes mass on the southern shore. "
                    "Whoever controls the bridges controls the flow of war. "
                    "Villages near each crossing provide precious healing and gold.",
        map_data=m, sides=[side_a, side_b],
        max_turns=30, turns_to_record=22,
        time_of_day=TimeOfDay.MORNING, weather=WeatherType.CLEAR,
        camera_pacing="cinematic", camera_zoom=0.9,
        music="northern_mountains.ogg",
    )


# =============================================================================
# SCENARIO 5: SWAMP OF THE DEAD
# =============================================================================
def create_swamp_of_dead() -> ScenarioDef:
    """Undead territory — swamp terrain with dark atmosphere."""
    W, H = 20, 14
    m = _fill("St", W, H)  # Swamp

    # Some firmer ground (grass patches)
    grass_patches = [
        (1, 1, 5, 3), (15, 1, 19, 3),    # Side starts
        (8, 5, 12, 8),                     # Center island
        (3, 10, 7, 12), (13, 10, 17, 12), # Lower islands
    ]
    for x1, y1, x2, y2 in grass_patches:
        m = _draw_terrain_rect(m, x1, y1, x2, y2, "Gg")

    # Deep swamp water
    swamp_water = [
        (6, 4), (7, 4), (13, 4), (14, 4),
        (4, 7), (5, 7), (15, 7), (16, 7),
        (8, 2), (9, 2), (11, 2), (12, 2),
        (8, 11), (9, 11), (11, 11), (12, 11),
    ]
    for wx, wy in swamp_water:
        m = _set_terrain(m, wx, wy, "Wt")

    # Dead trees (forest on swamp)
    dead_trees = [
        (6, 6), (7, 8), (13, 6), (14, 8),
        (3, 5), (17, 5), (3, 9), (17, 9),
    ]
    for fx, fy in dead_trees:
        m = _set_terrain(m, fx, fy, "Ss^Fp")

    # Villages on islands
    villages = [(9, 6), (10, 6), (10, 7), (5, 11), (15, 11), (3, 2), (17, 2)]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 3, 2, 1)
    m = _place_castle(m, 17, 2, 2)

    # Paths through swamp
    m = _draw_road(m, [(3, 3), (5, 4), (8, 6), (10, 7)])
    m = _draw_road(m, [(10, 7), (12, 6), (15, 4), (17, 3)])

    side_a = SideConfig(
        side_number=1, faction="Undead", color="purple",
        gold=180, income=3,
        leader_type="Ancient Lich",
        leader_x=3, leader_y=2,
        can_recruit=["Skeleton", "Skeleton Archer", "Ghost", "Necrophage",
                      "Ghoul", "Dark Adept", "Bone Shooter", "Blood Bat"],
        ai_aggression=0.5, ai_caution=0.3,
        extra_units=[
            {"type": "Skeleton", "x": 2, "y": 2},
            {"type": "Ghost", "x": 4, "y": 2},
            {"type": "Dark Adept", "x": 2, "y": 3},
            {"type": "Ghoul", "x": 4, "y": 3},
            {"type": "Skeleton Archer", "x": 3, "y": 4},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Northerners", color="red",
        gold=160, income=2,
        leader_type="Orcish Warlord",
        leader_x=17, leader_y=2,
        can_recruit=["Orcish Grunt", "Orcish Archer", "Troll", "Wolf Rider",
                      "Orcish Assassin", "Goblin Spearman", "Orcish Crossbowman"],
        ai_aggression=0.6, ai_caution=0.25,
        extra_units=[
            {"type": "Orcish Grunt", "x": 16, "y": 2},
            {"type": "Troll", "x": 18, "y": 2},
            {"type": "Orcish Archer", "x": 16, "y": 3},
            {"type": "Wolf Rider", "x": 18, "y": 3},
        ],
    )

    return ScenarioDef(
        id="swamp_of_dead",
        name="Swamp of the Dead",
        description="The Black Morass — a cursed swamp where the dead walk "
                    "freely. An Undead Lich commands his legions from a fortress "
                    "of bone, while an Orcish warlord seeks to claim the "
                    "swamp's dark power for himself. The treacherous terrain "
                    "slows all movement, but the undead care nothing for such "
                    "mortal concerns. Only the scattered islands of firm ground "
                    "offer any safe haven.",
        map_data=m, sides=[side_a, side_b],
        max_turns=30, turns_to_record=22,
        time_of_day=TimeOfDay.FIRST_WATCH, weather=WeatherType.FOG,
        camera_pacing="cinematic", camera_zoom=0.85,
        music="underground.ogg",
    )


# =============================================================================
# SCENARIO 6: MOUNTAIN PASS
# =============================================================================
def create_mountain_pass() -> ScenarioDef:
    """Narrow mountain corridors force tactical fighting."""
    W, H = 22, 14
    m = _fill("Mm", W, H)  # Mountains

    # Pass through the middle (narrow corridor)
    for y in range(4, 10):
        m = _set_terrain(m, 10, y, "Hh")
        m = _set_terrain(m, 11, y, "Hh")

    # Wider areas at each end of the pass
    for x in range(8, 14):
        for y in range(3, 11):
            if m[y].split(",")[x] == "Mm":
                m = _set_terrain(m, x, y, "Hh")

    # Side valleys (grass areas for deployment)
    for x in range(1, 6):
        for y in range(3, 11):
            m = _set_terrain(m, x, y, "Gg")
    for x in range(17, 21):
        for y in range(3, 11):
            m = _set_terrain(m, x, y, "Gg")

    # Forests in valleys
    valley_forests = [(2, 4), (3, 5), (2, 9), (3, 8), (18, 4), (19, 5), (18, 9), (19, 8)]
    for fx, fy in valley_forests:
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Scattered peaks (impassable)
    peaks = [(7, 2), (7, 12), (14, 2), (14, 12), (10, 1), (11, 1), (10, 12), (11, 12)]
    for px, py in peaks:
        m = _set_terrain(m, px, py, "Ms")

    # Villages in strategic positions
    villages = [
        (3, 7), (18, 7),           # Valley centers
        (8, 7), (13, 7),           # Pass entrances
        (10, 4), (11, 4),          # High pass
        (10, 9), (11, 9),          # Low pass
    ]
    m = _place_villages(m, villages)

    # Road through the pass
    m = _draw_road(m, [(3, 7), (6, 7), (8, 7), (10, 7), (13, 7), (15, 7), (18, 7)])

    # Castles
    m = _place_castle(m, 3, 7, 1)
    m = _place_castle(m, 19, 7, 2)

    side_a = SideConfig(
        side_number=1, faction="Knalgan Alliance", color="brown",
        gold=150, income=3,
        leader_type="Dwarvish Lord",
        leader_x=3, leader_y=7,
        can_recruit=["Dwarvish Fighter", "Dwarvish Thunderer", "Dwarvish Guardsman",
                      "Dwarvish Berserker", "Gryphon Rider", "Dwarvish Scout"],
        ai_aggression=0.4, ai_caution=0.4,  # Cautious in mountains
        extra_units=[
            {"type": "Dwarvish Fighter", "x": 2, "y": 6},
            {"type": "Dwarvish Fighter", "x": 4, "y": 6},
            {"type": "Dwarvish Thunderer", "x": 2, "y": 8},
            {"type": "Dwarvish Guardsman", "x": 4, "y": 8},
            {"type": "Gryphon Rider", "x": 3, "y": 5},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Drakes", color="red",
        gold=150, income=2,
        leader_type="Drake Flare",
        leader_x=19, leader_y=7,
        can_recruit=["Drake Clasher", "Drake Fighter", "Drake Burner",
                      "Drake Glider", "Saurian Skirmisher", "Saurian Augur"],
        ai_aggression=0.6, ai_caution=0.25,
        extra_units=[
            {"type": "Drake Fighter", "x": 18, "y": 6},
            {"type": "Drake Burner", "x": 20, "y": 6},
            {"type": "Drake Clasher", "x": 18, "y": 8},
            {"type": "Drake Glider", "x": 20, "y": 8},
            {"type": "Saurian Augur", "x": 19, "y": 5},
        ],
    )

    return ScenarioDef(
        id="mountain_pass",
        name="Mountain Pass",
        description="The Iron Peaks — a treacherous mountain range with only "
                    "one viable pass. The Dwarvish Alliance defends their "
                    "ancestral halls while Drakes seek to claim the high ground. "
                    "Mountains channel both armies into narrow corridors where "
                    "numbers matter less than positioning. Gryphons and Drake "
                    "Gliders alone can bypass the peaks, making air superiority "
                    "a crucial factor in this alpine war.",
        map_data=m, sides=[side_a, side_b],
        max_turns=30, turns_to_record=22,
        time_of_day=TimeOfDay.MORNING, weather=WeatherType.CLEAR,
        camera_pacing="cinematic", camera_zoom=0.85,
        music="northern_mountains.ogg",
    )


# =============================================================================
# SCENARIO 7: VILLAGE CONTROL (King of the Hill)
# =============================================================================
def create_village_control() -> ScenarioDef:
    """Many villages — control the center to win."""
    W, H = 22, 16
    m = _fill("Gg", W, H)

    # Dense village layout
    center_villages = [
        (10, 6), (11, 6), (10, 7), (11, 7), (10, 8), (11, 8), (10, 9), (11, 9),
        (9, 7), (12, 7),
    ]
    m = _place_villages(m, center_villages)

    # Ring of villages
    ring_villages = [
        (7, 4), (8, 3), (13, 3), (14, 4),
        (7, 11), (8, 12), (13, 12), (14, 11),
        (5, 7), (16, 7),
    ]
    m = _place_villages(m, ring_villages)

    # Outer villages
    outer_villages = [
        (3, 3), (3, 12), (18, 3), (18, 12),
        (10, 1), (11, 14),
    ]
    m = _place_villages(m, outer_villages)

    # Scattered forests
    forest_groups = [
        [(4, 5), (5, 5), (4, 6)],
        [(17, 5), (16, 5), (17, 6)],
        [(6, 9), (7, 9), (6, 10)],
        [(15, 9), (16, 9), (15, 10)],
        [(9, 2), (10, 2)],
        [(12, 13), (13, 13)],
    ]
    for group in forest_groups:
        for fx, fy in group:
            m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Hills
    hill_positions = [(8, 5), (13, 5), (8, 10), (13, 10), (5, 2), (16, 2), (5, 13), (16, 13)]
    for hx, hy in hill_positions:
        m = _set_terrain(m, hx, hy, "Hh")

    # Roads to center
    m = _draw_road(m, [(3, 8), (5, 8), (9, 8)])
    m = _draw_road(m, [(12, 8), (16, 8), (18, 8)])
    m = _draw_road(m, [(11, 1), (11, 4), (10, 6)])
    m = _draw_road(m, [(10, 13), (10, 10), (11, 8)])

    # Castles
    m = _place_castle(m, 3, 8, 1)
    m = _place_castle(m, 19, 8, 2)

    side_a = SideConfig(
        side_number=1, faction="Loyalists", color="blue",
        gold=120, income=1,
        leader_type="General",
        leader_x=3, leader_y=8,
        can_recruit=["Spearman", "Bowman", "Cavalryman", "Heavy Infantryman",
                      "Mage", "Fencer", "Horseman"],
        ai_aggression=0.55, ai_caution=0.25,
        extra_units=[
            {"type": "Spearman", "x": 2, "y": 7},
            {"type": "Bowman", "x": 4, "y": 7},
            {"type": "Cavalryman", "x": 2, "y": 9},
            {"type": "Spearman", "x": 4, "y": 9},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Rebels", color="red",
        gold=120, income=1,
        leader_type="Elvish Captain",
        leader_x=19, leader_y=8,
        can_recruit=["Elvish Fighter", "Elvish Archer", "Elvish Scout",
                      "Elvish Shaman", "Wose", "Elvish Druid"],
        ai_aggression=0.55, ai_caution=0.25,
        extra_units=[
            {"type": "Elvish Fighter", "x": 18, "y": 7},
            {"type": "Elvish Archer", "x": 20, "y": 7},
            {"type": "Elvish Scout", "x": 18, "y": 9},
            {"type": "Elvish Fighter", "x": 20, "y": 9},
        ],
    )

    return ScenarioDef(
        id="village_control",
        name="Village Control",
        description="The Heartlands — a rich territory dotted with villages. "
                    "Both armies know that whoever controls the most villages "
                    "will out-produce and out-last the other. The center is "
                    "densely packed with settlements, making it the primary "
                    "battleground. Light cavalry and scouts race to grab "
                    "peripheral villages while the main forces clash in the "
                    "center. Economy is everything.",
        map_data=m, sides=[side_a, side_b],
        max_turns=30, turns_to_record=25,
        time_of_day=TimeOfDay.MIDDAY, weather=WeatherType.CLEAR,
        camera_pacing="follow_action", camera_zoom=1.0,
        music="battle.ogg",
    )


# =============================================================================
# SCENARIO 8: COASTAL ASSAULT
# =============================================================================
def create_coastal_assault() -> ScenarioDef:
    """Land and sea map with Merfolk and Saurians."""
    W, H = 24, 16
    m = _fill("Gg", W, H)

    # Ocean on the right half
    for x in range(14, 24):
        for y in range(0, 16):
            if x >= 20:
                m = _set_terrain(m, x, y, "Wo")
            elif x >= 17:
                m = _set_terrain(m, x, y, "Ww")
            elif x >= 14:
                m = _set_terrain(m, x, y, "Ss")

    # Beach/coast
    for y in range(16):
        m = _set_terrain(m, 13, y, "Ds")

    # Reef
    reef_positions = [(16, 3), (17, 5), (18, 8), (17, 11), (16, 13)]
    for rx, ry in reef_positions:
        m = _set_terrain(m, rx, ry, "Ww")

    # Shallow water paths for Merfolk
    merfolk_paths = [
        (15, 2), (15, 3), (15, 4), (16, 4), (16, 5),
        (15, 6), (15, 7), (15, 8), (16, 8), (16, 9),
        (15, 10), (15, 11), (15, 12), (16, 12), (16, 13),
    ]
    for wx, wy in merfolk_paths:
        m = _set_terrain(m, wx, wy, "Ss")

    # Forests on land
    forest_positions = [
        (4, 2), (5, 2), (10, 2), (11, 2),
        (3, 5), (4, 5), (10, 5), (11, 5),
        (3, 10), (4, 10), (10, 10), (11, 10),
        (4, 13), (5, 13), (10, 13), (11, 13),
    ]
    for fx, fy in forest_positions:
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Hills
    hill_positions = [(7, 3), (8, 3), (7, 12), (8, 12)]
    for hx, hy in hill_positions:
        m = _set_terrain(m, hx, hy, "Hh")

    # Villages on land
    land_villages = [(3, 7), (7, 7), (11, 7), (6, 4), (9, 10)]
    m = _place_villages(m, land_villages)

    # Castles
    m = _place_castle(m, 3, 7, 1)
    # Side 2's "castle" is in the water (keep on shallow water)
    m = _place_castle(m, 16, 8, 2)
    # Override castle tiles to water for side 2
    ml = [line.split(",") for line in m]
    for y in range(len(ml)):
        for x in range(len(ml[y])):
            if ml[y][x] == "Cv" and x > 13:
                ml[y][x] = "Ss"  # Shallow water for Merfolk castle
    m = [",".join(row) for row in ml]

    side_a = SideConfig(
        side_number=1, faction="Loyalists", color="blue",
        gold=150, income=2,
        leader_type="General",
        leader_x=3, leader_y=7,
        can_recruit=["Spearman", "Bowman", "Cavalryman", "Heavy Infantryman",
                      "Mage", "Fencer"],
        ai_aggression=0.5, ai_caution=0.3,
        extra_units=[
            {"type": "Spearman", "x": 2, "y": 6},
            {"type": "Bowman", "x": 4, "y": 6},
            {"type": "Heavy Infantryman", "x": 2, "y": 8},
            {"type": "Spearman", "x": 4, "y": 8},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Merfolk", color="teal",
        gold=150, income=2,
        leader_type="Merfolk Diviner",
        leader_x=16, leader_y=8,
        can_recruit=["Merfolk Fighter", "Merfolk Entangler", "Merfolk Impaler",
                      "Merfolk Priestess", "Merfolk Netcaster", "Merfolk Hunter"],
        ai_aggression=0.55, ai_caution=0.3,
        extra_units=[
            {"type": "Merfolk Fighter", "x": 15, "y": 7},
            {"type": "Merfolk Impaler", "x": 17, "y": 7},
            {"type": "Merfolk Fighter", "x": 15, "y": 9},
            {"type": "Merfolk Entangler", "x": 17, "y": 9},
        ],
    )

    return ScenarioDef(
        id="coastal_assault",
        name="Coastal Assault",
        description="The Shattered Coast — where land meets sea. A Loyalist "
                    "army holds the shoreline against a Merfolk invasion force "
                    "emerging from the deep waters. The Merfolk move swiftly "
                    "through shallow waters but must venture onto land to "
                    "threaten the Loyalist keep. Beaches provide the only "
                    "landing zones, creating natural chokepoints. The outcome "
                    "hinges on whether the land army can hold the coast or "
                    "the sea folk can establish a beachhead.",
        map_data=m, sides=[side_a, side_b],
        max_turns=25, turns_to_record=20,
        time_of_day=TimeOfDay.AFTERNOON, weather=WeatherType.CLEAR,
        camera_pacing="cinematic", camera_zoom=0.9,
        music="battle.ogg",
    )


# =============================================================================
# SCENARIO 9: VAMPIRE BAT SWARM
# =============================================================================
def create_vampire_bat_swarm() -> ScenarioDef:
    """Swarm of vampire bats over a cursed swamp."""
    W, H = 18, 12
    m = _fill("St", W, H)  # Swamp base

    # Swamp water patches
    swamp_water = [
        (5, 2), (6, 2), (5, 3),
        (12, 2), (13, 2), (12, 3),
        (3, 6), (4, 6), (5, 6),
        (13, 6), (14, 6), (15, 6),
        (5, 9), (6, 9), (5, 10),
        (12, 9), (13, 9), (12, 10),
    ]
    for wx, wy in swamp_water:
        m = _set_terrain(m, wx, wy, "Wt")

    # Firmer ground patches for castles and villages
    for x1, y1, x2, y2 in [(0, 0, 5, 2), (13, 0, 17, 2), (7, 5, 10, 7), (0, 9, 5, 11), (13, 9, 17, 11)]:
        m = _draw_terrain_rect(m, x1, y1, x2, y2, "Gg")

    # Villages on firm ground
    villages = [(8, 5), (9, 6), (10, 5), (3, 1), (15, 1), (3, 10), (15, 10)]
    m = _place_villages(m, villages)

    # Castles on opposite sides
    m = _place_castle(m, 3, 1, 1)
    m = _place_castle(m, 15, 10, 2)

    # Paths through the swamp
    m = _draw_road(m, [(4, 2), (6, 4), (9, 6), (12, 8), (14, 10)])

    bat_units = []
    bat_positions = [
        (1, 0), (2, 0), (4, 0), (5, 0),
        (1, 1), (2, 1), (4, 1), (5, 1), (3, 2), (4, 2),
    ]
    for bx, by in bat_positions:
        bat_units.append({"type": "Vampire Bat", "x": bx, "y": by})

    side_a = SideConfig(
        side_number=1, faction="Undead", color="purple",
        gold=150, income=2,
        leader_type="Ancient Lich",
        leader_x=3, leader_y=1,
        can_recruit=["Vampire Bat", "Blood Bat", "Dread Bat"],
        ai_aggression=0.7, ai_caution=0.2,
        extra_units=bat_units,
    )

    side_b = SideConfig(
        side_number=2, faction="Loyalists", color="blue",
        gold=150, income=2,
        leader_type="General",
        leader_x=15, leader_y=10,
        can_recruit=["Spearman", "Bowman", "Cavalryman", "Heavy Infantryman",
                      "Mage", "Fencer", "Horseman"],
        ai_aggression=0.6, ai_caution=0.25,
        extra_units=[
            {"type": "Spearman", "x": 14, "y": 9},
            {"type": "Bowman", "x": 16, "y": 9},
            {"type": "Heavy Infantryman", "x": 14, "y": 11},
            {"type": "Cavalryman", "x": 16, "y": 11},
            {"type": "Mage", "x": 15, "y": 9},
        ],
    )

    return ScenarioDef(
        id="vampire_bat_swarm",
        name="Vampire Bat Swarm",
        description="A swarm of vampire bats darkens the sky over a cursed swamp. "
                    "The Loyalist soldiers can barely see through the cloud of "
                    "leathery wings as the undead lord sends wave after wave "
                    "of bats.",
        map_data=m, sides=[side_a, side_b],
        max_turns=25, turns_to_record=20,
        time_of_day=TimeOfDay.FIRST_WATCH, weather=WeatherType.FOG,
        camera_pacing="cinematic", camera_zoom=0.9,
        music="underground.ogg",
    )


# =============================================================================
# SCENARIO 10: TROLL RAMPAGE
# =============================================================================
def create_troll_rampage() -> ScenarioDef:
    """Trolls smashing through a mountain pass against dwarves."""
    W, H = 16, 12
    m = _fill("Hh", W, H)  # Hills base

    # Mountain ridges
    mountain_patches = [
        (2, 0, 4, 1), (11, 0, 14, 1),
        (0, 4, 1, 5), (14, 4, 15, 5),
        (0, 7, 1, 8), (14, 7, 15, 8),
        (2, 10, 4, 11), (11, 10, 14, 11),
    ]
    for x1, y1, x2, y2 in mountain_patches:
        m = _draw_terrain_rect(m, x1, y1, x2, y2, "Mm")

    # Peaks (impassable)
    for px, py in [(3, 5), (12, 5), (3, 6), (12, 6), (7, 2), (8, 2), (7, 9), (8, 9)]:
        m = _set_terrain(m, px, py, "Ms")

    # Grass valleys for movement
    for x1, y1, x2, y2 in [(4, 4, 6, 7), (9, 4, 11, 7), (5, 1, 10, 2), (5, 9, 10, 10)]:
        m = _draw_terrain_rect(m, x1, y1, x2, y2, "Gg")

    # Villages
    villages = [(5, 5), (10, 5), (7, 5), (8, 5), (7, 6), (8, 6), (3, 3), (12, 3), (3, 8), (12, 8)]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 3, 1, 1)
    m = _place_castle(m, 13, 10, 2)

    # Road
    m = _draw_road(m, [(3, 2), (5, 4), (7, 6), (10, 8), (13, 10)])

    troll_units = [
        {"type": "Troll", "x": 1, "y": 1},
        {"type": "Troll", "x": 2, "y": 1},
        {"type": "Troll", "x": 4, "y": 1},
        {"type": "Troll", "x": 5, "y": 1},
        {"type": "Troll", "x": 1, "y": 2},
        {"type": "Troll", "x": 5, "y": 2},
    ]

    side_a = SideConfig(
        side_number=1, faction="Northerners", color="red",
        gold=150, income=2,
        leader_type="Orcish Warlord",
        leader_x=3, leader_y=1,
        can_recruit=["Troll", "Troll Whelp", "Troll Rocklobber"],
        ai_aggression=0.7, ai_caution=0.2,
        extra_units=troll_units,
    )

    side_b = SideConfig(
        side_number=2, faction="Knalgan Alliance", color="brown",
        gold=170, income=3,
        leader_type="Dwarvish Lord",
        leader_x=13, leader_y=10,
        can_recruit=["Dwarvish Fighter", "Dwarvish Thunderer", "Dwarvish Guardsman",
                      "Dwarvish Berserker", "Gryphon Rider", "Dwarvish Scout"],
        ai_aggression=0.5, ai_caution=0.35,
        extra_units=[
            {"type": "Dwarvish Fighter", "x": 12, "y": 9},
            {"type": "Dwarvish Fighter", "x": 14, "y": 9},
            {"type": "Dwarvish Thunderer", "x": 12, "y": 11},
            {"type": "Dwarvish Guardsman", "x": 14, "y": 11},
            {"type": "Gryphon Rider", "x": 13, "y": 9},
        ],
    )

    return ScenarioDef(
        id="troll_rampage",
        name="Troll Rampage",
        description="A band of enormous trolls smashes through the mountain pass, "
                    "hurling boulders at the dwarven defenders. The dwarves must "
                    "use their superior positioning to bring down these hulking "
                    "beasts.",
        map_data=m, sides=[side_a, side_b],
        max_turns=25, turns_to_record=20,
        time_of_day=TimeOfDay.MORNING, weather=WeatherType.CLEAR,
        camera_pacing="cinematic", camera_zoom=0.9,
        music="northern_mountains.ogg",
    )


# =============================================================================
# SCENARIO 11: DRAKE INFERNO
# =============================================================================
def create_drake_inferno() -> ScenarioDef:
    """Fire-breathing drakes set the forest ablaze against elves."""
    W, H = 20, 14
    m = _fill("Gg", W, H)  # Grass base

    # Scattered forests
    forest_groups = [
        [(3, 2), (4, 2), (3, 3), (4, 3)],
        [(8, 1), (9, 1), (10, 1), (8, 2), (9, 2)],
        [(15, 2), (16, 2), (15, 3)],
        [(2, 6), (3, 6), (2, 7)],
        [(8, 5), (9, 5), (10, 5), (11, 5), (9, 6), (10, 6)],
        [(15, 6), (16, 6), (17, 6)],
        [(3, 10), (4, 10), (3, 11), (4, 11)],
        [(8, 11), (9, 11), (10, 11), (11, 11), (9, 12), (10, 12)],
        [(15, 10), (16, 10), (15, 11), (16, 11)],
    ]
    for group in forest_groups:
        for fx, fy in group:
            m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Hills
    for hx, hy in [(6, 4), (13, 4), (6, 9), (13, 9), (17, 7), (2, 7)]:
        m = _set_terrain(m, hx, hy, "Hh")

    # Villages
    villages = [(5, 3), (14, 3), (10, 7), (5, 10), (14, 10), (7, 7), (12, 7)]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 3, 7, 1)
    m = _place_castle(m, 17, 7, 2)

    # Road
    m = _draw_road(m, [(4, 7), (7, 7), (10, 7), (13, 7), (16, 7)])

    burner_units = [
        {"type": "Drake Burner", "x": 1, "y": 6},
        {"type": "Drake Burner", "x": 2, "y": 6},
        {"type": "Drake Burner", "x": 4, "y": 6},
        {"type": "Drake Burner", "x": 5, "y": 6},
        {"type": "Drake Burner", "x": 1, "y": 8},
        {"type": "Drake Burner", "x": 5, "y": 8},
    ]

    side_a = SideConfig(
        side_number=1, faction="Drakes", color="red",
        gold=160, income=2,
        leader_type="Drake Flare",
        leader_x=3, leader_y=7,
        can_recruit=["Drake Burner", "Drake Firestorm", "Drake Flare"],
        ai_aggression=0.8, ai_caution=0.15,
        extra_units=burner_units,
    )

    side_b = SideConfig(
        side_number=2, faction="Rebels", color="green",
        gold=150, income=2,
        leader_type="Elvish Captain",
        leader_x=17, leader_y=7,
        can_recruit=["Elvish Fighter", "Elvish Archer", "Elvish Scout",
                      "Elvish Shaman", "Elvish Druid", "Wose"],
        ai_aggression=0.5, ai_caution=0.3,
        extra_units=[
            {"type": "Elvish Fighter", "x": 16, "y": 6},
            {"type": "Elvish Archer", "x": 18, "y": 6},
            {"type": "Elvish Fighter", "x": 16, "y": 8},
            {"type": "Elvish Archer", "x": 18, "y": 8},
            {"type": "Elvish Shaman", "x": 17, "y": 6},
        ],
    )

    return ScenarioDef(
        id="drake_inferno",
        name="Drake Inferno",
        description="A flight of fire-breathing drakes sets the forest ablaze. "
                    "Elvish warriors must dodge streams of flame while trying "
                    "to bring down the drakes with their bows. The burning "
                    "forest lights up the night.",
        map_data=m, sides=[side_a, side_b],
        max_turns=25, turns_to_record=20,
        time_of_day=TimeOfDay.DUSK, weather=WeatherType.CLEAR,
        camera_pacing="cinematic", camera_zoom=0.9,
        music="battle.ogg",
    )


# =============================================================================
# SCENARIO 12: GHOST LEGION
# =============================================================================
def create_ghost_legion() -> ScenarioDef:
    """Ethereal army of ghosts vs mage-focused loyalists."""
    W, H = 18, 12
    m = _fill("Gg", W, H)  # Grass base

    # Fog-like scattered forests
    forest_positions = [
        (4, 1), (5, 2), (6, 1), (8, 3), (9, 2), (10, 3),
        (3, 5), (4, 6), (5, 5), (13, 5), (14, 6), (15, 5),
        (7, 8), (8, 9), (9, 8), (10, 9), (11, 8),
        (4, 10), (5, 10), (12, 10), (13, 10),
        (2, 3), (15, 3), (2, 8), (15, 8),
    ]
    for fx, fy in forest_positions:
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Villages
    villages = [(8, 5), (9, 6), (5, 3), (12, 3), (5, 8), (12, 8), (8, 1), (9, 10)]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 3, 2, 1)
    m = _place_castle(m, 15, 9, 2)

    # Road
    m = _draw_road(m, [(4, 3), (7, 5), (9, 6), (11, 7), (14, 9)])

    ghost_units = [
        {"type": "Ghost", "x": 1, "y": 1},
        {"type": "Ghost", "x": 2, "y": 1},
        {"type": "Ghost", "x": 4, "y": 1},
        {"type": "Ghost", "x": 5, "y": 1},
        {"type": "Ghost", "x": 1, "y": 2},
        {"type": "Ghost", "x": 5, "y": 2},
        {"type": "Ghost", "x": 2, "y": 3},
        {"type": "Ghost", "x": 4, "y": 3},
    ]

    side_a = SideConfig(
        side_number=1, faction="Undead", color="purple",
        gold=160, income=2,
        leader_type="Lich",
        leader_x=3, leader_y=2,
        can_recruit=["Ghost", "Wraith", "Shadow", "Spectre"],
        ai_aggression=0.6, ai_caution=0.2,
        extra_units=ghost_units,
    )

    side_b = SideConfig(
        side_number=2, faction="Loyalists", color="blue",
        gold=160, income=2,
        leader_type="White Mage",
        leader_x=15, leader_y=9,
        can_recruit=["Mage", "White Mage", "Silver Mage"],
        ai_aggression=0.5, ai_caution=0.3,
        extra_units=[
            {"type": "White Mage", "x": 14, "y": 8},
            {"type": "White Mage", "x": 16, "y": 8},
            {"type": "Mage", "x": 14, "y": 10},
            {"type": "Mage", "x": 16, "y": 10},
            {"type": "Silver Mage", "x": 15, "y": 8},
        ],
    )

    return ScenarioDef(
        id="ghost_legion",
        name="Ghost Legion",
        description="An ethereal army of ghosts and wraiths materializes on the "
                    "battlefield. Only magical attacks can truly harm these "
                    "spectral warriors. The Loyalist mages must concentrate "
                    "their fire while the ghosts drain the life from anyone "
                    "they touch.",
        map_data=m, sides=[side_a, side_b],
        max_turns=25, turns_to_record=20,
        time_of_day=TimeOfDay.DEEP_NIGHT, weather=WeatherType.FOG,
        camera_pacing="cinematic", camera_zoom=0.9,
        music="underground.ogg",
    )


# =============================================================================
# SCENARIO 13: WOSE FORTRESS
# =============================================================================
def create_wose_fortress() -> ScenarioDef:
    """Ancient trees awaken in the deepest forest vs drakes."""
    W, H = 20, 14
    m = _fill("Gg^Fp", W, H)  # Dense forest base

    # Clearings for movement and castles
    clearings = [
        (0, 0, 5, 3),     # NW clearing (side 1)
        (15, 11, 19, 13),  # SE clearing (side 2)
        (7, 5, 12, 9),    # Central clearing
        (2, 6, 4, 8),     # Side path
        (15, 5, 17, 7),   # Side path
    ]
    for x1, y1, x2, y2 in clearings:
        m = _draw_terrain_rect(m, x1, y1, x2, y2, "Gg")

    # Villages in clearings
    villages = [(3, 1), (16, 12), (9, 6), (10, 7), (11, 6), (3, 7), (16, 6)]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 3, 1, 1)
    m = _place_castle(m, 17, 12, 2)

    # Paths through forest
    m = _draw_road(m, [(4, 2), (6, 4), (9, 6)])
    m = _draw_road(m, [(11, 8), (14, 10), (16, 12)])
    m = _draw_road(m, [(3, 7), (6, 7), (9, 7)])

    wose_units = [
        {"type": "Wose", "x": 1, "y": 1},
        {"type": "Wose", "x": 2, "y": 1},
        {"type": "Wose", "x": 4, "y": 1},
        {"type": "Wose", "x": 5, "y": 1},
        {"type": "Wose", "x": 3, "y": 2},
    ]

    side_a = SideConfig(
        side_number=1, faction="Rebels", color="green",
        gold=150, income=3,
        leader_type="Elvish Captain",
        leader_x=3, leader_y=1,
        can_recruit=["Wose", "Wose Shrub", "Ancient Wose", "Elvish Fighter"],
        ai_aggression=0.5, ai_caution=0.3,
        extra_units=wose_units,
    )

    side_b = SideConfig(
        side_number=2, faction="Drakes", color="red",
        gold=150, income=2,
        leader_type="Drake Clasher",
        leader_x=17, leader_y=12,
        can_recruit=["Drake Clasher", "Drake Fighter", "Drake Burner",
                      "Drake Glider", "Drake Scout", "Saurian Skirmisher"],
        ai_aggression=0.7, ai_caution=0.2,
        extra_units=[
            {"type": "Drake Clasher", "x": 16, "y": 11},
            {"type": "Drake Fighter", "x": 18, "y": 11},
            {"type": "Drake Burner", "x": 16, "y": 13},
            {"type": "Drake Glider", "x": 18, "y": 13},
        ],
    )

    return ScenarioDef(
        id="wose_fortress",
        name="Wose Fortress",
        description="Ancient trees awaken in the deepest forest, their roots "
                    "tearing up the earth. The drakes find their fire ineffective "
                    "against these massive living trees. The forest itself seems "
                    "to fight alongside the rebels.",
        map_data=m, sides=[side_a, side_b],
        max_turns=28, turns_to_record=22,
        time_of_day=TimeOfDay.AFTERNOON, weather=WeatherType.CLEAR,
        camera_pacing="cinematic", camera_zoom=0.9,
        music="elvish_theme.ogg",
    )


# =============================================================================
# SCENARIO 14: SAURIAN WARS
# =============================================================================
def create_saurian_wars() -> ScenarioDef:
    """Saurian tribemen defend swamp homeland against orcish invasion."""
    W, H = 20, 14
    m = _fill("St", W, H)  # Swamp base

    # Swamp water patches
    swamp_water = [
        (3, 3), (4, 3), (15, 3), (16, 3),
        (7, 6), (8, 6), (11, 6), (12, 6),
        (3, 10), (4, 10), (15, 10), (16, 10),
        (9, 2), (10, 2), (9, 11), (10, 11),
    ]
    for wx, wy in swamp_water:
        m = _set_terrain(m, wx, wy, "Wt")

    # Firmer ground patches
    for x1, y1, x2, y2 in [(0, 0, 5, 3), (15, 0, 19, 3), (7, 4, 12, 9), (0, 11, 5, 13), (15, 11, 19, 13)]:
        m = _draw_terrain_rect(m, x1, y1, x2, y2, "Gg")

    # Some forest on the firm ground
    for fx, fy in [(2, 1), (3, 1), (17, 1), (18, 1), (8, 5), (9, 5), (10, 5), (11, 5),
                    (2, 12), (3, 12), (17, 12), (18, 12)]:
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Villages
    villages = [(9, 6), (10, 7), (3, 2), (17, 2), (3, 12), (17, 12), (7, 8), (12, 8)]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 3, 2, 1)
    m = _place_castle(m, 17, 11, 2)

    # Paths
    m = _draw_road(m, [(4, 3), (7, 5), (10, 7), (13, 9), (16, 11)])

    side_a = SideConfig(
        side_number=1, faction="Saurians", color="teal",
        gold=150, income=2,
        leader_type="Saurian Oracle",
        leader_x=3, leader_y=2,
        can_recruit=["Saurian Skirmisher", "Saurian Flanker", "Saurian Augur",
                      "Saurian Ambusher", "Saurian Soothsayer", "Saurian Spatulate-Head"],
        ai_aggression=0.5, ai_caution=0.3,
        extra_units=[
            {"type": "Saurian Skirmisher", "x": 2, "y": 1},
            {"type": "Saurian Skirmisher", "x": 4, "y": 1},
            {"type": "Saurian Augur", "x": 2, "y": 3},
            {"type": "Saurian Flanker", "x": 4, "y": 3},
            {"type": "Saurian Ambusher", "x": 3, "y": 1},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Northerners", color="red",
        gold=160, income=2,
        leader_type="Orcish Warlord",
        leader_x=17, leader_y=11,
        can_recruit=["Orcish Grunt", "Orcish Archer", "Troll", "Wolf Rider",
                      "Orcish Assassin", "Goblin Spearman", "Orcish Crossbowman"],
        ai_aggression=0.6, ai_caution=0.25,
        extra_units=[
            {"type": "Orcish Grunt", "x": 16, "y": 10},
            {"type": "Orcish Grunt", "x": 18, "y": 10},
            {"type": "Orcish Archer", "x": 16, "y": 12},
            {"type": "Troll", "x": 18, "y": 12},
        ],
    )

    return ScenarioDef(
        id="saurian_wars",
        name="Saurian Wars",
        description="Saurian tribemen defend their swamp homeland against an "
                    "orcish invasion. The saurians know every hidden path and "
                    "muddy bog, using the treacherous terrain to outmaneuver "
                    "the brute orcs.",
        map_data=m, sides=[side_a, side_b],
        max_turns=30, turns_to_record=22,
        time_of_day=TimeOfDay.DAWN, weather=WeatherType.FOG,
        camera_pacing="cinematic", camera_zoom=0.9,
        music="underground.ogg",
    )


# =============================================================================
# SCENARIO 15: OUTLAW AMBUSH
# =============================================================================
def create_outlaw_ambush() -> ScenarioDef:
    """Bandits prey on a Loyalist supply convoy in dark forest."""
    W, H = 18, 12
    m = _fill("Gg^Fp", W, H)  # Dense forest base

    # Clearings
    clearings = [
        (0, 4, 4, 7),      # West clearing (Loyalist march)
        (14, 4, 17, 7),    # East clearing
        (6, 2, 11, 4),     # NW clearing
        (6, 8, 11, 10),    # SE clearing
        (8, 4, 10, 7),     # Central clearing
    ]
    for x1, y1, x2, y2 in clearings:
        m = _draw_terrain_rect(m, x1, y1, x2, y2, "Gg")

    # Road (convoy route)
    m = _draw_road(m, [(2, 6), (5, 6), (8, 6), (10, 6), (13, 6), (15, 6)])

    # Villages along the road
    villages = [(4, 5), (7, 3), (10, 5), (13, 3), (7, 9), (10, 9), (4, 8), (13, 8)]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 2, 6, 1)
    m = _place_castle(m, 16, 6, 2)

    side_a = SideConfig(
        side_number=1, faction="Outlaws", color="orange",
        gold=140, income=2,
        leader_type="Outlaw",
        leader_x=2, leader_y=6,
        can_recruit=["Thief", "Rogue", "Assassin", "Footpad", "Poacher",
                      "Trapper", "Highwayman", "Bandit"],
        ai_aggression=0.6, ai_caution=0.25,
        extra_units=[
            {"type": "Thief", "x": 6, "y": 3},
            {"type": "Rogue", "x": 7, "y": 3},
            {"type": "Poacher", "x": 6, "y": 9},
            {"type": "Footpad", "x": 7, "y": 9},
            {"type": "Assassin", "x": 8, "y": 5},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Loyalists", color="blue",
        gold=150, income=2,
        leader_type="General",
        leader_x=16, leader_y=6,
        can_recruit=["Spearman", "Bowman", "Cavalryman", "Heavy Infantryman",
                      "Mage", "Fencer"],
        ai_aggression=0.5, ai_caution=0.35,
        extra_units=[
            {"type": "Spearman", "x": 15, "y": 5},
            {"type": "Bowman", "x": 17, "y": 5},
            {"type": "Heavy Infantryman", "x": 15, "y": 7},
            {"type": "Cavalryman", "x": 17, "y": 7},
        ],
    )

    return ScenarioDef(
        id="outlaw_ambush",
        name="Outlaw Ambush",
        description="Bandits and outlaws prey on a Loyalist supply convoy "
                    "winding through dark forest roads. The dense trees "
                    "provide perfect cover for ambushes, and the convoy "
                    "must fight its way through or be plundered.",
        map_data=m, sides=[side_a, side_b],
        max_turns=25, turns_to_record=20,
        time_of_day=TimeOfDay.SECOND_WATCH, weather=WeatherType.CLEAR,
        camera_pacing="cinematic", camera_zoom=0.95,
        music="elvish_theme.ogg",
    )


# =============================================================================
# SCENARIO 16: DRAKE SAURIAN ALLIANCE
# =============================================================================
def create_drake_saurian_alliance() -> ScenarioDef:
    """Drakes + Saurians vs Loyalists + Dwarves on mixed terrain."""
    W, H = 22, 16
    m = _fill("Gg", W, H)  # Grass base

    # Forest patches (SW quadrant)
    forest_sw = [(2, 9), (3, 9), (4, 9), (2, 10), (3, 10), (4, 10),
                 (1, 11), (2, 11), (5, 11), (1, 12), (2, 12), (5, 12),
                 (3, 13), (4, 13)]
    for fx, fy in forest_sw:
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Hills (NE quadrant)
    hills_ne = [(16, 2), (17, 2), (18, 2), (16, 3), (17, 3), (18, 3),
                (15, 4), (16, 4), (19, 4), (15, 5), (16, 5), (19, 5)]
    for hx, hy in hills_ne:
        m = _set_terrain(m, hx, hy, "Hh")

    # Mountains along top-right
    for x in range(18, 22):
        for y in range(0, 3):
            m = _set_terrain(m, x, y, "Mm")

    # Swamp patch (center)
    for x in range(9, 13):
        for y in range(7, 9):
            m = _set_terrain(m, x, y, "St")

    # Water feature
    m = _draw_river(m, 5, [(7, 9), (14, 16)], "Ww")

    # Villages
    villages = [
        (3, 7), (8, 3), (13, 3), (18, 7),
        (6, 5), (15, 5), (10, 10), (10, 6),
        (3, 14), (18, 14),
    ]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 3, 14, 1)
    m = _place_castle(m, 19, 2, 2)

    # Roads
    m = _draw_road(m, [(4, 13), (7, 10), (10, 8), (13, 6), (16, 4), (18, 3)])
    m = _draw_road(m, [(3, 7), (6, 7), (10, 7), (14, 7), (18, 7)])

    side_a = SideConfig(
        side_number=1, faction="Drakes", color="red",
        gold=180, income=3,
        leader_type="Drake Flare",
        leader_x=3, leader_y=14,
        can_recruit=["Drake Clasher", "Drake Fighter", "Drake Burner",
                      "Drake Glider", "Drake Scout", "Saurian Skirmisher",
                      "Saurian Augur", "Saurian Flanker"],
        ai_aggression=0.65, ai_caution=0.25,
        extra_units=[
            {"type": "Drake Burner", "x": 2, "y": 13},
            {"type": "Drake Clasher", "x": 4, "y": 13},
            {"type": "Drake Fighter", "x": 2, "y": 15},
            {"type": "Saurian Skirmisher", "x": 4, "y": 15},
            {"type": "Saurian Augur", "x": 3, "y": 13},
            {"type": "Drake Glider", "x": 5, "y": 14},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Loyalists", color="blue",
        gold=180, income=3,
        leader_type="General",
        leader_x=19, leader_y=2,
        can_recruit=["Spearman", "Bowman", "Cavalryman", "Heavy Infantryman",
                      "Mage", "Fencer", "Dwarvish Fighter", "Dwarvish Thunderer"],
        ai_aggression=0.55, ai_caution=0.3,
        extra_units=[
            {"type": "Spearman", "x": 18, "y": 1},
            {"type": "Bowman", "x": 20, "y": 1},
            {"type": "Heavy Infantryman", "x": 18, "y": 3},
            {"type": "Dwarvish Fighter", "x": 20, "y": 3},
            {"type": "Dwarvish Thunderer", "x": 19, "y": 1},
            {"type": "Cavalryman", "x": 19, "y": 3},
        ],
    )

    return ScenarioDef(
        id="drake_saurian_alliance",
        name="Drake-Saurian Alliance",
        description="A formidable alliance of fire-breathing drakes and cunning "
                    "saurians launches a coordinated assault on a fortified "
                    "human-dwarven alliance. Mixed terrain favors different "
                    "troop types on different fronts.",
        map_data=m, sides=[side_a, side_b],
        max_turns=30, turns_to_record=22,
        time_of_day=TimeOfDay.MIDDAY, weather=WeatherType.CLEAR,
        camera_pacing="cinematic", camera_zoom=0.85,
        music="battle.ogg",
    )


# =============================================================================
# SCENARIO 17: UNDEAD MERFOLK NIGHTMARE
# =============================================================================
def create_undead_merfolk_nightmare() -> ScenarioDef:
    """Undead drowned army vs Merfolk — half land, half water."""
    W, H = 22, 14
    m = _fill("Gg", W, H)

    # Right half is water
    for x in range(11, 22):
        for y in range(0, 14):
            if x >= 18:
                m = _set_terrain(m, x, y, "Wo")
            elif x >= 14:
                m = _set_terrain(m, x, y, "Ww")
            else:
                m = _set_terrain(m, x, y, "Ss")

    # Coastal transition
    for y in range(14):
        m = _set_terrain(m, 10, y, "Ds")

    # Swamp patches on land (undead territory)
    for fx, fy in [(3, 2), (4, 2), (3, 3), (6, 5), (7, 5), (6, 6),
                    (3, 10), (4, 10), (3, 11), (6, 8), (7, 8)]:
        m = _set_terrain(m, fx, fy, "St")

    # Forests on land
    for fx, fy in [(5, 3), (8, 2), (8, 11), (5, 10), (2, 6), (2, 7)]:
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Shallow water paths for Merfolk
    for wx, wy in [(12, 2), (12, 3), (13, 5), (13, 6), (13, 7), (13, 8),
                    (12, 10), (12, 11), (15, 4), (15, 5), (15, 8), (15, 9)]:
        m = _set_terrain(m, wx, wy, "Ss")

    # Villages
    land_villages = [(4, 5), (7, 7), (4, 9), (8, 7)]
    water_villages = [(12, 4), (12, 9), (15, 6), (15, 7)]
    m = _place_villages(m, land_villages + water_villages)

    # Castles
    m = _place_castle(m, 3, 7, 1)
    # Side 2's castle in water
    m = _place_castle(m, 14, 7, 2)
    # Override castle tiles to water for side 2
    ml = [line.split(",") for line in m]
    for y in range(len(ml)):
        for x in range(len(ml[y])):
            if ml[y][x] == "Cv" and x > 10:
                ml[y][x] = "Ss"
    m = [",".join(row) for row in ml]

    side_a = SideConfig(
        side_number=1, faction="Undead", color="purple",
        gold=160, income=2,
        leader_type="Ancient Lich",
        leader_x=3, leader_y=7,
        can_recruit=["Skeleton", "Skeleton Archer", "Ghost", "Necrophage",
                      "Ghoul", "Dark Adept", "Bone Shooter", "Walking Corpse"],
        ai_aggression=0.55, ai_caution=0.3,
        extra_units=[
            {"type": "Skeleton", "x": 2, "y": 6},
            {"type": "Skeleton Archer", "x": 4, "y": 6},
            {"type": "Ghost", "x": 2, "y": 8},
            {"type": "Ghoul", "x": 4, "y": 8},
            {"type": "Dark Adept", "x": 3, "y": 6},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Merfolk", color="teal",
        gold=160, income=2,
        leader_type="Merfolk Diviner",
        leader_x=14, leader_y=7,
        can_recruit=["Merfolk Fighter", "Merfolk Entangler", "Merfolk Impaler",
                      "Merfolk Priestess", "Merfolk Netcaster", "Merfolk Hunter"],
        ai_aggression=0.6, ai_caution=0.25,
        extra_units=[
            {"type": "Merfolk Fighter", "x": 13, "y": 6},
            {"type": "Merfolk Impaler", "x": 15, "y": 6},
            {"type": "Merfolk Fighter", "x": 13, "y": 8},
            {"type": "Merfolk Entangler", "x": 15, "y": 8},
        ],
    )

    return ScenarioDef(
        id="undead_merfolk_nightmare",
        name="Undead-Merfolk Nightmare",
        description="Undead corpses wash ashore as the Merfolk discover an ancient "
                    "lich has raised a drowned army. The sea folk must fight "
                    "both on land and in water against an enemy that doesn't "
                    "need to breathe.",
        map_data=m, sides=[side_a, side_b],
        max_turns=28, turns_to_record=22,
        time_of_day=TimeOfDay.DEEP_NIGHT, weather=WeatherType.FOG,
        camera_pacing="cinematic", camera_zoom=0.85,
        music="underground.ogg",
    )


# =============================================================================
# SCENARIO 18: FOUR FACTION MELEE
# =============================================================================
def create_four_faction_melee() -> ScenarioDef:
    """Four armies converge from every direction — chaotic multi-front warfare."""
    W, H = 24, 18
    m = _fill("Gg", W, H)  # Open grassland

    # Villages — many, spread across the map for control points
    center_villages = [(11, 8), (12, 8), (11, 9), (12, 9), (10, 8), (13, 9)]
    quadrant_villages = [
        # NW quadrant
        (5, 4), (6, 5), (7, 6),
        # NE quadrant
        (17, 4), (16, 5), (15, 6),
        # SW quadrant
        (5, 12), (6, 11), (7, 10),
        # SE quadrant
        (17, 12), (16, 11), (15, 10),
        # Mid points between quadrants
        (9, 5), (14, 5), (9, 12), (14, 12),
        (11, 3), (12, 14),
    ]
    m = _place_villages(m, center_villages + quadrant_villages)

    # Scattered forests for tactical cover
    forest_groups = [
        [(7, 3), (8, 3)], [(15, 3), (16, 3)],
        [(7, 13), (8, 13)], [(15, 13), (16, 13)],
        [(10, 6), (11, 6)], [(12, 11), (13, 11)],
        [(5, 7), (6, 7)], [(17, 7), (18, 7)],
        [(5, 9), (6, 9)], [(17, 9), (18, 9)],
    ]
    for group in forest_groups:
        for fx, fy in group:
            m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Hills at midpoints between corners
    for hx, hy in [(11, 5), (12, 5), (11, 12), (12, 12), (9, 8), (14, 8)]:
        m = _set_terrain(m, hx, hy, "Hh")

    # Roads connecting castles through center
    m = _draw_road(m, [(4, 4), (7, 6), (11, 9)])
    m = _draw_road(m, [(21, 4), (17, 6), (12, 9)])
    m = _draw_road(m, [(4, 14), (7, 12), (11, 9)])
    m = _draw_road(m, [(21, 14), (17, 12), (13, 9)])

    # Castles in 4 corners
    m = _place_castle(m, 3, 4, 1)    # NW — Loyalists
    m = _place_castle(m, 21, 4, 2)   # NE — Northerners
    m = _place_castle(m, 3, 14, 3)   # SW — Rebels
    m = _place_castle(m, 21, 14, 4)  # SE — Drakes

    side_nw = SideConfig(
        side_number=1, faction="Loyalists", color="blue",
        gold=120, income=1,
        leader_type="General",
        leader_x=3, leader_y=4,
        can_recruit=["Spearman", "Bowman", "Cavalryman", "Heavy Infantryman",
                      "Mage", "Fencer"],
        ai_aggression=0.55, ai_caution=0.25,
        extra_units=[
            {"type": "Spearman", "x": 2, "y": 3},
            {"type": "Bowman", "x": 4, "y": 3},
            {"type": "Spearman", "x": 2, "y": 5},
            {"type": "Cavalryman", "x": 4, "y": 5},
        ],
    )

    side_ne = SideConfig(
        side_number=2, faction="Northerners", color="red",
        gold=120, income=1,
        leader_type="Orcish Warlord",
        leader_x=21, leader_y=4,
        can_recruit=["Orcish Grunt", "Orcish Archer", "Troll", "Wolf Rider",
                      "Goblin Spearman", "Orcish Crossbowman"],
        ai_aggression=0.65, ai_caution=0.2,
        extra_units=[
            {"type": "Orcish Grunt", "x": 20, "y": 3},
            {"type": "Orcish Archer", "x": 22, "y": 3},
            {"type": "Troll", "x": 20, "y": 5},
            {"type": "Wolf Rider", "x": 22, "y": 5},
        ],
    )

    side_sw = SideConfig(
        side_number=3, faction="Rebels", color="green",
        gold=120, income=1,
        leader_type="Elvish Captain",
        leader_x=3, leader_y=14,
        can_recruit=["Elvish Fighter", "Elvish Archer", "Elvish Scout",
                      "Elvish Shaman", "Wose", "Elvish Druid"],
        ai_aggression=0.5, ai_caution=0.3,
        extra_units=[
            {"type": "Elvish Fighter", "x": 2, "y": 13},
            {"type": "Elvish Archer", "x": 4, "y": 13},
            {"type": "Elvish Scout", "x": 2, "y": 15},
            {"type": "Elvish Fighter", "x": 4, "y": 15},
        ],
    )

    side_se = SideConfig(
        side_number=4, faction="Drakes", color="orange",
        gold=120, income=1,
        leader_type="Drake Flare",
        leader_x=21, leader_y=14,
        can_recruit=["Drake Clasher", "Drake Fighter", "Drake Burner",
                      "Drake Glider", "Drake Scout", "Saurian Skirmisher"],
        ai_aggression=0.6, ai_caution=0.25,
        extra_units=[
            {"type": "Drake Fighter", "x": 20, "y": 13},
            {"type": "Drake Burner", "x": 22, "y": 13},
            {"type": "Drake Clasher", "x": 20, "y": 15},
            {"type": "Saurian Skirmisher", "x": 22, "y": 15},
        ],
    )

    return ScenarioDef(
        id="four_faction_melee",
        name="Four Faction Melee",
        description="Four armies converge on a rich heartland from every direction. "
                    "Alliance is temporary — only one faction can claim the "
                    "territory. Expect shifting fronts, betrayals, and chaotic "
                    "multi-front warfare.",
        map_data=m, sides=[side_nw, side_ne, side_sw, side_se],
        max_turns=40, turns_to_record=30,
        time_of_day=TimeOfDay.MIDDAY, weather=WeatherType.CLEAR,
        camera_pacing="follow_action", camera_zoom=0.8,
        music="battle.ogg",
    )




# =============================================================================
# SCENARIO 19: UNDEAD WAVE ATTACK
# =============================================================================
def create_undead_wave_attack() -> ScenarioDef:
    """Defenders hold a fortress against endless waves of undead. Waves get larger each turn."""
    W, H = 20, 14
    m = _fill("Gg", W, H)

    # Fortified position for defenders (side 2) on the right
    # Stone walls (mountains)
    for x in range(12, 18):
        m = _set_terrain(m, x, 2, "Mm")
        m = _set_terrain(m, x, 11, "Mm")
    for y in range(2, 12):
        m = _set_terrain(m, 17, y, "Mm")

    # Gate openings
    m = _set_terrain(m, 12, 6, "Re")
    m = _set_terrain(m, 12, 7, "Re")
    m = _set_terrain(m, 17, 6, "Mm")
    m = _set_terrain(m, 17, 7, "Mm")

    # Inner area grass
    for x in range(13, 17):
        for y in range(3, 11):
            m = _set_terrain(m, x, y, "Gg")

    # Swamp on the left (undead territory)
    for x in range(0, 5):
        for y in range(0, 14):
            m = _set_terrain(m, x, y, "St")
    # Firmer ground for castle
    for x in range(0, 5):
        for y in range(5, 9):
            m = _set_terrain(m, x, y, "Gg")

    # Forests in no-mans-land
    for fx, fy in [(7, 3), (8, 3), (7, 10), (8, 10), (6, 5), (6, 8), (9, 6), (9, 7)]:
        m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Hills as vantage points
    for hx, hy in [(10, 4), (10, 9), (11, 5), (11, 8)]:
        m = _set_terrain(m, hx, hy, "Hh")

    # Villages inside fortress and along the approach
    villages = [(14, 5), (15, 6), (16, 7), (15, 8), (14, 9), (10, 6), (10, 7)]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 2, 7, 1)
    m = _place_castle(m, 15, 7, 2)

    # Road from undead castle to fortress gate
    m = _draw_road(m, [(3, 7), (6, 7), (9, 7), (12, 7)])

    # Build wave events — undead get reinforcements every 3 turns
    wave_events = []
    wave_units_t1 = ["Walking Corpse", "Walking Corpse", "Skeleton", "Skeleton Archer"]
    wave_units_t2 = ["Skeleton", "Skeleton", "Skeleton Archer", "Ghoul", "Ghost"]
    wave_units_t3 = ["Skeleton", "Skeleton Archer", "Ghost", "Necrophage", "Dark Adept", "Ghoul"]
    wave_units_t4 = ["Skeleton", "Revenant", "Ghost", "Wraith", "Necrophage", "Dark Adept", "Banebow"]
    wave_units_t5 = ["Skeleton", "Revenant", "Ghost", "Wraith", "Necrophage", "Dark Adept", "Bone Knight"]

    spawn_positions = [(6, 5), (7, 6), (8, 7), (6, 8), (7, 4), (8, 9)]

    waves = [
        (3, wave_units_t1, "The dead stir... the first wave approaches!"),
        (6, wave_units_t2, "More undead emerge from the swamp!"),
        (9, wave_units_t3, "A tide of darkness floods the battlefield!"),
        (12, wave_units_t4, "Ancient horrors rise from the earth!"),
        (15, wave_units_t5, "The final wave — the lich unleashes everything!"),
        (18, wave_units_t5, "Relentless! The dead do not stop!"),
        (21, wave_units_t5, "One last push — the fortress must hold!"),
    ]

    for turn_num, unit_types, msg in waves:
        wave_events.append({"turn": turn_num, "action": "message", "side": 1, "text": msg})
        units_to_spawn = []
        for i, utype in enumerate(unit_types):
            sx, sy = spawn_positions[i % len(spawn_positions)]
            units_to_spawn.append({"type": utype, "x": sx, "y": sy})
        wave_events.append({"turn": turn_num, "action": "reinforcements", "side": 1, "units": units_to_spawn})

    side_a = SideConfig(
        side_number=1, faction="Undead", color="purple",
        gold=300, income=5,
        leader_type="Ancient Lich",
        leader_x=2, leader_y=7,
        can_recruit=["Skeleton", "Skeleton Archer", "Ghost", "Necrophage",
                      "Ghoul", "Dark Adept", "Bone Shooter", "Walking Corpse",
                      "Wraith", "Revenant"],
        ai_aggression=0.7, ai_caution=0.15,
        extra_units=[
            {"type": "Skeleton", "x": 1, "y": 6},
            {"type": "Skeleton", "x": 3, "y": 6},
            {"type": "Skeleton Archer", "x": 1, "y": 8},
            {"type": "Dark Adept", "x": 3, "y": 8},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Loyalists", color="blue",
        gold=200, income=4,
        leader_type="Grand Marshal",
        leader_x=15, leader_y=7,
        can_recruit=["Spearman", "Bowman", "Longbowman", "Heavy Infantryman",
                      "Cavalryman", "Mage", "White Mage", "Fencer"],
        ai_aggression=0.4, ai_caution=0.5,
        extra_units=[
            {"type": "Spearman", "x": 14, "y": 6},
            {"type": "Spearman", "x": 16, "y": 6},
            {"type": "Longbowman", "x": 14, "y": 8},
            {"type": "Heavy Infantryman", "x": 16, "y": 8},
            {"type": "Mage", "x": 15, "y": 6},
            {"type": "White Mage", "x": 15, "y": 8},
        ],
    )

    return ScenarioDef(
        id="undead_wave_attack",
        name="Undead Wave Attack",
        description="The undead horde launches wave after wave against a fortified "
                    "human stronghold. Every three turns, fresh corpses shamble "
                    "out of the swamp — and each wave is larger and more terrifying "
                    "than the last. The defenders must hold the walls or be "
                    "overwhelmed by sheer numbers. The fortress walls provide "
                    "crucial defensive bonuses, but the gate is a vulnerability.",
        map_data=m, sides=[side_a, side_b],
        max_turns=40, turns_to_record=30,
        time_of_day=TimeOfDay.FIRST_WATCH, weather=WeatherType.FOG,
        camera_pacing="cinematic", camera_zoom=0.9,
        music="underground.ogg",
        turn_events=wave_events,
    )


# =============================================================================
# SCENARIO 20: ORCISH HORDE INVASION
# =============================================================================
def create_orcish_horde_invasion() -> ScenarioDef:
    """Orc waves crash against elvish forest defenses. Progressive waves."""
    W, H = 22, 16
    m = _fill("Gg^Fp", W, H)  # Dense forest

    # Clearings for castles and fighting
    clearings = [
        (0, 0, 5, 3),       # NW — orc start
        (17, 13, 21, 15),   # SE — elf start
        (8, 5, 13, 10),     # Central battlefield
        (0, 6, 3, 9),       # West approach
        (10, 1, 13, 3),     # NE hill
    ]
    for x1, y1, x2, y2 in clearings:
        m = _draw_terrain_rect(m, x1, y1, x2, y2, "Gg")

    # Hills at the forest edge
    for hx, hy in [(6, 4), (7, 4), (14, 11), (15, 11), (10, 2), (11, 2)]:
        m = _set_terrain(m, hx, hy, "Hh")

    # Villages
    villages = [(9, 6), (10, 7), (11, 8), (4, 2), (18, 14),
                (7, 8), (14, 7), (3, 7), (18, 8), (10, 4)]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 3, 2, 1)
    m = _place_castle(m, 19, 14, 2)

    # Paths
    m = _draw_road(m, [(4, 3), (7, 5), (10, 7)])
    m = _draw_road(m, [(10, 7), (13, 9), (16, 11), (18, 13)])

    # Wave events — orcs get waves of reinforcements
    wave_events = []
    orc_waves = [
        (4, ["Orcish Grunt", "Orcish Grunt", "Goblin Spearman", "Goblin Spearman"],
         "The first war drums echo through the trees!"),
        (7, ["Orcish Grunt", "Orcish Archer", "Wolf Rider", "Goblin Spearman", "Orcish Grunt"],
         "The orcish vanguard pushes deeper into the forest!"),
        (10, ["Orcish Warrior", "Orcish Archer", "Troll", "Wolf Rider", "Orcish Grunt", "Goblin Rouser"],
         "Trolls smash through the undergrowth!"),
        (14, ["Orcish Warrior", "Orcish Crossbowman", "Troll", "Wolf Rider", "Orcish Assassin", "Orcish Grunt"],
         "The warlord sends his elite!"),
        (18, ["Orcish Slayer", "Orcish Sniper", "Troll Rocklobber", "Goblin Pillager", "Orcish Warrior", "Orcish Crossbowman"],
         "The full might of the horde descends!"),
    ]

    spawn_x = [1, 2, 3, 4, 5, 6]
    spawn_y_top = [0, 1, 2, 0, 1, 2]
    spawn_y_mid = [6, 7, 8, 6, 7, 8]

    for turn_num, unit_types, msg in orc_waves:
        wave_events.append({"turn": turn_num, "action": "message", "side": 1, "text": msg})
        units_to_spawn = []
        for i, utype in enumerate(unit_types):
            sx = spawn_x[i % len(spawn_x)]
            sy = spawn_y_top[i % len(spawn_y_top)] if i < 3 else spawn_y_mid[i % len(spawn_y_mid)]
            units_to_spawn.append({"type": utype, "x": sx, "y": sy})
        wave_events.append({"turn": turn_num, "action": "reinforcements", "side": 1, "units": units_to_spawn})

    side_a = SideConfig(
        side_number=1, faction="Northerners", color="red",
        gold=250, income=4,
        leader_type="Orcish Warlord",
        leader_x=3, leader_y=2,
        can_recruit=["Orcish Grunt", "Orcish Archer", "Troll", "Wolf Rider",
                      "Goblin Spearman", "Orcish Crossbowman", "Orcish Assassin"],
        ai_aggression=0.75, ai_caution=0.15,
        extra_units=[
            {"type": "Orcish Grunt", "x": 2, "y": 1},
            {"type": "Orcish Grunt", "x": 4, "y": 1},
            {"type": "Orcish Archer", "x": 2, "y": 3},
            {"type": "Troll", "x": 4, "y": 3},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Rebels", color="green",
        gold=180, income=3,
        leader_type="Elvish Captain",
        leader_x=19, leader_y=14,
        can_recruit=["Elvish Fighter", "Elvish Archer", "Elvish Scout",
                      "Elvish Shaman", "Wose", "Elvish Druid"],
        ai_aggression=0.5, ai_caution=0.35,
        extra_units=[
            {"type": "Elvish Fighter", "x": 18, "y": 13},
            {"type": "Elvish Archer", "x": 20, "y": 13},
            {"type": "Elvish Fighter", "x": 18, "y": 15},
            {"type": "Wose", "x": 20, "y": 15},
            {"type": "Elvish Shaman", "x": 19, "y": 13},
        ],
    )

    return ScenarioDef(
        id="orcish_horde_invasion",
        name="Orcish Horde Invasion",
        description="The orcish horde descends upon the ancient elvish forest in "
                    "wave after wave of green-skinned fury. The elves must use "
                    "the dense woodland to their advantage, ambush and retreat, "
                    "while the orcs throw ever-larger forces into the meat grinder. "
                    "Each orcish wave brings tougher units — from goblin spearmen "
                    "to armored orcish warriors and hulking trolls.",
        map_data=m, sides=[side_a, side_b],
        max_turns=40, turns_to_record=30,
        time_of_day=TimeOfDay.MORNING, weather=WeatherType.CLEAR,
        camera_pacing="cinematic", camera_zoom=0.85,
        music="battle.ogg",
        turn_events=wave_events,
    )


# =============================================================================
# SCENARIO 21: KING OF THE HILL
# =============================================================================
def create_king_of_the_hill() -> ScenarioDef:
    """Control the central fortress hill to win. All factions rush for the center."""
    W, H = 24, 18
    m = _fill("Gg", W, H)

    # Central hill fortress — the objective
    # Hill ring
    for dx in range(-3, 4):
        for dy in range(-2, 3):
            hx, hy = 11 + dx, 8 + dy
            if 0 <= hx < W and 0 <= hy < H:
                if abs(dx) + abs(dy) > 3:
                    m = _set_terrain(m, hx, hy, "Hh")

    # Central fortress (castle + keep on the hill)
    m = _place_castle(m, 11, 8, 5)  # Side 5 = neutral marker
    # Override the keep to be a special village (the objective)
    ml = [line.split(",") for line in m]
    ml[8][11] = "Vv"  # Center keep becomes a village (the hill objective)
    m = [",".join(row) for row in ml]

    # Surrounding villages forming rings
    inner_ring = [(10, 6), (12, 6), (10, 10), (12, 10), (9, 8), (13, 8)]
    mid_ring = [(8, 5), (14, 5), (8, 11), (14, 11), (6, 8), (16, 8),
                (9, 3), (13, 3), (9, 13), (13, 13)]
    outer_ring = [(4, 3), (19, 3), (4, 14), (19, 14),
                  (11, 1), (12, 1), (11, 16), (12, 16),
                  (3, 8), (20, 8)]
    m = _place_villages(m, inner_ring + mid_ring + outer_ring)

    # Forests for tactical cover
    forest_groups = [
        [(6, 4), (7, 4), (6, 5)],
        [(16, 4), (17, 4), (17, 5)],
        [(6, 12), (7, 12), (6, 11)],
        [(16, 12), (17, 12), (17, 11)],
        [(9, 2), (10, 2)], [(13, 2), (14, 2)],
        [(9, 14), (10, 14)], [(13, 14), (14, 14)],
        [(4, 6), (5, 6)], [(18, 6), (19, 6)],
        [(4, 10), (5, 10)], [(18, 10), (19, 10)],
    ]
    for group in forest_groups:
        for fx, fy in group:
            m = _set_terrain(m, fx, fy, "Gg^Fp")

    # Roads from each corner to center
    m = _draw_road(m, [(3, 3), (6, 5), (9, 7)])
    m = _draw_road(m, [(21, 3), (18, 5), (14, 7)])
    m = _draw_road(m, [(3, 14), (6, 12), (9, 10)])
    m = _draw_road(m, [(21, 14), (18, 12), (14, 10)])

    # Four corner castles
    m = _place_castle(m, 3, 3, 1)    # NW — Loyalists
    m = _place_castle(m, 21, 3, 2)   # NE — Northerners
    m = _place_castle(m, 3, 14, 3)   # SW — Rebels
    m = _place_castle(m, 21, 14, 4)  # SE — Undead

    side_nw = SideConfig(
        side_number=1, faction="Loyalists", color="blue",
        gold=130, income=1,
        leader_type="General",
        leader_x=3, leader_y=3,
        can_recruit=["Spearman", "Bowman", "Cavalryman", "Heavy Infantryman",
                      "Mage", "Fencer", "Horseman"],
        ai_aggression=0.6, ai_caution=0.25,
        extra_units=[
            {"type": "Spearman", "x": 2, "y": 2},
            {"type": "Bowman", "x": 4, "y": 2},
            {"type": "Cavalryman", "x": 2, "y": 4},
            {"type": "Spearman", "x": 4, "y": 4},
        ],
    )

    side_ne = SideConfig(
        side_number=2, faction="Northerners", color="red",
        gold=130, income=1,
        leader_type="Orcish Warlord",
        leader_x=21, leader_y=3,
        can_recruit=["Orcish Grunt", "Orcish Archer", "Troll", "Wolf Rider",
                      "Goblin Spearman", "Orcish Crossbowman"],
        ai_aggression=0.7, ai_caution=0.2,
        extra_units=[
            {"type": "Orcish Grunt", "x": 20, "y": 2},
            {"type": "Orcish Archer", "x": 22, "y": 2},
            {"type": "Troll", "x": 20, "y": 4},
            {"type": "Wolf Rider", "x": 22, "y": 4},
        ],
    )

    side_sw = SideConfig(
        side_number=3, faction="Rebels", color="green",
        gold=130, income=1,
        leader_type="Elvish Captain",
        leader_x=3, leader_y=14,
        can_recruit=["Elvish Fighter", "Elvish Archer", "Elvish Scout",
                      "Elvish Shaman", "Wose", "Elvish Druid"],
        ai_aggression=0.55, ai_caution=0.3,
        extra_units=[
            {"type": "Elvish Fighter", "x": 2, "y": 13},
            {"type": "Elvish Archer", "x": 4, "y": 13},
            {"type": "Elvish Scout", "x": 2, "y": 15},
            {"type": "Wose", "x": 4, "y": 15},
        ],
    )

    side_se = SideConfig(
        side_number=4, faction="Undead", color="purple",
        gold=130, income=1,
        leader_type="Ancient Lich",
        leader_x=21, leader_y=14,
        can_recruit=["Skeleton", "Skeleton Archer", "Ghost", "Necrophage",
                      "Ghoul", "Dark Adept", "Bone Shooter"],
        ai_aggression=0.6, ai_caution=0.25,
        extra_units=[
            {"type": "Skeleton", "x": 20, "y": 13},
            {"type": "Skeleton Archer", "x": 22, "y": 13},
            {"type": "Ghost", "x": 20, "y": 15},
            {"type": "Dark Adept", "x": 22, "y": 15},
        ],
    )

    # KotH events — narrative messages about controlling the hill
    koth_events = [
        {"turn": 1, "action": "message", "text": "Control the central hill fortress to dominate the battlefield!"},
        {"turn": 10, "action": "message", "text": "The battle for the hill intensifies — all factions are converging!"},
        {"turn": 20, "action": "message", "text": "The hill changes hands repeatedly — whoever holds it now may claim victory!"},
    ]

    return ScenarioDef(
        id="king_of_the_hill",
        name="King of the Hill",
        description="Four armies race to seize and hold the central hill fortress. "
                    "The elevated position offers superior defensive terrain and "
                    "overlooks vital village networks. Alliances shift moment by "
                    "moment as each faction prioritizes the hill. Cavalry and "
                    "fast units rush to claim it first, while heavy infantry "
                    "slowly grinds forward to reinforce. The faction that controls "
                    "the hill controls the flow of battle.",
        map_data=m, sides=[side_nw, side_ne, side_sw, side_se],
        max_turns=35, turns_to_record=25,
        time_of_day=TimeOfDay.AFTERNOON, weather=WeatherType.CLEAR,
        camera_pacing="follow_action", camera_zoom=0.8,
        music="battle.ogg",
        turn_events=koth_events,
    )


# =============================================================================
# SCENARIO 22: DRAKE INFERNO WAVE
# =============================================================================
def create_drake_firestorm_wave() -> ScenarioDef:
    """Drakes send waves of fire units against a dwarven mountain stronghold."""
    W, H = 20, 14
    m = _fill("Hh", W, H)  # Hills

    # Mountains forming the dwarven fortress
    for x in range(13, 19):
        m = _set_terrain(m, x, 2, "Mm")
        m = _set_terrain(m, x, 11, "Mm")
    for y in range(2, 12):
        m = _set_terrain(m, 18, y, "Mm")
    # Gate
    m = _set_terrain(m, 13, 6, "Re")
    m = _set_terrain(m, 13, 7, "Re")

    # Inner grass area
    for x in range(14, 18):
        for y in range(3, 11):
            m = _set_terrain(m, x, y, "Gg")

    # Left side — open terrain for drakes
    for x in range(0, 6):
        for y in range(0, 14):
            m = _set_terrain(m, x, y, "Gg")

    # Peaks
    for px, py in [(7, 1), (7, 12), (10, 1), (10, 12)]:
        m = _set_terrain(m, px, py, "Ms")

    # Villages
    villages = [(15, 5), (16, 7), (15, 9), (10, 6), (10, 7), (8, 4), (8, 9)]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 3, 7, 1)
    m = _place_castle(m, 16, 7, 2)

    # Road
    m = _draw_road(m, [(4, 7), (7, 7), (10, 7), (13, 7)])

    # Wave events
    wave_events = []
    drake_waves = [
        (3, ["Drake Burner", "Drake Burner", "Drake Fighter"],
         "The first drakes take to the sky!"),
        (6, ["Drake Burner", "Drake Burner", "Drake Fighter", "Drake Clasher", "Saurian Skirmisher"],
         "More drakes join the assault!"),
        (9, ["Drake Burner", "Drake Firestorm", "Drake Fighter", "Drake Clasher", "Drake Glider", "Saurian Augur"],
         "Firestorm drakes lead the vanguard!"),
        (12, ["Drake Firestorm", "Drake Firestorm", "Drake Warrior", "Drake Clasher", "Drake Glider", "Drake Hurricane"],
         "The skies burn with drake fire!"),
        (16, ["Drake Flare", "Drake Firestorm", "Drake Warrior", "Drake Hurricane", "Saurian Oracle"],
         "The Drake Flare himself leads the final assault!"),
    ]

    spawn_pos = [(1, 5), (2, 6), (1, 7), (2, 8), (1, 9), (3, 7)]

    for turn_num, unit_types, msg in drake_waves:
        wave_events.append({"turn": turn_num, "action": "message", "side": 1, "text": msg})
        units_to_spawn = []
        for i, utype in enumerate(unit_types):
            sx, sy = spawn_pos[i % len(spawn_pos)]
            units_to_spawn.append({"type": utype, "x": sx, "y": sy})
        wave_events.append({"turn": turn_num, "action": "reinforcements", "side": 1, "units": units_to_spawn})

    side_a = SideConfig(
        side_number=1, faction="Drakes", color="red",
        gold=280, income=5,
        leader_type="Drake Flare",
        leader_x=3, leader_y=7,
        can_recruit=["Drake Clasher", "Drake Fighter", "Drake Burner",
                      "Drake Glider", "Drake Scout", "Drake Firestorm",
                      "Saurian Skirmisher", "Saurian Augur"],
        ai_aggression=0.8, ai_caution=0.1,
        extra_units=[
            {"type": "Drake Burner", "x": 2, "y": 6},
            {"type": "Drake Fighter", "x": 4, "y": 6},
            {"type": "Drake Clasher", "x": 2, "y": 8},
            {"type": "Drake Glider", "x": 4, "y": 8},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Knalgan Alliance", color="brown",
        gold=200, income=4,
        leader_type="Dwarvish Lord",
        leader_x=16, leader_y=7,
        can_recruit=["Dwarvish Fighter", "Dwarvish Thunderer", "Dwarvish Guardsman",
                      "Dwarvish Berserker", "Gryphon Rider", "Dwarvish Scout"],
        ai_aggression=0.4, ai_caution=0.5,
        extra_units=[
            {"type": "Dwarvish Fighter", "x": 15, "y": 6},
            {"type": "Dwarvish Thunderer", "x": 17, "y": 6},
            {"type": "Dwarvish Guardsman", "x": 15, "y": 8},
            {"type": "Gryphon Rider", "x": 17, "y": 8},
            {"type": "Dwarvish Fighter", "x": 16, "y": 6},
            {"type": "Dwarvish Thunderer", "x": 16, "y": 8},
        ],
    )

    return ScenarioDef(
        id="drake_firestorm_wave",
        name="Drake Firestorm Wave",
        description="Fire-breathing drakes launch wave after wave of aerial assault "
                    "against a fortified dwarven stronghold in the mountains. Each "
                    "wave brings more powerful drakes — from common Drake Burners "
                    "to devastating Firestorm and Hurricane drakes. The dwarves "
                    "hunker down behind stone walls, returning fire with "
                    "thunderers and gryphon riders. The mountain pass funnels the "
                    "drakes into killing grounds.",
        map_data=m, sides=[side_a, side_b],
        max_turns=40, turns_to_record=30,
        time_of_day=TimeOfDay.DUSK, weather=WeatherType.CLEAR,
        camera_pacing="cinematic", camera_zoom=0.9,
        music="northern_mountains.ogg",
        turn_events=wave_events,
    )


# =============================================================================
# SCENARIO 23: THREE-WAY KING OF THE HILL
# =============================================================================
def create_three_way_koth() -> ScenarioDef:
    """Three factions fight over a central oasis in the desert."""
    W, H = 22, 16
    m = _fill("Ds", W, H)  # Desert

    # Central oasis (the hill)
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            ox, oy = 11 + dx, 7 + dy
            if 0 <= ox < W and 0 <= oy < H:
                m = _set_terrain(m, ox, oy, "Gg")
    # Oasis water in center
    m = _set_terrain(m, 11, 7, "Ss")
    m = _set_terrain(m, 10, 7, "Xos")
    m = _set_terrain(m, 12, 7, "Xos")
    m = _set_terrain(m, 11, 6, "Gg^Fm")
    m = _set_terrain(m, 11, 8, "Gg^Fm")

    # Village at the oasis center
    m = _place_villages(m, [(11, 7), (10, 6), (12, 8)])

    # Ring of villages around the oasis
    ring_villages = [(8, 4), (14, 4), (8, 10), (14, 10), (6, 7), (16, 7)]
    m = _place_villages(m, ring_villages)

    # Outer villages
    outer_villages = [(3, 3), (18, 3), (3, 12), (18, 12), (10, 1), (12, 14)]
    m = _place_villages(m, outer_villages)

    # Hills near oasis
    for hx, hy in [(9, 5), (13, 5), (9, 9), (13, 9)]:
        m = _set_terrain(m, hx, hy, "Hh")

    # Scattered desert hills
    for hx, hy in [(5, 2), (16, 2), (5, 13), (16, 13), (10, 3), (12, 11)]:
        m = _set_terrain(m, hx, hy, "Hh")

    # Roads to oasis
    m = _draw_road(m, [(3, 3), (6, 5), (9, 7)])
    m = _draw_road(m, [(19, 3), (16, 5), (13, 7)])
    m = _draw_road(m, [(3, 13), (6, 11), (9, 7)])
    m = _draw_road(m, [(19, 13), (16, 11), (13, 7)])

    # Three castles at triangle points
    m = _place_castle(m, 3, 3, 1)    # NW
    m = _place_castle(m, 19, 3, 2)   # NE
    m = _place_castle(m, 11, 14, 3)  # South

    side_nw = SideConfig(
        side_number=1, faction="Loyalists", color="blue",
        gold=140, income=1,
        leader_type="General",
        leader_x=3, leader_y=3,
        can_recruit=["Spearman", "Bowman", "Cavalryman", "Heavy Infantryman",
                      "Mage", "Fencer", "Horseman"],
        ai_aggression=0.6, ai_caution=0.25,
        extra_units=[
            {"type": "Spearman", "x": 2, "y": 2},
            {"type": "Bowman", "x": 4, "y": 2},
            {"type": "Cavalryman", "x": 2, "y": 4},
            {"type": "Spearman", "x": 4, "y": 4},
        ],
    )

    side_ne = SideConfig(
        side_number=2, faction="Drakes", color="red",
        gold=140, income=1,
        leader_type="Drake Flare",
        leader_x=19, leader_y=3,
        can_recruit=["Drake Clasher", "Drake Fighter", "Drake Burner",
                      "Drake Glider", "Drake Scout", "Saurian Skirmisher"],
        ai_aggression=0.7, ai_caution=0.2,
        extra_units=[
            {"type": "Drake Fighter", "x": 18, "y": 2},
            {"type": "Drake Burner", "x": 20, "y": 2},
            {"type": "Drake Clasher", "x": 18, "y": 4},
            {"type": "Saurian Skirmisher", "x": 20, "y": 4},
        ],
    )

    side_s = SideConfig(
        side_number=3, faction="Northerners", color="orange",
        gold=140, income=1,
        leader_type="Orcish Warlord",
        leader_x=11, leader_y=14,
        can_recruit=["Orcish Grunt", "Orcish Archer", "Troll", "Wolf Rider",
                      "Goblin Spearman", "Orcish Crossbowman"],
        ai_aggression=0.65, ai_caution=0.2,
        extra_units=[
            {"type": "Orcish Grunt", "x": 10, "y": 13},
            {"type": "Orcish Archer", "x": 12, "y": 13},
            {"type": "Troll", "x": 10, "y": 15},
            {"type": "Wolf Rider", "x": 12, "y": 15},
        ],
    )

    koth_events = [
        {"turn": 1, "action": "message", "text": "The oasis is the only source of water in the desert — control it or perish!"},
        {"turn": 12, "action": "message", "text": "The battle for the oasis rages — water is life!"},
        {"turn": 22, "action": "message", "text": "Only the strongest will claim the oasis!"},
    ]

    return ScenarioDef(
        id="three_way_koth",
        name="Three-Way King of the Hill",
        description="Three armies clash over a life-giving oasis in the scorching "
                    "desert. The oasis provides vital healing and serves as the "
                    "only source of fresh water. Loyalists approach from the "
                    "northwest, fire-breathing Drakes from the northeast, and "
                    "Orcish hordes from the south. The desert sands offer no "
                    "cover — only speed and brute force will carry the day.",
        map_data=m, sides=[side_nw, side_ne, side_s],
        max_turns=30, turns_to_record=22,
        time_of_day=TimeOfDay.AFTERNOON, weather=WeatherType.CLEAR,
        camera_pacing="follow_action", camera_zoom=0.85,
        music="battle.ogg",
        turn_events=koth_events,
    )


# =============================================================================
# SCENARIO 24: SURVIVAL WAVE — MERFOLK STORM
# =============================================================================
def create_survival_wave() -> ScenarioDef:
    """Player defends a coastal town against waves of undead sea creatures."""
    W, H = 20, 14
    m = _fill("Gg", W, H)

    # Ocean on right
    for x in range(14, 20):
        for y in range(0, 14):
            if x >= 17:
                m = _set_terrain(m, x, y, "Wo")
            else:
                m = _set_terrain(m, x, y, "Ww")
    # Coast
    for y in range(14):
        m = _set_terrain(m, 13, y, "Ds")
    # Shallow water
    for y in range(14):
        m = _set_terrain(m, 12, y, "Ss")

    # Fortress on left
    for x in range(2, 6):
        m = _set_terrain(m, x, 1, "Mm")
        m = _set_terrain(m, x, 12, "Mm")
    for y in range(1, 13):
        m = _set_terrain(m, 1, y, "Mm")

    # Gate
    m = _set_terrain(m, 6, 6, "Re")
    m = _set_terrain(m, 6, 7, "Re")

    # Inner grass
    for x in range(2, 6):
        for y in range(2, 12):
            m = _set_terrain(m, x, y, "Gg")

    # Beach obstacles (reefs)
    for wx, wy in [(11, 3), (11, 6), (11, 8), (11, 10), (12, 4), (12, 9)]:
        m = _set_terrain(m, wx, wy, "Ww")

    # Villages
    villages = [(4, 5), (4, 7), (4, 9), (8, 4), (8, 10), (10, 7), (6, 2), (6, 11)]
    m = _place_villages(m, villages)

    # Castles
    m = _place_castle(m, 3, 7, 1)
    m = _place_castle(m, 17, 7, 2)
    # Override side 2 castle to water
    ml = [line.split(",") for line in m]
    for y in range(len(ml)):
        for x in range(len(ml[y])):
            if ml[y][x] == "Cv" and x > 13:
                ml[y][x] = "Ww"
    m = [",".join(row) for row in ml]

    # Wave events — undead sea creatures
    wave_events = []
    sea_waves = [
        (3, ["Walking Corpse", "Walking Corpse", "Skeleton", "Skeleton Archer"],
         "Something stirs beneath the waves..."),
        (6, ["Walking Corpse", "Skeleton", "Ghoul", "Ghoul", "Skeleton Archer"],
         "Drowned corpses wash ashore!"),
        (9, ["Skeleton", "Ghoul", "Ghost", "Necrophage", "Skeleton Archer", "Walking Corpse"],
         "The sea spits out the undead!"),
        (12, ["Skeleton", "Ghost", "Wraith", "Necrophage", "Dark Adept", "Ghoul", "Banebow"],
         "Wraiths emerge from the deep!"),
        (15, ["Revenant", "Ghost", "Wraith", "Necrophage", "Dark Adept", "Banebow", "Bone Knight"],
         "The drowned armada attacks in full force!"),
        (18, ["Revenant", "Wraith", "Wraith", "Necrophage", "Dark Adept", "Banebow", "Bone Knight"],
         "A final surge from the abyss!"),
    ]

    sea_spawn = [(12, 2), (13, 3), (12, 5), (13, 6), (12, 8), (13, 9), (12, 11)]

    for turn_num, unit_types, msg in sea_waves:
        wave_events.append({"turn": turn_num, "action": "message", "side": 2, "text": msg})
        units_to_spawn = []
        for i, utype in enumerate(unit_types):
            sx, sy = sea_spawn[i % len(sea_spawn)]
            units_to_spawn.append({"type": utype, "x": sx, "y": sy})
        wave_events.append({"turn": turn_num, "action": "reinforcements", "side": 2, "units": units_to_spawn})

    side_a = SideConfig(
        side_number=1, faction="Loyalists", color="blue",
        gold=180, income=3,
        leader_type="General",
        leader_x=3, leader_y=7,
        can_recruit=["Spearman", "Bowman", "Heavy Infantryman", "Mage",
                      "Fencer", "Longbowman", "Cavalryman"],
        ai_aggression=0.4, ai_caution=0.45,
        extra_units=[
            {"type": "Spearman", "x": 4, "y": 6},
            {"type": "Spearman", "x": 4, "y": 8},
            {"type": "Longbowman", "x": 2, "y": 6},
            {"type": "Longbowman", "x": 2, "y": 8},
            {"type": "Mage", "x": 3, "y": 6},
            {"type": "Heavy Infantryman", "x": 3, "y": 8},
        ],
    )

    side_b = SideConfig(
        side_number=2, faction="Undead", color="purple",
        gold=250, income=4,
        leader_type="Ancient Lich",
        leader_x=17, leader_y=7,
        can_recruit=["Skeleton", "Skeleton Archer", "Ghost", "Necrophage",
                      "Ghoul", "Dark Adept", "Walking Corpse", "Wraith"],
        ai_aggression=0.7, ai_caution=0.15,
        extra_units=[
            {"type": "Skeleton", "x": 16, "y": 6},
            {"type": "Ghost", "x": 18, "y": 6},
            {"type": "Ghoul", "x": 16, "y": 8},
            {"type": "Dark Adept", "x": 18, "y": 8},
        ],
    )

    return ScenarioDef(
        id="survival_wave",
        name="Survival Wave — Coastal Defense",
        description="A coastal town faces an onslaught from the sea as an undead "
                    "lich raises drowned sailors and sea creatures. Wave after "
                    "wave of corpses emerge from the surf, each stronger than the "
                    "last. The defenders must hold the fortified town walls while "
                    "longbowmen rain arrows onto the beach. If the walls fall, "
                    "the town falls with them.",
        map_data=m, sides=[side_a, side_b],
        max_turns=40, turns_to_record=30,
        time_of_day=TimeOfDay.DUSK, weather=WeatherType.STORM,
        camera_pacing="cinematic", camera_zoom=0.9,
        music="siege_of_laurelmor.ogg",
        turn_events=wave_events,
    )


# =============================================================================
# SCENARIO REGISTRY
# =============================================================================

ALL_SCENARIOS: List[ScenarioDef] = []

def _register_all():
    """Register all scenarios."""
    global ALL_SCENARIOS
    ALL_SCENARIOS = [
        create_classic_battlefield(),
        create_castle_siege(),
        create_forest_ambush(),
        create_river_crossing(),
        create_swamp_of_dead(),
        create_mountain_pass(),
        create_village_control(),
        create_coastal_assault(),
        create_vampire_bat_swarm(),
        create_troll_rampage(),
        create_drake_inferno(),
        create_ghost_legion(),
        create_wose_fortress(),
        create_saurian_wars(),
        create_outlaw_ambush(),
        create_drake_saurian_alliance(),
        create_undead_merfolk_nightmare(),
        create_four_faction_melee(),
        create_undead_wave_attack(),
        create_orcish_horde_invasion(),
        create_king_of_the_hill(),
        create_drake_firestorm_wave(),
        create_three_way_koth(),
        create_survival_wave(),
    ]


_register_all()


def get_scenario_by_id(scenario_id: str) -> Optional[ScenarioDef]:
    """Get a scenario by its ID."""
    for s in ALL_SCENARIOS:
        if s.id == scenario_id:
            return s
    return None


def get_scenario_names() -> List[Tuple[str, str]]:
    """Get list of (id, name) tuples for all scenarios."""
    return [(s.id, s.name) for s in ALL_SCENARIOS]


def get_single_unit_scenarios() -> List[ScenarioDef]:
    """Get scenarios that feature a single dominant unit type."""
    return [s for s in ALL_SCENARIOS if s.id in (
        "vampire_bat_swarm", "troll_rampage", "drake_inferno",
        "ghost_legion", "wose_fortress",
    )]


# Faction-to-unit-type mappings (real Wesnoth unit IDs)



def get_wave_scenarios() -> List[ScenarioDef]:
    """Get scenarios that feature wave-based reinforcement events."""
    return [s for s in ALL_SCENARIOS if s.id in (
        "undead_wave_attack", "orcish_horde_invasion", "drake_firestorm_wave",
        "survival_wave",
    )]


def get_koth_scenarios() -> List[ScenarioDef]:
    """Get King of the Hill scenarios."""
    return [s for s in ALL_SCENARIOS if s.id in (
        "king_of_the_hill", "three_way_koth",
    )]


def get_multi_faction_scenarios() -> List[ScenarioDef]:
    """Get scenarios with more than 2 factions."""
    return [s for s in ALL_SCENARIOS if len(s.sides) > 2]


def get_scenario_categories() -> Dict[str, List[ScenarioDef]]:
    """Get all scenarios organized by category."""
    return {
        "All Scenarios": ALL_SCENARIOS,
        "Single Unit": get_single_unit_scenarios(),
        "Wave Attack": get_wave_scenarios(),
        "King of the Hill": get_koth_scenarios(),
        "Multi-Faction": get_multi_faction_scenarios(),
    }


FACTION_UNIT_POOLS: Dict[str, List[str]] = {
    "Loyalists": [
        "Spearman", "Pikeman", "Halberdier",
        "Bowman", "Longbowman", "Master Bowman",
        "Cavalryman", "Knight", "Paladin", "Lancer", "Dragoon",
        "Heavy Infantryman", "Infantry General", "Shock Trooper",
        "Fencer", "Master at Arms",
        "Mage", "White Mage", "Red Mage", "Silver Mage", "Arch Mage",
        "Horseman", "General", "Grand Marshal",
    ],
    "Rebels": [
        "Elvish Fighter", "Elvish Captain", "Elvish Hero",
        "Elvish Champion", "Elvish Marshal",
        "Elvish Archer", "Elvish Marksman", "Elvish Sharpshooter",
        "Elvish Ranger", "Elvish Avenger",
        "Elvish Scout", "Elvish Outrider", "Elvish Rider",
        "Elvish Shaman", "Elvish Druid", "Elvish Sylph",
        "Wose", "Wose Shrub", "Ancient Wose",
        "Mermaid Initiate", "Mermaid Priestess", "Mermaid Enchantress",
        "Elvish High Lord", "Elvish Sovereign",
    ],
    "Northerners": [
        "Orcish Grunt", "Orcish Warrior", "Orcish Slayer",
        "Orcish Archer", "Orcish Crossbowman", "Orcish Sniper",
        "Troll", "Troll Whelp", "Troll Rocklobber",
        "Wolf Rider", "Goblin Knight", "Goblin Pillager",
        "Orcish Assassin",
        "Goblin Spearman", "Goblin Rouser", "Goblin Impaler",
        "Orcish Warlord", "Orcish Sovereign",
        "Naga Fighter", "Naga Myrmidon", "Naga Warrior",
        "Naga Server", "Naga Sea Witch",
    ],
    "Undead": [
        "Skeleton", "Skeleton Archer", "Revenant", "Draug",
        "Bone Shooter", "Bone Knight", "Chocobone",
        "Ghost", "Wraith", "Shadow", "Spectre",
        "Walking Corpse", "Cemetery Guard", "Death Knight",
        "Necrophage", "Ghoul", "Ghoulish Haunting",
        "Vampire Bat", "Blood Bat", "Dread Bat",
        "Vampire", "Necromancer", "Dark Adept",
        "Ancient Lich", "Lich",
        "Baneling", "Giant Bat", "Giant Spider",
    ],
    "Drakes": [
        "Drake Clasher", "Drake Thrasher", "Drake Slash",
        "Drake Fighter", "Drake Warrior", "Drake Blademaster",
        "Drake Burner", "Drake Firestorm", "Drake Flare",
        "Drake Glider", "Drake Sky", "Drake Hurricane",
        "Drake Scout",
        "Saurian Skirmisher", "Saurian Flanker", "Saurian Spatulate-Head",
        "Saurian Augur", "Saurian Oracle", "Saurian Soothsayer",
        "Saurian Ambusher", "Saurian Assassin",
    ],
    "Knalgan Alliance": [
        "Dwarvish Fighter", "Dwarvish Steelclad", "Dwarvish Lord",
        "Dwarvish Thunderer", "Dwarvish Thunderguard", "Dwarvish Dragonguard",
        "Dwarvish Guardsman", "Dwarvish Stalwart", "Dwarvish Sentinel",
        "Dwarvish Berserker", "Dwarvish Berserker",
        "Dwarvish Scout", "Dwarvish Explorer", "Dwarvish Pathfinder",
        "Gryphon Rider", "Gryphon Master",
        "Giant", "Yeti",
        "Thief", "Rogue", "Assassin", "Footpad", "Poacher", "Trapper",
    ],
    "Saurians": [
        "Saurian Skirmisher", "Saurian Flanker", "Saurian Spatulate-Head",
        "Saurian Augur", "Saurian Oracle", "Saurian Soothsayer",
        "Saurian Ambusher", "Saurian Assassin",
    ],
    "Outlaws": [
        "Thief", "Rogue", "Assassin",
        "Footpad", "Poacher", "Trapper",
        "Highwayman", "Outlaw", "Bandit",
        "Fugitive",
    ],
    "Merfolk": [
        "Merfolk Fighter", "Merfolk Triton", "Merfolk Tyrant",
        "Merfolk Impaler", "Merfolk Spearfighter", "Merfolk Javelineer",
        "Merfolk Entangler", "Merfolk Netcaster",
        "Merfolk Priestess", "Merfolk Diviner", "Merfolk Siren",
        "Merfolk Hunter", "Merfolk Hoplite",
    ],
}

# =========================================================================
# MAP PREVIEW - Hex map renderer and widgets
# =========================================================================




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

# =========================================================================
# WESNOTH SCANNER - Cross-platform Wesnoth finder + addon scanner
# =========================================================================



# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ScanResult:
    """Result of scanning for a single Wesnoth installation."""

    source: str          # How it was found, e.g. "PATH", "Steam", "Flatpak"
    wesnoth_binary: str  # Path to the wesnoth executable (or flatpak command)
    version: str = ""    # Output of wesnoth --version (empty if unreadable)
    user_dir: str = ""   # User data directory
    data_dir: str = ""   # Game data directory
    addon_dirs: List[str] = field(default_factory=list)  # All addon directories


@dataclass
class PlatformInfo:
    """Detected platform details."""

    system: str       # "Linux", "Windows", "Darwin"
    is_flatpak: bool  # Running inside Flatpak sandbox?
    is_snap: bool     # Running inside Snap?
    is_steam_deck: bool
    home: str         # User home directory


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

class WesnothScanner:
    """Comprehensive cross-platform Wesnoth installation scanner."""

    def __init__(self, log_callback=None):
        """
        Args:
            log_callback: Optional callable(str) for progress messages.
        """
        self._log = log_callback or (lambda msg: None)
        self._platform = self._detect_platform()

    # ------------------------------------------------------------------
    # Platform detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_platform() -> PlatformInfo:
        system = platform.system()
        home = os.path.expanduser("~")

        is_flatpak = (
            os.path.isfile("/.flatpak-info") or
            os.environ.get("FLATPAK_ID", "") != ""
        )
        is_snap = os.environ.get("SNAP", "") != ""
        is_steam_deck = (
            is_snap and
            os.path.exists("/snap/steam/common")
        )

        return PlatformInfo(
            system=system,
            is_flatpak=is_flatpak,
            is_snap=is_snap,
            is_steam_deck=is_steam_deck,
            home=home,
        )

    def get_platform_info(self) -> PlatformInfo:
        """Return the detected platform information."""
        return self._platform

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_all_installations(self) -> List[ScanResult]:
        """Find ALL Wesnoth installations on the system.

        Returns a list of :class:`ScanResult` objects, sorted by
        preference (native binary > Steam > Flatpak/Snap > others).
        """
        results: List[ScanResult] = []

        self._log(f"Scanning for Wesnoth on {self._platform.system}...")

        # 1. Binary search (all methods for current platform)
        binary_candidates = self._find_binary_candidates()

        self._log(f"  Found {len(binary_candidates)} binary candidate(s)")

        for source, binary_path in binary_candidates:
            result = self._verify_and_build_result(source, binary_path)
            if result:
                results.append(result)

        # 2. If no binaries found, try to discover from data dirs alone
        if not results:
            self._log("  No binaries found; scanning data directories...")
            for source, user_dir, data_dir in self._find_data_dir_only():
                result = ScanResult(
                    source=source,
                    wesnoth_binary="",
                    user_dir=user_dir,
                    data_dir=data_dir,
                    addon_dirs=self._collect_addon_dirs(user_dir, data_dir, ""),
                )
                results.append(result)

        self._log(f"  Scan complete: {len(results)} installation(s) found")
        return results

    def find_best_installation(self) -> Optional[ScanResult]:
        """Find the single best Wesnoth installation.

        Prefers: native binary > Steam > Flatpak > Snap > data-only.
        Returns the first verified result, or None.
        """
        all_results = self.find_all_installations()
        return all_results[0] if all_results else None

    def find_user_dirs(self) -> List[Tuple[str, str]]:
        """Find all candidate Wesnoth user data directories.

        Returns list of (source_description, path) tuples.
        """
        p = self._platform
        candidates: List[Tuple[str, str]] = []

        if p.system == "Linux":
            candidates.extend(self._linux_user_dirs())
        elif p.system == "Darwin":
            candidates.extend(self._macos_user_dirs())
        elif p.system == "Windows":
            candidates.extend(self._windows_user_dirs())

        return candidates

    def find_data_dirs(self) -> List[Tuple[str, str]]:
        """Find all candidate Wesnoth game data directories.

        Returns list of (source_description, path) tuples.
        """
        p = self._platform
        candidates: List[Tuple[str, str]] = []

        if p.system == "Linux":
            candidates.extend(self._linux_data_dirs())
        elif p.system == "Darwin":
            candidates.extend(self._macos_data_dirs())
        elif p.system == "Windows":
            candidates.extend(self._windows_data_dirs())

        return candidates

    def find_addon_dirs(self) -> List[Tuple[str, str]]:
        """Find all candidate Wesnoth addon directories.

        Returns list of (source_description, path) tuples.
        Deduplicates paths that appear multiple times.
        """
        addon_dirs: List[Tuple[str, str]] = []
        seen_paths: set = set()

        # From user data dirs
        for source, user_dir in self.find_user_dirs():
            addon_path = os.path.join(user_dir, "data", "add-ons")
            if addon_path not in seen_paths:
                seen_paths.add(addon_path)
                addon_dirs.append((f"User ({source})", addon_path))

        # From game data dirs
        for source, data_dir in self.find_data_dirs():
            addon_path = os.path.join(data_dir, "data", "add-ons")
            if addon_path not in seen_paths:
                seen_paths.add(addon_path)
                addon_dirs.append((f"Game Data ({source})", addon_path))

        # Portable install: addons next to binary
        best = self.find_best_installation()
        if best and best.wesnoth_binary and not best.wesnoth_binary.startswith("flatpak"):
            bin_dir = os.path.dirname(os.path.abspath(best.wesnoth_binary))
            portable_addon = os.path.join(bin_dir, "data", "add-ons")
            if portable_addon not in seen_paths:
                addon_dirs.append(("Portable (next to binary)", portable_addon))

        return addon_dirs

    # ------------------------------------------------------------------
    # Binary discovery
    # ------------------------------------------------------------------

    def _find_binary_candidates(self) -> List[Tuple[str, str]]:
        """Return all candidate (source, path) tuples for the Wesnoth binary."""
        p = self._platform
        seen = set()
        candidates: List[Tuple[str, str]] = []

        def _add(source: str, path: str):
            path = os.path.abspath(path) if path and not path.startswith("flatpak") else path
            if path and path not in seen:
                seen.add(path)
                candidates.append((source, path))

        # --- All platforms: check PATH ---
        which_result = shutil.which("wesnoth")
        if which_result:
            _add("PATH", which_result)

        # --- Platform-specific ---
        if p.system == "Linux":
            for src, path in self._linux_binary_paths():
                _add(src, path)
        elif p.system == "Darwin":
            for src, path in self._macos_binary_paths():
                _add(src, path)
        elif p.system == "Windows":
            for src, path in self._windows_binary_paths():
                _add(src, path)

        return candidates

    # ------------------------------------------------------------------
    # Linux binary paths
    # ------------------------------------------------------------------

    def _linux_binary_paths(self) -> List[Tuple[str, str]]:
        p = self._platform
        h = p.home
        candidates: List[Tuple[str, str]] = []

        # Standard Linux install locations
        standard = [
            ("Linux /usr/bin", "/usr/bin/wesnoth"),
            ("Linux /usr/local/bin", "/usr/local/bin/wesnoth"),
            ("Linux /usr/games", "/usr/games/bin/wesnoth"),
            ("Linux /usr/local/games", "/usr/local/games/bin/wesnoth"),
            ("Snap", "/snap/bin/wesnoth"),
            ("User local bin", os.path.join(h, ".local", "bin", "wesnoth")),
            ("User games", os.path.join(h, "games", "wesnoth", "wesnoth")),
            ("Opt", "/opt/wesnoth/bin/wesnoth"),
            ("Opt local", "/opt/wesnoth/wesnoth"),
        ]
        candidates.extend(standard)

        # AppImage (any AppImage in common locations)
        appimage_dirs = [
            os.path.join(h, "Applications"),
            os.path.join(h, ".local", "share", "applications"),
            os.path.join(h, "bin"),
            os.path.join(h, "Downloads"),
            "/opt",
        ]
        for ad in appimage_dirs:
            if os.path.isdir(ad):
                try:
                    for f in os.listdir(ad):
                        if "wesnoth" in f.lower() and f.endswith(".AppImage"):
                            candidates.append(("AppImage", os.path.join(ad, f)))
                except PermissionError:
                    pass

        # Steam (Linux)
        steam_library_dirs = self._find_steam_library_dirs_linux()
        for steam_dir in steam_library_dirs:
            if os.path.isdir(steam_dir):
                try:
                    for entry in os.listdir(steam_dir):
                        if "wesnoth" in entry.lower():
                            # Check common binary locations inside
                            for sub in ["", "bin/", "linux64/", "linux32/"]:
                                wes_bin = os.path.join(steam_dir, entry, sub, "wesnoth")
                                if os.path.isfile(wes_bin):
                                    candidates.append(("Steam", wes_bin))
                            # Also check lib/ for steam-runtime wrapped binary
                            lib_bin = os.path.join(steam_dir, entry, "lib", "wesnoth")
                            if os.path.isfile(lib_bin):
                                candidates.append(("Steam (lib)", lib_bin))
                except PermissionError:
                    pass

        # Flatpak
        if shutil.which("flatpak"):
            try:
                result = subprocess.run(
                    ["flatpak", "list", "--app", "--columns=application"],
                    capture_output=True, text=True, timeout=10
                )
                if "wesnoth" in result.stdout.lower():
                    candidates.append(("Flatpak", "flatpak run org.wesnoth.Wesnoth"))
            except Exception:
                pass

        # Snap (if wesnoth is a snap)
        if p.is_snap:
            candidates.append(("Snap (runtime)", "/snap/bin/wesnoth"))

        return candidates

    def _find_steam_library_dirs_linux(self) -> List[str]:
        """Find all Steam library folders on Linux."""
        h = self._platform.home
        dirs = [
            os.path.join(h, ".steam", "steam", "steamapps", "common"),
            os.path.join(h, ".local", "share", "Steam", "steamapps", "common"),
            os.path.join(h, ".steam", "debian-installation", "steamapps", "common"),
        ]

        # Parse steamapps/libraryfolders.vdf for additional libraries
        vdf_paths = [
            os.path.join(h, ".steam", "steam", "steamapps", "libraryfolders.vdf"),
            os.path.join(h, ".local", "share", "Steam", "steamapps", "libraryfolders.vdf"),
        ]
        for vdf_path in vdf_paths:
            if os.path.isfile(vdf_path):
                extra = self._parse_steam_vdf_libraries(vdf_path)
                dirs.extend(extra)

        return dirs

    @staticmethod
    def _parse_steam_vdf_libraries(vdf_path: str) -> List[str]:
        """Parse a Steam libraryfolders.vdf to find extra library paths.

        Handles both the old flat format and the newer nested format:
          Old: "path" "D:\\SteamLibrary"
          New: "0" { "path" "D:\\SteamLibrary" ... }
        Also handles backslash-escaped paths.
        """
        extra_dirs: List[str] = []
        seen: set = set()
        try:
            with open(vdf_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Unescape VDF backslashes ("C:\\Steam" -> "C:\Steam")
            content_unescaped = content.replace(r'\\', '\\')

            # VDF format: "path" "/some/path"
            for m in re.finditer(r'"path"\s*"([^"]+)"', content_unescaped):
                lib_path = m.group(1)
                # Skip the default library (already handled by the caller)
                common = os.path.join(lib_path, "steamapps", "common")
                if common.lower() not in seen:
                    seen.add(common.lower())
                    extra_dirs.append(common)
        except Exception:
            pass
        return extra_dirs

    # ------------------------------------------------------------------
    # macOS binary paths
    # ------------------------------------------------------------------

    def _macos_binary_paths(self) -> List[Tuple[str, str]]:
        h = self._platform.home
        candidates: List[Tuple[str, str]] = []

        # Homebrew (Intel and Apple Silicon)
        brew_prefixes = ["/opt/homebrew", "/usr/local"]
        for prefix in brew_prefixes:
            bin_path = os.path.join(prefix, "bin", "wesnoth")
            candidates.append((f"Homebrew ({prefix})", bin_path))

        # MacPorts
        candidates.append(("MacPorts", "/opt/local/bin/wesnoth"))

        # /Applications (bundled .app)
        applications_dirs = [
            "/Applications",
            os.path.join(h, "Applications"),
        ]
        for app_dir in applications_dirs:
            if os.path.isdir(app_dir):
                try:
                    for entry in os.listdir(app_dir):
                        if "wesnoth" in entry.lower() and entry.endswith(".app"):
                            # macOS app bundles: Contents/MacOS/wesnoth
                            macos_bin = os.path.join(
                                app_dir, entry, "Contents", "MacOS", "wesnoth"
                            )
                            candidates.append((f"Application ({entry})", macos_bin))
                except PermissionError:
                    pass

        # Fink
        candidates.append(("Fink", "/sw/bin/wesnoth"))

        # User local
        candidates.append(("User local", os.path.join(h, ".local", "bin", "wesnoth")))

        # Steam (macOS)
        steam_base = os.path.join(
            h, "Library", "Application Support", "Steam", "steamapps", "common"
        )
        if os.path.isdir(steam_base):
            try:
                for entry in os.listdir(steam_base):
                    if "wesnoth" in entry.lower():
                        for sub in ["", "bin/", "Contents/MacOS/"]:
                            wes_bin = os.path.join(steam_base, entry, sub, "wesnoth")
                            candidates.append(("Steam (macOS)", wes_bin))
            except PermissionError:
                pass

        # Flatpak (rare on macOS but supported via https://github.com/nickvdp/flatpak-macos)
        if shutil.which("flatpak"):
            try:
                result = subprocess.run(
                    ["flatpak", "list", "--app", "--columns=application"],
                    capture_output=True, text=True, timeout=10
                )
                if "wesnoth" in result.stdout.lower():
                    candidates.append(("Flatpak", "flatpak run org.wesnoth.Wesnoth"))
            except Exception:
                pass

        # /usr/share (macOS X11 installs)
        candidates.append(("X11 install", "/usr/X11/bin/wesnoth"))

        return candidates

    # ------------------------------------------------------------------
    # Windows binary paths
    # ------------------------------------------------------------------

    def _windows_binary_paths(self) -> List[Tuple[str, str]]:
        h = self._platform.home
        candidates: List[Tuple[str, str]] = []

        # Program Files directories
        program_files = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.environ.get("ProgramW6432", r"C:\Program Files"),
        ]
        # Deduplicate
        seen_pf = set()
        for pf in program_files:
            if pf and pf not in seen_pf:
                seen_pf.add(pf)

        for pf in seen_pf:
            wesnoth_dir = os.path.join(pf, "Wesnoth")
            candidates.append((f"Program Files ({os.path.basename(pf)})", os.path.join(wesnoth_dir, "wesnoth.exe")))
            candidates.append((f"Program Files ({os.path.basename(pf)}) /bin", os.path.join(wesnoth_dir, "bin", "wesnoth.exe")))

        # Steam (Windows) — use manifest-based detection first, then fallback
        for src, path in self._find_wesnoth_in_steam_libraries_windows():
            candidates.append((src, path))

        # GOG Galaxy
        gog_dirs = [os.path.join(h, "GOG Games")]
        for pf in seen_pf:
            gog_dirs.append(os.path.join(pf, "GOG Galaxy", "Games"))
        for gog_dir in gog_dirs:
            if os.path.isdir(gog_dir):
                try:
                    for entry in os.listdir(gog_dir):
                        if "wesnoth" in entry.lower():
                            wes_bin = os.path.join(gog_dir, entry, "wesnoth.exe")
                            candidates.append(("GOG", wes_bin))
                            # Some GOG installs nest deeper
                            wes_bin2 = os.path.join(gog_dir, entry, "game", "wesnoth.exe")
                            candidates.append(("GOG (game subdir)", wes_bin2))
                except PermissionError:
                    pass

        # itch.io
        itch_dirs = [
            os.path.join(h, "AppData", "Local", "itch", "apps"),
            os.path.join(h, ".itch", "apps"),
        ]
        for itch_dir in itch_dirs:
            if os.path.isdir(itch_dir):
                try:
                    for entry in os.listdir(itch_dir):
                        if "wesnoth" in entry.lower():
                            wes_bin = os.path.join(itch_dir, entry, "wesnoth.exe")
                            candidates.append(("itch.io", wes_bin))
                except PermissionError:
                    pass

        # Microsoft Store (UWP) - installed as a packaged app
        # The binary is typically in WindowsApps which has restricted access
        local_appdata = os.environ.get("LOCALAPPDATA", os.path.join(h, "AppData", "Local"))
        ms_store = os.path.join(local_appdata, "Packages")
        if os.path.isdir(ms_store):
            try:
                for entry in os.listdir(ms_store):
                    if "wesnoth" in entry.lower():
                        # UWP apps: look for wesnoth.exe inside the package
                        for root, dirs, files in os.walk(os.path.join(ms_store, entry)):
                            if "wesnoth.exe" in [f.lower() for f in files]:
                                candidates.append(("Microsoft Store", os.path.join(root, "wesnoth.exe")))
                                break  # One match per package is enough
            except PermissionError:
                pass

        # Chocolatey
        choco_bin = r"C:\ProgramData\chocolatey\bin\wesnoth.exe"
        candidates.append(("Chocolatey", choco_bin))

        # Scoop
        scoop_bin = os.path.join(h, "scoop", "apps", "wesnoth", "current", "wesnoth.exe")
        candidates.append(("Scoop", scoop_bin))
        scoop_shims = os.path.join(h, "scoop", "shims", "wesnoth.exe")
        candidates.append(("Scoop (shim)", scoop_shims))

        # Portable / user installs
        portable_locs = [
            os.path.join(h, "Games", "Wesnoth", "wesnoth.exe"),
            os.path.join(h, "wesnoth", "wesnoth.exe"),
            os.path.join(h, "Downloads", "wesnoth.exe"),
            os.path.join(h, "Desktop", "wesnoth.exe"),
        ]
        for loc in portable_locs:
            candidates.append(("User install", loc))

        # Registry-based search (Windows only)
        reg_results = self._search_windows_registry()
        for src, path in reg_results:
            candidates.append((src, path))

        return candidates

    def _find_steam_dirs_windows(self) -> List[str]:
        """Find Steam library directories on Windows."""
        h = self._platform.home
        dirs = []

        # 1. Find Steam's own install path from the registry (covers custom drives)
        steam_root = self._find_steam_install_path_windows()

        # 2. Build list of candidate Steam root directories
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

        steam_roots = []
        if steam_root:
            steam_roots.append(steam_root)
        # Fallback defaults (even if registry found, keep as fallback)
        steam_roots.extend([
            os.path.join(program_files_x86, "Steam"),
            os.path.join(program_files, "Steam"),
            os.path.join(h, "Steam"),
        ])
        # Deduplicate
        seen_roots = set()
        unique_roots = []
        for r in steam_roots:
            r_lower = os.path.normpath(r).lower()
            if r_lower not in seen_roots:
                seen_roots.add(r_lower)
                unique_roots.append(r)

        for root in unique_roots:
            common = os.path.join(root, "steamapps", "common")
            if os.path.isdir(common):
                dirs.append(common)
            # Parse libraryfolders.vdf for additional libraries
            vdf_path = os.path.join(root, "steamapps", "libraryfolders.vdf")
            if os.path.isfile(vdf_path):
                extra = self._parse_steam_vdf_libraries(vdf_path)
                dirs.extend(extra)

        return dirs

    @staticmethod
    def _find_steam_install_path_windows() -> Optional[str]:
        """Find Steam's install directory from the Windows registry.

        Steam stores its install path in:
          HKCU\\SOFTWARE\\Valve\\Steam  ->  SteamPath
        This handles Steam installed on any drive (D:, E:, etc.).
        """
        try:
            import winreg
        except ImportError:
            return None

        for hive in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            try:
                key = winreg.OpenKey(hive, r"SOFTWARE\Valve\Steam")
                steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
                winreg.CloseKey(key)
                if steam_path and os.path.isdir(steam_path):
                    return steam_path
            except (OSError, FileNotFoundError):
                continue
        return None

    WESNOTH_STEAM_APPID = "366920"

    def _find_wesnoth_in_steam_libraries_windows(self) -> List[Tuple[str, str]]:
        """Search all Steam libraries for Wesnoth by appmanifest (appid 366920).

        This is more reliable than listing directories and guessing names,
        because it uses Steam's own manifest files.
        """
        results: List[Tuple[str, str]] = []
        steam_common_dirs = self._find_steam_dirs_windows()

        for common_dir in steam_common_dirs:
            # Method 1: Check for appmanifest_366920.acf in the parent steamapps dir
            steamapps_dir = os.path.dirname(common_dir)
            manifest_file = os.path.join(steamapps_dir, f"appmanifest_{self.WESNOTH_STEAM_APPID}.acf")
            if os.path.isfile(manifest_file):
                # Read the manifest to get the install dir name
                try:
                    with open(manifest_file, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    # Extract "installdir"  "SomeFolderName"
                    m = re.search(r'"installdir"\s*"([^"]+)"', content)
                    if m:
                        install_dir_name = m.group(1)
                        game_dir = os.path.join(common_dir, install_dir_name)
                        for sub in ["", "bin\\"]:
                            exe = os.path.join(game_dir, sub, "wesnoth.exe")
                            results.append(("Steam (manifest)", exe))
                        # Also check common subdirectory layouts used by Windows games
                        for sub in ["game\\", "play\\"]:
                            exe = os.path.join(game_dir, sub, "wesnoth.exe")
                            results.append((f"Steam (manifest/{sub})", exe))
                except Exception:
                    pass

            # Method 2: Fallback — list directories and match by name
            if os.path.isdir(common_dir):
                try:
                    for entry in os.listdir(common_dir):
                        if "wesnoth" in entry.lower():
                            for sub in ["", "bin\\"]:
                                exe = os.path.join(common_dir, entry, sub, "wesnoth.exe")
                                results.append(("Steam", exe))
                except PermissionError:
                    pass

        return results

    @staticmethod
    def _search_windows_registry() -> List[Tuple[str, str]]:
        """Search Windows registry for Wesnoth installation paths."""
        results: List[Tuple[str, str]] = []

        try:
            import winreg
        except ImportError:
            return results  # Not Windows or reg module unavailable

        # Registry keys where games commonly register uninstall info
        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wesnoth"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Wesnoth"),
        ]

        for hive, subkey in reg_paths:
            try:
                key = winreg.OpenKey(hive, subkey)
            except (OSError, FileNotFoundError):
                continue

            try:
                # Enumerate subkeys (for Uninstall keys)
                i = 0
                while True:
                    try:
                        name = winreg.EnumKey(key, i)
                        if "wesnoth" in name.lower():
                            try:
                                sub = winreg.OpenKey(key, name)
                                install_loc = WesnothScanner._reg_read_str(sub, "InstallLocation")
                                display_name = WesnothScanner._reg_read_str(sub, "DisplayName")
                                if install_loc:
                                    exe = os.path.join(install_loc, "wesnoth.exe")
                                    results.append((f"Registry: {display_name or name}", exe))
                                    exe2 = os.path.join(install_loc, "bin", "wesnoth.exe")
                                    results.append((f"Registry (bin): {display_name or name}", exe2))
                                winreg.CloseKey(sub)
                            except OSError:
                                pass
                    except OSError:
                        break
                    i += 1

                # Also check direct values (for SOFTWARE\\Wesnoth)
                try:
                    install_loc = WesnothScanner._reg_read_str(key, "InstallLocation")
                    exe_path = WesnothScanner._reg_read_str(key, "ExePath")
                    if install_loc:
                        results.append(("Registry (Wesnoth)", os.path.join(install_loc, "wesnoth.exe")))
                    if exe_path:
                        results.append(("Registry (ExePath)", exe_path))
                except OSError:
                    pass
            finally:
                winreg.CloseKey(key)

        return results

    @staticmethod
    def _reg_read_str(key, value_name: str) -> str:
        """Read a string value from a Windows registry key."""
        import winreg
        try:
            val, _ = winreg.QueryValueEx(key, value_name)
            if isinstance(val, str):
                return val
        except (OSError, FileNotFoundError):
            pass
        return ""

    # ------------------------------------------------------------------
    # User data directories
    # ------------------------------------------------------------------

    def _linux_user_dirs(self) -> List[Tuple[str, str]]:
        h = self._platform.home
        candidates: List[Tuple[str, str]] = []

        # XDG standard
        xdg_data = os.environ.get("XDG_DATA_HOME", os.path.join(h, ".local", "share"))
        candidates.append(("XDG_DATA_HOME", os.path.join(xdg_data, "wesnoth")))

        # Common Linux locations
        candidates.extend([
            ("Default (~/.local/share/wesnoth)", os.path.join(h, ".local", "share", "wesnoth")),
            ("Legacy (~/.wesnoth)", os.path.join(h, ".wesnoth")),
            ("XDG config (~/.config/wesnoth)", os.path.join(h, ".config", "wesnoth")),
        ])

        # Flatpak user data
        flatpak_data = os.path.join(
            h, ".var", "app", "org.wesnoth.Wesnoth", "data", "wesnoth"
        )
        candidates.append(("Flatpak sandbox", flatpak_data))
        # Also check the Flatpak-specific config path
        flatpak_config = os.path.join(
            h, ".var", "app", "org.wesnoth.Wesnoth", "config", "wesnoth"
        )
        candidates.append(("Flatpak config", flatpak_config))

        # Snap user data
        if self._platform.is_snap:
            snap_data = os.path.join(
                os.environ.get("SNAP_USER_DATA", h), "wesnoth"
            )
            candidates.append(("Snap user data", snap_data))
            snap_common = os.path.join(
                os.environ.get("SNAP_USER_COMMON", h), "wesnoth"
            )
            candidates.append(("Snap common data", snap_common))

        return candidates

    def _macos_user_dirs(self) -> List[Tuple[str, str]]:
        h = self._platform.home
        return [
            ("macOS standard", os.path.join(
                h, "Library", "Application Support", "Wesnoth"
            )),
            ("macOS XDG-style", os.path.join(h, ".local", "share", "wesnoth")),
            ("Legacy (~/.wesnoth)", os.path.join(h, ".wesnoth")),
            ("macOS config", os.path.join(h, "Library", "Preferences", "Wesnoth")),
        ]

    def _windows_user_dirs(self) -> List[Tuple[str, str]]:
        h = self._platform.home
        appdata = os.environ.get("APPDATA", os.path.join(h, "AppData", "Roaming"))
        local_appdata = os.environ.get("LOCALAPPDATA", os.path.join(h, "AppData", "Local"))

        return [
            ("APPDATA", os.path.join(appdata, "Wesnoth")),
            ("LOCALAPPDATA", os.path.join(local_appdata, "Wesnoth")),
            ("User profile (~/.wesnoth)", os.path.join(h, ".wesnoth")),
            ("Documents", os.path.join(h, "Documents", "Wesnoth")),
            ("Saved Games", os.path.join(h, "Saved Games", "Wesnoth")),
        ]

    # ------------------------------------------------------------------
    # Game data directories
    # ------------------------------------------------------------------

    def _linux_data_dirs(self) -> List[Tuple[str, str]]:
        candidates: List[Tuple[str, str]] = []

        # Standard installation data dirs
        standard = [
            ("Linux /usr/share", "/usr/share/wesnoth/data"),
            ("Linux /usr/share/games", "/usr/share/games/wesnoth/data"),
            ("Linux /usr/local/share", "/usr/local/share/wesnoth/data"),
            ("Opt", "/opt/wesnoth/share/wesnoth/data"),
            ("Opt (flat)", "/opt/wesnoth/data"),
            ("User local share", os.path.join(self._platform.home, ".local", "share", "wesnoth", "data")),
        ]
        candidates.extend(standard)

        # Also check without /data suffix (some installs put data directly)
        for src, path in list(standard):
            parent = os.path.dirname(path)
            if parent != path:
                candidates.append((f"{src} (parent)", parent))

        # Steam Linux: data is usually in the game install directory
        steam_dirs = self._find_steam_library_dirs_linux()
        for steam_dir in steam_dirs:
            if os.path.isdir(steam_dir):
                try:
                    for entry in os.listdir(steam_dir):
                        if "wesnoth" in entry.lower():
                            candidates.append(("Steam data", os.path.join(steam_dir, entry, "data")))
                            candidates.append(("Steam share", os.path.join(steam_dir, entry, "share", "wesnoth", "data")))
                except PermissionError:
                    pass

        # Flatpak: system data is inside the Flatpak installation
        flatpak_system = "/var/lib/flatpak/app/org.wesnoth.Wesnoth"
        if os.path.isdir(flatpak_system):
            candidates.append(("Flatpak system", os.path.join(flatpak_system, "current", "files", "share", "wesnoth", "data")))
        # Flatpak user installation
        flatpak_user = os.path.join(self._platform.home, ".local", "share", "flatpak", "app", "org.wesnoth.Wesnoth")
        if os.path.isdir(flatpak_user):
            candidates.append(("Flatpak user", os.path.join(flatpak_user, "current", "files", "share", "wesnoth", "data")))

        # Snap: data in /snap/wesnoth/current/
        snap_data = "/snap/wesnoth/current/usr/share/wesnoth/data"
        candidates.append(("Snap system", snap_data))

        return candidates

    def _macos_data_dirs(self) -> List[Tuple[str, str]]:
        h = self._platform.home
        candidates: List[Tuple[str, str]] = []

        # .app bundle (standard macOS install)
        app_dirs = ["/Applications", os.path.join(h, "Applications")]
        for app_dir in app_dirs:
            if os.path.isdir(app_dir):
                try:
                    for entry in os.listdir(app_dir):
                        if "wesnoth" in entry.lower() and entry.endswith(".app"):
                            bundle_data = os.path.join(
                                app_dir, entry, "Contents", "Resources",
                                "share", "wesnoth", "data"
                            )
                            candidates.append((f"App Bundle ({entry})", bundle_data))
                            # Some builds put it directly under Resources
                            alt = os.path.join(
                                app_dir, entry, "Contents", "Resources", "data"
                            )
                            candidates.append((f"App Bundle alt ({entry})", alt))
                except PermissionError:
                    pass

        # Homebrew
        for prefix in ["/opt/homebrew", "/usr/local"]:
            candidates.append((f"Homebrew ({prefix})", os.path.join(prefix, "share", "wesnoth", "data")))

        # MacPorts
        candidates.append(("MacPorts", "/opt/local/share/wesnoth/data"))

        # Standard unix paths (X11/XQuartz builds)
        candidates.append(("X11", "/usr/X11/share/wesnoth/data"))
        candidates.append(("X11 local", "/usr/local/share/wesnoth/data"))

        # Steam macOS
        steam_base = os.path.join(
            h, "Library", "Application Support", "Steam", "steamapps", "common"
        )
        if os.path.isdir(steam_base):
            try:
                for entry in os.listdir(steam_base):
                    if "wesnoth" in entry.lower():
                        candidates.append(("Steam data (macOS)", os.path.join(steam_base, entry, "data")))
                        candidates.append(("Steam bundle (macOS)", os.path.join(
                            steam_base, entry, "The Battle for Wesnoth.app",
                            "Contents", "Resources", "share", "wesnoth", "data"
                        )))
            except PermissionError:
                pass

        return candidates

    def _windows_data_dirs(self) -> List[Tuple[str, str]]:
        h = self._platform.home
        candidates: List[Tuple[str, str]] = []

        # Program Files
        program_files = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ]
        seen_pf = set()
        for pf in program_files:
            if pf and pf not in seen_pf:
                seen_pf.add(pf)
                candidates.append((f"Program Files ({os.path.basename(pf)})", os.path.join(pf, "Wesnoth", "data")))
                candidates.append((f"Program Files ({os.path.basename(pf)}) /share", os.path.join(pf, "Wesnoth", "share", "wesnoth", "data")))

        # Steam Windows
        steam_dirs = self._find_steam_dirs_windows()
        for steam_common in steam_dirs:
            if os.path.isdir(steam_common):
                try:
                    for entry in os.listdir(steam_common):
                        if "wesnoth" in entry.lower():
                            candidates.append(("Steam data", os.path.join(steam_common, entry, "data")))
                            candidates.append(("Steam data (share)", os.path.join(steam_common, entry, "share", "wesnoth", "data")))
                except PermissionError:
                    pass

        # GOG
        gog_dirs = [os.path.join(h, "GOG Games")]
        for gog_dir in gog_dirs:
            if os.path.isdir(gog_dir):
                try:
                    for entry in os.listdir(gog_dir):
                        if "wesnoth" in entry.lower():
                            candidates.append(("GOG data", os.path.join(gog_dir, entry, "data")))
                            candidates.append(("GOG game/data", os.path.join(gog_dir, entry, "game", "data")))
                except PermissionError:
                    pass

        # Microsoft Store
        local_appdata = os.environ.get("LOCALAPPDATA", os.path.join(h, "AppData", "Local"))
        ms_packages = os.path.join(local_appdata, "Packages")
        if os.path.isdir(ms_packages):
            try:
                for entry in os.listdir(ms_packages):
                    if "wesnoth" in entry.lower():
                        candidates.append(("MS Store data", os.path.join(ms_packages, entry, "LocalState", "data")))
            except PermissionError:
                pass

        # Portable / user installs
        portable = [
            os.path.join(h, "Games", "Wesnoth", "data"),
            os.path.join(h, "wesnoth", "data"),
        ]
        for loc in portable:
            candidates.append(("User install", loc))

        # Chocolatey
        candidates.append(("Chocolatey", r"C:\ProgramData\chocolatey\lib\wesnoth\tools\data"))

        # Scoop
        candidates.append(("Scoop", os.path.join(h, "scoop", "apps", "wesnoth", "current", "data")))

        return candidates

    # ------------------------------------------------------------------
    # Data-dir-only discovery (when no binary is found)
    # ------------------------------------------------------------------

    def _find_data_dir_only(self) -> List[Tuple[str, str, str]]:
        """Find installations from data/user directories even without a binary.

        Returns (source, user_dir, data_dir) tuples.
        """
        results: List[Tuple[str, str, str]] = []

        user_dirs = self.find_user_dirs()
        data_dirs = self.find_data_dirs()

        existing_user = [(s, p) for s, p in user_dirs if os.path.isdir(p)]
        existing_data = [(s, p) for s, p in data_dirs if os.path.isdir(p)]

        if existing_user:
            best_user = existing_user[0]
            best_data = existing_data[0] if existing_data else ("", "")
            results.append((
                f"Data-dir scan ({best_user[0]})",
                best_user[1],
                best_data[1],
            ))

        return results

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def _verify_and_build_result(
        self, source: str, binary_path: str
    ) -> Optional[ScanResult]:
        """Verify a binary candidate and build a full ScanResult."""
        is_flatpak = binary_path.startswith("flatpak")

        # Verify the binary exists and is accessible
        if not is_flatpak:
            if not os.path.isfile(binary_path):
                return None
            # On Windows, .exe files don't need X_OK check — existence is enough.
            # On Unix, verify the executable bit is set.
            if platform.system() != "Windows":
                if not os.access(binary_path, os.X_OK):
                    self._log(f"  Skipping {binary_path} (not executable)")
                    return None

        # Run --version to verify (but on Windows, accept .exe even if --version fails)
        version = self._get_version(binary_path)
        if not version and not is_flatpak:
            if platform.system() == "Windows" and binary_path.lower().endswith(".exe"):
                # Windows .exe confirmed to exist — accept without version
                self._log(f"  Accepting {binary_path} (version check skipped)")
                version = "unknown"
            else:
                return None

        # Find associated user dir, data dir, and addon dirs
        user_dir = self._find_user_dir_for_binary(binary_path)
        data_dir = self._find_data_dir_for_binary(binary_path)
        addon_dirs = self._collect_addon_dirs(user_dir, data_dir, binary_path)

        return ScanResult(
            source=source,
            wesnoth_binary=binary_path,
            version=version or "unknown",
            user_dir=user_dir,
            data_dir=data_dir,
            addon_dirs=addon_dirs,
        )

    def _get_version(self, binary_path: str) -> str:
        """Get the version string from a Wesnoth binary."""
        is_flatpak = binary_path.startswith("flatpak")
        cmd = binary_path.split() if is_flatpak else [binary_path]

        try:
            result = subprocess.run(
                cmd + ["--version"],
                capture_output=True, text=True, timeout=15,
                # On Windows, hide the console window
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if platform.system() == "Windows" and hasattr(subprocess, "CREATE_NO_WINDOW")
                    else 0
                )
            )
            version = result.stdout.strip()
            if not version:
                version = result.stderr.strip()
            # Extract just the version number for cleaner display
            m = re.search(r'(\d+\.\d+\.\d+[\w.]*)', version)
            return m.group(1) if m else version[:80]
        except Exception:
            return ""

    def _find_user_dir_for_binary(self, binary_path: str) -> str:
        """Find the user data dir associated with a binary."""
        is_flatpak = binary_path.startswith("flatpak")

        if is_flatpak:
            h = self._platform.home
            flatpak_user = os.path.join(
                h, ".var", "app", "org.wesnoth.Wesnoth", "data", "wesnoth"
            )
            if os.path.isdir(flatpak_user):
                return flatpak_user
            # Fallback to standard Flatpak path
            return flatpak_user

        # Check all candidate user dirs, prefer ones that exist
        for _, path in self.find_user_dirs():
            if os.path.isdir(path):
                return path

        # Return the first (default) candidate even if it doesn't exist
        user_dirs = self.find_user_dirs()
        return user_dirs[0][1] if user_dirs else ""

    def _find_data_dir_for_binary(self, binary_path: str) -> str:
        """Find the game data dir associated with a binary."""
        is_flatpak = binary_path.startswith("flatpak")

        if is_flatpak:
            # Check system and user Flatpak installations
            for fp_root in ["/var/lib/flatpak", os.path.join(self._platform.home, ".local", "share", "flatpak")]:
                fp_data = os.path.join(
                    fp_root, "app", "org.wesnoth.Wesnoth",
                    "current", "files", "share", "wesnoth", "data"
                )
                if os.path.isdir(fp_data):
                    return fp_data
            return ""

        # For native binaries: try to infer from the binary location
        bin_abs = os.path.abspath(binary_path)
        bin_dir = os.path.dirname(bin_abs)

        # If binary is in a "bin" subdirectory, data is usually in ../share/wesnoth/data
        if os.path.basename(bin_dir) == "bin":
            parent = os.path.dirname(bin_dir)
            candidate = os.path.join(parent, "share", "wesnoth", "data")
            if os.path.isdir(candidate):
                return candidate
            candidate2 = os.path.join(parent, "data")
            if os.path.isdir(candidate2):
                return candidate2

        # If binary is in a .app bundle (macOS)
        if "Contents/MacOS" in bin_abs:
            app_contents = bin_abs.split("Contents/MacOS")[0]
            candidate = os.path.join(app_contents, "Resources", "share", "wesnoth", "data")
            if os.path.isdir(candidate):
                return candidate
            candidate2 = os.path.join(app_contents, "Resources", "data")
            if os.path.isdir(candidate2):
                return candidate2

        # If binary is inside a Steam game directory
        if "steamapps" in bin_abs.lower():
            # Walk up to the game's root directory
            parts = Path(bin_abs).parts
            for i, part in enumerate(parts):
                if part.lower() == "common" and i + 1 < len(parts):
                    game_root = os.path.join(*parts[:i + 2])
                    for sub in ["data", "share/wesnoth/data"]:
                        candidate = os.path.join(game_root, sub)
                        if os.path.isdir(candidate):
                            return candidate
                    break

        # If binary is inside a GOG directory
        if "gog" in bin_abs.lower():
            for sub in ["data", "game/data"]:
                candidate = os.path.join(bin_dir, sub)
                if os.path.isdir(candidate):
                    return candidate

        # Check all known data dirs
        for _, path in self.find_data_dirs():
            if os.path.isdir(path):
                return path

        # Return the first candidate even if it doesn't exist
        data_dirs = self.find_data_dirs()
        return data_dirs[0][1] if data_dirs else ""

    def _collect_addon_dirs(
        self, user_dir: str, data_dir: str, binary_path: str
    ) -> List[str]:
        """Collect all addon directories from user dir, data dir, and portable installs."""
        dirs = []

        # User addons (primary)
        if user_dir:
            user_addons = os.path.join(user_dir, "data", "add-ons")
            dirs.append(user_addons)

        # Game data addons (bundled/core addons)
        if data_dir:
            data_addons = os.path.join(data_dir, "add-ons")
            if data_addons not in dirs:
                dirs.append(data_addons)

        # Portable: addons next to the binary
        if binary_path and not binary_path.startswith("flatpak"):
            bin_dir = os.path.dirname(os.path.abspath(binary_path))
            portable_addons = os.path.join(bin_dir, "data", "add-ons")
            if portable_addons not in dirs:
                dirs.append(portable_addons)
            # Also check sibling of bin/
            if os.path.basename(bin_dir) == "bin":
                parent_addons = os.path.join(os.path.dirname(bin_dir), "data", "add-ons")
                if parent_addons not in dirs:
                    dirs.append(parent_addons)

        return dirs

    # ------------------------------------------------------------------
    # Convenience methods (backward-compatible with old code)
    # ------------------------------------------------------------------

    def find_wesnoth_binary(self) -> Optional[str]:
        """Find the best Wesnoth binary path (backward-compatible)."""
        result = self.find_best_installation()
        return result.wesnoth_binary if result else None

    def find_wesnoth_user_dir(self) -> str:
        """Find the Wesnoth user data directory (backward-compatible)."""
        result = self.find_best_installation()
        if result and result.user_dir:
            return result.user_dir

        # Fallback: check known locations directly
        for _, path in self.find_user_dirs():
            if os.path.isdir(path):
                return path

        # Default fallback
        user_dirs = self.find_user_dirs()
        return user_dirs[0][1] if user_dirs else os.path.join(self._platform.home, ".local", "share", "wesnoth")

    def find_wesnoth_data_dir(self) -> str:
        """Find the Wesnoth game data directory."""
        result = self.find_best_installation()
        if result and result.data_dir:
            return result.data_dir

        # Fallback
        for _, path in self.find_data_dirs():
            if os.path.isdir(path):
                return path

        data_dirs = self.find_data_dirs()
        return data_dirs[0][1] if data_dirs else ""

    def find_existing_addon_dirs(self) -> List[str]:
        """Find all addon directories that actually exist on disk."""
        result = self.find_best_installation()
        if result:
            return [d for d in result.addon_dirs if os.path.isdir(d)]

        # Fallback: check all known locations
        existing = []
        for source, path in self.find_addon_dirs():
            if os.path.isdir(path):
                existing.append(path)
        return existing

    def get_scan_summary(self) -> str:
        """Get a human-readable summary of the scan results."""
        lines = []
        lines.append(f"Platform: {self._platform.system}")
        lines.append(f"Home: {self._platform.home}")
        if self._platform.is_flatpak:
            lines.append("Running inside Flatpak sandbox")
        if self._platform.is_snap:
            lines.append("Running inside Snap")
        lines.append("")

        installations = self.find_all_installations()
        if not installations:
            lines.append("No Wesnoth installations found.")
            lines.append("")
            lines.append("Candidate user data directories:")
            for source, path in self.find_user_dirs():
                exists = os.path.isdir(path)
                lines.append(f"  [{'OK' if exists else '  '}] {source}: {path}")
            lines.append("")
            lines.append("Candidate game data directories:")
            for source, path in self.find_data_dirs():
                exists = os.path.isdir(path)
                lines.append(f"  [{'OK' if exists else '  '}] {source}: {path}")
            lines.append("")
            lines.append("Candidate addon directories:")
            for source, path in self.find_addon_dirs():
                exists = os.path.isdir(path)
                lines.append(f"  [{'OK' if exists else '  '}] {source}: {path}")
        else:
            for i, inst in enumerate(installations, 1):
                lines.append(f"Installation #{i} (via {inst.source}):")
                lines.append(f"  Binary:   {inst.wesnoth_binary or '(none)'}")
                lines.append(f"  Version:  {inst.version}")
                lines.append(f"  User dir: {inst.user_dir or '(unknown)'}")
                lines.append(f"  Data dir: {inst.data_dir or '(unknown)'}")
                lines.append(f"  Addon dirs:")
                for ad in inst.addon_dirs:
                    exists = "exists" if os.path.isdir(ad) else "missing"
                    lines.append(f"    [{exists}] {ad}")
                lines.append("")

        return "\n".join(lines)


# =============================================================================
# ADDON SCANNER (merged from addon_scanner.py)
# =============================================================================

@dataclass
class AddonUnit:
    """A unit type discovered from an addon."""
    unit_id: str        # WML unit type id= field
    name: str           # WML name= field
    faction: str        # WML faction= field (may be empty)
    hp: int             # WML hitpoints= field
    addon_name: str     # Which addon it came from
    cfg_path: str       # Path to the .cfg file


@dataclass
class DiscoveredAddon:
    """An addon found on disk."""
    name: str           # Directory name
    path: str           # Full path
    unit_count: int     # Number of unit types found
    units: List[AddonUnit] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

class AddonScanner:
    """Scans Wesnoth addon directories for custom units.

    Uses WesnothScanner for cross-platform path detection (Windows, macOS,
    Linux).  Supports scanning multiple addon directories simultaneously
    (user addons, game data addons, portable installs, etc.).
    """

    # The relative path inside the Wesnoth user data dir where addons live.
    _ADDONS_RELATIVE: str = os.path.join("data", "add-ons")

    # Known Windows addon paths (Wesnoth 1.18 from Steam/standalone)
    _WINDOWS_KNOWN_ADDON_PATHS = [
        r"C:\Users\Entendore\Documents\My Games\Wesnoth1.18\data\add-ons",
    ]

    def __init__(self, wesnoth_user_dir: str = "", addon_dirs: List[str] = None):
        """Initialise with an optional custom Wesnoth user directory.

        Addon directories are collected from:
          1. WesnothScanner auto-detection (user dir, data dir, Steam, etc.)
          2. Known Windows paths (e.g. Steam Wesnoth 1.18)
          3. Any extra dirs passed via addon_dirs

        No manual "Add" button needed — all addon folders are found automatically.
        """
        self._scanner = WesnothScanner()

        if wesnoth_user_dir:
            self._user_dir: str = os.path.abspath(wesnoth_user_dir)
        else:
            self._user_dir = self._scanner.find_wesnoth_user_dir()

        self._addons_dir: str = os.path.join(self._user_dir, self._ADDONS_RELATIVE)
        self._extra_addon_dirs: List[str] = list(addon_dirs) if addon_dirs else []

        # Auto-add known Windows addon paths
        if sys.platform == "win32":
            for known_path in self._WINDOWS_KNOWN_ADDON_PATHS:
                if os.path.isdir(known_path) and known_path not in self._extra_addon_dirs:
                    self._extra_addon_dirs.append(known_path)

        self._discovered: List[DiscoveredAddon] = []
        self._all_units: List[AddonUnit] = []
        self._all_scanned_dirs: List[str] = []  # Track all dirs we scanned

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self) -> List[DiscoveredAddon]:
        """Scan all addons and return discovered units.

        Scans the primary user addons directory AND any extra addon
        directories.  The result is cached; call :meth:`scan` again to
        re-scan.
        """
        self._discovered.clear()
        self._all_units.clear()
        self._all_scanned_dirs.clear()

        # Collect all addon directories to scan
        dirs_to_scan: List[str] = [self._addons_dir]

        # Add auto-detected addon directories from WesnothScanner
        try:
            auto_addon_dirs = self._scanner.find_addon_dirs()
            for source, ad_path in auto_addon_dirs:
                if ad_path not in dirs_to_scan:
                    dirs_to_scan.append(ad_path)
        except Exception:
            pass

        # Add any extra user-specified dirs
        for extra in self._extra_addon_dirs:
            if extra not in dirs_to_scan:
                dirs_to_scan.append(extra)

        # Track already-seen addon names across all directories to avoid duplicates
        seen_addon_names: Dict[str, str] = {}

        # Scan each directory
        for ad_dir in dirs_to_scan:
            self._all_scanned_dirs.append(ad_dir)
            addons_path = Path(ad_dir)
            if not addons_path.is_dir():
                continue

            for entry in sorted(addons_path.iterdir()):
                if not entry.is_dir():
                    continue

                addon_name = entry.name

                # Skip our own generated addon
                if addon_name == "ai_movie_renderer":
                    continue

                # If we already found an addon with this name, append units
                # to the existing discovery instead of creating duplicates
                units = self._scan_addon_dir(entry, addon_name)
                if addon_name in seen_addon_names:
                    # Merge units into existing discovery
                    for disc in self._discovered:
                        if disc.name == addon_name:
                            disc.units.extend(units)
                            disc.unit_count = len(disc.units)
                            self._all_units.extend(units)
                            break
                else:
                    if units:  # Only record addons that have unit types
                        seen_addon_names[addon_name] = str(entry)
                        discovered = DiscoveredAddon(
                            name=addon_name,
                            path=str(entry),
                            unit_count=len(units),
                            units=units,
                        )
                        self._discovered.append(discovered)
                        self._all_units.extend(units)

        return self._discovered

    def get_scanned_dirs(self) -> List[str]:
        """Return all addon directories that were (or would be) scanned."""
        if self._all_scanned_dirs:
            return list(self._all_scanned_dirs)
        # Pre-compute without doing a full scan
        dirs = [self._addons_dir]
        try:
            for source, ad_path in self._scanner.find_addon_dirs():
                if ad_path not in dirs:
                    dirs.append(ad_path)
        except Exception:
            pass
        for extra in self._extra_addon_dirs:
            if extra not in dirs:
                dirs.append(extra)
        return dirs

    def add_addon_dir(self, path: str):
        """Add an extra addon directory to scan."""
        abs_path = os.path.abspath(path)
        if abs_path not in self._extra_addon_dirs:
            self._extra_addon_dirs.append(abs_path)

    def get_all_units(self) -> List[AddonUnit]:
        """Return a flat list of all discovered units from all addons."""
        return list(self._all_units)

    def get_unit_ids(self) -> List[str]:
        """Return just unit type IDs suitable for use in ``can_recruit`` lists."""
        return [u.unit_id for u in self._all_units]

    def get_units_by_addon(self) -> Dict[str, List[AddonUnit]]:
        """Return units grouped by addon name."""
        result: Dict[str, List[AddonUnit]] = {}
        for addon in self._discovered:
            if addon.units:
                result[addon.name] = list(addon.units)
        return result

    # ------------------------------------------------------------------
    # Auto-detection
    # ------------------------------------------------------------------

    @staticmethod
    def find_wesnoth_user_dir() -> str:
        """Find the Wesnoth user data directory.

        Uses WesnothScanner for cross-platform detection (Windows, macOS,
        Linux).  Checks platform-specific locations and returns the first
        one that exists, or the most likely default.
        """
        scanner = WesnothScanner()
        return scanner.find_wesnoth_user_dir()

    @staticmethod
    def find_all_addon_dirs() -> List[str]:
        """Find all addon directories that exist on disk.

        Uses WesnothScanner for comprehensive cross-platform detection.
        """
        scanner = WesnothScanner()
        return scanner.find_existing_addon_dirs()

    # ------------------------------------------------------------------
    # WML parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_comment(line: str) -> str:
        """Remove a trailing ``#`` comment from *line*.

        WML uses ``#`` for comments but a literal ``#`` inside a quoted
        string is not a comment.  We handle the simple common cases.
        """
        # If the line starts with # the whole thing is a comment.
        stripped = line.strip()
        if stripped.startswith("#"):
            return ""
        return line

    @staticmethod
    def _parse_name_value(raw: str) -> str:
        """Extract the human-readable name from a WML name= value.

        Handles:
        - ``name= _ "Vampire Bat"``
        - ``name="Vampire Bat"``
        - ``name=Vampire Bat``
        """
        raw = raw.strip()
        if not raw:
            return ""

        # Pattern: optional _ then optional whitespace then "quoted text"
        m = re.match(r'^_\s*"(.+)"$', raw)
        if m:
            return m.group(1).strip()

        # Pattern: "quoted text"
        m = re.match(r'^"(.+)"$', raw)
        if m:
            return m.group(1).strip()

        # Bare value (everything after potential leading _ and whitespace)
        cleaned = re.sub(r'^_\s*', '', raw)
        return cleaned.strip()

    def _parse_unit_type_block(
        self,
        lines: List[str],
        start_idx: int,
        addon_name: str,
        cfg_path: str,
    ) -> Optional[AddonUnit]:
        """Parse a ``[unit_type]`` block from WML *lines* starting at
        *start_idx*.

        Returns the parsed :class:`AddonUnit` or ``None`` if the block is
        incomplete or malformed.

        WML parsing rules applied:

        * ``[unit_type]`` starts the block.
        * ``key=value`` lines inside are attributes.
        * ``[/unit_type]`` ends the block.
        * Nested ``[...]`` / ``[/...]`` blocks are tracked and skipped.
        * ``#`` comment lines are ignored.
        """
        unit_id: str = ""
        name: str = ""
        faction: str = ""
        hp: int = 0

        depth = 0  # bracket nesting depth (0 == inside [unit_type] directly)
        i = start_idx + 1  # skip the [unit_type] line itself

        while i < len(lines):
            raw_line = self._strip_comment(lines[i])
            line = raw_line.strip()

            # Skip blanks and pure comment lines
            if not line:
                i += 1
                continue

            # Opening tag – increase depth
            open_match = re.match(r'^\[(\w+)\]$', line)
            if open_match:
                depth += 1
                i += 1
                continue

            # Closing tag
            close_match = re.match(r'^\[/\w+\]$', line)
            if close_match:
                if depth == 0:
                    # End of [unit_type]
                    break
                depth -= 1
                i += 1
                continue

            # Only parse key=value at depth 0 (direct children of unit_type)
            if depth == 0 and "=" in line:
                eq_pos = line.index("=")
                key = line[:eq_pos].strip().lower()
                value = line[eq_pos + 1 :].strip()

                if key == "id":
                    unit_id = value
                elif key == "name":
                    name = self._parse_name_value(value)
                elif key == "faction":
                    faction = value
                elif key == "hitpoints":
                    try:
                        hp = int(value)
                    except ValueError:
                        hp = 0

            i += 1

        if not unit_id:
            return None

        return AddonUnit(
            unit_id=unit_id,
            name=name or unit_id,
            faction=faction,
            hp=hp,
            addon_name=addon_name,
            cfg_path=cfg_path,
        )

    def _scan_cfg_file(self, filepath: str, addon_name: str) -> List[AddonUnit]:
        """Scan a single ``.cfg`` file for ``[unit_type]`` blocks."""
        units: List[AddonUnit] = []

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            return units

        i = 0
        while i < len(lines):
            stripped = self._strip_comment(lines[i]).strip()
            if stripped == "[unit_type]":
                unit = self._parse_unit_type_block(lines, i, addon_name, filepath)
                if unit is not None:
                    units.append(unit)
            i += 1

        return units

    # ------------------------------------------------------------------
    # Internal scanning
    # ------------------------------------------------------------------

    def _scan_addon_dir(self, addon_path: Path, addon_name: str) -> List[AddonUnit]:
        """Recursively scan an addon directory for ``.cfg`` files."""
        units: List[AddonUnit] = []

        try:
            all_files = sorted(addon_path.rglob("*.cfg"))
        except OSError:
            return units

        for cfg_file in all_files:
            if cfg_file.is_file():
                try:
                    units.extend(self._scan_cfg_file(str(cfg_file), addon_name))
                except Exception:
                    # Be robust – skip files that cause unexpected errors.
                    continue

        return units


# =========================================================================
# WESNOTH BRIDGE - Recording engine (Xvfb + VideoEncoder)
# =========================================================================




@dataclass
class WesnothPaths:
    """Resolved paths for Wesnoth installation."""
    wesnoth_binary: str
    data_dir: str = ""
    user_dir: str = ""
    addon_dir: str = ""


@dataclass
class RecordingConfig:
    """Configuration for a recording session."""
    wesnoth_path: str = "wesnoth"
    scenario_id: str = "classic_battlefield"
    addon_path: str = ""
    resolution: Tuple[int, int] = (1280, 720)
    fps: int = 30
    output_path: str = "output.mp4"
    video_codec: str = "libx264"
    video_crf: int = 23
    video_preset: str = "medium"
    use_xvfb: bool = True
    xvfb_display: str = ":99"
    max_turns: int = 30
    game_speed: float = 1.0  # 1.0 = normal, 2.0 = double speed
    audio_file: str = ""  # Optional background music


class WesnothBridge:
    """
    Bridge to the actual Battle for Wesnoth game.
    Handles: Xvfb display, Wesnoth launch, ffmpeg recording, and process management.
    """

    def __init__(self, config: RecordingConfig = None):
        self.config = config or RecordingConfig()
        self._xvfb_process: Optional[subprocess.Popen] = None
        self._wesnoth_process: Optional[subprocess.Popen] = None
        self._ffmpeg_process: Optional[subprocess.Popen] = None
        self._log_lines: List[str] = []
        self._on_log: Optional[Callable[[str], None]] = None
        self._cancelled = False
        self._recording_start_time: float = 0

    def set_log_callback(self, callback: Callable[[str], None]):
        self._on_log = callback

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self._log_lines.append(line)
        if self._on_log:
            self._on_log(line)

    # =========================================================================
    # WESNOTH DISCOVERY
    # =========================================================================

    @staticmethod
    def find_wesnoth() -> Optional[WesnothPaths]:
        """Auto-detect Wesnoth installation on the system.

        Uses the comprehensive cross-platform WesnothScanner to locate
        the binary, user data dir, game data dir, and addon dirs on
        Windows, macOS, and Linux.
        """
        scanner = WesnothScanner()
        result = scanner.find_best_installation()
        if not result:
            return None

        # Pick the first existing addon dir for backward compatibility
        addon_dir = ""
        for ad in result.addon_dirs:
            if os.path.isdir(ad):
                addon_dir = ad
                break
        if not addon_dir and result.user_dir:
            addon_dir = os.path.join(result.user_dir, "data", "add-ons")

        return WesnothPaths(
            wesnoth_binary=result.wesnoth_binary,
            data_dir=result.data_dir,
            user_dir=result.user_dir,
            addon_dir=addon_dir,
        )

    @staticmethod
    def find_all_installations() -> List[WesnothPaths]:
        """Find ALL Wesnoth installations on the system.

        Returns a list of WesnothPaths for each discovered installation.
        """
        scanner = WesnothScanner()
        results = scanner.find_all_installations()
        paths_list = []
        for r in results:
            addon_dir = ""
            for ad in r.addon_dirs:
                if os.path.isdir(ad):
                    addon_dir = ad
                    break
            if not addon_dir and r.user_dir:
                addon_dir = os.path.join(r.user_dir, "data", "add-ons")
            paths_list.append(WesnothPaths(
                wesnoth_binary=r.wesnoth_binary,
                data_dir=r.data_dir,
                user_dir=r.user_dir,
                addon_dir=addon_dir,
            ))
        return paths_list

    @staticmethod
    def get_scan_summary() -> str:
        """Get a human-readable summary of all found Wesnoth paths."""
        scanner = WesnothScanner()
        return scanner.get_scan_summary()

    @staticmethod
    def find_addon_dirs() -> List[str]:
        """Find all addon directories that exist on disk."""
        scanner = WesnothScanner()
        return scanner.find_existing_addon_dirs()

    @staticmethod
    def _find_user_dir() -> str:
        """Find the Wesnoth user data directory (backward compat)."""
        scanner = WesnothScanner()
        return scanner.find_wesnoth_user_dir()

    @staticmethod
    def check_dependencies() -> Dict[str, bool]:
        """Check which tools are available."""
        return {
            "wesnoth": shutil.which("wesnoth") is not None,
            "ffmpeg": shutil.which("ffmpeg") is not None,
            "xvfb": shutil.which("Xvfb") is not None,
            "python3": shutil.which("python3") is not None,
            "pip/Pillow": importlib.util.find_spec("PIL") is not None,
        }

    # =========================================================================
    # XVFB MANAGEMENT
    # =========================================================================

    def start_xvfb(self) -> bool:
        """Start Xvfb virtual display for headless rendering."""
        if not self.config.use_xvfb:
            self._log("Xvfb disabled — will use direct display")
            return True

        xvfb_path = shutil.which("Xvfb")
        if not xvfb_path:
            self._log("WARNING: Xvfb not found. Install: sudo apt install xvfb")
            self._log("Recording will try to use the current display instead.")
            self.config.use_xvfb = False
            return True

        self.stop_xvfb()

        w, h = self.config.resolution
        display = self.config.xvfb_display

        try:
            self._xvfb_process = subprocess.Popen(
                [xvfb_path, display, "-screen", "0", f"{w}x{h}x24",
                 "-ac", "+extension", "GLX", "+render", "-noreset"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.5)

            if self._xvfb_process.poll() is not None:
                self._log("ERROR: Xvfb failed to start")
                self.config.use_xvfb = False
                return False

            self._log(f"Xvfb started on display {display} ({w}x{h}x24)")
            return True
        except Exception as e:
            self._log(f"ERROR starting Xvfb: {e}")
            self.config.use_xvfb = False
            return True

    def stop_xvfb(self):
        """Stop Xvfb."""
        if self._xvfb_process:
            try:
                self._xvfb_process.terminate()
                self._xvfb_process.wait(timeout=5)
            except Exception:
                try:
                    self._xvfb_process.kill()
                except Exception:
                    pass
            self._xvfb_process = None

    # =========================================================================
    # WESNOTH EXECUTION
    # =========================================================================

    def _build_wesnoth_cmd(self) -> List[str]:
        """Build the Wesnoth command line for AI vs AI recording."""
        w, h = self.config.resolution
        is_flatpak = self.config.wesnoth_path.startswith("flatpak")
        cmd = self.config.wesnoth_path.split() if is_flatpak else [self.config.wesnoth_path]

        # Core options
        cmd.extend([
            "--resolution", f"{w}x{h}",
            "--fps", str(self.config.fps),
            "--nosound",
            "--nomusic",
        ])

        # Load addon path if specified
        if self.config.addon_path:
            cmd.extend(["--path", self.config.addon_path])

        # Run as multiplayer with both sides AI
        cmd.extend([
            "--multiplayer",
            "--scenario", self.config.scenario_id,
            "--controller", "1:ai",
            "--controller", "2:ai",
        ])

        # Exit when done (no GUI interaction needed)
        cmd.append("--exit-at-end")

        # No delay between animations for faster recording
        # (Lua delays handle cinematic pacing instead)
        if self.config.game_speed > 1.5:
            cmd.append("--nodelay")

        # Log level
        cmd.extend(["--log-warning", "all"])

        return cmd

    def _terminate_process(self, proc: Optional[subprocess.Popen], name: str):
        """Gracefully terminate a process."""
        if not proc:
            return
        try:
            if hasattr(os, 'killpg'):
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    # =========================================================================
    # FFMPEG RECORDING
    # =========================================================================

    def start_ffmpeg_recording(self) -> bool:
        """Start ffmpeg X11 grab to record the Wesnoth display."""
        w, h = self.config.resolution

        # Ensure output directory exists
        out_path = Path(self.config.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        display = self.config.xvfb_display if self.config.use_xvfb else os.environ.get("DISPLAY", ":0")

        cmd = [
            "ffmpeg", "-y",
            "-video_size", f"{w}x{h}",
            "-framerate", str(self.config.fps),
            "-f", "x11grab",
            "-draw_mouse", "0",  # No mouse cursor
            "-i", display,
            "-c:v", self.config.video_codec,
            "-preset", self.config.video_preset,
            "-crf", str(self.config.video_crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ]

        # Audio
        if self.config.audio_file and os.path.isfile(self.config.audio_file):
            cmd.extend(["-i", self.config.audio_file, "-c:a", "aac", "-b:a", "128k",
                        "-shortest"])
        else:
            cmd.append("-an")

        # Metadata
        cmd.extend([
            "-metadata", f"title={self.config.scenario_id}",
            "-metadata", "encoder=AI Movie Renderer for Battle for Wesnoth",
            str(self.config.output_path),
        ])

        self._log(f"Starting ffmpeg recording...")
        self._log(f"  Display: {display}")
        self._log(f"  Output: {self.config.output_path}")
        self._log(f"  Codec: {self.config.video_codec} preset={self.config.video_preset} crf={self.config.video_crf}")

        try:
            env = os.environ.copy()
            if self.config.use_xvfb:
                env["DISPLAY"] = self.config.xvfb_display

            self._ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None,
            )
            self._recording_start_time = time.time()
            self._log("ffmpeg recording started successfully")
            return True
        except FileNotFoundError:
            self._log("ERROR: ffmpeg not found! Install: sudo apt install ffmpeg")
            return False
        except Exception as e:
            self._log(f"ERROR starting ffmpeg: {e}")
            return False

    def stop_ffmpeg_recording(self):
        """Stop ffmpeg recording gracefully."""
        if self._ffmpeg_process:
            self._log("Stopping ffmpeg recording...")
            # Send 'q' to ffmpeg's stdin for clean termination
            try:
                self._ffmpeg_process.stdin.write(b'q')
                self._ffmpeg_process.stdin.flush()
            except Exception:
                pass

            try:
                self._ffmpeg_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._terminate_process(self._ffmpeg_process, "ffmpeg")

            self._ffmpeg_process = None

            # Check output
            if os.path.isfile(self.config.output_path):
                size_mb = os.path.getsize(self.config.output_path) / (1024 * 1024)
                duration = time.time() - self._recording_start_time
                self._log(f"Recording saved: {self.config.output_path}")
                self._log(f"  Size: {size_mb:.1f} MB, Duration: {duration:.1f}s")

    # =========================================================================
    # MAIN RECORDING WORKFLOW
    # =========================================================================

    def run_recording(self, log_callback: Optional[Callable] = None) -> bool:
        """
        Execute the full recording workflow:
        1. Start Xvfb
        2. Start ffmpeg recording
        3. Launch Wesnoth (AI vs AI)
        4. Wait for completion
        5. Stop recording
        """
        if log_callback:
            self._on_log = log_callback
        self._cancelled = False

        self._log("=" * 50)
        self._log("AI Movie Renderer — Starting Recording")
        self._log("=" * 50)

        # Step 1: Start Xvfb
        if not self.start_xvfb():
            self._log("FATAL: Cannot start virtual display. Aborting.")
            return False

        # Step 2: Start ffmpeg recording
        if not self.start_ffmpeg_recording():
            self.stop_xvfb()
            self._log("FATAL: Cannot start recording. Aborting.")
            return False

        # Small delay so ffmpeg can initialize
        time.sleep(1.0)

        # Step 3: Launch Wesnoth
        cmd = self._build_wesnoth_cmd()
        self._log(f"Launching Wesnoth...")
        self._log(f"  Scenario: {self.config.scenario_id}")
        self._log(f"  Command: {' '.join(cmd[:8])}...")

        env = os.environ.copy()
        if self.config.use_xvfb:
            env["DISPLAY"] = self.config.xvfb_display
            env["SDL_VIDEODRIVER"] = "x11"

        success = False
        try:
            self._wesnoth_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None,
            )

            # Monitor Wesnoth process
            while self._wesnoth_process.poll() is None:
                if self._cancelled:
                    self._log("Recording cancelled by user")
                    break

                # Log stderr periodically (contains game messages)
                try:
                    if self._wesnoth_process.stderr:
                        if select.select([self._wesnoth_process.stderr], [], [], 0.1)[0]:
                            line = self._wesnoth_process.stderr.readline()
                            if line:
                                decoded = line.decode("utf-8", errors="replace").strip()
                                if decoded and "ai_movie" in decoded.lower():
                                    self._log(f"  [game] {decoded[:200]}")
                except Exception:
                    pass

                time.sleep(0.5)

            returncode = self._wesnoth_process.poll()
            self._wesnoth_process = None

            if returncode == 0:
                self._log("Wesnoth battle completed successfully!")
                success = True
            else:
                self._log(f"Wesnoth exited with code {returncode}")
                # Still might have useful recording
                if os.path.isfile(self.config.output_path):
                    self._log("Video file exists — recording may be partial but usable.")
                    success = True

        except FileNotFoundError:
            self._log("ERROR: Wesnoth binary not found!")
            self._log("Install Battle for Wesnoth: https://github.com/wesnoth/wesnoth")
            self._log("Or: sudo apt install wesnoth / flatpak install org.wesnoth.Wesnoth")
        except Exception as e:
            self._log(f"ERROR running Wesnoth: {e}")
        finally:
            # Step 4 & 5: Cleanup
            self.stop_ffmpeg_recording()
            self.stop_xvfb()

        self._log("=" * 50)
        if success:
            self._log("Recording complete!")
        else:
            self._log("Recording failed.")
        self._log("=" * 50)

        return success

    def cancel(self):
        """Cancel the current recording."""
        self._cancelled = True
        if self._wesnoth_process:
            self._terminate_process(self._wesnoth_process, "wesnoth")
        if self._ffmpeg_process:
            self._stop_ffmpeg_recording()
        self.stop_xvfb()

    def get_recording_info(self) -> Dict:
        """Get info about the current/last recording."""
        info = {
            "scenario": self.config.scenario_id,
            "resolution": f"{self.config.resolution[0]}x{self.config.resolution[1]}",
            "fps": self.config.fps,
            "output": self.config.output_path,
        }
        if os.path.isfile(self.config.output_path):
            info["file_size_mb"] = round(
                os.path.getsize(self.config.output_path) / (1024 * 1024), 2
            )
            # Get duration from ffprobe
            ffprobe = shutil.which("ffprobe")
            if ffprobe:
                try:
                    result = subprocess.run(
                        [ffprobe, "-v", "quiet", "-print_format", "json",
                         "-show_format", str(self.config.output_path)],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        duration = float(data.get("format", {}).get("duration", 0))
                        info["duration_seconds"] = round(duration, 1)
                except Exception:
                    pass
        return info

# =========================================================================
# ADDON GENERATOR - WML/Lua output
# =========================================================================

import string



# =============================================================================
# WML GENERATION HELPERS
# =============================================================================

def _wml_indent(level: int) -> str:
    return "    " * level


def _wml_tag(tag: str, attrs: Dict, children: List[str] = None, indent: int = 0) -> str:
    """Generate a WML tag block."""
    ind = _wml_indent(indent)
    lines = [f"{ind}[{tag}]"]
    for k, v in attrs.items():
        lines.append(f"{ind}    {k}={v}")
    if children:
        for child in children:
            if child.strip():
                lines.append(child)
    lines.append(f"{ind}[/{tag}]")
    return "\n".join(lines)


def _wml_value(value) -> str:
    """Format a WML attribute value (strings need no quotes in WML)."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


# =============================================================================
# AI CONFIG GENERATION
# =============================================================================

def generate_ai_config(side_config: SideConfig, indent: int = 2) -> str:
    """Generate [ai] WML block for a side."""
    ind = _wml_indent(indent)
    lines = [f"{ind}[ai]"]

    # AI personality based on scenario config
    aggression = side_config.ai_aggression
    caution = side_config.ai_caution

    # Recruitment ratio
    lines.append(f"{ind}    recruitment_ratio={side_config.ai_recruitment_ratio:.2f}")

    # Aggression and caution
    lines.append(f"{ind}    aggression={aggression:.2f}")
    lines.append(f"{ind}    caution={caution:.2f}")

    # Simple targeting
    lines.append(f"{ind}    [goal]")
    lines.append(f"{ind}        name=target")
    lines.append(f"{ind}        value=target_leader")
    lines.append(f"{ind}    [/goal]")

    # Support villages (grab villages when possible)
    lines.append(f"{ind}    [goal]")
    lines.append(f"{ind}        name=protect_unit")
    lines.append(f"{ind}        value=leader")
    lines.append(f"{ind}    [/goal]")

    # Recruitment pattern
    if side_config.can_recruit:
        lines.append(f"{ind}    [recruitment]")
        for unit_type in side_config.can_recruit[:7]:
            lines.append(f"{ind}        {unit_type}")
        lines.append(f"{ind}    [/recruitment]")

    lines.append(f"{ind}[/ai]")
    return "\n".join(lines)


# =============================================================================
# MAP GENERATION
# =============================================================================

def generate_map_wml(scenario: ScenarioDef) -> str:
    """Generate [map] WML block from scenario map data."""
    lines = ["    [map_data]"]
    for row in scenario.map_data:
        lines.append(f"        {row}")
    lines.append("    [/map_data]")
    return "\n".join(lines)


# =============================================================================
# SIDE GENERATION
# =============================================================================

def generate_side_wml(side: SideConfig, scenario: ScenarioDef) -> str:
    """Generate a complete [side] WML block."""
    lines = ["    [side]"]
    lines.append(f'        side={side.side_number}')
    lines.append(f'        controller={side.controller}')
    lines.append(f'        gold={side.gold}')
    lines.append(f'        income={side.income}')

    if side.color:
        lines.append(f'        team_name={side.color}')
        # Map color names to Wesnoth color IDs
        color_map = {
            "blue": "2", "red": "3", "green": "4",
            "brown": "5", "purple": "6", "teal": "7",
            "orange": "8", "white": "1",
        }
        cid = color_map.get(side.color, "2")
        lines.append(f'        color={cid}')

    # Can recruit
    if side.can_recruit:
        recruit_str = ",".join(side.can_recruit)
        lines.append(f'        recruit={recruit_str}')

    # Use the scenario map for leader placement
    # The leader is already embedded in the map data via "N Kh" notation
    # But we also specify it explicitly for clarity
    if side.leader_type:
        lines.append(f'        type={side.leader_type}')
        lines.append(f'        x={side.leader_x}')
        lines.append(f'        y={side.leader_y}')
        lines.append(f'        canrecruit=yes')
        lines.append(f'        generate_name=yes')

    # Random gender for variety
    lines.append(f'        random_gender=yes')

    # AI configuration
    ai_block = generate_ai_config(side, indent=3)
    lines.append(ai_block)

    # Extra pre-placed units
    for unit in side.extra_units:
        lines.append("        [unit]")
        lines.append(f'            type={unit["type"]}')
        lines.append(f'            x={unit["x"]}')
        lines.append(f'            y={unit["y"]}')
        lines.append(f'            side={side.side_number}')
        lines.append(f'            generate_name=yes')
        lines.append("        [/unit]")

    lines.append("    [/side]")
    return "\n".join(lines)


# =============================================================================
# EVENT GENERATION
# =============================================================================

def generate_events_wml(scenario: ScenarioDef) -> str:
    """Generate WML [event] blocks for the scenario."""
    ev_open = "    " + "[" + "event]"
    ev_close = "    " + "[/event]"
    lua_open = "        " + "[" + "lua]"
    lua_close = "        " + "[/lua]"
    msg_open = "        " + "[" + "message]"
    msg_close = "        " + "[/message]"
    unit_open = "        " + "[" + "unit]"
    unit_close = "        " + "[/unit]"
    filter_open = "        " + "[" + "filter]"
    filter_close = "        " + "[/filter]"
    endlevel_open = "        " + "[" + "endlevel]"
    endlevel_close = "        " + "[/endlevel]"

    lines = []

    # --- START EVENT: Initialize movie system + opening narrative ---
    lines.append("    # Movie system initialization and opening")
    lines.append(ev_open)
    lines.append("        name=start")
    lines.append(lua_open)
    lines.append("            code <<")
    lines.append("            if wesnoth then")
    lines.append("                wesnoth.interface.scroll_to_tile(1, 1, false, 1000)")
    lines.append("                movie.init_zoom()")
    lines.append("                movie.apply_weather()")
    lines.append("            end")
    lines.append("            >>")
    lines.append(lua_close)
    lines.append(ev_close)

    # Opening narrative message
    lines.append("")
    lines.append(ev_open)
    lines.append("        name=start")
    lines.append(msg_open)
    lines.append("            speaker=narrator")
    faction_names = " vs ".join(s.faction for s in scenario.sides)
    narrative = scenario.name + " - " + faction_names
    lines.append('            message="' + narrative + '"')
    lines.append("            duration=3000")
    lines.append(msg_close)
    lines.append(ev_close)

    # --- TURN PACING EVENTS ---
    lines.append("")
    lines.append("    # Camera pacing events")

    # Generate pacing with strategic delays at key turns
    key_turns = set()
    key_turns.add(1)
    key_turns.add(min(5, scenario.turns_to_record))
    key_turns.add(scenario.turns_to_record // 3)
    key_turns.add(scenario.turns_to_record // 2)
    key_turns.add(scenario.turns_to_record - 3)
    key_turns.add(scenario.turns_to_record)

    for turn in range(1, scenario.turns_to_record + 1):
        lines.append(ev_open)
        lines.append("        name=turn " + str(turn))

        if turn in key_turns:
            # Key turn: dramatic camera sweep + delay
            lines.append(lua_open)
            lines.append("            code <<")
            lines.append("            movie.on_turn_start()")
            if turn == 1:
                lines.append("            movie.cinematic_delay(1500)")
            elif turn == scenario.turns_to_record:
                lines.append("            movie.cinematic_delay(1000)")
            else:
                lines.append("            movie.cinematic_delay(800)")
            lines.append("            >>")
            lines.append(lua_close)
        else:
            # Normal turn: brief delay
            lines.append(lua_open)
            lines.append("            code <<")
            lines.append("            movie.on_turn_start()")
            lines.append("            >>")
            lines.append(lua_close)

        lines.append(ev_close)

    # --- VICTORY EVENTS ---
    lines.append("")
    lines.append("    # Victory events")

    for side in scenario.sides:
        faction = side.faction
        victory_msg = "The " + faction + " have won the battle!"

        lines.append(ev_open)
        lines.append("        name=victory")
        lines.append(filter_open)
        lines.append("            side=" + str(side.side_number))
        lines.append("            canrecruit=yes")
        lines.append(filter_close)
        lines.append(msg_open)
        lines.append("            speaker=narrator")
        lines.append('            message="' + victory_msg + '"')
        lines.append("            duration=3000")
        lines.append(msg_close)
        lines.append(endlevel_open)
        lines.append("            result=victory")
        lines.append("            linger_mode=skip")
        lines.append(endlevel_close)
        lines.append(ev_close)

    # --- DEFEAT EVENT ---
    lines.append(ev_open)
    lines.append("        name=defeat")
    lines.append(msg_open)
    lines.append("            speaker=narrator")
    lines.append('            message="Defeat... The battle is lost."')
    lines.append("            duration=3000")
    lines.append(msg_close)
    lines.append(endlevel_open)
    lines.append("            result=defeat")
    lines.append("            linger_mode=skip")
    lines.append(endlevel_close)
    lines.append(ev_close)

    # --- SCENARIO STORY EVENTS ---
    if scenario.turn_events:
        lines.append("")
        lines.append("    # Scenario story events")
        for evt in scenario.turn_events:
            turn = evt.get("turn", 1)
            action = evt.get("action", "")

            lines.append(ev_open)
            lines.append("        name=turn " + str(turn))

            if action == "message":
                text = evt.get("text", "")
                lines.append(msg_open)
                lines.append("            speaker=narrator")
                lines.append('            message="' + text + '"')
                lines.append("            duration=2500")
                lines.append(msg_close)

            elif action == "reinforcements":
                for unit in evt.get("units", []):
                    lines.append(unit_open)
                    lines.append('            type=' + str(unit["type"]))
                    lines.append('            x=' + str(unit["x"]))
                    lines.append('            y=' + str(unit["y"]))
                    lines.append('            side=' + str(evt.get("side", 1)))
                    lines.append("            generate_name=yes")
                    lines.append(unit_close)

            lines.append(ev_close)

    return "\n".join(lines)


def generate_camera_director_lua(scenario: ScenarioDef) -> str:
    """Generate Lua script for cinematic camera control."""
    pacing = scenario.camera_pacing
    zoom = scenario.camera_zoom

    lua = f"""-- =============================================================================
-- AI Movie Renderer — Camera Director
-- Controls camera movement for cinematic recording of AI vs AI battles.
-- Works with the actual Wesnoth game engine (github.com/wesnoth/wesnoth).
-- =============================================================================

local movie = {{}}

-- Configuration
movie.config = {{
    pacing = "{pacing}",
    zoom = {zoom},
    scroll_speed = 500,       -- ms for scroll animation
    turn_delay = 800,         -- ms to pause between turns
    attack_delay = 400,       -- ms to pause on attacks
    move_delay = 200,         -- ms to pause on moves
    record_turns = {scenario.turns_to_record},
    current_turn = 0,
}}

-- Track units for camera following
movie.tracked_units = {{}}

-- Get all units for a given side
function movie.get_units(side)
    local units = {{}}
    for i, u in ipairs(wesnoth.units.get_on_map({{side}})) do
        table.insert(units, u)
    end
    return units
end

-- Find the unit closest to a position
function movie.find_nearest_unit(x, y, side)
    local best = nil
    local best_dist = 999999
    for i, u in ipairs(wesnoth.units.get_on_map({{side}})) do
        local ux, uy = u.x, u.y
        local d = math.abs(ux - x) + math.abs(uy - y)
        if d < best_dist then
            best_dist = d
            best = u
        end
    end
    return best
end

-- Center camera on the middle of the action (supports N sides)
function movie.center_on_action()
    local cx, cy = {scenario.width // 2}, {scenario.height // 2}
    local leaders = {{}}

    -- Collect all leaders from all sides
    for side_num = 1, {len(scenario.sides)} do
        local units = movie.get_units(side_num)
        for _, u in ipairs(units) do
            if u.canrecruit then
                table.insert(leaders, u)
                break
            end
        end
    end

    -- Average position of all leaders
    if #leaders > 0 then
        local sx, sy = 0, 0
        for _, l in ipairs(leaders) do
            sx = sx + l.x
            sy = sy + l.y
        end
        cx = math.floor(sx / #leaders)
        cy = math.floor(sy / #leaders)
    end

    wesnoth.interface.scroll_to_tile(cx, cy, false, movie.config.scroll_speed)
end

-- Pan camera between two points
function movie.pan_camera(x1, y1, x2, y2, duration)
    duration = duration or movie.config.scroll_speed
    wesnoth.interface.scroll_to_tile(x1, y1, false, math.floor(duration / 2))
    wesnoth.interface.scroll_to_tile(x2, y2, false, math.floor(duration / 2))
end

-- Apply weather/ambient effects
function movie.apply_weather()
    local weather = "{scenario.weather.value}"
    if weather == "rain" then
        wesnoth.interface.color_adjust(-20, -20, -10)
    elseif weather == "fog" then
        wesnoth.interface.color_adjust(-10, -10, -5)
    elseif weather == "snow" then
        wesnoth.interface.color_adjust(10, 10, 20)
    elseif weather == "storm" then
        wesnoth.interface.color_adjust(-30, -30, -15)
    end
end

-- Cinematic pacing: delay after each action
function movie.cinematic_delay(ms)
    wesnoth.interface.delay(ms or movie.config.turn_delay, false)
end

-- Called at turn start
function movie.on_turn_start()
    movie.config.current_turn = movie.config.current_turn + 1

    if movie.config.current_turn > movie.config.record_turns then
        -- End the scenario after recording turns
        wesnoth.end_level({{linger_mode = "skip"}})
        return
    end

    -- Apply atmospheric effects
    movie.apply_weather()

    -- Camera strategy based on pacing mode
    if movie.config.pacing == "cinematic" then
        -- Cycle through all sides, then center
        local num_sides = {len(scenario.sides)}
        local mod = movie.config.current_turn % (num_sides + 1)
        if mod < num_sides then
            -- Focus on side (mod + 1) leader
            local side_units = movie.get_units(mod + 1)
            for _, u in ipairs(side_units) do
                if u.canrecruit then
                    wesnoth.interface.scroll_to_tile(u.x, u.y, false, 800)
                    break
                end
            end
            movie.cinematic_delay(600)
        else
            -- Center view
            movie.center_on_action()
            movie.cinematic_delay(400)
        end
    elseif movie.config.pacing == "follow_action" then
        movie.center_on_action()
        movie.cinematic_delay(300)
    else
        -- Fast mode: minimal delays
        movie.cinematic_delay(100)
    end
end

-- Called when a unit is attacked
function movie.on_attack(attacker, defender)
    -- Zoom to combat location
    local cx = math.floor((attacker.x + defender.x) / 2)
    local cy = math.floor((attacker.y + defender.y) / 2)
    wesnoth.interface.scroll_to_tile(cx, cy, false, 200)
    movie.cinematic_delay(movie.config.attack_delay)
end

-- Called when a unit moves
function movie.on_move(unit, from_x, from_y, to_x, to_y)
    if movie.config.pacing == "follow_action" then
        wesnoth.interface.scroll_to_tile(to_x, to_y, false, 150)
    end
end

-- Apply initial zoom
function movie.init_zoom()
    if wesnoth.interface.zoom then
        wesnoth.interface.zoom({zoom}, false)
    end
end

return movie
"""
    return lua


# =============================================================================
# MAIN ADDON CONFIG
# =============================================================================

def generate_main_cfg(scenario_ids: List[str], addon_name: str = "ai_movie_renderer") -> str:
    """Generate the _main.cfg addon manifest."""
    scenario_includes = "\n".join(
        f'#[ifdef {sid}]\n'
        f'    {os.path.join("scenarios", sid + ".cfg")}\n'
        f'#[endif]'
        for sid in scenario_ids
    )

    # Random string for textdomain
    textdomain = addon_name.replace(" ", "_").lower()
    rand_suffix = ''.join(random.choices(string.ascii_lowercase, k=6))
    textdomain = f"{textdomain}-{rand_suffix}"

    cfg = f"""# =============================================================================
# AI Movie Renderer for Battle for Wesnoth — Addon Manifest
# Generates cinematic AI vs AI battles for video recording.
# Uses the actual Wesnoth game engine (github.com/wesnoth/wesnoth).
# =============================================================================

[textdomain]
    name={textdomain}
[/textdomain]

#ifdef MULTIPLAYER
[campaign]
    id={addon_name}
    name=_"AI Movie Renderer"
    abbrev=_"AI Movie"
    icon=_"units/unknown-unit.png~RC(magenta)>150"
    type=multiplayer
    define=AI_MOVIE_RENDERER
    # All scenarios are available as multiplayer scenarios
[/campaign]

# Campaign scenarios
{scenario_includes}

#endif
"""
    return cfg


# =============================================================================
# SCENARIO WML GENERATION
# =============================================================================


def generate_scenario_wml(scenario: ScenarioDef) -> str:
    """Generate a complete scenario .cfg file."""
    OPEN_MP = "[" + "multiplayer]"
    CLOSE_MP = "[" + "/multiplayer]"
    OPEN_SIDE = "    " + "[" + "side]"
    CLOSE_SIDE = "    " + "[" + "/side]"
    OPEN_EVENT = "    " + "[" + "event]"
    CLOSE_EVENT = "    " + "[" + "/event]"
    OPEN_LUA = "        " + "[" + "lua]"
    CLOSE_LUA = "        " + "[" + "/lua]"

    lines = []

    # Header
    lines.append("# " + scenario.name)
    lines.append("# " + scenario.description)
    lines.append("#")
    lines.append("# Map: " + str(scenario.width) + "x" + str(scenario.height))
    lines.append("# Sides: " + str(len(scenario.sides)))
    lines.append("# Max Turns: " + str(scenario.max_turns))
    lines.append("")

    # Time of day
    lines.append("    # Time of day: " + scenario.time_of_day.value)
    lines.append("")

    # Scenario tag
    lines.append(OPEN_MP)
    lines.append("    id=" + scenario.id)
    name_str = "\u201c" + scenario.name + "\u201d"
    lines.append('    name=_"' + scenario.name + '"')
    lines.append("    map_data=")

    # Map data
    for row in scenario.map_data:
        lines.append("        " + row)

    lines.append("    ")
    lines.append("    turns=" + str(scenario.max_turns))
    lines.append("    experience_modifier=70")
    lines.append('    music="' + scenario.music + '"')
    lines.append("    victory_when_enemies_defeated=yes")

    # Sides
    for side in scenario.sides:
        lines.append("")
        side_wml = generate_side_wml(side, scenario)
        lines.append(side_wml)

    # Events
    lines.append("")
    events = generate_events_wml(scenario)
    lines.append(events)

    lines.append(CLOSE_MP)

    return "\n".join(lines)


def _generate_tod_schedule(tod: TimeOfDay) -> str:
    """Generate WML time-of-day schedule."""
    # Default Wesnoth ToD schedule
    schedules = {
        TimeOfDay.DAWN: "dawn_schedule",
        TimeOfDay.MORNING: "morning_schedule",
        TimeOfDay.MIDDAY: "default_schedule",
        TimeOfDay.AFTERNOON: "afternoon_schedule",
        TimeOfDay.DUSK: "dusk_schedule",
        TimeOfDay.FIRST_WATCH: "first_watch_schedule",
        TimeOfDay.SECOND_WATCH: "second_watch_schedule",
        TimeOfDay.DEEP_NIGHT: "deep_night_schedule",
    }

    # Return the standard schedule name — Wesnoth has these built-in
    return f'    # Time of day: {tod.value}'


# =============================================================================
# FULL ADDON GENERATOR
# =============================================================================

class WesnothAddonGenerator:
    """
    Generates a complete Wesnoth addon from ScenarioDef definitions.
    Creates proper WML/Lua files that the actual game engine can load.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.addon_name = self.config.get("addon_name", "ai_movie_renderer")
        self.output_dir = self.config.get("output_dir", "")
        self.selected_scenarios: List[ScenarioDef] = []

    def set_scenarios(self, scenarios: List[ScenarioDef]):
        """Set which scenarios to include in the addon."""
        self.selected_scenarios = scenarios

    def generate(self, output_dir: str = "") -> str:
        """
        Generate the complete addon.
        Returns the path to the generated addon directory.
        """
        if output_dir:
            self.output_dir = output_dir

        if not self.output_dir:
            self.output_dir = os.path.join(
                os.path.expanduser("~/.local/share/wesnoth/data/add-ons"),
                self.addon_name
            )

        addon_dir = Path(self.output_dir)
        addon_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (addon_dir / "scenarios").mkdir(exist_ok=True)
        (addon_dir / "lua").mkdir(exist_ok=True)

        # 1. Generate _main.cfg
        scenario_ids = [s.id for s in self.selected_scenarios]
        main_cfg = generate_main_cfg(scenario_ids, self.addon_name)
        self._write_file(addon_dir / "_main.cfg", main_cfg)

        # 2. Generate each scenario
        for scenario in self.selected_scenarios:
            # Scenario WML
            scenario_wml = generate_scenario_wml(scenario)
            self._write_file(
                addon_dir / "scenarios" / f"{scenario.id}.cfg",
                scenario_wml
            )

            # Camera director Lua for this scenario
            camera_lua = generate_camera_director_lua(scenario)
            self._write_file(
                addon_dir / "lua" / f"{scenario.id}_camera.lua",
                camera_lua
            )

        # 3. Generate a shared movie utilities Lua file
        utils_lua = self._generate_movie_utils()
        self._write_file(addon_dir / "lua" / "movie_utils.lua", utils_lua)

        # 4. Generate AI configuration
        ai_cfg = self._generate_cinematic_ai_cfg()
        self._write_file(addon_dir / "ai" / "cinematic_ai.cfg", ai_cfg)

        return str(addon_dir)

    def generate_single_scenario(self, scenario: ScenarioDef, output_dir: str = "") -> str:
        """Generate addon with just one scenario."""
        self.selected_scenarios = [scenario]
        return self.generate(output_dir)

    def _write_file(self, path: Path, content: str):
        """Write a file, creating parent dirs if needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path), 'w', encoding='utf-8') as f:
            f.write(content)

    def _generate_movie_utils(self) -> str:
        """Generate shared Lua utility functions."""
        return """-- =============================================================================
-- AI Movie Renderer — Shared Utility Functions
-- =============================================================================

local utils = {}

-- Create a delay that can be interrupted
function utils.safe_delay(ms, can_accelerate)
    can_accelerate = can_accelerate or false
    local ok, err = pcall(function()
        if wesnoth and wesnoth.interface then
            wesnoth.interface.delay(ms, can_accelerate)
        end
    end)
    if not ok then
        -- Fallback: just do nothing (game will continue)
    end
end

-- Log a message (visible in Wesnoth's debug log)
function utils.log(msg)
    if wesnoth and wesnoth.log then
        wesnoth.log("info", "AI Movie: " .. tostring(msg))
    end
end

-- Get all living units for a side
function utils.get_side_units(side_num)
    local result = {}
    if wesnoth and wesnoth.units then
        for _, u in ipairs(wesnoth.units.get_on_map({side = side_num})) do
            table.insert(result, u)
        end
    end
    return result
end

-- Find the leader of a side
function utils.find_leader(side_num)
    local units = utils.get_side_units(side_num)
    for _, u in ipairs(units) do
        if u.canrecruit then
            return u
        end
    end
    return nil
end

-- Count units per side
function utils.count_units(side_num)
    return #utils.get_side_units(side_num)
end

-- Get village count for a side
function utils.count_villages(side_num)
    if wesnoth and wesnoth.sides then
        local side = wesnoth.sides[side_num]
        if side and side.village_count then
            return side.village_count
        end
    end
    return 0
end

return utils
"""

    def _generate_cinematic_ai_cfg(self) -> str:
        """Generate cinematic AI configuration file."""
        return """# =============================================================================
# AI Movie Renderer — Cinematic AI Configuration
# Configures both AI sides for entertaining battles (not optimal play).
# =============================================================================

# The AI is configured per-scenario in the scenario WML files.
# This file provides shared AI aspect overrides for cinematic behavior.

#ifdef AI_MOVIE_RENDERER

[ai]
    # Make AI slightly less optimal but more entertaining
    # Don't retreat leaders too far
    [goal]
        name=protect_unit
        value=leader
        value_max=0.6
    [/goal]

    # Prefer attacking over fleeing (more action for the movie)
    caution=0.25
    aggression=0.6

    # Scout aggressively
    [goal]
        name=scout
    [/goal]
[/ai]

#endif
"""


def generate_addon_for_scenario(
    scenario: ScenarioDef,
    output_dir: str = "",
    addon_name: str = "ai_movie_renderer"
) -> str:
    """
    Convenience function: generate a complete addon for a single scenario.
    Returns the output directory path.
    """
    generator = WesnothAddonGenerator({
        "addon_name": addon_name,
        "output_dir": output_dir,
    })
    return generator.generate_single_scenario(scenario)


def generate_addon_for_all_scenarios(output_dir: str = "") -> str:
    """
    Convenience function: generate addon with ALL scenarios.
    """

    generator = WesnothAddonGenerator({
        "addon_name": "ai_movie_renderer",
        "output_dir": output_dir,
    })
    generator.set_scenarios(ALL_SCENARIOS)
    return generator.generate()

# =========================================================================
# RECORD TAB - Scenario browser and recording controls
# =========================================================================



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

# =========================================================================
# BUILDER TAB - Custom scenario builder
# =========================================================================

# scenario_builder functions merged below


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
            MB.critical(self, "Error", f"Failed to build scenario:\n{e}")

    def _on_add_to_list(self):
        if not self._last_scenario:
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
            QMessageBox.warning(self, "Warning", "No addon units discovered yet. Scan addons first!")
            return
        count = len(self._addon_unit_ids)
        self.log_message.emit(
            f"Added {count} addon unit(s) to available pool for Custom Builder.",
            "success",
        )
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
# SCENARIO BUILDER LOGIC (merged from scenario_builder.py)
# =============================================================================

"""
Custom Scenario Builder — Create custom Wesnoth scenarios from the GUI.
Provides faction/unit selection, map template choices, and parameter tuning.
"""




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


# =========================================================================
# MAIN WINDOW
# =========================================================================



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

        # Record tab: scenario browser on top, recording controls + log on bottom
        self.record_panel = RecordPanel()
        self.recording_panel = RecordingPanel()

        rec_layout = QVBoxLayout(tab_record)
        rec_layout.setContentsMargins(0, 0, 0, 0)
        rec_layout.addWidget(self.record_panel, stretch=1)
        rec_layout.addWidget(self.recording_panel)

        # Builder tab
        self.builder_panel = BuilderPanel()
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


# =========================================================================
# ENTRY POINT
# =========================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="WesnothAI - AI Movie Renderer")
    parser.add_argument("--check-deps", action="store_true")
    parser.add_argument("--list-scenarios", action="store_true")
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--generate", type=str, default=None)
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()

    if args.version:
        print("WesnothAI v2.0.0"); return

    if args.check_deps:
        print("=" * 50)
        print("WesnothAI - Dependency Check")
        print("=" * 50)
        deps = WesnothBridge.check_dependencies()
        for n, ok in deps.items():
            print(f"  {'OK' if ok else 'MISSING':>8}  {n}")
        p = WesnothBridge.find_wesnoth()
        print(f"\nWesnoth: {p.wesnoth_binary if p else 'NOT detected'}")
        s = AddonScanner(); d = s.scan()
        print(f"Addons: {len(d)} ({len(s.get_all_units())} units)")
        return

    if args.list_scenarios:
        for i, sc in enumerate(ALL_SCENARIOS, 1):
            f = " vs ".join(side.faction for side in sc.sides)
            print(f"{i}. {sc.name}  ({f})")
        print(f"\nTotal: {len(ALL_SCENARIOS)}")
        return

    if args.generate or args.generate_only:
        scs = [get_scenario_by_id(args.generate)] if args.generate else ALL_SCENARIOS
        scs = [s for s in scs if s]
        g = WesnothAddonGenerator({"addon_name": "ai_movie_renderer", "output_dir": ""})
        g.set_scenarios(scs)
        print(f"Generated: {g.generate()}")
        return

    # GUI launch
    try:
        import ctypes
        try: ctypes.cdll.LoadLibrary("libEGL.so.1")
        except: pass
        app = QApplication(sys.argv)
        app.setStyleSheet(DARK_QSS)
        app.setStyle("Fusion")
        win = WesnothAIRendererApp()
        win.run()
        sys.exit(app.exec())
    except ImportError as e:
        print(f"Error importing GUI modules: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
