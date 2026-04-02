from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rl_developer_memory.utils.numeric_guards import is_finite_number


@dataclass(slots=True)
class CallbackState:
    should_stop: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class Callback:
    """Base training callback."""

    def on_step(self, *, step: int, metrics: dict[str, float], state: CallbackState) -> None:
        return None

    def on_train_end(self, *, step: int, metrics: dict[str, float], state: CallbackState) -> None:
        return None


class CallbackManager:
    """Fan out callback events to a list of callbacks."""

    def __init__(self, callbacks: list[Callback] | None = None) -> None:
        self.callbacks = callbacks or []
        self.state = CallbackState()

    def on_step(self, *, step: int, metrics: dict[str, float]) -> CallbackState:
        for callback in self.callbacks:
            callback.on_step(step=step, metrics=metrics, state=self.state)
        return self.state

    def on_train_end(self, *, step: int, metrics: dict[str, float]) -> CallbackState:
        for callback in self.callbacks:
            callback.on_train_end(step=step, metrics=metrics, state=self.state)
        return self.state


class CheckpointCallback(Callback):
    """Trigger checkpointing every N steps via a callable."""

    def __init__(self, *, every_steps: int, saver: Any) -> None:
        self.every_steps = max(int(every_steps), 1)
        self.saver = saver

    def on_step(self, *, step: int, metrics: dict[str, float], state: CallbackState) -> None:
        if step % self.every_steps == 0:
            self.saver(step=step, metrics=metrics)


class AnomalyCallback(Callback):
    """Capture NaN/Inf metrics and request early stop when needed."""

    def on_step(self, *, step: int, metrics: dict[str, float], state: CallbackState) -> None:
        bad_keys = [key for key, value in metrics.items() if not is_finite_number(value)]
        if bad_keys:
            state.should_stop = True
            state.metadata.setdefault("anomalies", []).append({"step": step, "keys": bad_keys})


class EarlyStopCallback(Callback):
    """Stop when a metric plateaus for too long."""

    def __init__(self, *, metric_key: str, patience: int, min_delta: float) -> None:
        self.metric_key = metric_key
        self.patience = max(int(patience), 1)
        self.min_delta = float(min_delta)
        self.history: list[float] = []

    def on_step(self, *, step: int, metrics: dict[str, float], state: CallbackState) -> None:
        value = metrics.get(self.metric_key)
        if value is None:
            return
        self.history.append(float(value))
        if len(self.history) < self.patience:
            return
        recent = self.history[-self.patience :]
        if max(recent) - min(recent) <= self.min_delta:
            state.should_stop = True
            state.metadata.setdefault("early_stop", []).append({"step": step, "metric": self.metric_key})
