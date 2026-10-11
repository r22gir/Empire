"""
EmpireBox Backend Application
"""
__version__ = "1.0.0"

# Data isolation for family editions (Max-e, Maxine). Must run before any
# other app module is imported. No-op on the Workroom.
from app.security import family_fs_guard as _family_fs_guard  # noqa: E402
_family_fs_guard.install()
