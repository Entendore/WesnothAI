"""
Battle for Wesnoth AI Movie Renderer — Scenario Definitions
Defines 8 cinematic scenarios with WML map data, unit compositions, and AI configs.
Uses REAL Wesnoth unit type IDs from the actual game (github.com/wesnoth/wesnoth).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional
import random


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





