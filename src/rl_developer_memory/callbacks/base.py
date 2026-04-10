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


class MetricLoggerCallback(Callback):
    """Record selected metrics each step for post-hoc analysis."""

    def __init__(self, *, keys: tuple[str, ...] | None = None) -> None:
        self.keys = keys
        self.log: list[dict[str, float]] = []

    def on_step(self, *, step: int, metrics: dict[str, float], state: CallbackState) -> None:
        if self.keys is not None:
            entry = {k: metrics[k] for k in self.keys if k in metrics}
        else:
            entry = dict(metrics)
        entry["_step"] = float(step)
        self.log.append(entry)


class LRScheduleCallback(Callback):
    """Apply a learning-rate schedule to the agent context each step.

    Requires the agent to be stored in ``state.metadata["agent"]``.
    """

    def __init__(self, *, schedule: Any) -> None:
        self.schedule = schedule

    def on_step(self, *, step: int, metrics: dict[str, float], state: CallbackState) -> None:
        agent = state.metadata.get("agent")
        if agent is None:
            return
        new_lr = self.schedule.get_lr(step)
        if hasattr(agent, "context"):
            agent.context.learning_rate = float(new_lr)


class GradientNormCallback(Callback):
    """Stop training if gradient norm exceeds a hard ceiling."""

    def __init__(self, *, max_gradient_norm: float = 100.0) -> None:
        self.max_gradient_norm = float(max_gradient_norm)

    def on_step(self, *, step: int, metrics: dict[str, float], state: CallbackState) -> None:
        grad_norm = metrics.get("gradient_norm", 0.0)
        if grad_norm > self.max_gradient_norm:
            state.should_stop = True
            state.metadata.setdefault("gradient_explosion", []).append(
                {"step": step, "gradient_norm": grad_norm}
            )
