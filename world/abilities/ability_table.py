"""Default unlocked abilities for each combat class."""

# Mapping: class name -> {level: [abilities]}
CLASS_ABILITY_TABLE = {
    "Warrior": {1: ["slash"]},
    "Mystic": {1: ["slash"]},
    "Wizard": {1: ["fireball"]},
    "Sorcerer": {1: ["fireball"]},
    "Mage": {1: ["fireball"]},
    "Battlemage": {1: ["slash", "fireball"]},
    "Necromancer": {1: ["fireball"]},
    "Spellbinder": {1: ["fireball"]},
    "Priest": {1: ["heal"]},
    "Paladin": {1: ["slash", "heal"]},
    "Druid": {1: ["heal"]},
    "Shaman": {1: ["fireball", "heal"]},
    "Rogue": {1: ["slash"]},
    "Ranger": {1: ["slash"]},
    "Warlock": {1: ["fireball"]},
    "Bard": {1: ["slash", "heal"]},
    "Swashbuckler": {1: ["slash"]},
}

__all__ = ["CLASS_ABILITY_TABLE"]
