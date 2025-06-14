"""Test package setup for Evennia."""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

# Ensure Evennia fully initializes so SESSION_HANDLER and other globals exist
import evennia

if getattr(evennia, "SESSION_HANDLER", None) is None:
    evennia._init()

