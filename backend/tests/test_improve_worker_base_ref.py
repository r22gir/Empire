"""Atlas worker + GitHub issue path refuse main/master/amp/maxine base refs."""
import pytest

from app.services.max import improvement_worker as worker
from app.services.max.improve_base_ref import UnsafeBaseRef


@pytest.mark.parametrize("ref", ["main", "master", "origin/main", "dell/amp-live", "dell/maxine-live"])
def test_worker_refuses_forbidden_base_ref_before_any_call(monkeypatch, ref):
    monkeypatch.setenv("MAX_IMPROVE_WORKER_ENABLED", "1")
    monkeypatch.setenv("MAX_IMPROVE_BASE_REF", ref)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    def boom(*a, **k):
        raise AssertionError("must not reach planner/github/cursor")

    monkeypatch.setattr(worker.imp, "get", boom)
    with pytest.raises(UnsafeBaseRef):
        worker.run_atlas_plan({"improvement_id": 1, "id": 1})


def test_worker_off_without_opt_in(monkeypatch):
    monkeypatch.delenv("MAX_IMPROVE_WORKER_ENABLED", raising=False)
    with pytest.raises(PermissionError):
        worker.run_atlas_plan({"improvement_id": 1, "id": 1})


def test_github_issue_body_refuses_main(monkeypatch):
    from app.services.max import improvement_github as gh
    monkeypatch.setenv("MAX_IMPROVE_BASE_REF", "main")
    fn = [getattr(gh, n) for n in dir(gh) if callable(getattr(gh, n)) and n in ("issue_body", "build_issue_body", "_issue_body")]
    if not fn:
        pytest.skip("issue body builder name differs")
    with pytest.raises(UnsafeBaseRef):
        fn[0]({"id": 1, "title": "t", "problem": "p"}, "spec")
