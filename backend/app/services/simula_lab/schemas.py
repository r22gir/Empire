"""Shared schema constants for the Empire-native SimulaLab pilot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DATASET_ID = "max_command_routing_v1"
DOMAIN = "max_command_routing"
SCHEMA_VERSION = "1.0"
INTENDED_USE = "eval_only"
GENERATOR_ID = "deterministic_internal_v1"
DEFAULT_OUTPUT_ROOT = Path("/data/empire/simula")

EXPECTED_MODES = frozenset(
    {
        "answer",
        "code_task",
        "approval_required",
        "email",
        "status_check",
        "refuse",
        "clarify",
    }
)

EXPECTED_ROUTES = frozenset(
    {
        "max_only",
        "openclaw",
        "gmail",
        "calendar",
        "backend_api",
        "frontend",
        "manual",
    }
)

REQUIRED_FIELDS = (
    "id",
    "domain",
    "input",
    "expected_mode",
    "expected_route",
    "requires_approval",
    "must_check",
    "must_not_do",
    "ideal_response_summary",
    "synthetic",
    "intended_use",
    "schema_version",
)

SECRET_MARKERS = (
    "sk-",
    "xai-",
    "ghp_",
    "api_key",
    "openai_api_key",
    "anthropic_api_key",
    "password=",
    "token=",
)

OUTPUT_DIRECTORIES = (
    "datasets",
    "manifests",
    "reports",
    "taxonomies",
    "eval_runs",
)


@dataclass(frozen=True)
class SimulaOutputPaths:
    root: Path
    dataset: Path
    manifest: Path
    report: Path
    taxonomies: Path
    eval_runs: Path

    def as_strings(self) -> dict[str, str]:
        return {
            "root": str(self.root),
            "dataset": str(self.dataset),
            "manifest": str(self.manifest),
            "report": str(self.report),
            "taxonomies": str(self.taxonomies),
            "eval_runs": str(self.eval_runs),
        }
