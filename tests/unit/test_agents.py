"""Unit tests for ActorCriticAgent and agent lifecycle."""

from __future__ import annotations

from typing import Any

from rl_developer_memory.agents.base import ActorCriticAgent, AgentContext
from rl_developer_memory.networks.base import ScalarPolicyNetwork


def _make_context(**overrides: Any) -> AgentContext:
    defaults: dict[str, Any] = {
        "discount": 0.99,
        "learning_rate": 0.01,
        "entropy_temperature": 0.1,
        "target_update_tau": 0.05,
    }
    defaults.update(overrides)
    return AgentContext(**defaults)


class TestActorCriticAgent:
    def test_act_clamps_to_range(self) -> None:
        agent = ActorCriticAgent(
            context=_make_context(),
            policy=ScalarPolicyNetwork(weight=100.0, bias=0.0),
        )
        assert agent.act(1.0) == 1.0
        assert agent.act(-1.0) == -1.0

    def test_act_default_zero_weights(self) -> None:
        agent = ActorCriticAgent(context=_make_context())
        assert agent.act(5.0) == 0.0

    def test_compute_td_target_non_terminal(self) -> None:
        agent = ActorCriticAgent(context=_make_context(discount=0.9))
        td = agent.compute_td_target(reward=1.0, next_value=2.0, done=False)
        assert abs(td - 2.8) < 1e-9

    def test_compute_td_target_terminal(self) -> None:
        agent = ActorCriticAgent(context=_make_context(discount=0.9))
        td = agent.compute_td_target(reward=1.0, next_value=999.0, done=True)
        assert td == 1.0

    def test_bellman_residual(self) -> None:
        agent = ActorCriticAgent(context=_make_context())
        assert agent.compute_bellman_residual(prediction=2.0, td_target=3.0) == 1.0

    def test_critic_objective_is_squared_residual(self) -> None:
        agent = ActorCriticAgent(context=_make_context())
        obj = agent.compute_critic_objective(prediction=2.0, td_target=5.0)
        assert abs(obj - 9.0) < 1e-9

    def test_learn_updates_weights(self) -> None:
        agent = ActorCriticAgent(context=_make_context(learning_rate=0.1))
        w_before = agent.value.weight
        agent.learn(observation=1.0, reward=1.0, next_observation=0.0, done=False)
        assert agent.value.weight != w_before

    def test_learn_returns_metrics(self) -> None:
        agent = ActorCriticAgent(context=_make_context())
        metrics = agent.learn(observation=1.0, reward=1.0, next_observation=0.0, done=False)
        assert "td_target" in metrics
        assert "bellman_residual" in metrics
        assert "critic_objective" in metrics
        assert "actor_objective" in metrics
        assert "entropy_temperature" in metrics

    def test_update_target_network_soft(self) -> None:
        agent = ActorCriticAgent(context=_make_context(target_update_tau=0.5))
        agent.value.weight = 2.0
        agent.target_value.weight = 0.0
        agent.update_target_network()
        assert abs(agent.target_value.weight - 1.0) < 1e-9

    def test_update_target_network_override_tau(self) -> None:
        agent = ActorCriticAgent(context=_make_context(target_update_tau=0.0))
        agent.value.weight = 4.0
        agent.target_value.weight = 0.0
        agent.update_target_network(tau=1.0)
        assert abs(agent.target_value.weight - 4.0) < 1e-9

    def test_state_dict_roundtrip(self) -> None:
        agent = ActorCriticAgent(context=_make_context())
        agent.learn(observation=1.0, reward=1.0, next_observation=0.5, done=False)
        state = agent.state_dict()
        agent2 = ActorCriticAgent(context=_make_context())
        agent2.load_state_dict(state)
        assert agent2.value.weight == agent.value.weight
        assert agent2.policy.weight == agent.policy.weight
        assert agent2.target_value.weight == agent.target_value.weight

    def test_entropy_temperature_loss(self) -> None:
        agent = ActorCriticAgent(context=_make_context(entropy_temperature=0.5))
        loss = agent.compute_entropy_temperature_loss(entropy=0.2, target_entropy=0.5)
        assert abs(loss - 0.15) < 1e-9
