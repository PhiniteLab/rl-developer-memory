"""Unit tests for evaluation module."""

from __future__ import annotations

from rl_developer_memory.agents.base import ActorCriticAgent, AgentContext
from rl_developer_memory.envs.base import Environment, EnvSpec, StepResult
from rl_developer_memory.evaluation.base import Evaluator


class FixedEnv(Environment):
    """Always returns (+1 reward, same obs, terminated after 2 steps)."""

    def __init__(self) -> None:
        self._step_count = 0
        self.spec = EnvSpec(
            env_id="fixed",
            observation_shape=(1,),
            action_shape=(1,),
            action_low=-1.0,
            action_high=1.0,
        )

    def reset(self) -> float:
        self._step_count = 0
        return 0.0

    def step(self, action: float) -> StepResult:
        self._step_count += 1
        return StepResult(
            observation=0.0,
            reward=1.0,
            terminated=self._step_count >= 2,
            truncated=False,
            info={},
        )


def _make_agent() -> ActorCriticAgent:
    return ActorCriticAgent(
        context=AgentContext(
            discount=0.99,
            learning_rate=0.01,
            entropy_temperature=0.1,
            target_update_tau=0.05,
        )
    )


class TestEvaluator:
    def test_evaluate_returns_correct_structure(self) -> None:
        result = Evaluator().evaluate(agent=_make_agent(), env=FixedEnv(), episodes=3)
        assert len(result.episode_returns) == 3
        assert result.return_mean == 2.0  # 2 steps * 1.0 reward each

    def test_evaluate_std_with_single_episode(self) -> None:
        result = Evaluator().evaluate(agent=_make_agent(), env=FixedEnv(), episodes=1)
        assert result.return_std == 0.0

    def test_evaluate_std_uses_sample_stdev(self) -> None:
        # With identical returns, sample stdev should also be 0
        result = Evaluator().evaluate(agent=_make_agent(), env=FixedEnv(), episodes=5)
        assert result.return_std == 0.0

    def test_evaluate_control_effort_nonnegative(self) -> None:
        result = Evaluator().evaluate(agent=_make_agent(), env=FixedEnv(), episodes=2)
        assert result.control_effort >= 0.0

    def test_evaluate_crash_rate_zero(self) -> None:
        result = Evaluator().evaluate(agent=_make_agent(), env=FixedEnv(), episodes=2)
        assert result.crash_rate == 0.0
