import asyncio
import importlib

from fastapi import BackgroundTasks, Response

from app.services.max.ambiguity_gate import should_clarify_inventory_request

max_router = importlib.import_module("app.routers.max.router")


def test_inventory_live_magazines_clarifies_before_category_plan():
    assert should_clarify_inventory_request("inventory my live magazines") is True

    request = max_router.ChatRequest(
        message="inventory my live magazines",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "clarification-gate"
    assert "confirm the category" in response.response
    assert "LIFE magazine issues" in response.response
    assert "Playboy" not in response.response
    assert response.metadata["skill_used"] == "inventory_ambiguity_gate"


def test_specific_inventory_category_can_pass_gate():
    assert should_clarify_inventory_request("inventory my LIFE magazines from 1969") is False
