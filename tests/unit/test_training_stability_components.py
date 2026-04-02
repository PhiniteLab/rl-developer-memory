from __future__ import annotations

from rl_developer_memory.agents.base import ActorCriticAgent, AgentContext
from rl_developer_memory.trainers.stability import (
    EntropyTemperatureController,
    HardTargetUpdatePolicy,
    ObservationNormalizer,
    RewardNormalizer,
)
from rl_developer_memory.utils.reproducibility import DeterministicSeedDiscipline


def test_seed_discipline_is_repeatable() -> None:
    discipline = DeterministicSeedDiscipline(11)
    first = discipline.apply()
    second = discipline.apply()
    assert first.seed == second.seed == 11


def test_normalizers_track_running_statistics() -> None:
    observation = ObservationNormalizer(enabled=True, clip_range=10.0)
    reward = RewardNormalizer(enabled=True, clip_range=10.0)
    obs_value = observation.normalize(2.0)
    reward_value = reward.normalize(1.0)
    assert observation.count == 1
    assert reward.count == 1
    assert isinstance(obs_value, float)
    assert isinstance(reward_value, float)


def test_entropy_controller_respects_bounds() -> None:
    controller = EntropyTemperatureController(
        initial_temperature=0.1,
        min_temperature=0.05,
        max_temperature=0.2,
        learning_rate=0.1,
        target_entropy=0.5,
    )
    updated = controller.update(0.0)
    assert 0.05 <= updated <= 0.2


def test_hard_target_update_policy_only_applies_on_interval() -> None:
    agent = ActorCriticAgent(
        context=AgentContext(
            discount=0.95,
            learning_rate=0.1,
            entropy_temperature=0.1,
            target_update_tau=0.5,
        )
    )
    agent.value.weight = 2.0
    policy = HardTargetUpdatePolicy(interval=2)
    skipped = policy.apply(agent, step=1)
    applied = policy.apply(agent, step=2)
    assert skipped["target_update_applied"] == 0.0
    assert applied["target_update_applied"] == 1.0
