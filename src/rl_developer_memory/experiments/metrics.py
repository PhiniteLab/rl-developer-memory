from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import DefaultDict


class MetricsCollector:
    """Collect scalar metrics and summarize them into risk-aware aggregates."""

    def __init__(self) -> None:
        self._series: DefaultDict[str, list[float]] = defaultdict(list)

    def log(self, **metrics: float) -> None:
        for key, value in metrics.items():
            self._series[key].append(float(value))

    def summary(self) -> dict[str, float]:
        payload: dict[str, float] = {}
        for key, values in self._series.items():
            payload[f"{key}_mean"] = mean(values)
        if "bellman_residual" in self._series:
            values = [abs(item) for item in self._series["bellman_residual"]]
            payload["bellman_residual_abs_mean"] = mean(values)
        if "advantage" in self._series:
            values = [abs(item) for item in self._series["advantage"]]
            payload["advantage_abs_mean"] = mean(values)
        if "hjb_residual" in self._series:
            values = [abs(item) for item in self._series["hjb_residual"]]
            payload["hjb_residual_abs_mean"] = mean(values)
        if "constraint_margin" in self._series:
            payload["constraint_margin_mean"] = mean(self._series["constraint_margin"])
        if "lyapunov_margin" not in payload:
            payload["lyapunov_margin"] = min(payload.get("return_mean", 0.0), 1.0)
        return payload
