#!/usr/bin/env python3
"""
WesnothAI - AI Movie Renderer for Battle for Wesnoth
=====================================================
Records AI vs AI battles as MP4 videos.
Uses the actual game engine: github.com/wesnoth/wesnoth

Usage:
    python main.py                  Launch the GUI
    python main.py --check-deps     Check dependencies
    python main.py --list-scenarios List scenarios
    python main.py --generate-only  Generate addon files
"""

import os
import sys
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def check_dependencies():
    print("=" * 50)
    print("WesnothAI - Dependency Check")
    print("=" * 50)
    from wesnoth_bridge import WesnothBridge
    deps = WesnothBridge.check_dependencies()
    for name, ok in deps.items():
        print(f"  {'OK' if ok else 'MISSING':>8}  {name}")
    paths = WesnothBridge.find_wesnoth()
    if paths:
        print(f"\nWesnoth: {paths.wesnoth_binary}")
        if paths.addon_dir:
            print(f"  Addon dir: {paths.addon_dir}")
    else:
        print("\nWesnoth: NOT detected")
    from wesnoth_bridge import AddonScanner
    scanner = AddonScanner()
    d = scanner.scan()
    print(f"Addons: {len(d)} ({len(scanner.get_all_units())} units)")


def list_scenarios():
    from scenarios import ALL_SCENARIOS
    for i, s in enumerate(ALL_SCENARIOS, 1):
        fac = " vs ".join(side.faction for side in s.sides)
        print(f"{i}. {s.name}  ({fac})")
    print(f"\nTotal: {len(ALL_SCENARIOS)}")


def generate_addon(scenario_id=None):
    from scenarios import ALL_SCENARIOS, get_scenario_by_id
    from addon_generator import WesnothAddonGenerator
    scenarios = [get_scenario_by_id(scenario_id)] if scenario_id else ALL_SCENARIOS
    scenarios = [s for s in scenarios if s]
    gen = WesnothAddonGenerator({"addon_name": "ai_movie_renderer", "output_dir": ""})
    gen.set_scenarios(scenarios)
    print(f"Generated: {gen.generate()}")


def main():
    parser = argparse.ArgumentParser(description="WesnothAI")
    parser.add_argument("--check-deps", action="store_true")
    parser.add_argument("--list-scenarios", action="store_true")
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--generate", type=str, default=None)
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()

    if args.version:
        print("WesnothAI v2.0.0"); return
    if args.check_deps:
        check_dependencies(); return
    if args.list_scenarios:
        list_scenarios(); return
    if args.generate or args.generate_only:
        generate_addon(args.generate); return

    # Launch GUI
    try:
        import ctypes
        try:
            ctypes.cdll.LoadLibrary("libEGL.so.1")
        except Exception:
            pass
        from PySide6.QtWidgets import QApplication
        from gui_app import WesnothAIRendererApp, DARK_QSS
        app = QApplication(sys.argv)
        app.setStyleSheet(DARK_QSS)
        app.setStyle("Fusion")
        window = WesnothAIRendererApp()
        window.run()
        sys.exit(app.exec())
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all files are in the same directory:")
        print("  main.py, gui_app.py, scenarios.py, addon_generator.py,")
        print("  wesnoth_bridge.py, video_encoder.py, npc_database.py")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
