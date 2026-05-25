"""Test that /api/v1/dev/git reports runtime truth, not hardcoded paths."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_dev_git_runtime_truth():
    """Verify dev/git derives repo_root from running code path, not ~/empire-repo."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/dev/git")
        assert r.status_code == 200
        data = r.json()

    # Must report the actual repo root this code lives in
    assert data["repo_root"] == "/home/rg/empire-repo-main", (
        f"Expected /home/rg/empire-repo-main, got {data['repo_root']}"
    )
    # Must report the actual branch
    assert data["branch"] == "main", f"Expected main, got {data['branch']}"
    # Must report the backend port we're actually running on
    assert data["backend_port"] == 8000
    # Must report the expected frontend port for stable lane
    assert data["frontend_expected_port"] == 3005
    # runtime_lane must be stable/main
    assert data["runtime_lane"] == "stable/main"
    # source_method must indicate runtime path derivation
    assert data["source_method"] == "runtime_path"
    # commit_hash must be a valid git hash
    assert len(data["commit_hash"]) == 40, f"Expected 40-char hash, got {data['commit_hash']}"
    assert data["short_commit"] == data["commit_hash"][:7]
    # Must have all required fields
    for field in ["repo_root", "backend_cwd", "router_file", "branch", "commit_hash",
                  "short_commit", "commit_message", "dirty", "uncommitted_count",
                  "dirty_files", "runtime_lane", "backend_port", "frontend_expected_port",
                  "source_method"]:
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_dev_git_commit_matches_head():
    """Verify the commit_hash reported matches git rev-parse HEAD of the actual repo."""
    import subprocess
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/dev/git")
        data = r.json()

    # Cross-check against actual git rev-parse on the repo root
    repo_root = "/home/rg/empire-repo-main"
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root, capture_output=True, text=True, timeout=5
    ).stdout.strip()

    assert data["commit_hash"] == head, (
        f"commit_hash {data['commit_hash']} != git HEAD {head}"
    )
