#!/usr/bin/env python3
"""
AI Movie Renderer for Battle for Wesnoth
=========================================
A real Wesnoth addon that uses the actual game engine
(github.com/wesnoth/wesnoth) to record AI vs AI battles
featuring all NPCs and export them as MP4 videos.

Workflow:
  1. Select a scenario (8 cinematic battle scenarios)
  2. Configure recording (resolution, quality, FPS)
  3. App generates WML/Lua addon files
  4. Launches Wesnoth on Xvfb with both sides AI
  5. ffmpeg captures the X11 display as MP4

Usage:
    python main.py                  # Launch the GUI
    python main.py --generate-only   # Generate addon without GUI
    python main.py --list-scenarios  # List all scenarios
    python main.py --check-deps      # Check system dependencies
    python main.py --generate-all    # Generate ALL scenarios as addon
"""

import os
import sys
import argparse
import importlib.util
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)


def check_dependencies():
    """Check and report system dependencies."""
    print("=" * 60)
    print("AI Movie Renderer for Battle for Wesnoth")
    print("Using actual game: github.com/wesnoth/wesnoth")
    print("=" * 60)
    print()

    # Python packages
    py_deps = {
        "Python 3": (sys.version_info >= (3, 8), sys.version.split()[0]),
        "Pillow (PIL)": (importlib.util.find_spec("PIL") is not None,
                         "pip install Pillow"),
        "PySide6": (importlib.util.find_spec("PySide6") is not None,
                    "pip install PySide6"),
    }

    # System tools
    sys_deps = {
        "Wesnoth": ("wesnoth", "https://github.com/wesnoth/wesnoth"),
        "FFmpeg": ("ffmpeg", "sudo apt install ffmpeg"),
        "Xvfb": ("Xvfb", "sudo apt install xvfb  (for headless recording)"),
    }

    all_ok = True

    print("Python Dependencies:")
    for name, (found, info) in py_deps.items():
        status = "OK" if found else "MISSING"
        required = " REQUIRED" if name in ("Pillow (PIL)", "PySide6") else ""
        print(f"  [{status:>8}]  {name:<25} {info}{required}")
        if not found and "REQUIRED" in required:
            all_ok = False

    print()
    print("System Tools:")
    for name, (cmd, install_hint) in sys_deps.items():
        found = shutil.which(cmd) is not None
        # Special: check flatpak for Wesnoth
        if name == "Wesnoth" and not found:
            flatpak = shutil.which("flatpak")
            if flatpak:
                try:
                    result = __import__('subprocess').run(
                        ["flatpak", "list", "--app", "--columns=application"],
                        capture_output=True, text=True, timeout=10
                    )
                    if "wesnoth" in result.stdout.lower():
                        found = True
                        cmd = "flatpak run org.wesnoth.Wesnoth"
                except Exception:
                    pass

        status = "OK" if found else "MISSING"
        required = " REQUIRED" if name in ("Wesnoth", "FFmpeg") else " (optional)"
        print(f"  [{status:>8}]  {name:<25} {cmd if found else install_hint}{required}")
        if not found and "REQUIRED" in required:
            all_ok = False

    print()

    # Check for Wesnoth user dir
    from wesnoth_bridge import WesnothBridge
    wesnoth = WesnothBridge.find_wesnoth()
    if wesnoth:
        print(f"Wesnoth detected: {wesnoth.wesnoth_binary}")
        print(f"  User dir:   {wesnoth.user_dir}")
        print(f"  Data dir:   {wesnoth.data_dir or '(not found)'}")
        print(f"  Addon dir:  {wesnoth.addon_dir}")
    else:
        print("Wesnoth: NOT detected")
        print("  The app will still work for addon generation.")
        print("  Install Wesnoth to record videos.")

    # Show all candidate paths
    from wesnoth_scanner import WesnothScanner
    scanner = WesnothScanner()
    user_dirs = scanner.find_user_dirs()
    data_dirs = scanner.find_data_dirs()
    addon_dirs = scanner.find_addon_dirs()

    existing_user = [p for _, p in user_dirs if os.path.isdir(p)]
    existing_data = [p for _, p in data_dirs if os.path.isdir(p)]
    existing_addon = [p for _, p in addon_dirs if os.path.isdir(p)]

    print()
    if existing_user:
        print(f"User data dirs found: {len(existing_user)}")
        for p in existing_user:
            print(f"  {p}")
    if existing_data:
        print(f"Game data dirs found: {len(existing_data)}")
        for p in existing_data:
            print(f"  {p}")
    if existing_addon:
        print(f"Addon dirs found: {len(existing_addon)}")
        for p in existing_addon:
            print(f"  {p}")

    print()
    if all_ok:
        print("All required dependencies available. Run 'python main.py' to start.")
    else:
        print("Some required dependencies are missing.")
        print()
        print("Quick install (Debian/Ubuntu):")
        print("  sudo apt install wesnoth ffmpeg xvfb python3-pil")
        print("  pip install PySide6")
        print()
        print("Quick install (Flatpak):")
        print("  flatpak install flathub org.wesnoth.Wesnoth")
        print("  sudo apt install ffmpeg xvfb python3-pil")
        print("  pip install PySide6")

    return all_ok


def list_scenarios():
    """List all available scenarios."""
    from scenarios import ALL_SCENARIOS

    print("=" * 60)
    print("AI Movie Renderer — Battle Scenarios")
    print("=" * 60)
    print()

    for i, s in enumerate(ALL_SCENARIOS, 1):
        factions = " vs ".join(side.faction for side in s.sides)
        print(f"{i}. {s.name}")
        print(f"   ID: {s.id}")
        print(f"   Map: {s.width}x{s.height} | Turns: {s.turns_to_record}/{s.max_turns}")
        print(f"   Factions: {factions}")
        print(f"   Weather: {s.weather.value} | Camera: {s.camera_pacing}")
        print(f"   {s.description[:120]}...")
        print()

    print(f"Total: {len(ALL_SCENARIOS)} scenarios")


def generate_addon(scenario_id: str = None, output_dir: str = ""):
    """Generate addon file(s)."""
    from scenarios import ALL_SCENARIOS, get_scenario_by_id
    from addon_generator import WesnothAddonGenerator

    if scenario_id:
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            print(f"Scenario '{scenario_id}' not found!")
            return
        scenarios = [scenario]
    else:
        scenarios = ALL_SCENARIOS

    print(f"Generating addon for {len(scenarios)} scenario(s)...")

    generator = WesnothAddonGenerator({
        "addon_name": "ai_movie_renderer",
        "output_dir": output_dir or "",
    })
    generator.set_scenarios(scenarios)
    path = generator.generate()

    print(f"Addon generated to: {path}")
    print()
    print("Directory structure:")
    for root, dirs, files in os.walk(path):
        level = root.replace(path, "").count(os.sep)
        indent = "  " * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = "  " * (level + 1)
        for file in files:
            size = os.path.getsize(os.path.join(root, file))
            print(f"{sub_indent}{file} ({size} bytes)")

    print()
    print("To use:")
    wesnoth_user_dir = os.path.expanduser("~/.local/share/wesnoth")
    addon_dest = os.path.join(wesnoth_user_dir, "data", "add-ons", "ai_movie_renderer")
    print(f"  1. Copy '{path}' to:")
    print(f"     {addon_dest}")
    print(f"  2. Launch Wesnoth and select the scenario from Multiplayer")
    print(f"  3. Or run from command line:")
    for s in scenarios:
        print(f"     wesnoth --multiplayer --scenario={s.id} "
              f"--controller=1:ai --controller=2:ai --exit-at-end")


def main():
    parser = argparse.ArgumentParser(
        description="AI Movie Renderer for Battle for Wesnoth",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                   Launch the GUI application
  python main.py --check-deps      Check system dependencies
  python main.py --list-scenarios  List all battle scenarios
  python main.py --generate-only   Generate addon (all scenarios)
  python main.py --generate classic_battlefield
                                 Generate addon for one scenario
        """,
    )
    parser.add_argument("--check-deps", action="store_true",
                        help="Check system dependencies")
    parser.add_argument("--list-scenarios", action="store_true",
                        help="List all battle scenarios")
    parser.add_argument("--generate-only", action="store_true",
                        help="Generate addon without GUI (all scenarios)")
    parser.add_argument("--generate", type=str, default=None,
                        metavar="SCENARIO_ID",
                        help="Generate addon for a specific scenario")
    parser.add_argument("--output-dir", type=str, default="",
                        help="Output directory for generated addon")
    parser.add_argument("--version", action="store_true",
                        help="Show version info")

    args = parser.parse_args()

    if args.version:
        print("AI Movie Renderer for Battle for Wesnoth v2.0.0")
        print("Using actual game engine: github.com/wesnoth/wesnoth")
        return

    if args.check_deps:
        check_dependencies()
        return

    if args.list_scenarios:
        list_scenarios()
        return

    if args.generate:
        generate_addon(args.generate, args.output_dir)
        return

    if args.generate_only:
        generate_addon(None, args.output_dir)
        return

    # Launch GUI
    try:
        from gui_app import WesnothAIRendererApp
        app = WesnothAIRendererApp()
        app.run()
        # run() calls show() and starts the Qt event loop via sys.exit(app.exec())
    except ImportError as e:
        print(f"Error importing GUI modules: {e}")
        print("Make sure all files are in the same directory:")
        print("  main.py, gui_app.py, scenarios.py, addon_generator.py,")
        print("  wesnoth_bridge.py, video_encoder.py, npc_database.py")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()