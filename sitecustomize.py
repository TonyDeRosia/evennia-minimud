import os
import django
import evennia

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()
if getattr(evennia, "SESSION_HANDLER", None) is None:
    evennia._init()
