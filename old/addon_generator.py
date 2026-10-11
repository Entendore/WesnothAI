"""
Wesnoth Addon Generator — Generates real WML/Lua addon files for Battle for Wesnoth.
Creates a complete, installable addon from ScenarioDef definitions.
The addon uses Wesnoth's built-in AI for both sides, with Lua camera control
and timing for cinematic recording via external ffmpeg capture.

Addon structure:
  ai_movie_renderer/
    _main.cfg          — Addon manifest
    scenarios/
      <id>.cfg         — Per-scenario WML (map, sides, events)
    lua/
      camera_director.lua  — Cinematic camera control
      movie_utils.lua      — Utility functions
    ai/
      cinematic_ai.cfg — AI config for both sides
"""

import os
import shutil
import random
import string
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from scenarios import (
    ScenarioDef, SideConfig, FACTION_UNIT_POOLS,
    WeatherType, TimeOfDay,
)


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
    from scenarios import ALL_SCENARIOS

    generator = WesnothAddonGenerator({
        "addon_name": "ai_movie_renderer",
        "output_dir": output_dir,
    })
    generator.set_scenarios(ALL_SCENARIOS)
    return generator.generate()