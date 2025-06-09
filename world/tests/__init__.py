import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()
import evennia
if getattr(evennia, "SESSION_HANDLER", None) is None:
    evennia._init()
