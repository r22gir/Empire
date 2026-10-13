"""AI desk registry is the single source of truth — 17 desks."""
from app.services.max.desks.desk_registry import (
    CANONICAL_DESK_COUNT,
    REGISTERED_DESKS,
    assert_matches_live,
    registered_desk_ids,
    registry_payload,
)


def test_canonical_count_is_seventeen():
    assert CANONICAL_DESK_COUNT == 17
    assert len(REGISTERED_DESKS) == 17
    assert len(set(registered_desk_ids())) == 17


def test_registry_payload_shape():
    payload = registry_payload()
    assert payload["source"] == "desk_registry"
    assert payload["count"] == 17
    ids = [d["id"] for d in payload["desks"]]
    assert "forge" in ids
    assert "codeforge" in ids
    assert "innovation" in ids


def test_live_manager_matches_registry():
    from app.services.max.desks.desk_manager import AIDeskManager

    manager = AIDeskManager()
    manager.initialize()
    assert_matches_live(manager.router.desk_ids)
    assert len(manager.router.desk_ids) == CANONICAL_DESK_COUNT
