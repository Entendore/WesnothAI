"""
AI Movie Renderer for Battle for Wesnoth - PySide6 GUI Application
Features:
  - Hex map preview with terrain legend
  - 8 cinematic scenarios + custom scenario builder
  - Random faction matchup generator
  - Video quality presets (YouTube, Discord, Archive, etc.)
  - Batch recording (record multiple scenarios in sequence)
  - Recording history with video info
  - Real Wesnoth addon generation (WML/Lua)
  - ffmpeg X11 grab recording pipeline
"""

import os
import sys
import time
import json
import threading
import queue
import shutil
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QSlider, QTextEdit, QListWidget, QListWidgetItem, QTabWidget,
    QGroupBox, QLineEdit, QFileDialog, QMessageBox, QScrollArea, QSplitter,
    QStatusBar, QFrame, QSizePolicy,
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QSize, QThread, QMutex, QObject,
)
from PySide6.QtGui import (
    QPixmap, QIcon, QFont, QColor, QPalette, QAction, QKeySequence,
    QIntValidator,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from scenarios import (
    ALL_SCENARIOS, get_scenario_names, get_single_unit_scenarios,
    ScenarioDef, SideConfig, FACTION_UNIT_POOLS,
)
from addon_scanner import AddonScanner, AddonUnit, DiscoveredAddon
from addon_generator import WesnothAddonGenerator
from wesnoth_bridge import WesnothBridge, RecordingConfig, WesnothPaths
from wesnoth_scanner import WesnothScanner, ScanResult, PlatformInfo
from video_encoder import VideoEncoder
from map_preview import render_map_to_pixmap, get_terrain_summary
from scenario_builder import (
    build_custom_scenario, get_random_matchup, get_leader_for_faction,
    get_recruitable_units, get_faction_color, FACTION_INFO, MAP_TEMPLATES,
    build_multi_faction_scenario, build_wave_scenario, build_koth_scenario,
    SIDE_COLORS,
)
from scenarios import get_scenario_categories
from quality_presets import (
    QUALITY_PRESETS, get_preset_by_name, get_preset_menu_items, PRESET_NAMES,
)


# =============================================================================
# DARK THEME QSS
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
# HISTORY TRACKER
# =============================================================================
class RecordingHistory:
    """Tracks completed recordings for the session."""

    def __init__(self, path: str = ""):
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
# LOG SIGNAL HELPER
# =============================================================================
class _LogSignalEmitter(QObject):
    """Emits log lines across thread boundaries via Qt signals."""
    log_line = Signal(str, str)  # (message, tag)


# =============================================================================
# MAP PREVIEW LABEL
# =============================================================================
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
        """Render a WML map to this label."""
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


# =============================================================================
# MAIN APPLICATION
# =============================================================================
class WesnothAIRendererApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.wesnoth_paths: Optional[WesnothPaths] = None
        self._log_queue = queue.Queue()
        self._log_signal = _LogSignalEmitter()
        self._log_signal.log_line.connect(self._append_log_line)
        self._recording_thread: Optional[threading.Thread] = None
        self._is_recording = False
        self._current_bridge: Optional[WesnothBridge] = None
        self._history = RecordingHistory()
        self._custom_scenarios: List[ScenarioDef] = []
        self._last_custom_scenario: Optional[ScenarioDef] = None
        self._current_tab = 0
        self._addon_scanner = AddonScanner()
        self._addon_units: List[AddonUnit] = []
        self._discovered_addons: List[DiscoveredAddon] = []
        self._filtered_scenarios: List = list(ALL_SCENARIOS)

        self.setWindowTitle("AI Movie Renderer - Battle for Wesnoth")
        self.resize(1200, 820)
        self.setMinimumSize(1000, 700)

        self._setup_ui()
        self._setup_timer()

        # Center window
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def run(self):
        self.show()
        QTimer.singleShot(500, self._check_deps_background)

    def _setup_timer(self):
        """Timer to poll the log queue from the main thread."""
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_log_queue)
        self._poll_timer.start(100)

    # =========================================================================
    # UI SETUP
    # =========================================================================

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # Title bar
        self._build_title(main_layout)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_change)
        main_layout.addWidget(self.tabs, stretch=1)

        tab_scenarios = QWidget()
        tab_builder = QWidget()
        tab_batch = QWidget()
        tab_addons = QWidget()
        tab_paths = QWidget()
        self.tabs.addTab(tab_scenarios, "  Scenarios  ")
        self.tabs.addTab(tab_builder, "  Custom Builder  ")
        self.tabs.addTab(tab_batch, "  Batch Record  ")
        self.tabs.addTab(tab_addons, "  Addon Units  ")
        self.tabs.addTab(tab_paths, "  Paths  ")

        self._build_scenarios_tab(tab_scenarios)
        self._build_builder_tab(tab_builder)
        self._build_batch_tab(tab_batch)
        self._build_addon_tab(tab_addons)
        self._build_paths_tab(tab_paths)

        # Bottom: config + log side by side
        bottom_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(bottom_splitter, stretch=1)

        config_widget = QWidget()
        log_widget = QWidget()
        bottom_splitter.addWidget(config_widget)
        bottom_splitter.addWidget(log_widget)
        bottom_splitter.setSizes([500, 500])
        bottom_splitter.setHandleWidth(2)

        self._build_config_panel(config_widget)
        self._build_log_panel(log_widget)

        # Action bar
        self._build_action_bar(main_layout)

    def _build_title(self, layout: QVBoxLayout):
        title_bar = QHBoxLayout()
        layout.addLayout(title_bar)

        title_label = QLabel("AI Movie Renderer")
        title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title_label.setStyleSheet("color: #e94560; background: transparent;")
        title_bar.addWidget(title_label)

        subtitle = QLabel("Battle for Wesnoth | github.com/wesnoth/wesnoth")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #8090a0; background: transparent; margin-left: 15px;")
        title_bar.addWidget(subtitle)
        title_bar.addStretch()

        self.wesnoth_badge = QLabel("Checking...")
        self.wesnoth_badge.setFont(QFont("Segoe UI", 9))
        self.wesnoth_badge.setStyleSheet(
            "background-color: #1e2a4a; color: #8090a0; padding: 2px 8px; border-radius: 3px;"
        )
        title_bar.addWidget(self.wesnoth_badge)

        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.status_label.setStyleSheet("color: #2ecc71; background: transparent; margin-left: 10px;")
        title_bar.addWidget(self.status_label)

    # =========================================================================
    # TAB 1: SCENARIOS
    # =========================================================================

    def _build_scenarios_tab(self, parent: QWidget):
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(5, 5, 5, 5)

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
        self._populate_scenario_list(ALL_SCENARIOS)
        self.scenario_list.setCurrentRow(0)
        left_panel.addWidget(self.scenario_list, stretch=1)
        layout.addLayout(left_panel, stretch=1)

        # Right: details + map
        right = QVBoxLayout()
        layout.addLayout(right, stretch=1)
        right.setSpacing(4)

        # Description
        self.scenario_desc = QTextEdit()
        self.scenario_desc.setReadOnly(True)
        self.scenario_desc.setMaximumHeight(80)
        self.scenario_desc.setStyleSheet(
            "background-color: #1e2a4a; color: #e0e0e0; border: 1px solid #2a3a5c; "
            "border-radius: 3px; font-family: 'Segoe UI'; font-size: 9pt;"
        )
        right.addWidget(self.scenario_desc)

        # Info bar
        info_bar = QHBoxLayout()
        self.scenario_info_label = QLabel("")
        self.scenario_info_label.setFont(QFont("Segoe UI", 9))
        self.scenario_info_label.setStyleSheet("color: #8090a0; background: transparent;")
        info_bar.addWidget(self.scenario_info_label)

        self.scenario_factions_label = QLabel("")
        self.scenario_factions_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.scenario_factions_label.setStyleSheet("color: #e94560; background: transparent;")
        info_bar.addWidget(self.scenario_factions_label)
        right.addLayout(info_bar)

        # Map preview
        map_group = QGroupBox("  Map Preview  ")
        map_layout = QVBoxLayout(map_group)
        self.map_preview = MapPreviewLabel(width=420, height=280)
        map_layout.addWidget(self.map_preview, stretch=1)
        right.addWidget(map_group, stretch=1)

        # Terrain summary
        self.terrain_summary_label = QLabel("")
        self.terrain_summary_label.setFont(QFont("Consolas", 8))
        self.terrain_summary_label.setStyleSheet("color: #8090a0; background: transparent;")
        right.addWidget(self.terrain_summary_label)

        self._on_scenario_select(0)

    def _on_scenario_select(self, row: int):
        if row < 0:
            return
        scenarios = getattr(self, "_filtered_scenarios", ALL_SCENARIOS)
        if row >= len(scenarios):
            return
        scenario = scenarios[row]

        self.scenario_desc.setPlainText(scenario.description)

        factions = " vs ".join(s.faction for s in scenario.sides)
        total_units = sum(len(s.extra_units) + 1 for s in scenario.sides)
        self.scenario_info_label.setText(
            f"Map: {scenario.width}x{scenario.height} | "
            f"Turns: {scenario.turns_to_record}/{scenario.max_turns} | "
            f"Weather: {scenario.weather.value} | Units: {total_units}"
        )
        self.scenario_factions_label.setText(factions)

        self.map_preview.render_map(scenario.map_data)

        summary = get_terrain_summary(scenario.map_data)
        parts = [f"{t}:{c}" for t, c in sorted(summary.items(), key=lambda x: -x[1])[:8]]
        self.terrain_summary_label.setText("Terrain: " + " | ".join(parts))

    def _populate_scenario_list(self, scenarios):
        """Populate the scenario list widget with given scenarios."""
        self.scenario_list.clear()
        self._filtered_scenarios = list(scenarios)
        for s in self._filtered_scenarios:
            prefix = ""
            if len(s.sides) > 2:
                prefix = f"[{len(s.sides)}-Way] "
            elif s.turn_events and any(e.get("action") == "reinforcements" for e in s.turn_events):
                prefix = "[Wave] "
            self.scenario_list.addItem(f"{prefix}{s.name}")
        if self._filtered_scenarios:
            self.scenario_list.setCurrentRow(0)

    def _on_scenario_filter(self, category: str):
        """Filter scenarios by category."""
        cats = get_scenario_categories()
        filtered = cats.get(category, ALL_SCENARIOS)
        self._populate_scenario_list(filtered)

    # =========================================================================
    # TAB 2: CUSTOM BUILDER
    # =========================================================================

    def _build_builder_tab(self, parent: QWidget):
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(5, 5, 5, 5)

        # Left: configuration
        left = QWidget()
        left_layout = QGridLayout(left)
        left_layout.setSpacing(6)
        left_layout.setContentsMargins(0, 0, 10, 0)
        layout.addWidget(left)

        row = 0
        left_layout.addWidget(QLabel("Scenario Name:"), row, 0, Qt.AlignRight)
        self.custom_name_edit = QLineEdit("Custom Battle")
        left_layout.addWidget(self.custom_name_edit, row, 1)

        row += 1
        left_layout.addWidget(QLabel("Side 1 Faction:"), row, 0, Qt.AlignRight)
        self.faction_a_combo = QComboBox()
        self.faction_a_combo.addItems(list(FACTION_INFO.keys()))
        self.faction_a_combo.setCurrentText("Loyalists")
        left_layout.addWidget(self.faction_a_combo, row, 1)

        row += 1
        left_layout.addWidget(QLabel("Side 2 Faction:"), row, 0, Qt.AlignRight)
        self.faction_b_combo = QComboBox()
        self.faction_b_combo.addItems(list(FACTION_INFO.keys()))
        self.faction_b_combo.setCurrentText("Northerners")
        left_layout.addWidget(self.faction_b_combo, row, 1)

        row += 1
        rand_btn = QPushButton("Random Matchup")
        rand_btn.clicked.connect(self._randomize_matchup)
        left_layout.addWidget(rand_btn, row, 1, Qt.AlignLeft)

        row += 1
        left_layout.addWidget(QLabel("Map Template:"), row, 0, Qt.AlignRight)
        self.map_template_combo = QComboBox()
        self.map_template_combo.addItems(list(MAP_TEMPLATES.keys()))
        left_layout.addWidget(self.map_template_combo, row, 1)

        row += 1
        left_layout.addWidget(QLabel("Starting Gold:"), row, 0, Qt.AlignRight)
        self.custom_gold_spin = QSpinBox()
        self.custom_gold_spin.setRange(50, 500)
        self.custom_gold_spin.setSingleStep(25)
        self.custom_gold_spin.setValue(150)
        left_layout.addWidget(self.custom_gold_spin, row, 1, Qt.AlignLeft)

        row += 1
        left_layout.addWidget(QLabel("Units/Side:"), row, 0, Qt.AlignRight)
        self.custom_units_spin = QSpinBox()
        self.custom_units_spin.setRange(2, 12)
        self.custom_units_spin.setValue(4)
        left_layout.addWidget(self.custom_units_spin, row, 1, Qt.AlignLeft)

        row += 1
        left_layout.addWidget(QLabel("Record Turns:"), row, 0, Qt.AlignRight)
        self.custom_turns_spin = QSpinBox()
        self.custom_turns_spin.setRange(5, 60)
        self.custom_turns_spin.setSingleStep(5)
        self.custom_turns_spin.setValue(25)
        left_layout.addWidget(self.custom_turns_spin, row, 1, Qt.AlignLeft)

        row += 1
        left_layout.addWidget(QLabel("Seed:"), row, 0, Qt.AlignRight)
        self.custom_seed_spin = QSpinBox()
        self.custom_seed_spin.setRange(1, 99999)
        self.custom_seed_spin.setValue(42)
        left_layout.addWidget(self.custom_seed_spin, row, 1, Qt.AlignLeft)

        # --- Specific Unit Mode ---
        row += 1
        self.specific_unit_cb = QCheckBox("Use specific unit only (like Vampire Bat)")
        self.specific_unit_cb.setStyleSheet("color: #f39c12; background: transparent;")
        self.specific_unit_cb.setToolTip(
            "When checked, ALL extra units on Side 1 will be the same type.\n"
            "Use this for fun scenarios like 'Vampire Bat Swarm' or 'Troll Rampage'."
        )
        left_layout.addWidget(self.specific_unit_cb, row, 0, 1, 2)

        row += 1
        left_layout.addWidget(QLabel("Unit Type:"), row, 0, Qt.AlignRight)
        specific_unit_row = QHBoxLayout()
        left_layout.addLayout(specific_unit_row, row, 1)
        self.specific_unit_combo = QComboBox()
        self.specific_unit_combo.setEditable(True)
        self.specific_unit_combo.setMinimumWidth(200)
        # Populate with all known units
        all_known_units = set()
        for units in FACTION_UNIT_POOLS.values():
            all_known_units.update(units)
        for uid in sorted(all_known_units):
            self.specific_unit_combo.addItem(uid)
        specific_unit_row.addWidget(self.specific_unit_combo, stretch=1)

        row += 1
        gen_btn = QPushButton("  Generate & Preview  ")
        gen_btn.setProperty("accent", True)
        gen_btn.clicked.connect(self._generate_custom)
        left_layout.addWidget(gen_btn, row, 0, 1, 2)

        row += 1
        add_btn = QPushButton("Add to Scenario List")
        add_btn.clicked.connect(self._add_custom_to_list)
        left_layout.addWidget(add_btn, row, 0, 1, 2)

        # --- Scenario Type ---
        row += 1
        type_label = QLabel("Builder Type:")
        type_label.setStyleSheet("color: #e94560; background: transparent; font-weight: bold; margin-top: 8px;")
        left_layout.addWidget(type_label, row, 0, 1, 2)

        row += 1
        self.builder_type_combo = QComboBox()
        self.builder_type_combo.addItems([
            "Standard (2 Factions)", "Multi-Faction (3+)", "Wave Attack", "King of the Hill",
        ])
        self.builder_type_combo.currentTextChanged.connect(self._on_builder_type_change)
        left_layout.addWidget(self.builder_type_combo, row, 0, 1, 2)

        # --- Multi-faction panel (hidden by default) ---
        row += 1
        self.multi_faction_group = QGroupBox("  Factions  ")
        mf_layout = QVBoxLayout(self.multi_faction_group)
        mf_layout.setSpacing(3)

        self.faction_list_widget = QListWidget()
        self.faction_list_widget.setMaximumHeight(120)
        for fname in list(FACTION_INFO.keys()):
            self.faction_list_widget.addItem(fname)
        # Select first 3 for multi-faction default
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
        mf_row_count_label = QLabel("Selected: 3")
        mf_row_count_label.setStyleSheet("color: #8090a0; background: transparent;")
        self._mf_count_label = mf_row_count_label
        mf_btn_row.addWidget(mf_row_count_label)
        mf_btn_row.addStretch()
        mf_layout.addLayout(mf_btn_row)

        self.multi_faction_group.setVisible(False)
        left_layout.addWidget(self.multi_faction_group, row, 0, 1, 2)

        # --- Wave attack panel (hidden by default) ---
        row += 1
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
        left_layout.addWidget(self.wave_group, row, 0, 1, 2)

        # --- KotH panel (hidden by default) ---
        row += 1
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
        left_layout.addWidget(self.koth_group, row, 0, 1, 2)

        left_layout.setRowStretch(row + 1, 1)

        # Right: preview
        right = QVBoxLayout()
        layout.addLayout(right, stretch=1)

        self.custom_preview_label = QLabel("Build a scenario and click Generate & Preview")
        self.custom_preview_label.setStyleSheet("color: #8090a0; background: transparent;")
        right.addWidget(self.custom_preview_label)

        self.custom_map_preview = MapPreviewLabel(width=500, height=350)
        right.addWidget(self.custom_map_preview, stretch=1)

        self.custom_info_label = QLabel("")
        self.custom_info_label.setFont(QFont("Segoe UI", 9))
        self.custom_info_label.setStyleSheet("color: #8090a0; background: transparent;")
        right.addWidget(self.custom_info_label)

    def _on_builder_type_change(self, btype: str):
        """Show/hide panels based on builder type."""
        is_standard = "Standard" in btype
        is_multi = "Multi-Faction" in btype
        is_wave = "Wave" in btype
        is_koth = "Hill" in btype

        # Hide all special panels
        self.multi_faction_group.setVisible(is_multi)
        self.wave_group.setVisible(is_wave)
        self.koth_group.setVisible(is_koth)

        # Show/hide standard faction selectors
        self.faction_a_combo.setVisible(is_standard or is_wave)
        self.faction_b_combo.setVisible(is_standard or is_wave)

        # Label updates
        if is_wave:
            self.custom_name_edit.setText("Wave Attack")
        elif is_multi:
            self.custom_name_edit.setText("Multi-Faction Battle")
        elif is_koth:
            self.custom_name_edit.setText("King of the Hill")
        else:
            self.custom_name_edit.setText("Custom Battle")

    def _mf_add_faction(self):
        """Select one more faction in the list."""
        current = self.faction_list_widget.count()
        selected = sum(1 for i in range(current) if self.faction_list_widget.item(i).isSelected())
        # Find first unselected
        for i in range(current):
            if not self.faction_list_widget.item(i).isSelected():
                self.faction_list_widget.item(i).setSelected(True)
                selected += 1
                break
        self._mf_count_label.setText(f"Selected: {selected}")

    def _mf_remove_faction(self):
        """Deselect last selected faction."""
        current = self.faction_list_widget.count()
        selected_indices = [i for i in range(current) if self.faction_list_widget.item(i).isSelected()]
        if selected_indices:
            self.faction_list_widget.item(selected_indices[-1]).setSelected(False)
        selected = sum(1 for i in range(current) if self.faction_list_widget.item(i).isSelected())
        self._mf_count_label.setText(f"Selected: {selected}")

    def _get_selected_factions(self):
        """Return list of faction names currently selected in the multi-faction list."""
        factions = []
        for i in range(self.faction_list_widget.count()):
            if self.faction_list_widget.item(i).isSelected():
                factions.append(self.faction_list_widget.item(i).text())
        return factions

    def _randomize_matchup(self):
        import random
        a, b = get_random_matchup()
        self.faction_a_combo.setCurrentText(a)
        self.faction_b_combo.setCurrentText(b)
        self.custom_seed_spin.setValue(random.randint(1, 99999))
        self._log(f"Random matchup: {a} vs {b}")

    def _generate_custom(self):
        try:
            btype = self.builder_type_combo.currentText()
            specific_unit = None
            if self.specific_unit_cb.isChecked():
                specific_unit = self.specific_unit_combo.currentText().strip()
                if not specific_unit:
                    QMessageBox.warning(self, "Warning", "Enter or select a unit type!")
                    return

            name = self.custom_name_edit.text()
            template = self.map_template_combo.currentText()
            seed = self.custom_seed_spin.value()
            turns = self.custom_turns_spin.value()
            ups = self.custom_units_spin.value()

            if "Wave" in btype:
                # Wave attack scenario
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
                    faction_a=self.faction_a_combo.currentText(),
                    faction_b=self.faction_b_combo.currentText(),
                    template=template,
                    gold=self.custom_gold_spin.value(),
                    income=2,
                    max_turns=30,
                    record_turns=turns,
                    units_per_side=ups,
                    seed=seed,
                    specific_unit=specific_unit,
                    addon_units=[u.unit_id for u in self._addon_units],
                )
            self._last_custom_scenario = scenario
            self.custom_map_preview.render_map(scenario.map_data)

            tmpl = MAP_TEMPLATES.get(self.map_template_combo.currentText(), {})
            factions_str = " vs ".join(s.faction for s in scenario.sides)
            extra = ""
            if scenario.turn_events and any(e.get("action") == "reinforcements" for e in scenario.turn_events):
                wave_count = sum(1 for e in scenario.turn_events if e.get("action") == "reinforcements")
                extra = f" | Waves: {wave_count}"
            self.custom_info_label.setText(
                f"Map: {scenario.width}x{scenario.height} | "
                f"Factions ({len(scenario.sides)}): {factions_str} | "
                f"Terrain: {tmpl.get('description', 'N/A')}{extra}"
            )
            self.custom_preview_label.setText(f"'{scenario.name}' generated successfully!")
            self.custom_preview_label.setStyleSheet("color: #2ecc71; background: transparent;")
            self._log(f"Custom scenario generated: {scenario.name} ({scenario.width}x{scenario.height})", "success")
        except Exception as e:
            self._log(f"Error building custom scenario: {e}", "error")
            QMessageBox.critical(self, "Error", f"Failed to build scenario:\n{e}")

    def _add_custom_to_list(self):
        if not self._last_custom_scenario:
            QMessageBox.warning(self, "Warning", "Generate a scenario first!")
            return
        s = self._last_custom_scenario
        self._custom_scenarios.append(s)
        self.scenario_list.addItem(f"[Custom] {s.name}")
        self._log(f"Added custom scenario: {s.name}", "success")
        QMessageBox.information(
            self, "Added",
            f"'{s.name}' added to scenario list.\nSwitch to Scenarios tab to select it."
        )

    # =========================================================================
    # TAB 3: BATCH RECORD
    # =========================================================================

    def _build_batch_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(5, 5, 5, 5)

        hint = QLabel("Select scenarios to record in sequence (from current category filter):")
        hint.setStyleSheet("background: transparent;")
        layout.addWidget(hint)

        # Scroll area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(2)

        self.batch_checkboxes: List[QCheckBox] = []
        all_scenarios_for_batch = ALL_SCENARIOS + self._custom_scenarios
        for i, s in enumerate(all_scenarios_for_batch):
            prefix = "[Custom] " if s in self._custom_scenarios else ""
            cb = QCheckBox(f"{prefix}{s.name} ({s.width}x{s.height}, {s.sides[0].faction} vs {s.sides[1].faction})")
            cb.setChecked(i < 3)
            self.batch_checkboxes.append(cb)
            scroll_layout.addWidget(cb)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, stretch=1)

        # Buttons row
        btn_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in self.batch_checkboxes])
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(lambda: [cb.setChecked(False) for cb in self.batch_checkboxes])
        btn_row.addWidget(select_all_btn)
        btn_row.addWidget(deselect_all_btn)
        btn_row.addStretch()

        self.batch_progress_label = QLabel("")
        self.batch_progress_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.batch_progress_label.setStyleSheet("color: #e94560; background: transparent;")
        btn_row.addWidget(self.batch_progress_label)
        layout.addLayout(btn_row)

        # Output directory
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("Output Directory:"))
        self.batch_dir_edit = QLineEdit()
        dir_row.addWidget(self.batch_dir_edit, stretch=1)
        browse_dir_btn = QPushButton("Browse...")
        browse_dir_btn.clicked.connect(self._browse_batch_dir)
        dir_row.addWidget(browse_dir_btn)
        layout.addLayout(dir_row)

        # Start batch
        self.batch_start_btn = QPushButton("  Start Batch Recording  ")
        self.batch_start_btn.setProperty("accent", True)
        self.batch_start_btn.clicked.connect(self._start_batch_recording)
        layout.addWidget(self.batch_start_btn)

    # =========================================================================
    # TAB 4: ADDON UNITS
    # =========================================================================

    def _build_addon_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(5, 5, 5, 5)

        # Explanation
        hint = QLabel(
            "Scan your Wesnoth addons folder for custom units from downloaded addons. "
            "Discovered units can be used in the Custom Builder tab."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8090a0; background: transparent;")
        layout.addWidget(hint)

        # Scan button row
        scan_row = QHBoxLayout()
        self.scan_addons_btn = QPushButton("  Scan Addons Folder  ")
        self.scan_addons_btn.setProperty("accent", True)
        self.scan_addons_btn.clicked.connect(self._scan_addons)
        scan_row.addWidget(self.scan_addons_btn)

        self.addon_dir_label = QLabel("")
        self.addon_dir_label.setStyleSheet("color: #8090a0; background: transparent; margin-left: 10px;")
        scan_row.addWidget(self.addon_dir_label)
        scan_row.addStretch()
        layout.addLayout(scan_row)

        # Splitter: addon list | unit details
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, stretch=1)

        # Left: addon list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        addon_list_label = QLabel("Discovered Addons:")
        addon_list_label.setStyleSheet("color: #e94560; background: transparent; font-weight: bold;")
        left_layout.addWidget(addon_list_label)
        self.addon_list = QListWidget()
        self.addon_list.currentRowChanged.connect(self._on_addon_select)
        left_layout.addWidget(self.addon_list, stretch=1)
        splitter.addWidget(left)

        # Right: unit list
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        unit_list_label = QLabel("Units in Selected Addon:")
        unit_list_label.setStyleSheet("color: #e94560; background: transparent; font-weight: bold;")
        right_layout.addWidget(unit_list_label)
        self.addon_unit_list = QListWidget()
        right_layout.addWidget(self.addon_unit_list, stretch=1)
        splitter.addWidget(right)
        splitter.setSizes([300, 400])

        # Bottom: action buttons
        bottom_row = QHBoxLayout()
        self.addon_status_label = QLabel("No addons scanned yet.")
        self.addon_status_label.setStyleSheet("color: #8090a0; background: transparent;")
        bottom_row.addWidget(self.addon_status_label)
        bottom_row.addStretch()

        self.use_addon_units_btn = QPushButton("Add All to Custom Builder")
        self.use_addon_units_btn.clicked.connect(self._add_addon_units_to_builder)
        bottom_row.addWidget(self.use_addon_units_btn)
        layout.addLayout(bottom_row)

    def _scan_addons(self):
        """Scan the Wesnoth addons folder for custom units."""
        self.scan_addons_btn.setEnabled(False)
        self.scan_addons_btn.setText("  Scanning...  ")
        self.addon_status_label.setText("Scanning...")

        def scan_worker():
            try:
                self._discovered_addons = self._addon_scanner.scan()
                self._addon_units = self._addon_scanner.get_all_units()
            except Exception as e:
                self._discovered_addons = []
                self._addon_units = []
                self._log(f"Addon scan error: {e}", "error")

            def update_ui():
                self.scan_addons_btn.setEnabled(True)
                self.scan_addons_btn.setText("  Rescan Addons Folder  ")

                # Show user dir and all scanned dirs
                user_dir = AddonScanner.find_wesnoth_user_dir()
                all_dirs = self._addon_scanner.get_scanned_dirs()
                dirs_summary = user_dir
                if len(all_dirs) > 1:
                    dirs_summary += f"  (+{len(all_dirs) - 1} more)"
                self.addon_dir_label.setText(f"Scanning: {dirs_summary}")

                # Populate addon list
                self.addon_list.clear()
                if not self._discovered_addons:
                    self.addon_status_label.setText("No addons with custom units found.")
                    self._log("No addon units found. Install Wesnoth addons to discover custom units.", "warning")
                    return

                total_units = sum(a.unit_count for a in self._discovered_addons)
                self.addon_status_label.setText(
                    f"Found {len(self._discovered_addons)} addon(s) with {total_units} custom unit(s)."
                )
                self._log(
                    f"Addon scan: {len(self._discovered_addons)} addons, "
                    f"{total_units} custom units discovered.",
                    "success",
                )

                for addon in self._discovered_addons:
                    display = f"{addon.name}  ({addon.unit_count} units)"
                    self.addon_list.addItem(display)

                if self._discovered_addons:
                    self.addon_list.setCurrentRow(0)

            QTimer.singleShot(0, update_ui)

        threading.Thread(target=scan_worker, daemon=True).start()

    def _on_addon_select(self, row: int):
        """When an addon is selected, show its units."""
        self.addon_unit_list.clear()
        if row < 0 or row >= len(self._discovered_addons):
            return
        addon = self._discovered_addons[row]
        for unit in addon.units:
            hp_str = f"HP:{unit.hp}" if unit.hp > 0 else ""
            faction_str = f"[{unit.faction}] " if unit.faction else ""
            display = f"{unit.unit_id}  —  {faction_str}{unit.name}  {hp_str}"
            self.addon_unit_list.addItem(display)

    def _add_addon_units_to_builder(self):
        """Add discovered addon unit IDs to the custom builder's available pool."""
        if not self._addon_units:
            QMessageBox.warning(self, "Warning", "No addon units discovered yet. Scan addons first!")
            return

        # Show which units were added
        unit_ids = [u.unit_id for u in self._addon_units]
        count = len(unit_ids)
        self._log(f"Added {count} addon unit(s) to available pool for Custom Builder.", "success")
        self.tabs.setCurrentIndex(1)  # Switch to Custom Builder tab
        QMessageBox.information(
            self, "Units Available",
            f"{count} addon unit(s) are now available in the Custom Builder.\n\n"
            f"Use them in the 'Specific Unit' field when building a scenario."
        )

    # =========================================================================
    # TAB 5: PATHS DISCOVERY
    # =========================================================================

    def _build_paths_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(5, 5, 5, 5)

        # Explanation
        hint = QLabel(
            "Comprehensive scanner for Wesnoth installations, user data, "
            "game data, and addon folders across Windows, macOS, and Linux. "
            "Click 'Full Scan' to discover all paths on your system."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8090a0; background: transparent;")
        layout.addWidget(hint)

        # Scan button row
        scan_row = QHBoxLayout()
        self.paths_scan_btn = QPushButton("  Full Scan  ")
        self.paths_scan_btn.setProperty("accent", True)
        self.paths_scan_btn.clicked.connect(self._full_path_scan)
        scan_row.addWidget(self.paths_scan_btn)

        self.platform_label = QLabel("")
        self.platform_label.setStyleSheet("color: #8090a0; background: transparent; margin-left: 10px;")
        scan_row.addWidget(self.platform_label)
        scan_row.addStretch()

        # Manual addon dir button
        self.add_addon_dir_btn = QPushButton("Add Custom Addon Dir...")
        self.add_addon_dir_btn.clicked.connect(self._add_custom_addon_dir)
        scan_row.addWidget(self.add_addon_dir_btn)
        layout.addLayout(scan_row)

        # Main content: scroll area with results
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(6)

        # --- Platform Info Group ---
        platform_group = QGroupBox("  Platform  ")
        pg_layout = QVBoxLayout(platform_group)
        pg_layout.setSpacing(2)
        self.paths_platform_info = QTextEdit()
        self.paths_platform_info.setReadOnly(True)
        self.paths_platform_info.setMaximumHeight(80)
        self.paths_platform_info.setFont(QFont("Consolas", 9))
        self.paths_platform_info.setStyleSheet(
            "background-color: #1e2a4a; color: #e0e0e0; border: 1px solid #2a3a5c; "
            "border-radius: 3px; font-size: 9pt;"
        )
        pg_layout.addWidget(self.paths_platform_info)
        scroll_layout.addWidget(platform_group)

        # --- Found Installations Group ---
        inst_group = QGroupBox("  Found Installations  ")
        ig_layout = QVBoxLayout(inst_group)
        ig_layout.setSpacing(2)
        self.paths_installations = QTextEdit()
        self.paths_installations.setReadOnly(True)
        self.paths_installations.setFont(QFont("Consolas", 9))
        self.paths_installations.setStyleSheet(
            "background-color: #1e2a4a; color: #e0e0e0; border: 1px solid #2a3a5c; "
            "border-radius: 3px; font-size: 9pt;"
        )
        ig_layout.addWidget(self.paths_installations)
        scroll_layout.addWidget(inst_group)

        # --- User Data Dirs Group ---
        user_group = QGroupBox("  User Data Directories  ")
        ug_layout = QVBoxLayout(user_group)
        ug_layout.setSpacing(2)
        self.paths_user_dirs = QTextEdit()
        self.paths_user_dirs.setReadOnly(True)
        self.paths_user_dirs.setMaximumHeight(160)
        self.paths_user_dirs.setFont(QFont("Consolas", 9))
        self.paths_user_dirs.setStyleSheet(
            "background-color: #1e2a4a; color: #e0e0e0; border: 1px solid #2a3a5c; "
            "border-radius: 3px; font-size: 9pt;"
        )
        ug_layout.addWidget(self.paths_user_dirs)
        scroll_layout.addWidget(user_group)

        # --- Game Data Dirs Group ---
        game_group = QGroupBox("  Game Data Directories  ")
        gg_layout = QVBoxLayout(game_group)
        gg_layout.setSpacing(2)
        self.paths_game_dirs = QTextEdit()
        self.paths_game_dirs.setReadOnly(True)
        self.paths_game_dirs.setMaximumHeight(160)
        self.paths_game_dirs.setFont(QFont("Consolas", 9))
        self.paths_game_dirs.setStyleSheet(
            "background-color: #1e2a4a; color: #e0e0e0; border: 1px solid #2a3a5c; "
            "border-radius: 3px; font-size: 9pt;"
        )
        gg_layout.addWidget(self.paths_game_dirs)
        scroll_layout.addWidget(game_group)

        # --- Addon Dirs Group ---
        addon_group = QGroupBox("  Addon Directories  ")
        ag_layout = QVBoxLayout(addon_group)
        ag_layout.setSpacing(2)
        self.paths_addon_dirs = QTextEdit()
        self.paths_addon_dirs.setReadOnly(True)
        self.paths_addon_dirs.setMaximumHeight(160)
        self.paths_addon_dirs.setFont(QFont("Consolas", 9))
        self.paths_addon_dirs.setStyleSheet(
            "background-color: #1e2a4a; color: #e0e0e0; border: 1px solid #2a3a5c; "
            "border-radius: 3px; font-size: 9pt;"
        )
        ag_layout.addWidget(self.paths_addon_dirs)
        scroll_layout.addWidget(addon_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)

        # Set initial platform info
        scanner = WesnothScanner()
        info = scanner.get_platform_info()
        self.platform_label.setText(
            f"Platform: {info.system} | Home: {info.home}"
            + (" | Flatpak" if info.is_flatpak else "")
            + (" | Snap" if info.is_snap else "")
        )
        self.paths_platform_info.setPlainText(
            f"System:    {info.system}\n"
            f"Home:      {info.home}\n"
            f"Flatpak:   {'Yes' if info.is_flatpak else 'No'}\n"
            f"Snap:      {'Yes' if info.is_snap else 'No'}\n"
            f"Steam Deck: {'Yes' if info.is_steam_deck else 'No'}\n"
        )

    def _full_path_scan(self):
        """Run a comprehensive scan and populate the Paths tab."""
        self.paths_scan_btn.setEnabled(False)
        self.paths_scan_btn.setText("  Scanning...  ")

        def scan_worker():
            scanner = WesnothScanner(log_callback=lambda m: self._log(f"[scan] {m}", "info"))

            # Platform info
            info = scanner.get_platform_info()

            # Find all installations
            installations = scanner.find_all_installations()

            # Find user dirs
            user_dirs = scanner.find_user_dirs()

            # Find game data dirs
            data_dirs = scanner.find_data_dirs()

            # Find addon dirs
            addon_dirs = scanner.find_addon_dirs()

            def update_ui():
                self.paths_scan_btn.setEnabled(True)
                self.paths_scan_btn.setText("  Full Scan  ")

                self.platform_label.setText(
                    f"Platform: {info.system} | Home: {info.home}"
                    + (" | Flatpak" if info.is_flatpak else "")
                    + (" | Snap" if info.is_snap else "")
                )
                self.paths_platform_info.setPlainText(
                    f"System:     {info.system}\n"
                    f"Home:       {info.home}\n"
                    f"Flatpak:    {'Yes' if info.is_flatpak else 'No'}\n"
                    f"Snap:       {'Yes' if info.is_snap else 'No'}\n"
                    f"Steam Deck: {'Yes' if info.is_steam_deck else 'No'}\n"
                )

                # Installations
                if installations:
                    inst_lines = []
                    for i, inst in enumerate(installations, 1):
                        inst_lines.append(f"Installation #{i} ({inst.source}):")
                        inst_lines.append(f"  Binary:   {inst.wesnoth_binary or '(none)'}")
                        inst_lines.append(f"  Version:  {inst.version}")
                        inst_lines.append(f"  User dir: {inst.user_dir or '(unknown)'}")
                        inst_lines.append(f"  Data dir: {inst.data_dir or '(unknown)'}")
                        inst_lines.append(f"  Addon dirs:")
                        for ad in inst.addon_dirs:
                            exists = "EXISTS" if os.path.isdir(ad) else "missing"
                            inst_lines.append(f"    [{exists:>7}] {ad}")
                        inst_lines.append("")
                    self.paths_installations.setPlainText("\n".join(inst_lines))
                else:
                    self.paths_installations.setPlainText(
                        "No Wesnoth installations found.\n\n"
                        "Install options:\n"
                        "  Linux:   sudo apt install wesnoth\n"
                        "           flatpak install flathub org.wesnoth.Wesnoth\n"
                        "  macOS:   brew install wesnoth\n"
                        "           Or download from wesnoth.org\n"
                        "  Windows: Download from wesnoth.org\n"
                        "           Or install via Steam / GOG / Microsoft Store"
                    )

                # User dirs
                user_lines = []
                for source, path in user_dirs:
                    exists = os.path.isdir(path)
                    tag = "OK" if exists else "  "
                    user_lines.append(f"[{tag}] {source}: {path}")
                self.paths_user_dirs.setPlainText("\n".join(user_lines) if user_lines else "None found.")

                # Game data dirs
                game_lines = []
                for source, path in data_dirs:
                    exists = os.path.isdir(path)
                    tag = "OK" if exists else "  "
                    game_lines.append(f"[{tag}] {source}: {path}")
                self.paths_game_dirs.setPlainText("\n".join(game_lines) if game_lines else "None found.")

                # Addon dirs
                addon_lines = []
                for source, path in addon_dirs:
                    exists = os.path.isdir(path)
                    tag = "OK" if exists else "  "
                    addon_lines.append(f"[{tag}] {source}: {path}")
                self.paths_addon_dirs.setPlainText("\n".join(addon_lines) if addon_lines else "None found.")

                # Update the main wesnoth detection if we found one
                if installations:
                    best = installations[0]
                    self.wesnoth_paths = WesnothPaths(
                        wesnoth_binary=best.wesnoth_binary,
                        data_dir=best.data_dir,
                        user_dir=best.user_dir,
                        addon_dir=next((d for d in best.addon_dirs if os.path.isdir(d)), ""),
                    )
                    self.wesnoth_path_edit.setText(best.wesnoth_binary)
                    self.wesnoth_badge.setText(f"Wesnoth {best.version}")
                    self.wesnoth_badge.setStyleSheet(
                        "background-color: #1a3a1a; color: #2ecc71; padding: 2px 8px; border-radius: 3px;"
                    )

                self._log(
                    f"Path scan complete: {len(installations)} installation(s), "
                    f"{sum(1 for _, p in user_dirs if os.path.isdir(p))} user dir(s), "
                    f"{sum(1 for _, p in data_dirs if os.path.isdir(p))} data dir(s), "
                    f"{sum(1 for _, p in addon_dirs if os.path.isdir(p))} addon dir(s).",
                    "success",
                )

            QTimer.singleShot(0, update_ui)

        threading.Thread(target=scan_worker, daemon=True).start()

    def _add_custom_addon_dir(self):
        """Let the user manually add an addon directory to the scanner."""
        d = QFileDialog.getExistingDirectory(self, "Select Addon Directory to Scan")
        if d:
            self._addon_scanner.add_addon_dir(d)
            self._log(f"Added custom addon directory: {d}", "success")
            self._log("Click 'Rescan Addons Folder' in the Addon Units tab to scan it.", "info")
            QMessageBox.information(
                self, "Addon Directory Added",
                f"Added: {d}\n\n"
                f"Go to the 'Addon Units' tab and click 'Rescan Addons Folder' to scan it."
            )

    def _browse_batch_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory for Batch")
        if d:
            self.batch_dir_edit.setText(d)

    def _start_batch_recording(self):
        selected = []
        all_scenarios = ALL_SCENARIOS + self._custom_scenarios
        for i, cb in enumerate(self.batch_checkboxes):
            if cb.isChecked() and i < len(all_scenarios):
                selected.append(all_scenarios[i])

        if not selected:
            QMessageBox.warning(self, "Warning", "No scenarios selected!")
            return

        out_dir = self.batch_dir_edit.text()
        if not out_dir:
            out_dir = os.path.join(os.path.dirname(SCRIPT_DIR), "download", "batch_recordings")
        os.makedirs(out_dir, exist_ok=True)
        self.batch_dir_edit.setText(out_dir)

        wesnoth_bin = self.wesnoth_path_edit.text()
        if not wesnoth_bin:
            QMessageBox.critical(self, "Error", "Wesnoth path not set! Go to Settings.")
            return

        self._is_recording = True
        self.status_label.setText("Batch Recording...")
        self.status_label.setStyleSheet("color: #f39c12; background: transparent;")

        t = threading.Thread(
            target=self._batch_worker, args=(selected, wesnoth_bin, out_dir), daemon=True
        )
        t.start()

    def _batch_worker(self, scenarios, wesnoth_bin, out_dir):
        # Prepend the current filtered category name for context
        total = len(scenarios)
        success_count = 0

        for i, scenario in enumerate(scenarios):
            self._log_signal.log_line.emit(
                f"Recording {i+1}/{total}: {scenario.name}", "info"
            )
            self.batch_progress_label.setText(f"Recording {i+1}/{total}: {scenario.name}")

            output = os.path.join(out_dir, f"{scenario.id}.mp4")
            addon_dir = tempfile.mkdtemp(prefix="wesnoth_batch_")
            try:
                gen = WesnothAddonGenerator({"addon_name": "ai_movie_renderer", "output_dir": addon_dir})
                gen.generate_single_scenario(scenario)

                w, h = map(int, self.resolution_combo.currentText().split("x"))
                config = RecordingConfig(
                    wesnoth_path=wesnoth_bin, scenario_id=scenario.id,
                    addon_path=addon_dir, resolution=(w, h),
                    fps=self.fps_spin.value(), output_path=output,
                    video_crf=self.crf_spin.value(),
                    video_preset=self.preset_combo.currentText(),
                )

                bridge = WesnothBridge(config)
                bridge.set_log_callback(self._on_bridge_log)
                success = bridge.run_recording(self._on_bridge_log)

                if success:
                    success_count += 1
                    info = bridge.get_recording_info()
                    self._history.add(scenario.name, scenario.id, output,
                                       str(info.get("duration_seconds", "")),
                                       str(info.get("file_size_mb", "")))
                    self._log_signal.log_line.emit(
                        f"  Batch [{success_count}/{total}] Done: {scenario.name} -> {output}", "success"
                    )
                else:
                    self._log_signal.log_line.emit(f"  Batch FAILED: {scenario.name}", "error")
            except Exception as e:
                self._log_signal.log_line.emit(f"  Batch ERROR {scenario.name}: {e}", "error")
            finally:
                shutil.rmtree(addon_dir, ignore_errors=True)

        def on_done():
            self._is_recording = False
            self.status_label.setText("Batch Complete!")
            self.status_label.setStyleSheet("color: #2ecc71; background: transparent;")
            self.batch_progress_label.setText(f"Completed: {success_count}/{total}")
            self._log(f"Batch recording complete: {success_count}/{total} succeeded", "success")

        QTimer.singleShot(0, on_done)

    # =========================================================================
    # CONFIG PANEL
    # =========================================================================

    def _build_config_panel(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 5, 0)

        group = QGroupBox("  Settings  ")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(4)

        # Row: Quality preset
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Quality Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(PRESET_NAMES)
        self.preset_combo.setCurrentText("YouTube 720p")
        self.preset_combo.currentTextChanged.connect(self._on_preset_change)
        preset_row.addWidget(self.preset_combo)
        self.preset_desc_label = QLabel("")
        self.preset_desc_label.setFont(QFont("Segoe UI", 8))
        self.preset_desc_label.setStyleSheet("color: #8090a0; background: transparent; margin-left: 5px;")
        preset_row.addWidget(self.preset_desc_label, stretch=1)
        group_layout.addLayout(preset_row)
        self._on_preset_change("YouTube 720p")

        # Row: Wesnoth path
        wesnoth_row = QHBoxLayout()
        wesnoth_row.addWidget(QLabel("Wesnoth:"))
        self.wesnoth_path_edit = QLineEdit("wesnoth")
        wesnoth_row.addWidget(self.wesnoth_path_edit, stretch=1)
        auto_btn = QPushButton("Auto-Detect")
        auto_btn.clicked.connect(self._auto_detect_wesnoth)
        wesnoth_row.addWidget(auto_btn)
        browse_w_btn = QPushButton("Browse...")
        browse_w_btn.clicked.connect(self._browse_wesnoth)
        wesnoth_row.addWidget(browse_w_btn)
        group_layout.addLayout(wesnoth_row)

        # Row: Resolution + FPS + Speed
        res_row = QHBoxLayout()
        res_row.addWidget(QLabel("Resolution:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["1024x576", "1280x720", "1366x768", "1600x900", "1920x1080", "2560x1440"])
        self.resolution_combo.setCurrentText("1280x720")
        res_row.addWidget(self.resolution_combo)

        res_row.addWidget(QLabel("FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(15, 60)
        self.fps_spin.setSingleStep(5)
        self.fps_spin.setValue(30)
        res_row.addWidget(self.fps_spin)

        res_row.addWidget(QLabel("Speed:"))
        self.speed_label = QLabel("1.0x")
        self.speed_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.speed_label.setStyleSheet("color: #e94560; background: transparent;")
        res_row.addWidget(self.speed_label)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(5, 30)  # 0.5 to 3.0, step 0.5
        self.speed_slider.setValue(10)  # 1.0
        self.speed_slider.setFixedWidth(80)
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(f"{v / 10:.1f}x")
        )
        res_row.addWidget(self.speed_slider)
        group_layout.addLayout(res_row)

        # Row: CRF slider
        crf_row = QHBoxLayout()
        crf_row.addWidget(QLabel("CRF:"))
        self.crf_label = QLabel("23")
        self.crf_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.crf_label.setStyleSheet("color: #e94560; background: transparent;")
        crf_row.addWidget(self.crf_label)
        self.crf_slider = QSlider(Qt.Horizontal)
        self.crf_slider.setRange(0, 51)
        self.crf_slider.setValue(23)
        self.crf_slider.setFixedWidth(120)
        self.crf_slider.valueChanged.connect(lambda v: self.crf_label.setText(str(v)))
        crf_row.addWidget(self.crf_slider)
        crf_hint = QLabel("(lower=better)")
        crf_hint.setFont(QFont("Segoe UI", 8))
        crf_hint.setStyleSheet("color: #8090a0; background: transparent; margin-left: 5px;")
        crf_row.addWidget(crf_hint)
        crf_row.addStretch()
        group_layout.addLayout(crf_row)

        # Row: Output path
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output:"))
        self.output_edit = QLineEdit()
        out_row.addWidget(self.output_edit, stretch=1)
        save_btn = QPushButton("Save As...")
        save_btn.clicked.connect(self._browse_output)
        out_row.addWidget(save_btn)
        group_layout.addLayout(out_row)

        # Row: Audio path
        audio_row = QHBoxLayout()
        audio_row.addWidget(QLabel("Music:"))
        self.audio_edit = QLineEdit()
        audio_row.addWidget(self.audio_edit, stretch=1)
        audio_btn = QPushButton("Browse...")
        audio_btn.clicked.connect(self._browse_audio)
        audio_row.addWidget(audio_btn)
        group_layout.addLayout(audio_row)

        # Auto-open checkbox
        self.auto_open_cb = QCheckBox("Open video when done")
        self.auto_open_cb.setChecked(True)
        group_layout.addWidget(self.auto_open_cb)

        layout.addWidget(group)

    def _on_preset_change(self, name: str):
        preset = get_preset_by_name(name)
        self.resolution_combo.setCurrentText(preset.resolution)
        self.fps_spin.setValue(preset.fps)
        self.crf_slider.setValue(preset.crf)
        self.crf_label.setText(str(preset.crf))
        self.preset_desc_label.setText(preset.description)

    # =========================================================================
    # LOG PANEL
    # =========================================================================

    def _build_log_panel(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("  Log  ")
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(5, 14, 5, 5)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        group_layout.addWidget(self.log_text)

        layout.addWidget(group)

        # Show recent history
        history = self._history.get_last(3)
        if history:
            self._log("Recent recordings:")
            for r in reversed(history):
                self._log(f"  [{r['timestamp'][:16]}] {r['scenario_name']} -> {r.get('file_size', '?')} MB")

    # =========================================================================
    # ACTION BAR
    # =========================================================================

    def _build_action_bar(self, parent: QVBoxLayout):
        bar = QHBoxLayout()
        parent.addLayout(bar)

        gen_btn = QPushButton("Generate Addon")
        gen_btn.clicked.connect(self._generate_addon)
        bar.addWidget(gen_btn)

        self.record_btn = QPushButton("  Record Battle  ")
        self.record_btn.setProperty("accent", True)
        self.record_btn.clicked.connect(self._start_recording)
        bar.addWidget(self.record_btn)

        self.stop_btn = QPushButton("  Stop  ")
        self.stop_btn.setProperty("stop", True)
        self.stop_btn.clicked.connect(self._stop_recording)
        self.stop_btn.setVisible(False)
        bar.addWidget(self.stop_btn)

        bar.addStretch()

        self.recording_info_label = QLabel("")
        self.recording_info_label.setFont(QFont("Segoe UI", 9))
        self.recording_info_label.setStyleSheet("color: #8090a0; background: transparent;")
        bar.addWidget(self.recording_info_label)

    # =========================================================================
    # TAB CHANGE
    # =========================================================================

    def _on_tab_change(self, index: int):
        self._current_tab = index

    # =========================================================================
    # DEPENDENCY CHECK
    # =========================================================================

    def _check_deps_background(self):
        def check():
            deps = WesnothBridge.check_dependencies()
            found = WesnothBridge.find_wesnoth()
            QTimer.singleShot(0, lambda: self._update_deps_ui(deps, found))
        threading.Thread(target=check, daemon=True).start()

    def _update_deps_ui(self, deps, wesnoth):
        if wesnoth:
            self.wesnoth_paths = wesnoth
            self.wesnoth_path_edit.setText(wesnoth.wesnoth_binary)
            badge_text = "Wesnoth Found"
            if wesnoth.data_dir:
                self._log(f"  Data dir:  {wesnoth.data_dir}")
            if wesnoth.addon_dir:
                self._log(f"  Addon dir: {wesnoth.addon_dir}")
            self.wesnoth_badge.setText(badge_text)
            self.wesnoth_badge.setStyleSheet(
                "background-color: #1a3a1a; color: #2ecc71; padding: 2px 8px; border-radius: 3px;"
            )
        else:
            self.wesnoth_badge.setText("Wesnoth NOT Found")
            self.wesnoth_badge.setStyleSheet(
                "background-color: #3a1a1a; color: #e74c3c; padding: 2px 8px; border-radius: 3px;"
            )

        self._log("Dependencies:")
        for name, ok in deps.items():
            tag = "success" if ok else "warning"
            self._log(f"  {'OK' if ok else 'MISSING':>8} {name}", tag)

        if not wesnoth:
            self._log("")
            self._log("Wesnoth required for recording. Install:", "error")
            self._log("  sudo apt install wesnoth", "warning")
            self._log("  Or: flatpak install flathub org.wesnoth.Wesnoth", "warning")
            self._log("Addon generation still works without Wesnoth.", "info")

    # =========================================================================
    # FILE BROWSERS
    # =========================================================================

    def _browse_wesnoth(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Wesnoth Binary", "", "")
        if path:
            self.wesnoth_path_edit.setText(path)

    def _auto_detect_wesnoth(self):
        self._log("Searching for Wesnoth...")
        found = WesnothBridge.find_wesnoth()
        if found:
            self.wesnoth_paths = found
            self.wesnoth_path_edit.setText(found.wesnoth_binary)
            self.wesnoth_badge.setText("Wesnoth Found")
            self.wesnoth_badge.setStyleSheet(
                "background-color: #1a3a1a; color: #2ecc71; padding: 2px 8px; border-radius: 3px;"
            )
            self._log(f"Found: {found.wesnoth_binary}", "success")
        else:
            self._log("Wesnoth not found.", "error")

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Video As", "wesnoth_battle.mp4", "MP4 Video (*.mp4);;All Files (*)"
        )
        if path:
            self.output_edit.setText(path)

    def _browse_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Music", "",
            "Audio Files (*.mp3 *.ogg *.wav *.flac);;All Files (*)"
        )
        if path:
            self.audio_edit.setText(path)

    # =========================================================================
    # ADDON GENERATION
    # =========================================================================

    def _generate_addon(self):
        scenario = self._get_selected_scenario()
        if not scenario:
            QMessageBox.critical(self, "Error", "No scenario selected!")
            return

        default_dir = os.path.join(
            os.path.expanduser("~/.local/share/wesnoth/data/add-ons"), "ai_movie_renderer"
        )
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Addon Output Directory", os.path.dirname(default_dir)
        )
        if not output_dir:
            return

        addon_dir = os.path.join(output_dir, "ai_movie_renderer")
        self._log(f"Generating addon: {scenario.name}")
        try:
            gen = WesnothAddonGenerator({"addon_name": "ai_movie_renderer", "output_dir": addon_dir})
            path = gen.generate_single_scenario(scenario)
            self._log(f"Addon generated: {path}", "success")
            self._log("  Copy to: ~/.local/share/wesnoth/data/add-ons/")
            self._log(f"  Run: wesnoth --multiplayer --scenario={scenario.id} "
                      f"--controller=1:ai --controller=2:ai --exit-at-end")
            QMessageBox.information(self, "Success", f"Addon generated to:\n{addon_dir}")
        except Exception as e:
            self._log(f"Error: {e}", "error")
            QMessageBox.critical(self, "Error", str(e))

    def _get_selected_scenario(self) -> Optional[ScenarioDef]:
        row = self.scenario_list.currentRow()
        if row < 0:
            return None

        filtered = getattr(self, "_filtered_scenarios", ALL_SCENARIOS)
        if row < len(filtered):
            return filtered[row]

        # Check custom scenarios
        custom_offset = row - len(filtered)
        if 0 <= custom_offset < len(self._custom_scenarios):
            return self._custom_scenarios[custom_offset]
        return None

    # =========================================================================
    # RECORDING
    # =========================================================================

    def _start_recording(self):
        scenario = self._get_selected_scenario()
        if not scenario:
            QMessageBox.critical(self, "Error", "No scenario selected!")
            return

        wesnoth_bin = self.wesnoth_path_edit.text()
        if not wesnoth_bin or (
            not os.path.isfile(wesnoth_bin) and not wesnoth_bin.startswith("flatpak")
        ):
            QMessageBox.critical(
                self, "Error",
                "Wesnoth not found!\n\nInstall: sudo apt install wesnoth\n"
                "Or: flatpak install flathub org.wesnoth.Wesnoth"
            )
            return

        output = self.output_edit.text()
        if not output:
            download_dir = os.path.join(os.path.dirname(SCRIPT_DIR), "download")
            os.makedirs(download_dir, exist_ok=True)
            output = os.path.join(download_dir, f"{scenario.id}.mp4")
            self.output_edit.setText(output)

        try:
            w, h = map(int, self.resolution_combo.currentText().split("x"))
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid resolution!")
            return

        addon_dir = tempfile.mkdtemp(prefix="wesnoth_addon_")
        self._log(f"Recording: {scenario.name} ({w}x{h} @ {self.fps_spin.value()}fps)")

        try:
            gen = WesnothAddonGenerator({"addon_name": "ai_movie_renderer", "output_dir": addon_dir})
            gen.generate_single_scenario(scenario)
        except Exception as e:
            self._log(f"Addon generation failed: {e}", "error")
            QMessageBox.critical(self, "Error", str(e))
            return

        config = RecordingConfig(
            wesnoth_path=wesnoth_bin, scenario_id=scenario.id,
            addon_path=addon_dir, resolution=(w, h),
            fps=self.fps_spin.value(), output_path=output,
            video_crf=self.crf_slider.value(),
            video_preset=self.preset_combo.currentText(),
            game_speed=self.speed_slider.value() / 10.0,
            audio_file=self.audio_edit.text(),
        )

        self._is_recording = True
        self.status_label.setText("Recording...")
        self.status_label.setStyleSheet("color: #f39c12; background: transparent;")
        self.record_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        self.recording_info_label.setText("Starting...")

        self._current_bridge = WesnothBridge(config)
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
                self.stop_btn.setVisible(False)
                self.record_btn.setVisible(True)
                self._current_bridge = None

                if success:
                    self.status_label.setText("Complete!")
                    self.status_label.setStyleSheet("color: #2ecc71; background: transparent;")
                    info = bridge.get_recording_info()
                    dur = info.get("duration_seconds", "?")
                    size = info.get("file_size_mb", "?")
                    self.recording_info_label.setText(f"{dur}s | {size} MB")
                    self._log(f"Video saved: {info['output']}", "success")
                    self._history.add(
                        scenario.name, scenario.id, info["output"],
                        str(dur), str(size),
                    )

                    if self.auto_open_cb.isChecked() and os.path.isfile(info["output"]):
                        try:
                            subprocess.Popen(
                                ["xdg-open", info["output"]],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            )
                        except Exception:
                            pass
                else:
                    self.status_label.setText("Failed")
                    self.status_label.setStyleSheet("color: #e74c3c; background: transparent;")
                    self.recording_info_label.setText("Failed - check log")
                    self._log("Recording failed.", "error")

                shutil.rmtree(addon_dir, ignore_errors=True)

            QTimer.singleShot(0, on_done)
        except Exception as e:
            self._log(f"Recording error: {e}", "error")
            QTimer.singleShot(0, lambda: self.status_label.setText("Error"))

    def _stop_recording(self):
        if self._current_bridge:
            self._current_bridge.cancel()
        self._is_recording = False
        self.status_label.setText("Stopping...")
        self.status_label.setStyleSheet("color: #f39c12; background: transparent;")

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
                elif any(w in msg.lower() for w in ["ok", "success", "complete", "saved"]):
                    tag = "success"
                self._log(msg, tag)
        except queue.Empty:
            pass

    TAG_COLORS = {
        "error": "#e74c3c",
        "success": "#2ecc71",
        "warning": "#f39c12",
        "info": "#e0e0e0",
    }

    def _append_log_line(self, msg: str, tag: str):
        """Slot called from the signal to append to the log safely."""
        color = self.TAG_COLORS.get(tag, "#e0e0e0")
        self.log_text.append(f'<span style="color:{color}">{msg}</span>')

    def _log(self, msg: str, tag: str = "info"):
        if not hasattr(self, "log_text"):
            return
        color = self.TAG_COLORS.get(tag, "#e0e0e0")
        self.log_text.append(f'<span style="color:{color}">{msg}</span>')

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


# =============================================================================
# ENTRY POINT
# =============================================================================
def main():
    # Preload EGL if needed (some systems lack it)
    import ctypes
    try:
        ctypes.cdll.LoadLibrary(
            "/home/z/.cache/ms-playwright/chromium-1228/chrome-linux64/libEGL.so"
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    app.setStyle("Fusion")

    window = WesnothAIRendererApp()
    window.run()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()