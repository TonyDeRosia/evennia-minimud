from datetime import datetime
from typeclasses.scripts import Script

class MerchantLogic(Script):
    """Restock goods and refuse trade at night."""

    def at_script_creation(self):
        self.key = "merchant_logic"
        self.desc = "Merchant restocking behavior"
        self.interval = 60
        self.persistent = True

    def at_repeat(self):
        npc = self.obj
        if not npc:
            return
        hour = datetime.now().hour
        npc.db.closed = hour < 6
        if hasattr(npc, "restock"):
            npc.restock()
