from django.conf import settings
from evennia.accounts.models import AccountDB
from evennia.utils import logger


def admin_debug(msg: str) -> None:
    """Send a debug ``msg`` to connected admins and log it."""
    logger.log_debug(msg)
    if not getattr(settings, "COMBAT_ADMIN_DEBUG", False):
        return
    for account in AccountDB.objects.filter(is_superuser=True):
        try:
            if account.is_connected:
                account.msg(msg)
        except Exception:
            pass
