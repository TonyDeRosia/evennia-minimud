from evennia.commands.default.muxcommand import MuxCommand
from evennia.server.sessionhandler import SESSIONS
from evennia.utils.evtable import EvTable
from evennia.utils.utils import time_format
import time


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
        headers = ["Character", "Title", "Idle"]
        if is_admin:
            headers.insert(0, "Account")
        table = EvTable(*headers, border="cells")

        for sess in sessions:
            if not sess.logged_in:
                continue
            account = sess.account
            puppet = sess.puppet
            delta_cmd = time.time() - sess.cmd_last_visible
            idle = time_format(delta_cmd, 0)
            title = puppet.db.title if puppet else ""
            char = puppet.get_display_name(caller) if puppet else "None"
            if not puppet and not is_admin:
                continue
            row = [char, title, idle]
            if is_admin:
                row.insert(0, account.key)
            table.add_row(*row)

        caller.msg(str(table))
