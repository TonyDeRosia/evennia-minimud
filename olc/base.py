from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from evennia.utils.evmenu import EvMenu


@dataclass
class OLCState:
    """Holds temporary data while editing with an OLC menu."""

    data: Dict[str, Any] = field(default_factory=dict)
    vnum: Optional[int] = None


class OLCValidator:
    """Simple validator returning a list of warnings."""

    def validate(self, data: Dict[str, Any]) -> List[str]:
        return []


class OLCEditor:
    """Base helper for launching EvMenu based editors."""

    def __init__(
        self,
        caller,
        menu_module: str,
        *,
        startnode: str = "menunode_main",
        state: Optional[OLCState] = None,
        validator: Optional[OLCValidator] = None,
    ) -> None:
        self.caller = caller
        self.menu_module = menu_module
        self.startnode = startnode
        self.state = state or OLCState()
        self.validator = validator or OLCValidator()

    # ------------------------------------------------------------------
    # Menu management
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Begin the editing session using ``EvMenu``."""
        EvMenu(
            self.caller,
            self.menu_module,
            startnode=self.startnode,
            cmd_on_exit=self._on_exit,
        )

    # ------------------------------------------------------------------
    def _on_exit(self, caller, menu) -> None:
        """Called when the menu exits; performs validation."""
        warnings = self.validator.validate(self.state.data)
        if warnings:
            caller.msg("\n".join(warnings))
        # store the state for potential later use
        caller.ndb.olc_state = self.state
