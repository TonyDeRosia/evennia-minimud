"""One-time script to grant characters any missing level-based abilities."""

import os
import sys
import django
from django.apps import apps
from django.conf import settings


# Include project root so "server" package is importable when run directly
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))


def _ensure_django():
    """Ensure Django is configured and apps are ready."""
    if not settings.configured or not apps.ready:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        if ROOT_DIR not in sys.path:
            sys.path.insert(0, ROOT_DIR)
        django.setup()


def backfill():
    """Grant abilities unlocked by level to all characters."""
    _ensure_django()
    from evennia.utils import logger
    from typeclasses.characters import Character
    from world.abilities import CLASS_ABILITY_TABLE
    from world.system import state_manager

    added = 0
    for char in Character.objects.all():
        charclass = char.db.charclass
        if not charclass:
            continue
        level = int(char.db.level or 1)
        pre_skills = set(char.db.skills or [])
        pre_spells = {
            s if isinstance(s, str) else getattr(s, "key", "")
            for s in (char.db.spells or [])
        }
        for lvl in range(1, level + 1):
            for ability in CLASS_ABILITY_TABLE.get(charclass, {}).get(lvl, []):
                state_manager.grant_ability(char, ability, mark_new=False)
        state_manager.grant_ability(char, "kick", proficiency=25, mark_new=False)
        post_skills = set(char.db.skills or [])
        post_spells = {
            s if isinstance(s, str) else getattr(s, "key", "")
            for s in (char.db.spells or [])
        }
        added += len(post_skills - pre_skills) + len(post_spells - pre_spells)
    logger.log_info(f"Backfill complete: added {added} abilities.")


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    if ROOT_DIR not in sys.path:
        sys.path.insert(0, ROOT_DIR)
    django.setup()
    backfill()
