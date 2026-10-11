"""Builder Panel — Full-featured custom scenario builder.

Supports: Standard 2-faction, Multi-Faction (3+), Wave Attack, King of the Hill,
specific unit mode, addon unit integration, random matchup generator.
"""

import os
import sys
import random
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSpinBox, QGroupBox, QGridLayout, QLineEdit, QCheckBox, QListWidget,
    QScrollArea, QSplitter,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

# Ensure parent dir is in path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from scenarios import (
    ScenarioDef, SideConfig, FACTION_UNIT_POOLS,
)
# scenario_builder functions merged below
from map_preview import MapPreviewLabel


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
# SCENARIO BUILDER LOGIC (merged from scenario_builder.py)
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
