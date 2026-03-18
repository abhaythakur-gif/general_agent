"""
app/db/mongo.py — SHIM
-----------------------
Backward-compatibility shim. All real logic lives in resources/mongodb.py.
Do not add new code here.
"""

# Re-export everything callers expect from the new canonical location.
from resources.mongodb import (  # noqa: F401
    get_mongo_db,
    ensure_indexes,
    get_or_create_user,
)

# Legacy code below is dead — kept only for reference, never executed.
if False:
    _LEGACY_PLACEHOLDER = None


# shim complete
