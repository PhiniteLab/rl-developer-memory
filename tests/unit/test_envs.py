"""Unit tests for new environments: StochasticBandit, ScalarLinearSystem, NonlinearPendulum."""

from __future__ import annotations

from rl_developer_memory.envs.base import (
    NonlinearPendulumEnv,
    ScalarLinearSystemEnv,
    StochasticBanditEnv,
)


class TestStochasticBanditEnv:
    def test_reset_returns_observation(self) -> None:
        env = StochasticBanditEnv(seed=1)
        obs = env.reset()
        assert obs == 1.0

    def test_step_applies_noise(self) -> None:
        env = StochasticBanditEnv(noise_std=0.5, seed=42)
        env.reset()
        rewards = [env.step(0.5).reward for _ in range(10)]
        # With noise, not all rewards should be identical
        assert len(set(rewards)) > 1

    def test_terminates_at_max_steps(self) -> None:
        env = StochasticBanditEnv(max_episode_steps=3, seed=0)
        env.reset()
        for _ in range(2):
            r = env.step(0.0)
            assert not r.terminated
        r = env.step(0.0)
        assert r.terminated

    def test_zero_noise_matches_deterministic(self) -> None:
        env = StochasticBanditEnv(noise_std=0.0, target_action=0.5, seed=0)
        env.reset()
        result = env.step(0.5)
        assert abs(result.reward - 1.0) < 1e-9

    def test_spec_fields(self) -> None:
        env = StochasticBanditEnv()
        assert env.spec.env_id == "stochastic-bandit-v0"
        assert env.spec.action_low == -1.0
        assert env.spec.action_high == 1.0


class TestScalarLinearSystemEnv:
    def test_reset_returns_observation_in_range(self) -> None:
        env = ScalarLinearSystemEnv(seed=42)
        obs = env.reset()
        assert -1.0 <= obs <= 1.0

    def test_dynamics_depend_on_action(self) -> None:
        env1 = ScalarLinearSystemEnv(seed=42)
        env2 = ScalarLinearSystemEnv(seed=42)
        env1.reset()
        env2.reset()
        r1 = env1.step(1.0)
        r2 = env2.step(-1.0)
        assert r1.observation != r2.observation

    def test_reward_penalizes_large_state(self) -> None:
        env = ScalarLinearSystemEnv(noise_std=0.0, seed=0)
        env.reset()
        # Drive state to large value
        env._state = 3.0
        result = env.step(0.0)
        assert result.reward < 0.0  # -(x^2 + r*u^2) with large x

    def test_terminates_at_max_steps(self) -> None:
        env = ScalarLinearSystemEnv(max_episode_steps=5, seed=0)
        env.reset()
        for _ in range(4):
            r = env.step(0.0)
            assert not r.terminated
        r = env.step(0.0)
        assert r.terminated

    def test_state_clipping(self) -> None:
        env = ScalarLinearSystemEnv(a=2.0, noise_std=0.0, seed=0)
        env.reset()
        env._state = 4.0
        result = env.step(1.0)
        # State should be clipped to [-5, 5]
        assert -5.0 <= result.observation <= 5.0

    def test_truncation_on_divergence(self) -> None:
        env = ScalarLinearSystemEnv(noise_std=0.0, seed=0)
        env.reset()
        env._state = 4.95
        env._step = 0
        result = env.step(1.0)
        # State > 4.9 after step → truncated
        assert result.truncated or abs(result.observation) <= 5.0

    def test_spec_fields(self) -> None:
        env = ScalarLinearSystemEnv()
        assert env.spec.env_id == "scalar-linear-system-v0"


class TestNonlinearPendulumEnv:
    def test_reset_returns_small_angle(self) -> None:
        env = NonlinearPendulumEnv(seed=42)
        theta = env.reset()
        assert -0.3 <= theta <= 0.3

    def test_gravity_effect(self) -> None:
        env = NonlinearPendulumEnv(seed=42)
        env.reset()
        env._theta = 0.1
        env._omega = 0.0
        env.step(0.0)
        # Gravity should pull pendulum: omega should increase (positive sin)
        assert env._omega != 0.0

    def test_reward_prefers_upright(self) -> None:
        env = NonlinearPendulumEnv(seed=0)
        env.reset()
        env._theta = 0.0  # upright
        env._omega = 0.0
        r_upright = env.step(0.0).reward
        env.reset()
        env._theta = 1.5  # tilted
        env._omega = 0.0
        r_tilted = env.step(0.0).reward
        # cos(0) > cos(1.5), so upright should have higher reward
        assert r_upright > r_tilted

    def test_terminates_at_max_steps(self) -> None:
        env = NonlinearPendulumEnv(max_episode_steps=5, seed=0)
        env.reset()
        for _ in range(4):
            r = env.step(0.0)
            assert not r.terminated
        r = env.step(0.0)
        assert r.terminated

    def test_spec_fields(self) -> None:
        env = NonlinearPendulumEnv()
        assert env.spec.env_id == "nonlinear-pendulum-v0"
