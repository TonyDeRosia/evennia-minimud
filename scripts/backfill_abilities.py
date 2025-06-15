"""One-time script to grant characters any missing level-based abilities."""

import os
import sys
import django

# 👇 Add this line to set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

# Include project root so "server" package is importable when run directly
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 👇 Setup Django environment
django.setup()

from evennia.utils import logger
from typeclasses.characters import Character
from world.abilities import CLASS_ABILITY_TABLE
from world.system import state_manager


def backfill():
    """Grant abilities unlocked by level to all characters."""
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
    backfill()
