"""
Cross-Platform Wesnoth Installation Scanner
=============================================

Comprehensive scanner that locates Battle for Wesnoth installations,
user data directories, game data directories, and addon folders on
Windows, macOS, and Linux.

Detection strategies per platform:

  **Binary (executable):**
    - Linux:  PATH, /usr/bin, /usr/local/bin, /usr/games/bin, /snap/bin,
              /opt, Steam, Flatpak, AppImage
    - macOS:  PATH, /Applications/*.app, Homebrew, MacPorts, Steam,
              /opt/homebrew, Flatpak
    - Windows: PATH, C:\\Program Files*, Steam, GOG, itch.io, Microsoft Store,
               Wesnoth.org installer, portable installs

  **User Data Dir (configs, saves, addons):**
    - Linux:  XDG_DATA_HOME/wesnoth, ~/.local/share/wesnoth, ~/.wesnoth,
              ~/.config/wesnoth, Flatpak sandbox
    - macOS:  ~/Library/Application Support/Wesnoth, ~/.wesnoth
    - Windows: %APPDATA%\\Wesnoth, %USERPROFILE%\\.wesnoth,
               %LOCALAPPDATA%\\Wesnoth

  **Game Data Dir (core units, images, sounds):**
    - Linux:  /usr/share/wesnoth/data, /usr/share/games/wesnoth/data,
              /usr/local/share/wesnoth/data, Steam, Flatpak, Snap
    - macOS:  *.app/Contents/Resources/share/wesnoth/data,
              /usr/local/share/wesnoth/data, Homebrew
    - Windows:  C:\\Program Files*\\Wesnoth\\data, Steam, GOG,
                Microsoft Store, portable installs

  **Addon Dirs (user-installed addons):**
    - Scanned from: user_data_dir/data/add-ons
    - Also checks: game_data_dir/data/add-ons (for packaged/bundled addons)
    - Also checks: directories adjacent to the binary (portable installs)
"""

from __future__ import annotations

import ctypes
import os
import platform
import re
import subprocess
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    scanner = WesnothScanner(log_callback=print)
    print(scanner.get_scan_summary())


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