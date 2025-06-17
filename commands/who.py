from evennia.server.sessionhandler import SESSIONS

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
        lines = []

        for sess in sessions:
            if not sess.logged_in:
                continue
            account = sess.account
            puppet = sess.puppet
            if not puppet and not is_admin:
                continue

            name = puppet.get_display_name(caller) if puppet else "None"
            title = puppet.db.title or "" if puppet else ""
            race = getattr(puppet.db, "race", "Unknown") or "Unknown" if puppet else "Unknown"
            cls = getattr(puppet.db, "charclass", "Unknown") or "Unknown" if puppet else "Unknown"

            if title:
                name = f"{name} {title}"

            line = f"{name} (|c{race}|n / |c{cls}|n)"
            if is_admin:
                line = f"{account.key}: {line}"
            lines.append(line)

        caller.msg("\n".join(lines))
