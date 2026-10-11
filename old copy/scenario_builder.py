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
