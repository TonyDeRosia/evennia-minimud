from evennia import CmdSet
from ..command import Command


class CmdPull(Command):
    """Pull a character into play and take control."""

    key = "@pull"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Usage: @pull <character>")
            return
        target = caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        if target.sessions.count():
            caller.msg(f"{target.key} is already puppeted.")
            return
        if not target.access(caller.account, "puppet"):
            caller.msg("You do not have permission to puppet that character.")
            return
        if caller.location:
            target.move_to(caller.location, quiet=True)
        caller.account.puppet_object(self.session, target)
        caller.msg(f"You pull {target.key} to you and take control.")
        target.msg(f"You are pulled into the game by {caller.key}.")


class CmdPush(Command):
    """Unpuppet a controlled character."""

    key = "@push"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Usage: @push <character>")
            return
        target = caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        sess = target.sessions.get()
        if isinstance(sess, list):
            sess = sess[0] if sess else None
        if not sess:
            caller.msg(f"{target.key} is not currently puppeted.")
            return
        account = sess.get_account() if hasattr(sess, "get_account") else sess.account
        if account != caller.account:
            caller.msg(f"You are not controlling {target.key}.")
            return
        caller.account.unpuppet_object(sess)
        sess.disconnect()
        caller.msg(f"You push {target.key} out of the game.")


class CmdPuppet(Command):
    """Temporarily puppet another character without giving up your own body."""

    key = "@puppet"
    aliases = ["ghost"]
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        if caller.ndb.puppet_proxy and not self.args:
            target = caller.ndb.puppet_proxy
            caller.ndb.puppet_proxy = None
            caller.msg(f"Stopped puppeting {target.key}.")
            return
        if not self.args:
            caller.msg("Usage: @puppet <character>")
            return
        if caller.ndb.puppet_proxy:
            caller.msg("Already puppeting a character. Use '@puppet' to stop first.")
            return
        target = caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        if target.sessions.count():
            caller.msg(f"{target.key} is already puppeted.")
            return
        caller.ndb.puppet_proxy = target
        caller.msg(f"You begin puppeting {target.key}. Use '@puppet' again to stop.")


class PuppetCmdSet(CmdSet):
    """CmdSet bundling puppeting utilities."""

    key = "PuppetCmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdPull)
        self.add(CmdPush)
        self.add(CmdPuppet)
