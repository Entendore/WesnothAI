"""
Battle for Wesnoth — Complete NPC Unit Database
All factions, all unit types with stats, abilities, and pixel-art color profiles.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
import random


class TerrainType(Enum):
    GRASS = "grass"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    HILLS = "hills"
    WATER = "water"
    SWAMP = "swamp"
    SAND = "sand"
    CASTLE = "castle"
    VILLAGE = "village"
    CAVE = "cave"
    SNOW = "snow"
    FROZEN = "frozen"
    DESERT = "desert"


class AttackType(Enum):
    BLADE = "blade"
    PIERCE = "pierce"
    IMPACT = "impact"
    FIRE = "fire"
    COLD = "cold"
    ARCANE = "arcane"
    LIGHTNING = "lightning"


class Alignment(Enum):
    LAWFUL = "lawful"
    NEUTRAL = "neutral"
    CHAOTIC = "chaotic"
    LIMINAL = "liminal"


@dataclass
class Attack:
    name: str
    type: AttackType
    damage: int
    strikes: int
    range: str  # "melee" or "ranged"
    special: Optional[str] = None


@dataclass
class UnitDef:
    id: str
    name: str
    race: str
    faction: str
    level: int
    hp: int
    cost: int
    movement: int
    vision: int
    alignment: Alignment
    attacks: List[Attack]
    advances_to: List[str] = field(default_factory=list)
    # Visual profile for pixel-art rendering
    primary_color: str = "#FFFFFF"
    secondary_color: str = "#808080"
    accent_color: str = "#404040"
    body_type: str = "humanoid"  # humanoid, beast, flying, undead, aquatic
    has_cape: bool = False
    has_wings: bool = False
    has_helm: bool = False
    has_shield: bool = False
    has_staff: bool = False
    has_bow: bool = False
    size: int = 1  # 1=normal, 2=large


# ============================================================
# FACTION DEFINITIONS — All NPCs organized by faction
# ============================================================

def _build_database() -> Dict[str, UnitDef]:
    db = {}

    # ===================== LOYALISTS =====================
    db["Fencer"] = UnitDef(
        id="Fencer", name="Fencer", race="human", faction="Loyalists",
        level=1, hp=28, cost=14, movement=6, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Sword", AttackType.BLADE, 5, 3, "melee")],
        advances_to=["Fencer II", "Master at Arms"],
        primary_color="#3366CC", secondary_color="#CC3333", accent_color="#DAA520",
        body_type="humanoid", has_helm=True,
    )
    db["Fencer II"] = UnitDef(
        id="Fencer_II", name="Fencer", race="human", faction="Loyalists",
        level=2, hp=36, cost=22, movement=6, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 7, 4, "melee"),
            Attack("Crossbow", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        advances_to=["Master at Arms"],
        primary_color="#3366CC", secondary_color="#CC3333", accent_color="#FFD700",
        body_type="humanoid", has_helm=True,
    )
    db["Master at Arms"] = UnitDef(
        id="Master_at_Arms", name="Master at Arms", race="human", faction="Loyalists",
        level=3, hp=44, cost=36, movement=6, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 9, 4, "melee", "firststrike"),
            Attack("Crossbow", AttackType.PIERCE, 6, 3, "ranged"),
        ],
        primary_color="#2850A8", secondary_color="#B22222", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_cape=True,
    )
    db["Heavy Infantryman"] = UnitDef(
        id="Heavy_Infantryman", name="Heavy Infantryman", race="human", faction="Loyalists",
        level=1, hp=40, cost=19, movement=4, vision=3,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Mace", AttackType.IMPACT, 8, 2, "melee")],
        advances_to=["Infantry General", "Shock Trooper"],
        primary_color="#555555", secondary_color="#888888", accent_color="#3366CC",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Infantry General"] = UnitDef(
        id="Infantry_General", name="Infantry General", race="human", faction="Loyalists",
        level=2, hp=52, cost=30, movement=4, vision=3,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Mace", AttackType.IMPACT, 10, 3, "melee"),
            Attack("Javelin", AttackType.PIERCE, 7, 2, "ranged"),
        ],
        advances_to=["Grand Marshal"],
        primary_color="#444444", secondary_color="#777777", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Shock Trooper"] = UnitDef(
        id="Shock_Trooper", name="Shock Trooper", race="human", faction="Loyalists",
        level=2, hp=48, cost=30, movement=5, vision=3,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Mace", AttackType.IMPACT, 11, 3, "melee")],
        primary_color="#666666", secondary_color="#999999", accent_color="#CC3333",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Grand Marshal"] = UnitDef(
        id="Grand_Marshal", name="Grand Marshal", race="human", faction="Loyalists",
        level=3, hp=60, cost=50, movement=5, vision=3,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Mace", AttackType.IMPACT, 12, 3, "melee", "charge"),
            Attack("Javelin", AttackType.PIERCE, 8, 3, "ranged"),
        ],
        primary_color="#333333", secondary_color="#666666", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Spearman"] = UnitDef(
        id="Spearman", name="Spearman", race="human", faction="Loyalists",
        level=1, hp=28, cost=14, movement=5, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Spear", AttackType.PIERCE, 5, 3, "melee")],
        advances_to=["Pikeman", "Javelineer"],
        primary_color="#339966", secondary_color="#CC3333", accent_color="#DAA520",
        body_type="humanoid", has_helm=True,
    )
    db["Pikeman"] = UnitDef(
        id="Pikeman", name="Pikeman", race="human", faction="Loyalists",
        level=2, hp=38, cost=23, movement=5, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Pike", AttackType.PIERCE, 8, 3, "melee")],
        advances_to=["Halberdier"],
        primary_color="#228B22", secondary_color="#B22222", accent_color="#DAA520",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Halberdier"] = UnitDef(
        id="Halberdier", name="Halberdier", race="human", faction="Loyalists",
        level=3, hp=50, cost=40, movement=5, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Halberd", AttackType.BLADE, 10, 3, "melee", "charge")],
        primary_color="#006400", secondary_color="#8B0000", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Javelineer"] = UnitDef(
        id="Javelineer", name="Javelineer", race="human", faction="Loyalists",
        level=2, hp=30, cost=22, movement=5, vision=5,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Spear", AttackType.PIERCE, 6, 2, "melee"),
            Attack("Javelin", AttackType.PIERCE, 7, 2, "ranged"),
        ],
        primary_color="#339966", secondary_color="#CC6633", accent_color="#DAA520",
        body_type="humanoid", has_helm=True,
    )
    db["Bowman"] = UnitDef(
        id="Bowman", name="Bowman", race="human", faction="Loyalists",
        level=1, hp=24, cost=14, movement=5, vision=5,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Bow", AttackType.PIERCE, 5, 3, "ranged")],
        advances_to=["Longbowman", "Master Bowman"],
        primary_color="#228B22", secondary_color="#8B4513", accent_color="#DAA520",
        body_type="humanoid", has_bow=True,
    )
    db["Longbowman"] = UnitDef(
        id="Longbowman", name="Longbowman", race="human", faction="Loyalists",
        level=2, hp=32, cost=24, movement=5, vision=6,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Longbow", AttackType.PIERCE, 7, 4, "ranged")],
        advances_to=["Master Bowman"],
        primary_color="#006400", secondary_color="#654321", accent_color="#DAA520",
        body_type="humanoid", has_bow=True,
    )
    db["Master Bowman"] = UnitDef(
        id="Master_Bowman", name="Master Bowman", race="human", faction="Loyalists",
        level=3, hp=38, cost=40, movement=5, vision=7,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Master Bow", AttackType.PIERCE, 9, 4, "ranged", "marksman")],
        primary_color="#004D00", secondary_color="#3E2723", accent_color="#FFD700",
        body_type="humanoid", has_bow=True, has_cape=True,
    )
    db["Cavalryman"] = UnitDef(
        id="Cavalryman", name="Cavalryman", race="human", faction="Loyalists",
        level=1, hp=34, cost=19, movement=8, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Sword", AttackType.BLADE, 6, 3, "melee")],
        advances_to=["Knight", "Lancer", "Dragoon"],
        primary_color="#3366CC", secondary_color="#8B4513", accent_color="#DAA520",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Knight"] = UnitDef(
        id="Knight", name="Knight", race="human", faction="Loyalists",
        level=2, hp=46, cost=28, movement=8, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 8, 3, "melee", "charge"),
            Attack("Lance", AttackType.PIERCE, 9, 1, "melee"),
        ],
        advances_to=["Paladin", "Grand Knight"],
        primary_color="#2850A8", secondary_color="#8B4513", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Paladin"] = UnitDef(
        id="Paladin", name="Paladin", race="human", faction="Loyalists",
        level=3, hp=56, cost=46, movement=8, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Holy Sword", AttackType.ARCANE, 10, 3, "melee", "charge"),
            Attack("Lance", AttackType.PIERCE, 10, 2, "melee"),
        ],
        primary_color="#1A237E", secondary_color="#FFD700", accent_color="#FFFFFF",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Grand Knight"] = UnitDef(
        id="Grand_Knight", name="Grand Knight", race="human", faction="Loyalists",
        level=3, hp=58, cost=44, movement=9, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 10, 4, "melee"),
            Attack("Lance", AttackType.PIERCE, 11, 2, "melee", "charge"),
        ],
        primary_color="#1A237E", secondary_color="#B22222", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Lancer"] = UnitDef(
        id="Lancer", name="Lancer", race="human", faction="Loyalists",
        level=2, hp=44, cost=27, movement=9, vision=5,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Lance", AttackType.PIERCE, 9, 2, "melee", "charge")],
        advances_to=["Paladin", "Grand Knight"],
        primary_color="#3366CC", secondary_color="#8B4513", accent_color="#C0C0C0",
        body_type="humanoid", has_helm=True,
    )
    db["Dragoon"] = UnitDef(
        id="Dragoon", name="Dragoon", race="human", faction="Loyalists",
        level=2, hp=40, cost=25, movement=8, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 7, 3, "melee"),
            Attack("Pistol", AttackType.FIRE, 8, 2, "ranged"),
        ],
        primary_color="#4169E1", secondary_color="#8B4513", accent_color="#DAA520",
        body_type="humanoid", has_helm=True,
    )
    db["Mage"] = UnitDef(
        id="Mage", name="Mage", race="human", faction="Loyalists",
        level=1, hp=22, cost=17, movement=5, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Fireball", AttackType.FIRE, 7, 3, "ranged")],
        advances_to=["White Mage", "Red Mage", "Silver Mage"],
        primary_color="#6633CC", secondary_color="#9966FF", accent_color="#FFD700",
        body_type="humanoid", has_staff=True,
    )
    db["White Mage"] = UnitDef(
        id="White_Mage", name="White Mage", race="human", faction="Loyalists",
        level=2, hp=30, cost=27, movement=5, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Holy Light", AttackType.ARCANE, 9, 3, "ranged", "heal")],
        advances_to=["Arch Mage"],
        primary_color="#EEEEFF", secondary_color="#6633CC", accent_color="#FFD700",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Red Mage"] = UnitDef(
        id="Red_Mage", name="Red Mage", race="human", faction="Loyalists",
        level=2, hp=32, cost=27, movement=5, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Fireball", AttackType.FIRE, 10, 3, "ranged"),
            Attack("Staff", AttackType.IMPACT, 5, 2, "melee"),
        ],
        advances_to=["Arch Mage"],
        primary_color="#CC3333", secondary_color="#FF6633", accent_color="#FFD700",
        body_type="humanoid", has_staff=True,
    )
    db["Silver Mage"] = UnitDef(
        id="Silver_Mage", name="Silver Mage", race="human", faction="Loyalists",
        level=2, hp=30, cost=30, movement=5, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Lightning", AttackType.LIGHTNING, 9, 3, "ranged"),
            Attack("Staff", AttackType.IMPACT, 5, 2, "melee"),
        ],
        advances_to=["Arch Mage"],
        primary_color="#C0C0C0", secondary_color="#6633CC", accent_color="#00BFFF",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Arch Mage"] = UnitDef(
        id="Arch_Mage", name="Arch Mage", race="human", faction="Loyalists",
        level=3, hp=38, cost=46, movement=5, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Meteor", AttackType.FIRE, 12, 3, "ranged"),
            Attack("Staff", AttackType.IMPACT, 6, 2, "melee"),
        ],
        primary_color="#4B0082", secondary_color="#8B00FF", accent_color="#FFD700",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Horseman"] = UnitDef(
        id="Horseman", name="Horseman", race="human", faction="Loyalists",
        level=0, hp=28, cost=15, movement=7, vision=4,
        alignment=Alignment.LAWFUL,
        attacks=[Attack("Sword", AttackType.BLADE, 5, 3, "melee")],
        advances_to=["Cavalryman"],
        primary_color="#3366CC", secondary_color="#8B4513", accent_color="#DAA520",
        body_type="humanoid", has_helm=True,
    )

    # ===================== REBELS (ELVES) =====================
    db["Elvish Fighter"] = UnitDef(
        id="Elvish_Fighter", name="Elvish Fighter", race="elf", faction="Rebels",
        level=1, hp=26, cost=14, movement=6, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Sword", AttackType.BLADE, 5, 3, "melee")],
        advances_to=["Elvish Captain", "Elvish Hero", "Elvish Champion"],
        primary_color="#228B22", secondary_color="#32CD32", accent_color="#8B4513",
        body_type="humanoid",
    )
    db["Elvish Captain"] = UnitDef(
        id="Elvish_Captain", name="Elvish Captain", race="elf", faction="Rebels",
        level=2, hp=36, cost=24, movement=6, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 7, 3, "melee"),
            Attack("Bow", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        advances_to=["Elvish Marshal"],
        primary_color="#1B5E20", secondary_color="#2E7D32", accent_color="#FFD700",
        body_type="humanoid", has_helm=True,
    )
    db["Elvish Hero"] = UnitDef(
        id="Elvish_Hero", name="Elvish Hero", race="elf", faction="Rebels",
        level=2, hp=38, cost=25, movement=6, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Great Sword", AttackType.BLADE, 8, 3, "melee"),
            Attack("Bow", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        advances_to=["Elvish Champion"],
        primary_color="#2E7D32", secondary_color="#43A047", accent_color="#C0C0C0",
        body_type="humanoid",
    )
    db["Elvish Champion"] = UnitDef(
        id="Elvish_Champion", name="Elvish Champion", race="elf", faction="Rebels",
        level=3, hp=48, cost=42, movement=6, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 10, 4, "melee", "firststrike"),
            Attack("Bow", AttackType.PIERCE, 6, 3, "ranged"),
        ],
        primary_color="#1B5E20", secondary_color="#A5D6A7", accent_color="#FFD700",
        body_type="humanoid", has_cape=True,
    )
    db["Elvish Marshal"] = UnitDef(
        id="Elvish_Marshal", name="Elvish Marshal", race="elf", faction="Rebels",
        level=3, hp=46, cost=42, movement=6, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 9, 3, "melee", "leadership"),
            Attack("Bow", AttackType.PIERCE, 6, 3, "ranged"),
        ],
        primary_color="#004D40", secondary_color="#26A69A", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_cape=True,
    )
    db["Elvish Archer"] = UnitDef(
        id="Elvish_Archer", name="Elvish Archer", race="elf", faction="Rebels",
        level=1, hp=22, cost=14, movement=6, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Bow", AttackType.PIERCE, 5, 3, "ranged", "marksman")],
        advances_to=["Elvish Marksman", "Elvish Ranger", "Elvish Avenger"],
        primary_color="#228B22", secondary_color="#8B4513", accent_color="#32CD32",
        body_type="humanoid", has_bow=True,
    )
    db["Elvish Marksman"] = UnitDef(
        id="Elvish_Marksman", name="Elvish Marksman", race="elf", faction="Rebels",
        level=2, hp=28, cost=24, movement=6, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Longbow", AttackType.PIERCE, 8, 4, "ranged", "marksman")],
        advances_to=["Elvish Sharpshooter"],
        primary_color="#1B5E20", secondary_color="#654321", accent_color="#FFD700",
        body_type="humanoid", has_bow=True,
    )
    db["Elvish Sharpshooter"] = UnitDef(
        id="Elvish_Sharpshooter", name="Elvish Sharpshooter", race="elf", faction="Rebels",
        level=3, hp=34, cost=42, movement=6, vision=8,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Master Bow", AttackType.PIERCE, 10, 5, "ranged", "marksman")],
        primary_color="#004D40", secondary_color="#3E2723", accent_color="#FFD700",
        body_type="humanoid", has_bow=True, has_cape=True,
    )
    db["Elvish Ranger"] = UnitDef(
        id="Elvish_Ranger", name="Elvish Ranger", race="elf", faction="Rebels",
        level=2, hp=30, cost=22, movement=6, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 5, 2, "melee"),
            Attack("Bow", AttackType.PIERCE, 7, 3, "ranged"),
        ],
        advances_to=["Elvish Avenger"],
        primary_color="#2E7D32", secondary_color="#1B5E20", accent_color="#8B4513",
        body_type="humanoid", has_bow=True,
    )
    db["Elvish Avenger"] = UnitDef(
        id="Elvish_Avenger", name="Elvish Avenger", race="elf", faction="Rebels",
        level=3, hp=38, cost=40, movement=6, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Sword", AttackType.BLADE, 7, 3, "melee"),
            Attack("Bow", AttackType.PIERCE, 9, 4, "ranged"),
        ],
        primary_color="#1B5E20", secondary_color="#A5D6A7", accent_color="#FF6347",
        body_type="humanoid", has_bow=True, has_cape=True,
    )
    db["Elvish Shaman"] = UnitDef(
        id="Elvish_Shaman", name="Elvish Shaman", race="elf", faction="Rebels",
        level=1, hp=20, cost=15, movement=5, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Staff", AttackType.IMPACT, 4, 2, "melee", "heal")],
        advances_to=["Elvish Druid", "Elvish Sorceress"],
        primary_color="#9C27B0", secondary_color="#228B22", accent_color="#FFD700",
        body_type="humanoid", has_staff=True,
    )
    db["Elvish Druid"] = UnitDef(
        id="Elvish_Druid", name="Elvish Druid", race="elf", faction="Rebels",
        level=2, hp=28, cost=25, movement=5, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Entangle", AttackType.IMPACT, 5, 3, "ranged", "slow"),
            Attack("Staff", AttackType.IMPACT, 5, 2, "melee", "heal"),
        ],
        advances_to=["Elvish Sylph"],
        primary_color="#6A1B9A", secondary_color="#1B5E20", accent_color="#FFD700",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Elvish Sorceress"] = UnitDef(
        id="Elvish_Sorceress", name="Elvish Sorceress", race="elf", faction="Rebels",
        level=2, hp=28, cost=26, movement=5, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Frost", AttackType.COLD, 9, 3, "ranged"),
            Attack("Staff", AttackType.IMPACT, 5, 2, "melee"),
        ],
        advances_to=["Elvish Enchantress"],
        primary_color="#7B1FA2", secondary_color="#CE93D8", accent_color="#00BFFF",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Elvish Enchantress"] = UnitDef(
        id="Elvish_Enchantress", name="Elvish Enchantress", race="elf", faction="Rebels",
        level=3, hp=36, cost=44, movement=5, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Glacier", AttackType.COLD, 11, 3, "ranged"),
            Attack("Staff", AttackType.IMPACT, 6, 2, "melee"),
        ],
        primary_color="#4A148C", secondary_color="#E1BEE7", accent_color="#00BFFF",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Elvish Sylph"] = UnitDef(
        id="Elvish_Sylph", name="Elvish Sylph", race="elf", faction="Rebels",
        level=3, hp=34, cost=44, movement=6, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Faerie Fire", AttackType.ARCANE, 9, 3, "ranged", "heal"),
            Attack("Staff", AttackType.IMPACT, 6, 2, "melee"),
        ],
        primary_color="#1B5E20", secondary_color="#81C784", accent_color="#FFD700",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Wose"] = UnitDef(
        id="Wose", name="Wose", race="wose", faction="Rebels",
        level=1, hp=42, cost=18, movement=3, vision=2,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Crush", AttackType.IMPACT, 9, 2, "melee")],
        advances_to=["Elder Wose"],
        primary_color="#2E7D32", secondary_color="#5D4037", accent_color="#388E3C",
        body_type="beast", size=2,
    )
    db["Elder Wose"] = UnitDef(
        id="Elder_Wose", name="Elder Wose", race="wose", faction="Rebels",
        level=2, hp=58, cost=30, movement=3, vision=2,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Crush", AttackType.IMPACT, 12, 2, "melee")],
        primary_color="#1B5E20", secondary_color="#3E2723", accent_color="#4CAF50",
        body_type="beast", size=2,
    )
    db["Merman Fighter"] = UnitDef(
        id="Merman_Fighter", name="Merman Fighter", race="merman", faction="Rebels",
        level=1, hp=26, cost=14, movement=5, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 5, 3, "melee")],
        advances_to=["Merman Warrior", "Merman Entangler"],
        primary_color="#006994", secondary_color="#40E0D0", accent_color="#8B4513",
        body_type="aquatic",
    )
    db["Merman Warrior"] = UnitDef(
        id="Merman_Warrior", name="Merman Warrior", race="merman", faction="Rebels",
        level=2, hp=36, cost=23, movement=5, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Trident", AttackType.PIERCE, 8, 3, "melee"),
            Attack("Spear", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        primary_color="#004D6E", secondary_color="#00CED1", accent_color="#B8860B",
        body_type="aquatic",
    )
    db["Merman Entangler"] = UnitDef(
        id="Merman_Entangler", name="Merman Entangler", race="merman", faction="Rebels",
        level=2, hp=34, cost=22, movement=5, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Trident", AttackType.PIERCE, 7, 3, "melee"),
            Attack("Net", AttackType.IMPACT, 4, 2, "ranged", "slow"),
        ],
        primary_color="#006994", secondary_color="#20B2AA", accent_color="#2E8B57",
        body_type="aquatic",
    )

    # ===================== NORTHERNERS (ORCS) =====================
    db["Orcish Grunt"] = UnitDef(
        id="Orcish_Grunt", name="Orcish Grunt", race="orc", faction="Northerners",
        level=1, hp=32, cost=12, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Axe", AttackType.BLADE, 7, 2, "melee")],
        advances_to=["Orcish Warrior", "Orcish Assassin"],
        primary_color="#8B4513", secondary_color="#556B2F", accent_color="#A0522D",
        body_type="humanoid",
    )
    db["Orcish Warrior"] = UnitDef(
        id="Orcish_Warrior", name="Orcish Warrior", race="orc", faction="Northerners",
        level=2, hp=44, cost=21, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Axe", AttackType.BLADE, 10, 3, "melee"),
            Attack("Crossbow", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        advances_to=["Orcish Warlord"],
        primary_color="#5C4033", secondary_color="#556B2F", accent_color="#B22222",
        body_type="humanoid", has_helm=True,
    )
    db["Orcish Warlord"] = UnitDef(
        id="Orcish_Warlord", name="Orcish Warlord", race="orc", faction="Northerners",
        level=3, hp=56, cost=35, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Great Axe", AttackType.BLADE, 12, 3, "melee", "leadership"),
            Attack("Crossbow", AttackType.PIERCE, 6, 2, "ranged"),
        ],
        primary_color="#3E2723", secondary_color="#556B2F", accent_color="#FF4500",
        body_type="humanoid", has_helm=True, has_cape=True,
    )
    db["Orcish Assassin"] = UnitDef(
        id="Orcish_Assassin", name="Orcish Assassin", race="orc", faction="Northerners",
        level=2, hp=36, cost=22, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Dagger", AttackType.BLADE, 6, 4, "melee", "poison"),
            Attack("Throwing Knife", AttackType.BLADE, 5, 2, "ranged", "poison"),
        ],
        primary_color="#333333", secondary_color="#556B2F", accent_color="#00FF00",
        body_type="humanoid",
    )
    db["Orcish Archer"] = UnitDef(
        id="Orcish_Archer", name="Orcish Archer", race="orc", faction="Northerners",
        level=1, hp=26, cost=13, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Bow", AttackType.PIERCE, 6, 2, "ranged")],
        advances_to=["Orcish Crossbowman"],
        primary_color="#8B4513", secondary_color="#556B2F", accent_color="#A0522D",
        body_type="humanoid", has_bow=True,
    )
    db["Orcish Crossbowman"] = UnitDef(
        id="Orcish_Crossbowman", name="Orcish Crossbowman", race="orc", faction="Northerners",
        level=2, hp=34, cost=22, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Crossbow", AttackType.PIERCE, 8, 3, "ranged")],
        primary_color="#5C4033", secondary_color="#556B2F", accent_color="#A0522D",
        body_type="humanoid", has_bow=True,
    )
    db["Orcish Slurbow"] = UnitDef(
        id="Orcish_Slurbow", name="Orcish Slurbow", race="orc", faction="Northerners",
        level=2, hp=30, cost=21, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Slurbow", AttackType.PIERCE, 9, 2, "ranged")],
        primary_color="#5C4033", secondary_color="#8B4513", accent_color="#00FF00",
        body_type="humanoid", has_bow=True,
    )
    db["Troll"] = UnitDef(
        id="Troll", name="Troll", race="troll", faction="Northerners",
        level=1, hp=40, cost=16, movement=4, vision=3,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Club", AttackType.IMPACT, 9, 2, "melee")],
        advances_to=["Troll Warrior", "Troll Rocklobber"],
        primary_color="#6B8E23", secondary_color="#556B2F", accent_color="#8B4513",
        body_type="beast", size=2,
    )
    db["Troll Warrior"] = UnitDef(
        id="Troll_Warrior", name="Troll Warrior", race="troll", faction="Northerners",
        level=2, hp=54, cost=26, movement=4, vision=3,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Great Club", AttackType.IMPACT, 12, 3, "melee")],
        primary_color="#556B2F", secondary_color="#2F4F2F", accent_color="#8B4513",
        body_type="beast", size=2,
    )
    db["Troll Rocklobber"] = UnitDef(
        id="Troll_Rocklobber", name="Troll Rocklobber", race="troll", faction="Northerners",
        level=2, hp=48, cost=24, movement=4, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Club", AttackType.IMPACT, 10, 2, "melee"),
            Attack("Rock", AttackType.IMPACT, 8, 2, "ranged"),
        ],
        primary_color="#6B8E23", secondary_color="#8B8682", accent_color="#A9A9A9",
        body_type="beast", size=2,
    )
    db["Goblin Knight"] = UnitDef(
        id="Goblin_Knight", name="Goblin Knight", race="goblin", faction="Northerners",
        level=1, hp=28, cost=15, movement=8, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Spear", AttackType.PIERCE, 5, 3, "melee")],
        advances_to=["Goblin Pillager", "Goblin Impaler"],
        primary_color="#556B2F", secondary_color="#8B4513", accent_color="#A0522D",
        body_type="humanoid", has_helm=True,
    )
    db["Goblin Pillager"] = UnitDef(
        id="Goblin_Pillager", name="Goblin Pillager", race="goblin", faction="Northerners",
        level=2, hp=36, cost=24, movement=8, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Spear", AttackType.PIERCE, 7, 3, "melee"),
            Attack("Bomb", AttackType.FIRE, 8, 1, "ranged"),
        ],
        primary_color="#2F4F2F", secondary_color="#8B4513", accent_color="#FF4500",
        body_type="humanoid", has_helm=True,
    )
    db["Goblin Impaler"] = UnitDef(
        id="Goblin_Impaler", name="Goblin Impaler", race="goblin", faction="Northerners",
        level=2, hp=34, cost=23, movement=8, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Trident", AttackType.PIERCE, 9, 2, "melee", "charge")],
        primary_color="#33691E", secondary_color="#795548", accent_color="#A0522D",
        body_type="humanoid", has_helm=True,
    )
    db["Naga Fighter"] = UnitDef(
        id="Naga_Fighter", name="Naga Fighter", race="naga", faction="Northerners",
        level=1, hp=30, cost=14, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Trident", AttackType.PIERCE, 6, 3, "melee")],
        advances_to=["Naga Warrior", "Naga Myrmidon"],
        primary_color="#2E8B57", secondary_color="#8B0000", accent_color="#DAA520",
        body_type="aquatic",
    )
    db["Naga Warrior"] = UnitDef(
        id="Naga_Warrior", name="Naga Warrior", race="naga", faction="Northerners",
        level=2, hp=40, cost=22, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Trident", AttackType.PIERCE, 9, 3, "melee"),
            Attack("Spear", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        primary_color="#1B5E20", secondary_color="#B71C1C", accent_color="#FFD700",
        body_type="aquatic",
    )
    db["Naga Myrmidon"] = UnitDef(
        id="Naga_Myrmidon", name="Naga Myrmidon", race="naga", faction="Northerners",
        level=3, hp=52, cost=38, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Trident", AttackType.PIERCE, 11, 3, "melee"),
            Attack("Spear", AttackType.PIERCE, 7, 3, "ranged"),
        ],
        primary_color="#004D40", secondary_color="#880E4F", accent_color="#FFD700",
        body_type="aquatic", has_cape=True,
    )
    db["Wolf Rider"] = UnitDef(
        id="Wolf_Rider", name="Wolf Rider", race="orc", faction="Northerners",
        level=1, hp=26, cost=15, movement=9, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Sword", AttackType.BLADE, 5, 3, "melee")],
        advances_to=["Wolf Raider", "Goblin Rouser"],
        primary_color="#556B2F", secondary_color="#8B4513", accent_color="#A0522D",
        body_type="humanoid",
    )
    db["Wolf Raider"] = UnitDef(
        id="Wolf_Raider", name="Wolf Raider", race="orc", faction="Northerners",
        level=2, hp=36, cost=24, movement=9, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Sword", AttackType.BLADE, 8, 3, "melee")],
        primary_color="#33691E", secondary_color="#5D4037", accent_color="#B22222",
        body_type="humanoid",
    )

    # ===================== UNDEAD =====================
    db["Skeleton"] = UnitDef(
        id="Skeleton", name="Skeleton", race="undead", faction="Undead",
        level=1, hp=22, cost=11, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Sword", AttackType.BLADE, 5, 2, "melee")],
        advances_to=["Skeleton Archer", "Revenant"],
        primary_color="#E8E8E8", secondary_color="#BDBDBD", accent_color="#424242",
        body_type="undead",
    )
    db["Skeleton Archer"] = UnitDef(
        id="Skeleton_Archer", name="Skeleton Archer", race="undead", faction="Undead",
        level=1, hp=18, cost=12, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Bow", AttackType.PIERCE, 5, 3, "ranged")],
        advances_to=["Bone Shooter", "Banebow"],
        primary_color="#E0E0E0", secondary_color="#9E9E9E", accent_color="#424242",
        body_type="undead", has_bow=True,
    )
    db["Bone Shooter"] = UnitDef(
        id="Bone_Shooter", name="Bone Shooter", race="undead", faction="Undead",
        level=2, hp=26, cost=22, movement=5, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Crossbow", AttackType.PIERCE, 7, 3, "ranged")],
        primary_color="#BDBDBD", secondary_color="#757575", accent_color="#333333",
        body_type="undead", has_bow=True,
    )
    db["Banebow"] = UnitDef(
        id="Banebow", name="Banebow", race="undead", faction="Undead",
        level=2, hp=30, cost=23, movement=5, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Longbow", AttackType.PIERCE, 8, 4, "ranged", "poison")],
        primary_color="#9E9E9E", secondary_color="#616161", accent_color="#00FF00",
        body_type="undead", has_bow=True,
    )
    db["Revenant"] = UnitDef(
        id="Revenant", name="Revenant", race="undead", faction="Undead",
        level=2, hp=34, cost=20, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Sword", AttackType.BLADE, 7, 3, "melee"),
            Attack("Cold Touch", AttackType.COLD, 5, 2, "melee"),
        ],
        primary_color="#BDBDBD", secondary_color="#757575", accent_color="#000080",
        body_type="undead",
    )
    db["Death Knight"] = UnitDef(
        id="Death_Knight", name="Death Knight", race="undead", faction="Undead",
        level=3, hp=48, cost=38, movement=7, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Sword", AttackType.BLADE, 9, 3, "melee", "charge"),
            Attack("Cold Touch", AttackType.COLD, 7, 2, "melee"),
        ],
        primary_color="#424242", secondary_color="#BDBDBD", accent_color="#191970",
        body_type="undead", has_helm=True, has_cape=True,
    )
    db["Ghost"] = UnitDef(
        id="Ghost", name="Ghost", race="undead", faction="Undead",
        level=1, hp=16, cost=13, movement=7, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Touch", AttackType.COLD, 6, 3, "melee")],
        advances_to=["Shadow", "Wraith", "Spectre"],
        primary_color="#B0C4DE", secondary_color="#E0E8F0", accent_color="#4169E1",
        body_type="undead",
    )
    db["Shadow"] = UnitDef(
        id="Shadow", name="Shadow", race="undead", faction="Undead",
        level=2, hp=22, cost=23, movement=7, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Claws", AttackType.BLADE, 7, 3, "melee")],
        primary_color="#2F2F4F", secondary_color="#4B4B7A", accent_color="#6A5ACD",
        body_type="undead",
    )
    db["Wraith"] = UnitDef(
        id="Wraith", name="Wraith", race="undead", faction="Undead",
        level=2, hp=26, cost=25, movement=7, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Claws", AttackType.BLADE, 8, 3, "melee"),
            Attack("Cold Aura", AttackType.COLD, 6, 2, "ranged"),
        ],
        primary_color="#1C1C3C", secondary_color="#3C3C6C", accent_color="#483D8B",
        body_type="undead",
    )
    db["Spectre"] = UnitDef(
        id="Spectre", name="Spectre", race="undead", faction="Undead",
        level=3, hp=32, cost=40, movement=7, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Claws", AttackType.BLADE, 9, 4, "melee"),
            Attack("Cold Aura", AttackType.COLD, 7, 2, "ranged"),
        ],
        primary_color="#0D0D2B", secondary_color="#2D2D5B", accent_color="#6A0DAD",
        body_type="undead", has_cape=True,
    )
    db["Vampire Bat"] = UnitDef(
        id="Vampire_Bat", name="Vampire Bat", race="undead", faction="Undead",
        level=1, hp=14, cost=10, movement=8, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Bite", AttackType.BLADE, 4, 3, "melee")],
        advances_to=["Blood Bat", "Dread Bat"],
        primary_color="#4A0E4E", secondary_color="#800080", accent_color="#FF0000",
        body_type="flying", has_wings=True,
    )
    db["Blood Bat"] = UnitDef(
        id="Blood_Bat", name="Blood Bat", race="undead", faction="Undead",
        level=2, hp=22, cost=20, movement=9, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Bite", AttackType.BLADE, 6, 4, "melee", "drain")],
        primary_color="#4A0E4E", secondary_color="#8B0000", accent_color="#FF0000",
        body_type="flying", has_wings=True,
    )
    db["Dread Bat"] = UnitDef(
        id="Dread_Bat", name="Dread Bat", race="undead", faction="Undead",
        level=3, hp=30, cost=35, movement=9, vision=7,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Bite", AttackType.BLADE, 8, 4, "melee", "drain"),
            Attack("Screech", AttackType.IMPACT, 5, 2, "ranged"),
        ],
        primary_color="#2D0033", secondary_color="#4B0082", accent_color="#FF0000",
        body_type="flying", has_wings=True,
    )
    db["Necromancer"] = UnitDef(
        id="Necromancer", name="Necromancer", race="human", faction="Undead",
        level=2, hp=30, cost=26, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Staff", AttackType.COLD, 7, 2, "melee"),
            Attack("Shadow Wave", AttackType.COLD, 9, 2, "ranged"),
        ],
        advances_to=["Dark Sorcerer"],
        primary_color="#2D0033", secondary_color="#4B0082", accent_color="#9400D3",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Dark Sorcerer"] = UnitDef(
        id="Dark_Sorcerer", name="Dark Sorcerer", race="human", faction="Undead",
        level=3, hp=38, cost=44, movement=5, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Staff", AttackType.COLD, 8, 2, "melee"),
            Attack("Shadow Storm", AttackType.COLD, 11, 3, "ranged"),
        ],
        primary_color="#1A0025", secondary_color="#38006B", accent_color="#BF00FF",
        body_type="humanoid", has_staff=True, has_cape=True,
    )
    db["Walking Corpse"] = UnitDef(
        id="Walking_Corpse", name="Walking Corpse", race="undead", faction="Undead",
        level=0, hp=18, cost=8, movement=4, vision=3,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Claws", AttackType.BLADE, 4, 2, "melee")],
        primary_color="#8B7355", secondary_color="#6B5B3A", accent_color="#4A3C28",
        body_type="undead",
    )

    # ===================== DRAKES =====================
    db["Drake Clasher"] = UnitDef(
        id="Drake_Clasher", name="Drake Clasher", race="drake", faction="Drakes",
        level=1, hp=36, cost=16, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("War Blade", AttackType.BLADE, 6, 3, "melee")],
        advances_to=["Drake Slasher", "Drake Arbiter"],
        primary_color="#FF8C00", secondary_color="#FFD700", accent_color="#8B0000",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Slash"] = UnitDef(
        id="Drake_Slasher", name="Drake Slasher", race="drake", faction="Drakes",
        level=2, hp=48, cost=28, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Great Blade", AttackType.BLADE, 9, 3, "melee")],
        advances_to=["Drake Blade-master"],
        primary_color="#FF6600", secondary_color="#FFD700", accent_color="#8B0000",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Blade-master"] = UnitDef(
        id="Drake_Blade_master", name="Drake Blade-master", race="drake", faction="Drakes",
        level=3, hp=60, cost=42, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Master Blade", AttackType.BLADE, 12, 4, "melee")],
        primary_color="#E65100", secondary_color="#FFD700", accent_color="#B71C1C",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Arbiter"] = UnitDef(
        id="Drake_Arbiter", name="Drake Arbiter", race="drake", faction="Drakes",
        level=2, hp=46, cost=27, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("War Blade", AttackType.BLADE, 8, 3, "melee", "leadership"),
            Attack("Fire Breath", AttackType.FIRE, 6, 2, "ranged"),
        ],
        advances_to=["Drake Flare-master"],
        primary_color="#FF8C00", secondary_color="#FFD700", accent_color="#B71C1C",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Flare-master"] = UnitDef(
        id="Drake_Flare_master", name="Drake Flare-master", race="drake", faction="Drakes",
        level=3, hp=56, cost=42, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("War Blade", AttackType.BLADE, 9, 3, "melee", "leadership"),
            Attack("Fire Breath", AttackType.FIRE, 9, 3, "ranged"),
        ],
        primary_color="#E65100", secondary_color="#FFD700", accent_color="#FF0000",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Burner"] = UnitDef(
        id="Drake_Burner", name="Drake Burner", race="drake", faction="Drakes",
        level=1, hp=32, cost=16, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Fire Breath", AttackType.FIRE, 7, 2, "ranged")],
        advances_to=["Drake Firestarter", "Drake Flamer"],
        primary_color="#FF4500", secondary_color="#FFD700", accent_color="#FF0000",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Firestarter"] = UnitDef(
        id="Drake_Firestarter", name="Drake Firestarter", race="drake", faction="Drakes",
        level=2, hp=44, cost=28, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Fire Breath", AttackType.FIRE, 10, 3, "ranged"),
            Attack("Claws", AttackType.BLADE, 5, 2, "melee"),
        ],
        primary_color="#FF0000", secondary_color="#FFD700", accent_color="#8B0000",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Fighter"] = UnitDef(
        id="Drake_Fighter", name="Drake Fighter", race="drake", faction="Drakes",
        level=1, hp=34, cost=15, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Claws", AttackType.BLADE, 5, 3, "melee")],
        advances_to=["Drake Warrior", "Drake Glider"],
        primary_color="#FF8C00", secondary_color="#FFA500", accent_color="#8B4513",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Warrior"] = UnitDef(
        id="Drake_Warrior", name="Drake Warrior", race="drake", faction="Drakes",
        level=2, hp=46, cost=26, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Claws", AttackType.BLADE, 8, 3, "melee"),
            Attack("Fire Breath", AttackType.FIRE, 5, 2, "ranged"),
        ],
        primary_color="#FF6600", secondary_color="#FFA500", accent_color="#8B4513",
        body_type="flying", has_wings=True, size=2,
    )
    db["Drake Glider"] = UnitDef(
        id="Drake_Glider", name="Drake Glider", race="drake", faction="Drakes",
        level=2, hp=40, cost=25, movement=8, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Claws", AttackType.BLADE, 7, 3, "melee")],
        primary_color="#20B2AA", secondary_color="#FFD700", accent_color="#FF8C00",
        body_type="flying", has_wings=True, size=2,
    )

    # ===================== KNALGAN ALLIANCE (DWARVES) =====================
    db["Dwarvish Fighter"] = UnitDef(
        id="Dwarvish_Fighter", name="Dwarvish Fighter", race="dwarf", faction="Knalgan Alliance",
        level=1, hp=34, cost=13, movement=4, vision=3,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Axe", AttackType.BLADE, 6, 3, "melee")],
        advances_to=["Dwarvish Steelclad", "Dwarvish Thunderer", "Dwarvish Berserker"],
        primary_color="#8B4513", secondary_color="#A0522D", accent_color="#B8860B",
        body_type="humanoid", has_helm=True,
    )
    db["Dwarvish Steelclad"] = UnitDef(
        id="Dwarvish_Steelclad", name="Dwarvish Steelclad", race="dwarf", faction="Knalgan Alliance",
        level=2, hp=48, cost=23, movement=4, vision=3,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Axe", AttackType.BLADE, 9, 3, "melee"),
            Attack("Crossbow", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        advances_to=["Dwarvish Lord"],
        primary_color="#654321", secondary_color="#8B4513", accent_color="#DAA520",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Dwarvish Lord"] = UnitDef(
        id="Dwarvish_Lord", name="Dwarvish Lord", race="dwarf", faction="Knalgan Alliance",
        level=3, hp=60, cost=40, movement=4, vision=3,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Great Axe", AttackType.BLADE, 11, 3, "melee", "leadership"),
            Attack("Crossbow", AttackType.PIERCE, 6, 2, "ranged"),
        ],
        primary_color="#4A2C0A", secondary_color="#8B4513", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True, has_cape=True,
    )
    db["Dwarvish Thunderer"] = UnitDef(
        id="Dwarvish_Thunderer", name="Dwarvish Thunderer", race="dwarf", faction="Knalgan Alliance",
        level=1, hp=28, cost=16, movement=4, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Musket", AttackType.IMPACT, 9, 2, "ranged")],
        advances_to=["Dwarvish Dragonguard", "Dwarvish Runemaster"],
        primary_color="#8B4513", secondary_color="#696969", accent_color="#FFD700",
        body_type="humanoid", has_helm=True,
    )
    db["Dwarvish Dragonguard"] = UnitDef(
        id="Dwarvish_Dragonguard", name="Dwarvish Dragonguard", race="dwarf", faction="Knalgan Alliance",
        level=2, hp=38, cost=28, movement=4, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Musket", AttackType.IMPACT, 12, 2, "ranged"),
            Attack("Hammer", AttackType.IMPACT, 7, 2, "melee"),
        ],
        advances_to=["Dwarvish Stalwart"],
        primary_color="#654321", secondary_color="#4A4A4A", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Dwarvish Stalwart"] = UnitDef(
        id="Dwarvish_Stalwart", name="Dwarvish Stalwart", race="dwarf", faction="Knalgan Alliance",
        level=3, hp=52, cost=46, movement=4, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Heavy Musket", AttackType.IMPACT, 15, 2, "ranged"),
            Attack("Hammer", AttackType.IMPACT, 9, 2, "melee"),
        ],
        primary_color="#4A2C0A", secondary_color="#333333", accent_color="#FFD700",
        body_type="humanoid", has_helm=True, has_shield=True,
    )
    db["Dwarvish Runemaster"] = UnitDef(
        id="Dwarvish_Runemaster", name="Dwarvish Runemaster", race="dwarf", faction="Knalgan Alliance",
        level=2, hp=36, cost=30, movement=4, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Musket", AttackType.IMPACT, 10, 2, "ranged"),
            Attack("Runed Hammer", AttackType.ARCANE, 7, 2, "melee"),
        ],
        advances_to=["Dwarvish Runesmith"],
        primary_color="#654321", secondary_color="#191970", accent_color="#00BFFF",
        body_type="humanoid", has_helm=True, has_staff=True,
    )
    db["Dwarvish Runesmith"] = UnitDef(
        id="Dwarvish_Runesmith", name="Dwarvish Runesmith", race="dwarf", faction="Knalgan Alliance",
        level=3, hp=44, cost=46, movement=4, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[
            Attack("Musket", AttackType.IMPACT, 11, 2, "ranged"),
            Attack("Runed Hammer", AttackType.ARCANE, 9, 3, "melee"),
        ],
        primary_color="#4A2C0A", secondary_color="#0D47A1", accent_color="#00E5FF",
        body_type="humanoid", has_helm=True, has_staff=True, has_cape=True,
    )
    db["Dwarvish Berserker"] = UnitDef(
        id="Dwarvish_Berserker", name="Dwarvish Berserker", race="dwarf", faction="Knalgan Alliance",
        level=2, hp=38, cost=22, movement=5, vision=3,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Axe", AttackType.BLADE, 7, 4, "melee", "berserk")],
        primary_color="#B22222", secondary_color="#8B4513", accent_color="#FFD700",
        body_type="humanoid", has_helm=True,
    )
    db["Gryphon"] = UnitDef(
        id="Gryphon", name="Gryphon", race="gryphon", faction="Knalgan Alliance",
        level=2, hp=38, cost=25, movement=8, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Claws", AttackType.BLADE, 8, 3, "melee")],
        primary_color="#DAA520", secondary_color="#F5DEB3", accent_color="#8B4513",
        body_type="flying", has_wings=True, size=2,
    )
    db["Gryphon Master"] = UnitDef(
        id="Gryphon_Master", name="Gryphon Master", race="gryphon", faction="Knalgan Alliance",
        level=3, hp=50, cost=42, movement=9, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Talon", AttackType.BLADE, 11, 3, "melee")],
        primary_color="#B8860B", secondary_color="#F5DEB3", accent_color="#8B4513",
        body_type="flying", has_wings=True, size=2,
    )

    # ===================== SAURIANS =====================
    db["Saurian Skirmisher"] = UnitDef(
        id="Saurian_Skirmisher", name="Saurian Skirmisher", race="saurian", faction="Saurians",
        level=1, hp=24, cost=12, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Spear", AttackType.PIERCE, 5, 2, "melee")],
        advances_to=["Saurian Fighter", "Saurian Augur"],
        primary_color="#556B2F", secondary_color="#8FBC8F", accent_color="#DAA520",
        body_type="humanoid",
    )
    db["Saurian Fighter"] = UnitDef(
        id="Saurian_Fighter", name="Saurian Fighter", race="saurian", faction="Saurians",
        level=2, hp=34, cost=21, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Spear", AttackType.PIERCE, 7, 3, "melee"),
            Attack("Javelin", AttackType.PIERCE, 6, 2, "ranged"),
        ],
        advances_to=["Saurian Warrior", "Saurian Oracle"],
        primary_color="#4A5D23", secondary_color="#6B8E23", accent_color="#B8860B",
        body_type="humanoid", has_shield=True,
    )
    db["Saurian Warrior"] = UnitDef(
        id="Saurian_Warrior", name="Saurian Warrior", race="saurian", faction="Saurians",
        level=3, hp=44, cost=35, movement=6, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Spear", AttackType.PIERCE, 9, 3, "melee"),
            Attack("Javelin", AttackType.PIERCE, 8, 2, "ranged"),
        ],
        primary_color="#3B4A1B", secondary_color="#556B2F", accent_color="#DAA520",
        body_type="humanoid", has_shield=True, has_helm=True,
    )
    db["Saurian Augur"] = UnitDef(
        id="Saurian_Augur", name="Saurian Augur", race="saurian", faction="Saurians",
        level=2, hp=28, cost=24, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Cold Bolt", AttackType.COLD, 8, 2, "ranged")],
        advances_to=["Saurian Oracle"],
        primary_color="#2E8B57", secondary_color="#556B2F", accent_color="#00BFFF",
        body_type="humanoid", has_staff=True,
    )
    db["Saurian Oracle"] = UnitDef(
        id="Saurian_Oracle", name="Saurian Oracle", race="saurian", faction="Saurians",
        level=3, hp=36, cost=40, movement=6, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Ice Storm", AttackType.COLD, 11, 3, "ranged")],
        primary_color="#1B5E20", secondary_color="#2E8B57", accent_color="#00E5FF",
        body_type="humanoid", has_staff=True, has_cape=True,
    )

    # ===================== OUTLAWS =====================
    db["Thief"] = UnitDef(
        id="Thief", name="Thief", race="human", faction="Outlaws",
        level=1, hp=22, cost=13, movement=6, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Dagger", AttackType.BLADE, 4, 3, "melee")],
        advances_to=["Rogue", "Footpad"],
        primary_color="#2F2F2F", secondary_color="#555555", accent_color="#8B4513",
        body_type="humanoid",
    )
    db["Rogue"] = UnitDef(
        id="Rogue", name="Rogue", race="human", faction="Outlaws",
        level=2, hp=30, cost=22, movement=6, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Dagger", AttackType.BLADE, 6, 3, "melee", "backstab"),
            Attack("Throwing Knife", AttackType.PIERCE, 5, 2, "ranged"),
        ],
        advances_to=["Assassin"],
        primary_color="#1A1A1A", secondary_color="#444444", accent_color="#8B0000",
        body_type="humanoid",
    )
    db["Assassin"] = UnitDef(
        id="Assassin", name="Assassin", race="human", faction="Outlaws",
        level=3, hp=38, cost=38, movement=6, vision=7,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Dagger", AttackType.BLADE, 7, 4, "melee", "backstab poison"),
            Attack("Throwing Knife", AttackType.PIERCE, 6, 3, "ranged", "poison"),
        ],
        primary_color="#0D0D0D", secondary_color="#333333", accent_color="#00FF00",
        body_type="humanoid", has_cape=True,
    )
    db["Footpad"] = UnitDef(
        id="Footpad", name="Footpad", race="human", faction="Outlaws",
        level=1, hp=24, cost=11, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Club", AttackType.IMPACT, 5, 2, "melee")],
        advances_to=["Highwayman", "Trapper"],
        primary_color="#5D4037", secondary_color="#795548", accent_color="#8B4513",
        body_type="humanoid",
    )
    db["Highwayman"] = UnitDef(
        id="Highwayman", name="Highwayman", race="human", faction="Outlaws",
        level=2, hp=32, cost=20, movement=5, vision=4,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Club", AttackType.IMPACT, 7, 3, "melee"),
            Attack("Crossbow", AttackType.PIERCE, 6, 2, "ranged"),
        ],
        primary_color="#3E2723", secondary_color="#5D4037", accent_color="#B8860B",
        body_type="humanoid",
    )
    db["Trapper"] = UnitDef(
        id="Trapper", name="Trapper", race="human", faction="Outlaws",
        level=2, hp=28, cost=19, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Club", AttackType.IMPACT, 6, 2, "melee"),
            Attack("Net", AttackType.IMPACT, 4, 2, "ranged", "slow"),
        ],
        primary_color="#4A3C28", secondary_color="#6B5B3A", accent_color="#2E8B57",
        body_type="humanoid",
    )
    db["Poacher"] = UnitDef(
        id="Poacher", name="Poacher", race="human", faction="Outlaws",
        level=1, hp=20, cost=11, movement=5, vision=5,
        alignment=Alignment.CHAOTIC,
        attacks=[Attack("Sling", AttackType.IMPACT, 5, 2, "ranged")],
        advances_to=["Huntsman"],
        primary_color="#556B2F", secondary_color="#8B4513", accent_color="#696969",
        body_type="humanoid",
    )
    db["Huntsman"] = UnitDef(
        id="Huntsman", name="Huntsman", race="human", faction="Outlaws",
        level=2, hp=28, cost=20, movement=5, vision=6,
        alignment=Alignment.CHAOTIC,
        attacks=[
            Attack("Sling", AttackType.IMPACT, 7, 3, "ranged"),
            Attack("Dagger", AttackType.BLADE, 4, 2, "melee"),
        ],
        primary_color="#33691E", secondary_color="#5D4037", accent_color="#696969",
        body_type="humanoid",
    )

    # ===================== MERFOLK =====================
    db["Merfolk Diviner"] = UnitDef(
        id="Merfolk_Diviner", name="Merfolk Diviner", race="merman", faction="Merfolk",
        level=1, hp=20, cost=15, movement=5, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 4, 2, "melee"), Attack("Water Bolt", AttackType.COLD, 6, 2, "ranged")],
        advances_to=["Merfolk Enchantress", "Merfolk Priestess"],
        primary_color="#006994", secondary_color="#40E0D0", accent_color="#E040FB",
        body_type="aquatic", has_staff=True,
    )
    db["Merfolk Enchantress"] = UnitDef(
        id="Merfolk_Enchantress", name="Merfolk Enchantress", race="merman", faction="Merfolk",
        level=2, hp=28, cost=25, movement=5, vision=6,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 5, 2, "melee"), Attack("Tidal Wave", AttackType.COLD, 9, 2, "ranged")],
        advances_to=["Merfolk Siren"],
        primary_color="#004D6E", secondary_color="#00CED1", accent_color="#AA00FF",
        body_type="aquatic", has_staff=True, has_cape=True,
    )
    db["Merfolk Siren"] = UnitDef(
        id="Merfolk_Siren", name="Merfolk Siren", race="merman", faction="Merfolk",
        level=3, hp=36, cost=44, movement=5, vision=7,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 6, 2, "melee"), Attack("Tsunami", AttackType.COLD, 12, 3, "ranged")],
        primary_color="#003344", secondary_color="#008B8B", accent_color="#D500F9",
        body_type="aquatic", has_staff=True, has_cape=True,
    )
    db["Merfolk Priestess"] = UnitDef(
        id="Merfolk_Priestess", name="Merfolk Priestess", race="merman", faction="Merfolk",
        level=2, hp=26, cost=26, movement=5, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 4, 2, "melee"), Attack("Holy Water", AttackType.ARCANE, 8, 2, "ranged", "heal")],
        primary_color="#1A237E", secondary_color="#40E0D0", accent_color="#FFD700",
        body_type="aquatic", has_staff=True,
    )
    db["Merfolk Netcaster"] = UnitDef(
        id="Merfolk_Netcaster", name="Merfolk Netcaster", race="merman", faction="Merfolk",
        level=1, hp=22, cost=13, movement=5, vision=5,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 5, 2, "melee"), Attack("Net", AttackType.IMPACT, 3, 2, "ranged", "slow")],
        primary_color="#006994", secondary_color="#2E8B57", accent_color="#DAA520",
        body_type="aquatic",
    )
    db["Merfolk Hoplite"] = UnitDef(
        id="Merfolk_Hoplite", name="Merfolk Hoplite", race="merman", faction="Merfolk",
        level=2, hp=34, cost=22, movement=5, vision=4,
        alignment=Alignment.NEUTRAL,
        attacks=[Attack("Trident", AttackType.PIERCE, 8, 3, "melee"), Attack("Spear", AttackType.PIERCE, 5, 2, "ranged")],
        primary_color="#004D6E", secondary_color="#B8860B", accent_color="#DAA520",
        body_type="aquatic", has_shield=True,
    )

    return db


# Module-level singleton
DATABASE: Dict[str, UnitDef] = _build_database()


def get_all_factions() -> List[str]:
    """Return sorted list of all faction names."""
    return sorted(set(u.faction for u in DATABASE.values()))


def get_units_by_faction(faction: str) -> List[UnitDef]:
    """Return all units belonging to a faction, sorted by level then name."""
    units = [u for u in DATABASE.values() if u.faction == faction]
    return sorted(units, key=lambda u: (u.level, u.name))


def get_unit_by_id(unit_id: str) -> Optional[UnitDef]:
    """Look up a unit definition by its id."""
    return DATABASE.get(unit_id)


def get_all_units() -> List[UnitDef]:
    """Return every unit in the database sorted by faction, level, name."""
    return sorted(DATABASE.values(), key=lambda u: (u.faction, u.level, u.name))


def get_faction_color(faction: str) -> str:
    """Return a representative color for each faction."""
    colors = {
        "Loyalists": "#3366CC",
        "Rebels": "#228B22",
        "Northerners": "#8B4513",
        "Undead": "#4B0082",
        "Drakes": "#FF6600",
        "Knalgan Alliance": "#8B4513",
        "Saurians": "#556B2F",
        "Outlaws": "#333333",
        "Merfolk": "#006994",
    }
    return colors.get(faction, "#808080")