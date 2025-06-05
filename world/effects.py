from dataclasses import dataclass
from typing import Dict


@dataclass
class Effect:
    """Definition for a temporary effect."""

    key: str
    name: str
    desc: str
    type: str = "status"  # "buff" or "status"


EFFECTS: Dict[str, Effect] = {
    "speed": Effect(
        key="speed",
        name="Speed Boost",
        desc="You move more quickly than normal.",
        type="buff",
    ),
    "stunned": Effect(
        key="stunned",
        name="Stunned",
        desc="You are unable to act.",
        type="status",
    ),
    "STR": Effect(
        key="STR",
        name="Strength Bonus",
        desc="Your strength is temporarily increased.",
        type="buff",
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
}
