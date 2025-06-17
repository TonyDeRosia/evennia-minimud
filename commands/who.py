from evennia.server.sessionhandler import SESSIONS
from evennia.utils.evtable import EvTable
from evennia.utils.utils import time_format
import time

from .command import MuxCommand


class CmdWho(MuxCommand):
    """List who is online."""

    key = "who"
    aliases = ("online",)
    account_caller = False

    def func(self):
        caller = self.caller
        sessions = SESSIONS.get_sessions()
        if not sessions:
            caller.msg("No one is connected.")
            return

        is_admin = caller.check_permstring("Admins")

        headers = []
        if is_admin:
            headers.append("|cAccount|n")
        headers.extend(["|cCharacter|n", "|cTitle|n", "|cRace|n", "|cClass|n", "|cIdle|n"])
        table = EvTable(*headers, border="cells")

        for sess in sessions:
            if not sess.logged_in:
                continue
            account = sess.account
            puppet = sess.puppet
            if not puppet and not is_admin:
                continue

            charname = puppet.get_display_name(caller) if puppet else "None"
            title = puppet.db.title or "None" if puppet else "None"
            race = getattr(puppet.db, "race", None) if puppet else None
            cls = getattr(puppet.db, "charclass", None) if puppet else None
            race = f"|c{race}|n" if race else "|cUnknown|n"
            cls = f"|c{cls}|n" if cls else "|cUnknown|n"

            idle = time_format(time.time() - sess.cmd_last, 0)

            row = []
            if is_admin:
                row.append(account.key)
            row.extend([charname, title, race, cls, idle])
            table.add_row(*row)

        caller.msg(str(table))
