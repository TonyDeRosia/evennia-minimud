from dataclasses import dataclass
from typing import Dict

@dataclass
class Spell:
    key: str
    stat: str
    mana_cost: int
    desc: str = ""


SPELLS: Dict[str, Spell] = {
    "fireball": Spell("fireball", "INT", 10, "Hurl a ball of fire at your target."),
    "heal": Spell("heal", "WIS", 8, "Restore a small amount of health."),
}
