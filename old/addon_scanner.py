"""
Addon Scanner for Battle for Wesnoth.

Scans the Wesnoth user addons directory for custom unit types defined in
WML .cfg files, extracting unit IDs, names, factions, and hitpoints so
they can be referenced when building scenarios.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from wesnoth_scanner import WesnothScanner


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

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

    def __init__(self, wesnoth_user_dir: str = "", addon_dirs: List[str] = None):
        """Initialise with an optional custom Wesnoth user directory.

        Args:
            wesnoth_user_dir: If non-empty, use this as the primary user dir
                (backward compatible).  If empty, auto-detect via WesnothScanner.
            addon_dirs: Optional list of explicit addon directory paths to scan.
                If provided, these are scanned IN ADDITION to the auto-detected
                user addons dir.
        """
        self._scanner = WesnothScanner()

        if wesnoth_user_dir:
            self._user_dir: str = os.path.abspath(wesnoth_user_dir)
        else:
            self._user_dir = self._scanner.find_wesnoth_user_dir()

        self._addons_dir: str = os.path.join(self._user_dir, self._ADDONS_RELATIVE)
        self._extra_addon_dirs: List[str] = list(addon_dirs) if addon_dirs else []
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


# ---------------------------------------------------------------------------
# Standalone demo / test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    scanner = AddonScanner()
    print(f"Wesnoth user dir : {scanner._user_dir}")
    print(f"Addons directory : {scanner._addons_dir}")
    print()

    if not os.path.isdir(scanner._addons_dir):
        print("Addons directory does not exist – nothing to scan.")
        print("Install some addons in Wesnoth first, then re-run.")
    else:
        discovered = scanner.scan()
        if not discovered:
            print("No addons found.")
        else:
            print(f"Found {len(discovered)} addon(s):\n")
            for addon in discovered:
                print(f"  [{addon.name}]  ({addon.unit_count} unit type(s))")
                for u in addon.units:
                    print(f"    id={u.unit_id!r}  name={u.name!r}  "
                          f"faction={u.faction!r}  hp={u.hp}")
                print()

            # Demonstrate helper methods
            print(f"Total unit IDs: {scanner.get_unit_ids()}")
            print()
            print("Units by addon:")
            for name, units in scanner.get_units_by_addon().items():
                print(f"  {name}: {[u.unit_id for u in units]}")