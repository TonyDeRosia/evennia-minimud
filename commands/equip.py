"""Custom equipment commands."""

from evennia.contrib.game_systems.clothing.clothing import (
    CmdWear as ContribCmdWear,
    ContribClothing,
    get_worn_clothes,
    CLOTHING_OVERALL_LIMIT,
    CLOTHING_TYPE_LIMIT,
    WEARSTYLE_MAXLENGTH,
    single_type_count,
)
from evennia.utils import at_search_result, inherits_from
from utils import normalize_slot


class CmdWear(ContribCmdWear):
    """Wear an item of clothing with extra slot normalization."""

    # expose additional aliases
    aliases = ["equip", "puton"]

    def func(self):
        """Normalize slot tags before delegating to the parent implementation."""
        if not self.args:
            # fall back to parent behavior which prints usage message
            return super().func()

        # The following replicates the search logic of the parent command so we
        # can operate on the item before it's worn.
        if not self.rhs:
            clothing = self.caller.search(self.lhs, candidates=self.caller.contents, quiet=True)
            if not clothing:
                argslist = self.lhs.split()
                self.lhs = argslist[0]
                self.rhs = " ".join(argslist[1:])
                clothing = self.caller.search(self.lhs, candidates=self.caller.contents)
            else:
                clothing = at_search_result(clothing, self.caller, self.lhs)
        else:
            clothing = self.caller.search(self.lhs, candidates=self.caller.contents)

        if not clothing:
            return
        if not inherits_from(clothing, ContribClothing):
            self.caller.msg(f"{clothing.name} isn't something you can wear.")
            return

        # Normalize slot tags on the item before checking limits
        for slot in clothing.tags.get(category="slot", return_list=True) or []:
            canonical = normalize_slot(slot)
            if canonical and not clothing.tags.get(canonical, category="slot"):
                clothing.tags.add(canonical, category="slot")

        # If already worn, allow adjusting wearstyle as usual
        if clothing.db.worn:
            if not self.rhs:
                self.caller.msg(f"You're already wearing your {clothing.name}.")
                return
            elif len(self.rhs) > WEARSTYLE_MAXLENGTH:
                self.caller.msg(
                    "Please keep your wear style message to less than"
                    f" {WEARSTYLE_MAXLENGTH} characters."
                )
                return
            else:
                clothing.db.worn = self.rhs
                self.caller.location.msg_contents(
                    f"$You() $conj(wear) {clothing.name} {self.rhs}.", from_obj=self.caller
                )
                return

        already_worn = get_worn_clothes(self.caller)

        if CLOTHING_OVERALL_LIMIT and len(already_worn) >= CLOTHING_OVERALL_LIMIT:
            self.caller.msg("You can't wear any more clothes.")
            return

        if clothing_type := clothing.db.clothing_type:
            if clothing_type in CLOTHING_TYPE_LIMIT:
                type_count = single_type_count(already_worn, clothing_type)
                if type_count >= CLOTHING_TYPE_LIMIT[clothing_type]:
                    self.caller.msg(
                        f"You can't wear any more clothes of the type '{clothing_type}'."
                    )
                    return

        wearstyle = self.rhs or True
        clothing.wear(self.caller, wearstyle)

