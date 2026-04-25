"""Validation helpers for SimulaLab JSONL rows and generated datasets."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .schemas import (
    DOMAIN,
    EXPECTED_MODES,
    EXPECTED_ROUTES,
    INTENDED_USE,
    REQUIRED_FIELDS,
    SCHEMA_VERSION,
    SECRET_MARKERS,
)


class SimulaValidationError(ValueError):
    """Raised when a SimulaLab row or dataset violates the Phase 1 schema."""


@dataclass
class ValidationResult:
    passed: bool
    sample_count: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _prefix(row_number: int | None) -> str:
    return f"row {row_number}: " if row_number is not None else ""


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _iter_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_strings(nested)


def _secret_hits(row: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for text in _iter_strings(row):
        lowered = text.lower()
        for marker in SECRET_MARKERS:
            if marker in lowered:
                hits.append(marker)
    return sorted(set(hits))


def validate_row(row: dict[str, Any], row_number: int | None = None) -> None:
    """Validate a single JSON-serializable dataset row."""
    prefix = _prefix(row_number)
    if not isinstance(row, dict):
        raise SimulaValidationError(f"{prefix}row must be an object")

    missing = [field_name for field_name in REQUIRED_FIELDS if field_name not in row]
    if missing:
        raise SimulaValidationError(f"{prefix}missing required fields: {', '.join(missing)}")

    for field_name in ("id", "domain", "input", "expected_mode", "expected_route", "ideal_response_summary"):
        if not isinstance(row[field_name], str) or not row[field_name].strip():
            raise SimulaValidationError(f"{prefix}{field_name} must be a non-empty string")

    if row["domain"] != DOMAIN:
        raise SimulaValidationError(f"{prefix}domain must be {DOMAIN}")

    if row["expected_mode"] not in EXPECTED_MODES:
        raise SimulaValidationError(f"{prefix}invalid expected_mode: {row['expected_mode']}")

    if row["expected_route"] not in EXPECTED_ROUTES:
        raise SimulaValidationError(f"{prefix}invalid expected_route: {row['expected_route']}")

    if not isinstance(row["requires_approval"], bool):
        raise SimulaValidationError(f"{prefix}requires_approval must be a boolean")

    for field_name in ("must_check", "must_not_do"):
        values = row[field_name]
        if not isinstance(values, list) or not all(isinstance(item, str) and item.strip() for item in values):
            raise SimulaValidationError(f"{prefix}{field_name} must be a list of non-empty strings")

    if row["synthetic"] is not True:
        raise SimulaValidationError(f"{prefix}synthetic must be true")

    if row["intended_use"] != INTENDED_USE:
        raise SimulaValidationError(f"{prefix}intended_use must be {INTENDED_USE}")

    if row["schema_version"] != SCHEMA_VERSION:
        raise SimulaValidationError(f"{prefix}schema_version must be {SCHEMA_VERSION}")

    hits = _secret_hits(row)
    if hits:
        raise SimulaValidationError(f"{prefix}possible secret marker found: {', '.join(hits)}")


def validate_rows(rows: list[dict[str, Any]]) -> ValidationResult:
    errors: list[str] = []
    for index, row in enumerate(rows, start=1):
        try:
            validate_row(row, row_number=index)
        except SimulaValidationError as exc:
            errors.append(str(exc))
    return ValidationResult(passed=not errors, sample_count=len(rows), errors=errors)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise SimulaValidationError(f"row {line_number}: invalid JSONL: {exc}") from exc
            if not isinstance(value, dict):
                raise SimulaValidationError(f"row {line_number}: JSONL item must be an object")
            rows.append(value)
    return rows


def validate_jsonl(path: Path) -> ValidationResult:
    rows = read_jsonl(path)
    return validate_rows(rows)
