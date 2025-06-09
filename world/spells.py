from dataclasses import dataclass
from typing import Dict

@dataclass
class Spell:
    key: str
    stat: str
    mana_cost: int
    desc: str = ""
    cooldown: int = 0
    proficiency: int = 0


SPELLS: Dict[str, Spell] = {
    "fireball": Spell("fireball", "INT", 10, "Hurl a ball of fire at your target.", cooldown=5),
    "heal": Spell("heal", "WIS", 8, "Restore a small amount of health.", cooldown=3),
}
