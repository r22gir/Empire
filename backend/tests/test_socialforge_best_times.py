"""SocialForge best-time suggestions — isolated, no live data."""
from app.services.social_best_times import default_windows, engagement_score, suggest_best_times


def test_defaults_when_no_history():
    result = suggest_best_times([], platform="instagram")
    assert result["used_defaults"] is True
    assert result["history_posts"] == 0
    assert len(result["suggestions"]) == 3
    assert all(s["source"] == "default" for s in result["suggestions"])
    assert result["suggestions"][0]["weekday"] == "Wednesday"
    assert result["suggestions"][0]["hour"] == 11


def test_unknown_platform_uses_generic_defaults():
    result = suggest_best_times([], platform="nextdoor")
    assert result["used_defaults"] is True
    labels = [s["label"] for s in result["suggestions"]]
    assert any("Tue" in label for label in labels)


def test_history_overrides_defaults_with_enough_samples():
    posts = []
    for i in range(6):
        posts.append({
            "platform": "instagram",
            "status": "posted",
            "posted_at": f"2026-04-{7 + i:02d}T19:00:00",  # Tue Apr 7 2026 is a Tuesday
            "engagement": {"likes": 40, "comments": 8, "shares": 2, "reach": 400},
        })
    thursdays = [
        "2026-04-02", "2026-04-09", "2026-04-16",
        "2026-04-23", "2026-04-30", "2026-05-07",
    ]
    for post, day in zip(posts, thursdays):
        post["posted_at"] = f"{day}T15:00:00"

    result = suggest_best_times(posts, platform="instagram")
    assert result["used_defaults"] is False
    assert result["suggestions"][0]["source"] == "history"
    assert result["suggestions"][0]["weekday"] == "Thursday"
    assert result["suggestions"][0]["hour"] == 15
    assert result["suggestions"][0]["sample_size"] >= 2


def test_filters_other_platforms_and_drafts():
    posts = [
        {"platform": "facebook", "status": "posted", "posted_at": "2026-04-08T10:00:00",
         "engagement": {"likes": 99}},
        {"platform": "instagram", "status": "draft", "posted_at": "2026-04-08T10:00:00",
         "engagement": {"likes": 99}},
    ]
    result = suggest_best_times(posts, platform="instagram")
    assert result["used_defaults"] is True
    assert result["history_posts"] == 0


def test_engagement_weights_comments_and_shares():
    light = engagement_score({"likes": 10, "comments": 0, "shares": 0, "reach": 0})
    heavy = engagement_score({"likes": 10, "comments": 5, "shares": 2, "reach": 0})
    assert heavy > light


def test_default_windows_are_sane():
    windows = default_windows("linkedin")
    assert windows[0]["hour"] == 8
    assert 0 <= windows[0]["hour"] <= 23
