"""Unit tests for new callbacks: MetricLogger, LRSchedule, GradientNorm."""

from __future__ import annotations

from rl_developer_memory.agents.base import ActorCriticAgent, AgentContext
from rl_developer_memory.callbacks.base import (
    CallbackManager,
    CallbackState,
    GradientNormCallback,
    LRScheduleCallback,
    MetricLoggerCallback,
)
from rl_developer_memory.trainers.schedules import LinearDecayLR


class TestMetricLoggerCallback:
    def test_logs_all_metrics(self) -> None:
        cb = MetricLoggerCallback()
        state = CallbackState()
        cb.on_step(step=1, metrics={"reward": 1.0, "loss": 0.5}, state=state)
        assert len(cb.log) == 1
        assert cb.log[0]["reward"] == 1.0
        assert cb.log[0]["_step"] == 1.0

    def test_logs_selected_keys(self) -> None:
        cb = MetricLoggerCallback(keys=("reward",))
        state = CallbackState()
        cb.on_step(step=1, metrics={"reward": 1.0, "loss": 0.5}, state=state)
        assert "reward" in cb.log[0]
        assert "loss" not in cb.log[0]

    def test_multiple_steps(self) -> None:
        cb = MetricLoggerCallback()
        state = CallbackState()
        for s in range(1, 6):
            cb.on_step(step=s, metrics={"r": float(s)}, state=state)
        assert len(cb.log) == 5


class TestLRScheduleCallback:
    def test_updates_agent_lr(self) -> None:
        agent = ActorCriticAgent(
            context=AgentContext(
                discount=0.99, learning_rate=0.1,
                entropy_temperature=0.1, target_update_tau=0.05,
            )
        )
        schedule = LinearDecayLR(initial_lr=0.1, final_lr=0.01, total_steps=100)
        cb = LRScheduleCallback(schedule=schedule)
        state = CallbackState(metadata={"agent": agent})
        cb.on_step(step=50, metrics={}, state=state)
        assert agent.context.learning_rate < 0.1

    def test_no_agent_no_crash(self) -> None:
        schedule = LinearDecayLR(initial_lr=0.1, final_lr=0.01, total_steps=100)
        cb = LRScheduleCallback(schedule=schedule)
        state = CallbackState()
        cb.on_step(step=50, metrics={}, state=state)  # no crash


class TestGradientNormCallback:
    def test_stops_on_explosion(self) -> None:
        cb = GradientNormCallback(max_gradient_norm=10.0)
        state = CallbackState()
        cb.on_step(step=5, metrics={"gradient_norm": 100.0}, state=state)
        assert state.should_stop

    def test_normal_gradient_continues(self) -> None:
        cb = GradientNormCallback(max_gradient_norm=10.0)
        state = CallbackState()
        cb.on_step(step=5, metrics={"gradient_norm": 5.0}, state=state)
        assert not state.should_stop

    def test_missing_key_continues(self) -> None:
        cb = GradientNormCallback(max_gradient_norm=10.0)
        state = CallbackState()
        cb.on_step(step=5, metrics={"reward": 1.0}, state=state)
        assert not state.should_stop


class TestCallbackManagerWithNew:
    def test_multiple_callbacks(self) -> None:
        logger = MetricLoggerCallback()
        grad = GradientNormCallback(max_gradient_norm=100.0)
        mgr = CallbackManager(callbacks=[logger, grad])
        mgr.on_step(step=1, metrics={"reward": 1.0, "gradient_norm": 5.0})
        assert len(logger.log) == 1
        assert not mgr.state.should_stop
