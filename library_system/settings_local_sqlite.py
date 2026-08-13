"""
THROWAWAY LOCAL TEST SETTINGS -- not used by the real app or CI.

The project's real settings.py (Asiedu's file) points DATABASES at
PostgreSQL via .env. Nobody has committed migrations yet, and this machine's
local Postgres instance needs real credentials filled into .env before
`manage.py migrate` will work against it.

This module exists only so `apps.notifications` (and, incidentally, every
other app's models) can be migrated and unit-tested against SQLite without
touching anyone's Postgres setup. Delete it once the team has real DB
credentials wired up, or just ignore it -- it changes nothing about the
real settings.py.

Usage:
    python manage.py test apps.notifications --settings=library_system.settings_local_sqlite
"""

from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_local_test.sqlite3",  # noqa: F405
    }
}
