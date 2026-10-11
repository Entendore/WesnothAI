"""
AI Battle Engine — Simulates turn-based Wesnoth combat with AI scene direction.
Generates battle events, manages unit placement, and directs camera for recording.
"""

import math
import random
import colorsys
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum

from npc_database import (
    UnitDef, Attack, AttackType, Alignment, TerrainType,
    DATABASE, get_units_by_faction, get_all_factions, get_faction_color,
)


class EventType(Enum):
    TURN_START = "turn_start"
    MOVE = "move"
    ATTACK = "attack"
    DAMAGE = "damage"
    DEATH = "death"
    HEAL = "heal"
    LEVEL_UP = "level_up"
    RETALIATION = "retaliation"
    MISS = "miss"
    POISON = "poison"
    DRAIN = "drain"
    CAMERA_PAN = "camera_pan"
    ZOOM = "zoom"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"


@dataclass
class BattleEvent:
    event_type: EventType
    turn: int
    unit_name: str = ""
    faction: str = ""
    from_pos: Tuple[int, int] = (0, 0)
    to_pos: Tuple[int, int] = (0, 0)
    damage: int = 0
    hp_remaining: int = 0
    attack_name: str = ""
    attack_type: str = ""
    killed: bool = False
    frame_offset: int = 0  # frames after event start to trigger this
    description: str = ""


@dataclass
class ActiveUnit:
    unit_def: UnitDef
    pos: Tuple[int, int]
    current_hp: int
    team: int  # 0=team_a, 1=team_b
    xp: int = 0
    poisoned: bool = False
    slowed: bool = False
    can_act: bool = True


@dataclass
class BattleState:
    units: List[ActiveUnit] = field(default_factory=list)
    turn: int = 1
    current_team: int = 0
    events: List[BattleEvent] = field(default_factory=list)
    map_width: int = 12
    map_height: int = 10
    map_terrain: List[List[TerrainType]] = field(default_factory=list)
    team_a_name: str = "Loyalists"
    team_b_name: str = "Northerners"


def _hex_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Manhattan-like distance on offset hex grid."""
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return max(dx, dy, dx + dy - max(dx, dy))


def _hex_neighbors(pos: Tuple[int, int], w: int, h: int) -> List[Tuple[int, int]]:
    """Get valid neighboring hex positions."""
    x, y = pos
    neighbors = []
    if y % 2 == 0:
        offsets = [(-1, 0), (1, 0), (0, -1), (-1, -1), (0, 1), (-1, 1)]
    else:
        offsets = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]
    for dx, dy in offsets:
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            neighbors.append((nx, ny))
    return neighbors


def _terrain_defense_bonus(terrain: TerrainType, alignment: Alignment) -> float:
    """Calculate terrain defense bonus (0-40%) based on terrain and time-of-day."""
    defense_map = {
        TerrainType.GRASS: (30, 30, 30),
        TerrainType.FOREST: (60, 40, 40),
        TerrainType.MOUNTAIN: (60, 50, 50),
        TerrainType.HILLS: (50, 40, 40),
        TerrainType.WATER: (20, 20, 20),
        TerrainType.SWAMP: (20, 20, 20),
        TerrainType.SAND: (20, 20, 20),
        TerrainType.CASTLE: (60, 60, 60),
        TerrainType.VILLAGE: (60, 60, 60),
        TerrainType.CAVE: (40, 40, 40),
        TerrainType.SNOW: (30, 30, 30),
        TerrainType.FROZEN: (20, 20, 20),
        TerrainType.DESERT: (20, 20, 20),
    }
    lawful_d, neutral_d, chaotic_d = defense_map.get(terrain, (30, 30, 30))
    if alignment == Alignment.LAWFUL:
        return lawful_d / 100.0
    elif alignment == Alignment.CHAOTIC:
        return chaotic_d / 100.0
    return neutral_d / 100.0


def _time_of_day_modifier(alignment: Alignment, turn: int) -> float:
    """Wesnoth time-of-day damage modifier: lawful good during day, chaotic at night."""
    tod = (turn - 1) % 6
    if tod < 2:  # Dawn
        mod = 1.0
    elif tod < 4:  # Day
        mod = 1.0
    else:  # Night
        mod = 1.0
    # Simplified: lawful +25% day, chaotic +25% night
    if tod < 3:  # Day
        if alignment == Alignment.LAWFUL:
            mod = 1.25
        elif alignment == Alignment.CHAOTIC:
            mod = 0.75
    else:  # Night
        if alignment == Alignment.CHAOTIC:
            mod = 1.25
        elif alignment == Alignment.LAWFUL:
            mod = 0.75
    return mod


def _generate_terrain(w: int, h: int, seed: Optional[int] = None) -> List[List[TerrainType]]:
    """Generate a random terrain map using cellular automata-like approach."""
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    # Start with random terrain
    terrain_types = list(TerrainType)
    grid = [[rng.choice(terrain_types) for _ in range(w)] for _ in range(h)]

    # Smooth with cellular automata (2 passes)
    for _ in range(2):
        new_grid = [row[:] for row in grid]
        for y in range(h):
            for x in range(w):
                counts = {}
                neighbors = _hex_neighbors((x, y), w, h)
                for n in neighbors:
                    t = grid[n[1]][n[0]]
                    counts[t] = counts.get(t, 0) + 1
                current = grid[y][x]
                counts[current] = counts.get(current, 0) + 2
                new_grid[y][x] = max(counts, key=counts.get)
        grid = new_grid

    # Ensure castles at deployment zones
    if h > 2:
        for x in range(max(0, w // 2 - 2), min(w, w // 2 + 3)):
            grid[0][x] = TerrainType.CASTLE
            grid[h - 1][x] = TerrainType.CASTLE

    # Add some villages
    for _ in range(w * h // 10):
        vx, vy = rng.randint(0, w - 1), rng.randint(1, h - 2)
        grid[vy][vx] = TerrainType.VILLAGE

    return grid


class AIBattleEngine:
    """Core AI engine that simulates battles and generates scene events."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.state: Optional[BattleState] = None
        self._rng = random.Random(self.config.get("seed", 42))

    def setup_battle(
        self,
        faction_a: str,
        faction_b: str,
        units_per_side: int = 6,
        map_width: int = 16,
        map_height: int = 12,
        max_turns: int = 20,
        seed: Optional[int] = None,
    ) -> BattleState:
        """Set up a new battle with two factions."""
        if seed is not None:
            self._rng = random.Random(seed)

        terrain = _generate_terrain(map_width, map_height, seed)

        units_a_defs = get_units_by_faction(faction_a)
        units_b_defs = get_units_by_faction(faction_b)

        all_units: List[ActiveUnit] = []

        # Place team A at top of map
        for i in range(units_per_side):
            udef = units_a_defs[i % len(units_a_defs)]
            x = (map_width // 2) - (units_per_side // 2) + i
            y = 1
            x = max(0, min(map_width - 1, x))
            all_units.append(ActiveUnit(
                unit_def=udef, pos=(x, y),
                current_hp=udef.hp, team=0,
            ))

        # Place team B at bottom of map
        for i in range(units_per_side):
            udef = units_b_defs[i % len(units_b_defs)]
            x = (map_width // 2) - (units_per_side // 2) + i
            y = map_height - 2
            x = max(0, min(map_width - 1, x))
            all_units.append(ActiveUnit(
                unit_def=udef, pos=(x, y),
                current_hp=udef.hp, team=1,
            ))

        self.state = BattleState(
            units=all_units,
            turn=1,
            current_team=0,
            map_width=map_width,
            map_height=map_height,
            map_terrain=terrain,
            team_a_name=faction_a,
            team_b_name=faction_b,
        )

        self._max_turns = max_turns
        self._events: List[BattleEvent] = []

        return self.state

    def _find_best_move(self, unit: ActiveUnit, enemies: List[ActiveUnit]) -> Tuple[int, int]:
        """AI: Find optimal hex to move to (closest enemy, prefer good terrain)."""
        best_pos = unit.pos
        best_score = -9999

        # BFS to find reachable positions within movement range
        visited = {unit.pos: 0}
        queue = [unit.pos]

        for _ in range(unit.unit_def.movement * 2):
            if not queue:
                break
            next_queue = []
            for pos in queue:
                for nb in _hex_neighbors(pos, self.state.map_width, self.state.map_height):
                    if nb not in visited:
                        # Check if position is occupied
                        occupied = any(u.pos == nb for u in self.state.units if u.current_hp > 0 and u != unit)
                        if not occupied:
                            visited[nb] = visited[pos] + 1
                            next_queue.append(nb)

                            # Score this position
                            terrain = self.state.map_terrain[nb[1]][nb[0]]
                            defense = _terrain_defense_bonus(terrain, unit.unit_def.alignment)
                            min_enemy_dist = min(_hex_distance(nb, e.pos) for e in enemies) if enemies else 99
                            is_ranged = any(a.range == "ranged" for a in unit.unit_def.attacks)

                            # Melee units want to be adjacent, ranged want 2-3 hex away
                            if is_ranged:
                                dist_score = -abs(min_enemy_dist - 2) * 10
                            else:
                                dist_score = -min_enemy_dist * 8

                            score = defense * 20 + dist_score
                            # Prefer center of map slightly
                            cx, cy = self.state.map_width / 2, self.state.map_height / 2
                            center_dist = math.sqrt((nb[0] - cx) ** 2 + (nb[1] - cy) ** 2)
                            score -= center_dist * 0.5

                            # Slight randomness for variety
                            score += self._rng.gauss(0, 3)

                            if score > best_score:
                                best_score = score
                                best_pos = nb
            queue = next_queue

        return best_pos

    def _resolve_combat(
        self, attacker: ActiveUnit, defender: ActiveUnit
    ) -> List[BattleEvent]:
        """Resolve combat between two units using Wesnoth mechanics."""
        events = []
        terrain = self.state.map_terrain[defender.pos[1]][defender.pos[0]]
        def_defense = _terrain_defense_bonus(terrain, defender.unit_def.alignment)
        tod_mod = _time_of_day_modifier(attacker.unit_def.alignment, self.state.turn)

        for attack in attacker.unit_def.attacks:
            if attack.range == "ranged" and _hex_distance(attacker.pos, defender.pos) > 1:
                pass  # Can use ranged
            elif attack.range == "melee" and _hex_distance(attacker.pos, defender.pos) > 1:
                continue  # Can't reach

            for strike in range(attack.strikes):
                # Hit chance: 60% - defender defense bonus
                hit_chance = 0.60 - def_defense
                hit_chance = max(0.1, min(0.9, hit_chance))

                if self._rng.random() > hit_chance:
                    events.append(BattleEvent(
                        event_type=EventType.MISS, turn=self.state.turn,
                        unit_name=attacker.unit_def.name,
                        faction=attacker.unit_def.faction,
                        from_pos=attacker.pos, to_pos=defender.pos,
                        attack_name=attack.name, attack_type=attack.type.value,
                        frame_offset=len(events) * 8,
                        description=f"{attacker.unit_def.name}'s {attack.name} misses!",
                    ))
                    continue

                # Calculate damage
                base_dmg = attack.damage
                # Terrain resistance for defender
                dmg = max(1, int(base_dmg * tod_mod * (1.0 - def_defense * 0.3)))

                # Apply special abilities
                if attack.special and "charge" in attack.special:
                    dmg = int(dmg * 1.5)

                defender.current_hp -= dmg
                is_killed = defender.current_hp <= 0

                evt_type = EventType.DAMAGE if not is_killed else EventType.DEATH
                events.append(BattleEvent(
                    event_type=evt_type, turn=self.state.turn,
                    unit_name=attacker.unit_def.name,
                    faction=attacker.unit_def.faction,
                    from_pos=attacker.pos, to_pos=defender.pos,
                    damage=dmg, hp_remaining=max(0, defender.current_hp),
                    attack_name=attack.name, attack_type=attack.type.value,
                    killed=is_killed,
                    frame_offset=len(events) * 8,
                    description=f"{attacker.unit_def.name} hits {defender.unit_def.name} for {dmg} damage!",
                ))

                if is_killed:
                    attacker.xp += defender.unit_def.level * 4
                    break

                # Drain
                if attack.special and "drain" in attack.special:
                    heal = dmg // 2
                    attacker.current_hp = min(attacker.unit_def.hp, attacker.current_hp + heal)
                    events.append(BattleEvent(
                        event_type=EventType.DRAIN, turn=self.state.turn,
                        unit_name=attacker.unit_def.name,
                        faction=attacker.unit_def.faction,
                        from_pos=attacker.pos,
                        damage=heal, hp_remaining=attacker.current_hp,
                        frame_offset=len(events) * 8,
                        description=f"{attacker.unit_def.name} drains {heal} HP!",
                    ))

                # Poison
                if attack.special and "poison" in attack.special and not defender.poisoned:
                    if self._rng.random() < 0.4:
                        defender.poisoned = True
                        events.append(BattleEvent(
                            event_type=EventType.POISON, turn=self.state.turn,
                            unit_name=defender.unit_def.name,
                            faction=defender.unit_def.faction,
                            to_pos=defender.pos,
                            frame_offset=len(events) * 8,
                            description=f"{defender.unit_def.name} is poisoned!",
                        ))

                # Retaliation
                if not is_killed and defender.current_hp > 0:
                    atk_terrain = self.state.map_terrain[attacker.pos[1]][attacker.pos[0]]
                    atk_defense = _terrain_defense_bonus(atk_terrain, attacker.unit_def.alignment)
                    def_tod = _time_of_day_modifier(defender.unit_def.alignment, self.state.turn)

                    for ret_attack in defender.unit_def.attacks:
                        if ret_attack.range != attack.range:
                            continue
                        for _ in range(ret_attack.strikes):
                            ret_hit = 0.60 - atk_defense
                            ret_hit = max(0.1, min(0.9, ret_hit))
                            if self._rng.random() > ret_hit:
                                events.append(BattleEvent(
                                    event_type=EventType.MISS, turn=self.state.turn,
                                    unit_name=defender.unit_def.name,
                                    faction=defender.unit_def.faction,
                                    from_pos=defender.pos, to_pos=attacker.pos,
                                    attack_name=ret_attack.name,
                                    attack_type=ret_attack.type.value,
                                    frame_offset=len(events) * 8,
                                    description=f"{defender.unit_def.name} retaliates but misses!",
                                ))
                                continue

                            ret_dmg = max(1, int(ret_attack.damage * def_tod * (1.0 - atk_defense * 0.3)))
                            attacker.current_hp -= ret_dmg
                            ret_killed = attacker.current_hp <= 0

                            events.append(BattleEvent(
                                event_type=EventType.DEATH if ret_killed else EventType.RETALIATION,
                                turn=self.state.turn,
                                unit_name=defender.unit_def.name,
                                faction=defender.unit_def.faction,
                                from_pos=defender.pos, to_pos=attacker.pos,
                                damage=ret_dmg,
                                hp_remaining=max(0, attacker.current_hp),
                                attack_name=f"{ret_attack.name} (retaliation)",
                                attack_type=ret_attack.type.value,
                                killed=ret_killed,
                                frame_offset=len(events) * 8,
                                description=f"{defender.unit_def.name} retaliates for {ret_dmg}!",
                            ))

                            if ret_killed:
                                defender.xp += attacker.unit_def.level * 4
                                break
                        if attacker.current_hp <= 0:
                            break
                    if attacker.current_hp <= 0:
                        break

                if defender.current_hp <= 0 or attacker.current_hp <= 0:
                    break

        return events

    def simulate_full_battle(self) -> List[BattleEvent]:
        """Run the entire battle simulation and return all events."""
        if not self.state:
            raise ValueError("Call setup_battle() first!")

        all_events: List[BattleEvent] = []

        # Fade in at start
        all_events.append(BattleEvent(
            event_type=EventType.FADE_IN, turn=0, frame_offset=0,
            description="Battle begins!",
        ))

        for turn_num in range(1, self._max_turns + 1):
            self.state.turn = turn_num

            # Check win condition
            alive_a = [u for u in self.state.units if u.team == 0 and u.current_hp > 0]
            alive_b = [u for u in self.state.units if u.team == 1 and u.current_hp > 0]
            if not alive_a or not alive_b:
                break

            # Turn start event
            all_events.append(BattleEvent(
                event_type=EventType.TURN_START, turn=turn_num, frame_offset=0,
                description=f"--- Turn {turn_num} ---",
            ))

            for team in [0, 1]:
                self.state.current_team = team
                current_units = [u for u in self.state.units if u.team == team and u.current_hp > 0]
                enemies = [u for u in self.state.units if u.team != team and u.current_hp > 0]

                if not enemies:
                    break

                # Shuffle for variety
                self._rng.shuffle(current_units)

                for unit in current_units:
                    if unit.current_hp <= 0:
                        continue

                    # Poison damage at start of turn
                    if unit.poisoned:
                        poison_dmg = 3
                        unit.current_hp -= poison_dmg
                        all_events.append(BattleEvent(
                            event_type=EventType.POISON, turn=turn_num,
                            unit_name=unit.unit_def.name, faction=unit.unit_def.faction,
                            to_pos=unit.pos, damage=poison_dmg,
                            hp_remaining=unit.current_hp,
                            frame_offset=len(all_events) * 4,
                            description=f"{unit.unit_def.name} takes {poison_dmg} poison damage!",
                        ))
                        if unit.current_hp <= 0:
                            all_events.append(BattleEvent(
                                event_type=EventType.DEATH, turn=turn_num,
                                unit_name=unit.unit_def.name, faction=unit.unit_def.faction,
                                to_pos=unit.pos, killed=True,
                                frame_offset=len(all_events) * 4,
                                description=f"{unit.unit_def.name} dies from poison!",
                            ))
                            continue
                        if self._rng.random() < 0.5:
                            unit.poisoned = False

                    # Move towards best position
                    old_pos = unit.pos
                    new_pos = self._find_best_move(unit, enemies)
                    if new_pos != old_pos:
                        unit.pos = new_pos
                        all_events.append(BattleEvent(
                            event_type=EventType.MOVE, turn=turn_num,
                            unit_name=unit.unit_def.name, faction=unit.unit_def.faction,
                            from_pos=old_pos, to_pos=new_pos,
                            frame_offset=len(all_events) * 4,
                            description=f"{unit.unit_def.name} moves to {new_pos}",
                        ))

                    # Attack if enemy adjacent
                    adj_enemies = [
                        e for e in enemies
                        if e.current_hp > 0 and _hex_distance(unit.pos, e.pos) <= 1
                    ]
                    ranged_enemies = [
                        e for e in enemies
                        if e.current_hp > 0 and _hex_distance(unit.pos, e.pos) <= 3
                    ]

                    if adj_enemies:
                        target = min(adj_enemies, key=lambda e: e.current_hp)
                        combat_events = self._resolve_combat(unit, target)
                        all_events.extend(combat_events)
                    elif ranged_enemies and any(a.range == "ranged" for a in unit.unit_def.attacks):
                        target = min(ranged_enemies, key=lambda e: e.current_hp)
                        combat_events = self._resolve_combat(unit, target)
                        all_events.extend(combat_events)

                    # Village healing
                    terrain = self.state.map_terrain[unit.pos[1]][unit.pos[0]]
                    if terrain == TerrainType.VILLAGE and unit.current_hp < unit.unit_def.hp:
                        heal = min(8, unit.unit_def.hp - unit.current_hp)
                        unit.current_hp += heal
                        all_events.append(BattleEvent(
                            event_type=EventType.HEAL, turn=turn_num,
                            unit_name=unit.unit_def.name, faction=unit.unit_def.faction,
                            to_pos=unit.pos, damage=heal, hp_remaining=unit.current_hp,
                            frame_offset=len(all_events) * 4,
                            description=f"{unit.unit_def.name} heals {heal} HP from village",
                        ))

        # Determine winner
        alive_a = [u for u in self.state.units if u.team == 0 and u.current_hp > 0]
        alive_b = [u for u in self.state.units if u.team == 1 and u.current_hp > 0]
        if alive_a and not alive_b:
            all_events.append(BattleEvent(
                event_type=EventType.FADE_OUT, turn=turn_num,
                description=f"{self.state.team_a_name} wins!",
            ))
        elif alive_b and not alive_a:
            all_events.append(BattleEvent(
                event_type=EventType.FADE_OUT, turn=turn_num,
                description=f"{self.state.team_b_name} wins!",
            ))
        else:
            all_events.append(BattleEvent(
                event_type=EventType.FADE_OUT, turn=turn_num,
                description="Draw - battle ended after max turns",
            ))

        self.state.events = all_events
        return all_events


class AIDirector:
    """AI-powered scene director that generates camera movements and visual cues."""

    def __init__(self, battle_state: BattleState, fps: int = 24):
        self.state = battle_state
        self.fps = fps
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0
        self.target_camera_x = 0.0
        self.target_camera_y = 0.0
        self.target_zoom = 1.0

    def generate_camera_plan(self, events: List[BattleEvent]) -> List[BattleEvent]:
        """Generate camera movement events interleaved with battle events."""
        camera_events = []

        for i, event in enumerate(events):
            if event.event_type in (EventType.TURN_START, EventType.FADE_IN):
                # Pan to center at turn start
                cx = self.state.map_width / 2
                cy = self.state.map_height / 2
                camera_events.append(BattleEvent(
                    event_type=EventType.CAMERA_PAN, turn=event.turn,
                    to_pos=(int(cx), int(cy)),
                    frame_offset=max(0, event.frame_offset - 12),
                    description=f"Camera centers on map",
                ))
            elif event.event_type in (EventType.ATTACK, EventType.DAMAGE, EventType.DEATH):
                # Zoom into combat
                camera_events.append(BattleEvent(
                    event_type=EventType.CAMERA_PAN, turn=event.turn,
                    to_pos=event.to_pos,
                    frame_offset=max(0, event.frame_offset - 6),
                    description=f"Camera focuses on {event.to_pos}",
                ))
                camera_events.append(BattleEvent(
                    event_type=EventType.ZOOM, turn=event.turn,
                    to_pos=(1, 1),  # zoom level encoded in tuple
                    frame_offset=max(0, event.frame_offset - 4),
                    description="Camera zooms in",
                ))

        # Merge and sort by frame_offset
        all_events = events + camera_events
        all_events.sort(key=lambda e: e.frame_offset)
        return all_events

    def get_camera_state(self, event: BattleEvent) -> Tuple[float, float, float]:
        """Get interpolated camera position for a given event."""
        if event.event_type == EventType.CAMERA_PAN:
            self.target_camera_x = event.to_pos[0]
            self.target_camera_y = event.to_pos[1]
        elif event.event_type == EventType.ZOOM:
            self.target_zoom = 1.3 if event.to_pos[0] > 0 else 1.0
        elif event.event_type == EventType.FADE_IN:
            self.zoom = 0.8
            self.target_zoom = 1.0

        # Smooth interpolation
        lerp = 0.15
        self.camera_x += (self.target_camera_x - self.camera_x) * lerp
        self.camera_y += (self.target_camera_y - self.camera_y) * lerp
        self.zoom += (self.target_zoom - self.zoom) * lerp

        return self.camera_x, self.camera_y, self.zoom