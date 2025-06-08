from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Effect:
    """Definition for a temporary effect."""

    key: str
    name: str
    desc: str
    type: str = "status"  # "buff" or "status"
    mods: Optional[Dict[str, int]] = field(default_factory=dict)


EFFECTS: Dict[str, Effect] = {
    "speed": Effect(
        key="speed",
        name="Speed Boost",
        desc="You move more quickly than normal.",
        type="buff",
        mods={"DEX": 2},
    ),
    "stunned": Effect(
        key="stunned",
        name="Stunned",
        desc="You are unable to act.",
        type="status",
        mods={"DEX": -5},
    ),
    "STR": Effect(
        key="STR",
        name="Strength Bonus",
        desc="Your strength is temporarily increased.",
        type="buff",
        mods={"STR": 5},
    ),
    "sleeping": Effect(
        key="sleeping",
        name="Sleeping",
        desc="You are fast asleep.",
        type="status",
    ),
    "unconscious": Effect(
        key="unconscious",
        name="Unconscious",
        desc="You are knocked out.",
        type="status",
    ),
    "sitting": Effect(
        key="sitting",
        name="Sitting",
        desc="You are sitting and resting.",
        type="status",
    ),
    "lying down": Effect(
        key="lying down",
        name="Lying Down",
        desc="You are sprawled on the ground.",
        type="status",
    ),
    "hungry_thirsty": Effect(
        key="hungry_thirsty",
        name="Hungry & Thirsty",
        desc="You are weakened from hunger and thirst.",
        type="status",
    ),
}
