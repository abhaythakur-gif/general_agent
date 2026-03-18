"""
app/config/loader.py
---------------------
Merges static defaults with any DB/env overrides.
Extend this module when you add per-tenant or runtime config loading.
"""

from app.config.settings import settings


def get_settings():
    """Return the active settings instance (single source of truth)."""
    return settings
