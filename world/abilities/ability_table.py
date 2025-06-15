"""Default unlocked abilities for each combat class."""

# Mapping: class name -> {level: [abilities]}
CLASS_ABILITY_TABLE = {
    "Warrior": {1: ["slash", "kick"]},
    "Mystic": {1: ["slash", "kick"]},
    "Wizard": {1: ["fireball", "kick"]},
    "Sorcerer": {1: ["fireball", "kick"]},
    "Mage": {1: ["fireball", "kick"]},
    "Battlemage": {1: ["slash", "fireball", "kick"]},
    "Necromancer": {1: ["fireball", "kick"]},
    "Spellbinder": {1: ["fireball", "kick"]},
    "Priest": {1: ["heal", "kick"]},
    "Paladin": {1: ["slash", "heal", "kick"]},
    "Druid": {1: ["heal", "kick"]},
    "Shaman": {1: ["fireball", "heal", "kick"]},
    "Rogue": {1: ["slash", "kick"]},
    "Ranger": {1: ["slash", "kick"]},
    "Warlock": {1: ["fireball", "kick"]},
    "Bard": {1: ["slash", "heal", "kick"]},
    "Swashbuckler": {1: ["slash", "kick"]},
}

__all__ = ["CLASS_ABILITY_TABLE"]
