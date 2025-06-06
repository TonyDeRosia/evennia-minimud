"""Helpers for NPC role tags."""


def has_role(obj, role: str) -> bool:
    """Return True if ``obj`` has the given NPC role tag."""
    if not obj:
        return False
    return obj.tags.has(role, category="npc_role")


def is_guildmaster(obj) -> bool:
    """Return True if ``obj`` can run guild management commands."""
    if not obj:
        return False
    if hasattr(obj, "check_permstring") and obj.check_permstring("Builder"):
        return True
    return has_role(obj, "guildmaster")


def is_receptionist(obj) -> bool:
    """Return True if ``obj`` is tagged as a guild receptionist."""
    return has_role(obj, "guild_receptionist")
