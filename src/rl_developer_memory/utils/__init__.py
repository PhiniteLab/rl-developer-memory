"""Utility helpers for reproducibility, numerics, and serialization."""

from .diagnostics import AnomalyEvent, FailureSignature, FailureSignatureCapture, TrainingDiagnosticsCollector
from .numeric_guards import (
    FiniteMetricCheck,
    NumericGuardResult,
    UpdateGuardResult,
    apply_gradient_clip,
    detect_exploding_update,
    detect_plateau,
    ensure_finite_metrics,
    is_finite_number,
)
from .reproducibility import DeterministicSeedDiscipline, seed_everything
from .serialization import atomic_write_json, load_json_file, safe_json_dumps

__all__ = [
    "AnomalyEvent",
    "DeterministicSeedDiscipline",
    "FailureSignature",
    "FailureSignatureCapture",
    "FiniteMetricCheck",
    "NumericGuardResult",
    "TrainingDiagnosticsCollector",
    "UpdateGuardResult",
    "apply_gradient_clip",
    "atomic_write_json",
    "detect_exploding_update",
    "detect_plateau",
    "ensure_finite_metrics",
    "is_finite_number",
    "load_json_file",
    "safe_json_dumps",
    "seed_everything",
]
