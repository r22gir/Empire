"""Empire-native SimulaLab Phase 1 dataset/eval pilot."""

from .generator import generate_samples
from .registry import run_dataset
from .schemas import DATASET_ID, DOMAIN, SCHEMA_VERSION
from .validator import SimulaValidationError, validate_row, validate_rows

__all__ = [
    "DATASET_ID",
    "DOMAIN",
    "SCHEMA_VERSION",
    "SimulaValidationError",
    "generate_samples",
    "run_dataset",
    "validate_row",
    "validate_rows",
]
