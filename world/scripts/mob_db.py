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
        """Store ``data`` for ``vnum``. Ensure ``spawn_count`` key exists."""
        vnum = int(vnum)
        proto = dict(data)
        # preserve existing spawn counter if re-adding
        if "spawn_count" not in proto:
            proto["spawn_count"] = self.db.vnums.get(vnum, {}).get("spawn_count", 0)
        self.db.vnums[vnum] = proto

    def increment_spawn_count(self, vnum):
        """Increase the stored spawn counter for ``vnum``."""
        vnum = int(vnum)
        proto = self.db.vnums.get(vnum)
        if not proto:
            return
        proto["spawn_count"] = int(proto.get("spawn_count", 0)) + 1
        self.db.vnums[vnum] = proto

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
