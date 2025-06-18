from evennia.server.sessionhandler import SESSION_HANDLER
from evennia.utils.evtable import EvTable

from ..command import Command


class CmdWhoIP(Command):
    """List online sessions with IP addresses."""

    key = "@whoip"
    aliases = ["@sockstat"]
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        filter_arg = self.args.strip().lower()
        table = EvTable(
            "|cAccount|n",
            "|cCharacter|n",
            "|cIP|n",
            "|cProto|n",
            "|cHost|n",
            "|cID|n",
            border="cells",
        )
        for sess in SESSION_HANDLER.get_sessions():
            account = sess.get_account() if hasattr(sess, "get_account") else sess.account
            account_name = account.key if account else "None"
            puppet = sess.get_puppet() if hasattr(sess, "get_puppet") else sess.puppet
            char_name = puppet.key if puppet else "None"
            ip = sess.address[0] if sess.address else "?"
            proto = getattr(sess, "protocol_key", "?")
            host = getattr(sess, "hostname", "") or "?"
            sid = getattr(sess, "sessid", getattr(sess, "sessionid", "?"))

            if filter_arg and filter_arg not in account_name.lower() and filter_arg not in ip.lower():
                continue

            table.add_row(account_name, char_name, ip, proto, host, str(sid))

        if table.nrows:
            self.msg(str(table))
        else:
            self.msg("No matching sessions found.")

