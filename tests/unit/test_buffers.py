"""Unit tests for replay and rollout buffers."""

from __future__ import annotations

from rl_developer_memory.buffers.base import (
    InMemoryReplayBuffer,
    InMemoryRolloutBuffer,
    Transition,
)


def _make_transition(obs: float = 0.0, reward: float = 1.0) -> Transition:
    return Transition(
        observation=obs, action=0.5, reward=reward, next_observation=obs + 1.0, done=False
    )


class TestInMemoryReplayBuffer:
    def test_add_and_sample_all(self) -> None:
        buf = InMemoryReplayBuffer()
        buf.add(_make_transition(1.0))
        buf.add(_make_transition(2.0))
        items = buf.sample()
        assert len(items) == 2
        assert items[0].observation == 1.0

    def test_capacity_limit_evicts_oldest(self) -> None:
        buf = InMemoryReplayBuffer(capacity=3)
        for i in range(5):
            buf.add(_make_transition(float(i)))
        assert len(buf) == 3
        obs = [t.observation for t in buf.sample()]
        assert 0.0 not in obs
        assert 1.0 not in obs
        assert 4.0 in obs

    def test_sample_with_batch_size(self) -> None:
        buf = InMemoryReplayBuffer()
        for i in range(20):
            buf.add(_make_transition(float(i)))
        batch = buf.sample(batch_size=5)
        assert len(batch) == 5

    def test_sample_batch_larger_than_buffer_returns_all(self) -> None:
        buf = InMemoryReplayBuffer()
        buf.add(_make_transition(1.0))
        buf.add(_make_transition(2.0))
        batch = buf.sample(batch_size=100)
        assert len(batch) == 2

    def test_sample_zero_batch_returns_all(self) -> None:
        buf = InMemoryReplayBuffer()
        for i in range(5):
            buf.add(_make_transition(float(i)))
        assert len(buf.sample(batch_size=0)) == 5

    def test_clear(self) -> None:
        buf = InMemoryReplayBuffer()
        buf.add(_make_transition())
        buf.clear()
        assert len(buf) == 0
        assert buf.sample() == []

    def test_default_capacity_is_large(self) -> None:
        buf = InMemoryReplayBuffer()
        for i in range(100):
            buf.add(_make_transition(float(i)))
        assert len(buf) == 100


class TestInMemoryRolloutBuffer:
    def test_add_and_collect(self) -> None:
        buf = InMemoryRolloutBuffer()
        buf.add(_make_transition(1.0))
        buf.add(_make_transition(2.0))
        items = buf.collect()
        assert len(items) == 2

    def test_collect_returns_copy(self) -> None:
        buf = InMemoryRolloutBuffer()
        buf.add(_make_transition(1.0))
        collected = buf.collect()
        collected.clear()
        assert len(buf.collect()) == 1

    def test_clear(self) -> None:
        buf = InMemoryRolloutBuffer()
        buf.add(_make_transition())
        buf.clear()
        assert buf.collect() == []
