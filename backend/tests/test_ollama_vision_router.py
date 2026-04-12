import asyncio
import httpx


def test_moondream_is_primary_vision_model_and_llava_is_fallback(monkeypatch):
    import app.services.ollama_vision_router as router

    calls: list[str] = []

    class FakeResponse:
        status_code = 200

        def __init__(self, model: str):
            self.model = model

        def raise_for_status(self):
            return None

        def json(self):
            return {"response": f"{self.model} ok"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            model = json["model"]
            calls.append(model)
            if model == "moondream":
                raise RuntimeError("moondream unavailable")
            return FakeResponse(model)

    monkeypatch.setattr(router.httpx, "AsyncClient", FakeClient)

    assert router.vision_model_order() == ["moondream", "llava"]

    text, model = asyncio.run(
        router.generate_vision_response(
            prompt="describe the image",
            image_b64="abc123",
        )
    )

    assert calls == ["moondream", "llava"]
    assert model == "llava"
    assert text == "llava ok"
