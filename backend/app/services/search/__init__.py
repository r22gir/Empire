"""Universal in-app search for Command Center / Max.

Edition-isolated, fail-closed, per-source timeouts. Max (Rafael) searches
every life area and business. Family editions never see Workroom-only
screens or data. Maxine never surfaces Argos Campestre legal/company details.
"""

from app.services.search.universal import run_universal_search

__all__ = ["run_universal_search"]
