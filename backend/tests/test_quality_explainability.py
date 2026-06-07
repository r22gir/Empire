"""Tests for quality explainability in MAX chat responses.

Previously the UI showed "Quality issue detected" with no explanation, while
MAX's text denied a quality issue. The fix enriches the `quality` field in
the ChatResponse with the reason codes from the underlying
response_quality_engine, so the UI can show the founder WHY a quality
issue was flagged.
"""
from app.services.max.response_quality_engine import (
    Channel,
    ResponseQualityEngine,
    QualityResult,
    QualityIssue,
    Severity,
)


def test_quality_issue_dataclass_carries_reason_fields():
    """QualityIssue has check/severity/message/auto_fixed/fix_description."""
    issue = QualityIssue(
        check="duplication",
        severity=Severity.MEDIUM,
        message="Removed 2 duplicate paragraph(s)",
        auto_fixed=True,
        fix_description="Duplicate paragraphs removed",
    )
    assert issue.check == "duplication"
    assert issue.severity == Severity.MEDIUM
    assert issue.auto_fixed is True


def test_quality_result_severity_property():
    """QualityResult.severity returns 'critical'/'medium'/'low'/'none'."""
    result_none = QualityResult(
        original="ok",
        cleaned="ok",
        channel="chat",
        mode="fast",
        issues=[],
    )
    assert result_none.severity == "none"

    result_low = QualityResult(
        original="x",
        cleaned="x",
        channel="chat",
        mode="fast",
        issues=[QualityIssue(check="ai_artifacts", severity=Severity.LOW, message="x")],
    )
    assert result_low.severity == "low"

    result_crit = QualityResult(
        original="x",
        cleaned="x",
        channel="chat",
        mode="fast",
        issues=[QualityIssue(check="quote_math", severity=Severity.CRITICAL, message="x")],
    )
    assert result_crit.severity == "critical"


def test_quality_engine_produces_issues_for_duplication():
    """The duplication check fires on clearly-repeated paragraphs."""
    eng = ResponseQualityEngine()
    text = (
        "This is the first paragraph of the response.\n\n"
        "This is the first paragraph of the response.\n\n"
        "This is the second paragraph which is genuinely different content."
    )
    result = eng.validate(text, channel=Channel.CHAT)
    assert any(i.check == "duplication" for i in result.issues)


def test_quality_engine_produces_issues_for_ai_artifacts():
    eng = ResponseQualityEngine()
    text = "As an AI language model, I think the answer is 42."
    result = eng.validate(text, channel=Channel.CHAT)
    assert any(i.check == "ai_artifacts" for i in result.issues)


def test_quality_result_is_serializable_for_api():
    """The issues list can be serialized with check/severity/message."""
    result = QualityResult(
        original="x",
        cleaned="x",
        channel="chat",
        mode="fast",
        issues=[
            QualityIssue(
                check="duplication",
                severity=Severity.MEDIUM,
                message="Removed 1 duplicate paragraph(s)",
                auto_fixed=True,
                fix_description="Duplicate paragraphs removed",
            ),
        ],
    )
    # This is what router.py attaches to ChatResponse.quality
    explainable = [
        {
            "check": i.check,
            "severity": i.severity.value if hasattr(i.severity, "value") else str(i.severity),
            "message": i.message,
            "auto_fixed": i.auto_fixed,
            "fix_description": i.fix_description,
        }
        for i in result.issues
    ]
    assert len(explainable) == 1
    assert explainable[0]["check"] == "duplication"
    assert explainable[0]["severity"] == "medium"
    assert "duplicate" in explainable[0]["message"].lower()
