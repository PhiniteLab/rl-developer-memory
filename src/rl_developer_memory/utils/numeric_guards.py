from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(slots=True, frozen=True)
class NumericGuardResult:
    finite: bool
    clipped_update: float
    gradient_norm: float
    exploded: bool


@dataclass(slots=True, frozen=True)
class FiniteMetricCheck:
    finite: bool
    invalid_keys: tuple[str, ...]
    invalid_values: dict[str, float]


@dataclass(slots=True, frozen=True)
class UpdateGuardResult:
    update: float
    reference_scale: float
    ratio: float
    exploded: bool


def is_finite_number(value: float) -> bool:
    return math.isfinite(float(value))


def apply_gradient_clip(update: float, *, max_norm: float) -> NumericGuardResult:
    normalized_update = float(update)
    gradient_norm = abs(normalized_update)
    if not is_finite_number(normalized_update):
        return NumericGuardResult(finite=False, clipped_update=0.0, gradient_norm=gradient_norm, exploded=True)
    if gradient_norm <= max_norm:
        return NumericGuardResult(finite=True, clipped_update=normalized_update, gradient_norm=gradient_norm, exploded=False)
    clipped = max(-max_norm, min(max_norm, normalized_update))
    return NumericGuardResult(finite=True, clipped_update=clipped, gradient_norm=gradient_norm, exploded=True)


def detect_plateau(history: Sequence[float], *, patience: int, min_delta: float) -> bool:
    if len(history) < max(patience, 2):
        return False
    recent = [float(item) for item in history[-patience:]]
    return max(recent) - min(recent) <= float(min_delta)


def ensure_finite_metrics(metrics: Mapping[str, float]) -> FiniteMetricCheck:
    invalid = {key: float(value) for key, value in metrics.items() if not is_finite_number(float(value))}
    return FiniteMetricCheck(finite=not invalid, invalid_keys=tuple(sorted(invalid)), invalid_values=invalid)


def detect_exploding_update(
    update: float,
    *,
    reference_scale: float,
    ratio_threshold: float,
    absolute_threshold: float,
) -> UpdateGuardResult:
    normalized_update = abs(float(update))
    normalized_reference = max(abs(float(reference_scale)), 1e-8)
    ratio = normalized_update / normalized_reference
    exploded = (not is_finite_number(float(update))) or normalized_update > float(absolute_threshold) or ratio > float(ratio_threshold)
    return UpdateGuardResult(
        update=float(update),
        reference_scale=normalized_reference,
        ratio=ratio,
        exploded=exploded,
    )
