"""Studio base-ref resolver: 1013b → 1013, never main/master/amp/maxine."""
from app.services.max.improve_base_ref import (
    STUDIO_FALLBACK,
    STUDIO_PRIMARY,
    UnsafeBaseRef,
    assert_safe_improve_base_ref,
    is_forbidden_base_ref,
    resolve_base_ref,
)


def test_default_is_studio_1013b_when_that_ref_exists(monkeypatch):
    monkeypatch.delenv("MAX_IMPROVE_BASE_REF", raising=False)
    monkeypatch.setenv("MAX_IMPROVE_EXISTING_REFS", f"{STUDIO_PRIMARY},{STUDIO_FALLBACK}")
    assert resolve_base_ref() == STUDIO_PRIMARY


def test_falls_back_to_1013_when_1013b_missing(monkeypatch):
    monkeypatch.delenv("MAX_IMPROVE_BASE_REF", raising=False)
    monkeypatch.setenv("MAX_IMPROVE_EXISTING_REFS", STUDIO_FALLBACK)
    assert resolve_base_ref() == STUDIO_FALLBACK


def test_explicit_1013b_falls_back_when_missing(monkeypatch):
    monkeypatch.setenv("MAX_IMPROVE_BASE_REF", STUDIO_PRIMARY)
    monkeypatch.setenv("MAX_IMPROVE_EXISTING_REFS", STUDIO_FALLBACK)
    assert resolve_base_ref() == STUDIO_FALLBACK


def test_explicit_safe_override(monkeypatch):
    monkeypatch.setenv("MAX_IMPROVE_BASE_REF", STUDIO_FALLBACK)
    monkeypatch.setenv("MAX_IMPROVE_EXISTING_REFS", f"{STUDIO_PRIMARY},{STUDIO_FALLBACK}")
    assert resolve_base_ref() == STUDIO_FALLBACK


def test_refuses_main_master_and_family_branches(monkeypatch):
    monkeypatch.setenv("MAX_IMPROVE_EXISTING_REFS", "main,master,amp,maxine,dell/amp-local")
    for ref in (
        "main",
        "master",
        "refs/heads/main",
        "amp",
        "maxine",
        "dell/amp-local-20261010",
        "cursor/maxine-ui",
        "amp/hotfix",
        "maxine/studio",
    ):
        monkeypatch.setenv("MAX_IMPROVE_BASE_REF", ref)
        assert is_forbidden_base_ref(ref)
        try:
            resolve_base_ref()
            raise AssertionError(f"should refuse {ref}")
        except UnsafeBaseRef as exc:
            assert "Refusing" in str(exc)


def test_guard_blocks_issue_or_pr_target():
    for ref in ("main", "master", "amp", "maxine"):
        try:
            assert_safe_improve_base_ref(ref)
            raise AssertionError(ref)
        except UnsafeBaseRef:
            pass
    assert assert_safe_improve_base_ref(STUDIO_PRIMARY) == STUDIO_PRIMARY
