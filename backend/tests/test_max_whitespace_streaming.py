from app.services.max.guardrails import sanitize_output_streaming


def _joined_stream(*chunks: str) -> str:
    return "".join(sanitize_output_streaming(chunk) for chunk in chunks)


def test_streaming_preserves_chunk_boundary_whitespace() -> None:
    rendered = _joined_stream(
        "Hi",
        " again. How",
        " can I help you today?",
        " I",
        " am MAX, the founder's command-center brain.",
        " I",
        " will make sure to leave spaces between words when I write.",
    )

    for bad in (
        "Hiagain",
        "HowcanI",
        "IamMAX",
        "Iwillmake",
        "spacesbetweenwords",
        "Thefounder",
        "Runtimecheckrequired",
        "delegationcheckrequired",
    ):
        assert bad not in rendered

    assert "Hi again. How can I help you today?" in rendered
    assert "I am MAX, the founder's command-center brain." in rendered
    assert "I will make sure to leave spaces between words when I write." in rendered
