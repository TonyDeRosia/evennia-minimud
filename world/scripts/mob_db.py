from evennia.utils import create
from evennia.scripts.scripts import DefaultScript
from evennia.scripts.models import ScriptDB


class MobDB(DefaultScript):
    """Simple in-memory database for NPC prototypes keyed by vnum."""

    def at_script_creation(self):
        """Initialize the script on first creation."""
        self.key = "mob_db"
        self.persistent = True
        self.db.vnums = {}
        self.db.next_vnum = 1

    # ------------------------------------------------------------------
    # Convenience API
    # ------------------------------------------------------------------
    def get_proto(self, vnum):
        """Return prototype dict for ``vnum`` or ``None``."""
        return self.db.vnums.get(int(vnum))

    def add_proto(self, vnum, data):
        """Store ``data`` for ``vnum``."""
        self.db.vnums[int(vnum)] = data

    def delete_proto(self, vnum):
        """Remove ``vnum`` from the database."""
        self.db.vnums.pop(int(vnum), None)

    def next_vnum(self):
        """Return the next available vnum and increment the counter."""
        vnum = int(self.db.next_vnum or 1)
        self.db.next_vnum = vnum + 1
        return vnum


def get_mobdb():
    """Return the global ``MobDB`` script, creating it if needed."""
    script, _ = ScriptDB.objects.get_or_create(
        db_key="mob_db",
        defaults={"db_typeclass_path": "world.scripts.mob_db.MobDB"},
    )
    # ensure correct typeclass
    if script.typeclass_path != "world.scripts.mob_db.MobDB":
        script.delete()
        script = create.create_script("world.scripts.mob_db.MobDB", key="mob_db")
    return script
