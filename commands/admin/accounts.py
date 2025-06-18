from django.db.models import Q
from evennia import CmdSet
from evennia.accounts.models import AccountDB
from evennia.utils.evtable import EvTable

from ..command import Command


class CmdAccounts(Command):
    """List accounts on the server."""

    key = "@accounts"
    aliases = ["@listaccounts"]
    locks = "cmd:perm(Builder) or perm(Admin)"
    help_category = "Admin"

    def parse(self):
        """Extract options."""
        self.search_name = None
        self.only_staff = False
        self.page = 1

        args = self.args.strip()
        if not args:
            return
        parts = args.split()
        idx = 0
        while idx < len(parts):
            part = parts[idx]
            if part == "name" and idx + 1 < len(parts):
                self.search_name = parts[idx + 1]
                idx += 2
            elif part == "staff":
                self.only_staff = True
                idx += 1
            elif part.isdigit():
                self.page = int(part)
                idx += 1
            else:
                idx += 1

    def func(self):
        """Display account list."""
        qs = AccountDB.objects.all().order_by("username")
        if self.search_name:
            qs = qs.filter(username__icontains=self.search_name)
        if self.only_staff:
            qs = qs.filter(Q(db_is_staff=True) | Q(db_is_superuser=True))

        accounts = list(qs)
        total = len(accounts)
        per_page = 20
        pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(self.page, pages))

        start = (page - 1) * per_page
        end = start + per_page
        subset = accounts[start:end]

        table = EvTable(
            "|wAccount Name|n",
            "|wChars|n",
            "|wFlags|n",
            "|wLast Login|n",
            border="cells",
        )

        for acc in subset:
            flags = []
            if acc.db_is_superuser:
                flags.append("Superuser")
            elif acc.db_is_staff:
                flags.append("Staff")
            table.add_row(
                acc.username,
                str(acc.characters.all().count()),
                ", ".join(flags) if flags else "",
                str(acc.db_last_login) if acc.db_last_login else "Never",
            )

        header = f"Page {page}/{pages}"
        if total == 0:
            self.msg("No accounts found.")
            return
        self.msg(header)
        self.msg(str(table))


class AccountsCmdSet(CmdSet):
    key = "AccountsCmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdAccounts)
