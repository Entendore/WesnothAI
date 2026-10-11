"""Record Panel — Scenario browser, details, map preview, and batch queue."""

import os
import sys
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QListWidget, QSplitter, QGroupBox, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

# Ensure parent dir is in path for sibling imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from scenarios import ALL_SCENARIOS, ScenarioDef, get_scenario_categories
from map_preview import MapPreviewLabel


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

from theme import QUALITY_PRESETS, get_preset_menu_items


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