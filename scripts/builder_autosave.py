from typeclasses.scripts import Script

class BuilderAutosave(Script):
    """Autosave NPC builder sessions periodically."""

    def at_script_creation(self):
        self.key = "builder_autosave"
        self.desc = "Autosave NPC builder data"
        self.interval = 60
        self.persistent = True

    def at_repeat(self):
        caller = self.obj
        if not caller:
            return
        data = getattr(caller.ndb, "buildnpc", None)
        if data:
            caller.db.builder_autosave = dict(data)
        else:
            caller.db.builder_autosave = None
