"""Utilities for calculating defensive stat effectiveness with diminishing returns.

This module provides the :class:`DefensiveStats` class which applies diminishing
returns scaling to various defensive stats in a typical RPG. The scaling uses

``effectiveness = stat / (stat + base_constant)``

where ``stat`` is the raw value and ``base_constant`` controls curve steepness.
The returned effectiveness is expressed as a percentage (0-99.9%).

Example
-------

>>> ds = DefensiveStats()
>>> ds.armor_effectiveness(100)
50.0
>>> ds.stat_for_effectiveness(0.5, "armor")
100.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

__all__ = ["DefensiveStats"]


@dataclass
class DefensiveStats:
    """Apply diminishing returns to defensive stats.

    Base constants can be customized per stat to tweak how quickly the
    effectiveness approaches its asymptotic cap.
    """

    armor_base: float = 100.0
    dodge_base: float = 100.0
    parry_base: float = 100.0
    block_base: float = 100.0
    evasion_base: float = 100.0
    magic_resist_base: float = 100.0
    _constants: Dict[str, float] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._constants = {
            "armor": self.armor_base,
            "dodge": self.dodge_base,
            "parry": self.parry_base,
            "block": self.block_base,
            "evasion": self.evasion_base,
            "magic_resist": self.magic_resist_base,
        }
        for key, val in self._constants.items():
            if val <= 0:
                raise ValueError(f"base constant for {key} must be positive")

    @staticmethod
    def _apply(stat: float, base_constant: float) -> float:
        """Return effectiveness percentage using the diminishing formula."""
        if stat < 0:
            raise ValueError("stat value must be non-negative")
        return (stat / (stat + base_constant)) * 100

    def armor_effectiveness(self, stat: float) -> float:
        """Return damage reduction percentage from ``stat`` armor."""
        return self._apply(stat, self._constants["armor"])

    def dodge_effectiveness(self, stat: float) -> float:
        """Return dodge chance percentage from ``stat``."""
        return self._apply(stat, self._constants["dodge"])

    def parry_effectiveness(self, stat: float) -> float:
        """Return parry chance percentage from ``stat``."""
        return self._apply(stat, self._constants["parry"])

    def block_effectiveness(self, stat: float) -> float:
        """Return block chance percentage from ``stat``."""
        return self._apply(stat, self._constants["block"])

    def evasion_effectiveness(self, stat: float) -> float:
        """Return evasion chance percentage from ``stat``."""
        return self._apply(stat, self._constants["evasion"])

    def magic_resist_effectiveness(self, stat: float) -> float:
        """Return magic damage reduction percentage from ``stat``."""
        return self._apply(stat, self._constants["magic_resist"])

    def stat_for_effectiveness(self, effectiveness: float, stat_type: str) -> float:
        """Return the raw stat required for ``effectiveness``.

        Parameters
        ----------
        effectiveness:
            Desired effectiveness expressed as a decimal between 0 and 1.
        stat_type:
            One of ``"armor"``, ``"dodge"``, ``"parry"``, ``"block"``,
            ``"evasion"`` or ``"magic_resist"``.
        """
        if not 0 <= effectiveness < 1:
            raise ValueError("effectiveness must be in [0, 1)")
        if stat_type not in self._constants:
            raise KeyError(f"unknown stat type: {stat_type}")
        base = self._constants[stat_type]
        return (effectiveness * base) / (1 - effectiveness)

    def compare_effectiveness(self, stat1: float, stat2: float, stat_type: str) -> float:
        """Return the percentage difference between two stat values."""
        eff1 = self._apply(stat1, self._constants[stat_type])
        eff2 = self._apply(stat2, self._constants[stat_type])
        return eff2 - eff1



if __name__ == "__main__":  # pragma: no cover - manual demonstration
    stats = DefensiveStats()
    for value in (0, 100, 200):
        pct = stats.armor_effectiveness(value)
        print(f"{value} armor -> {pct:.1f}% damage reduction")

