"""Unit tests for PrioritizedReplayBuffer."""

from __future__ import annotations

from rl_developer_memory.buffers.base import PrioritizedReplayBuffer, Transition


class TestPrioritizedReplayBuffer:
    def _make_transition(self, obs: float = 0.0) -> Transition:
        return Transition(
            observation=obs,
            action=0.0,
            reward=1.0,
            next_observation=obs + 1.0,
            done=False,
        )

    def test_add_and_len(self) -> None:
        buf = PrioritizedReplayBuffer(capacity=10)
        assert len(buf) == 0
        buf.add(self._make_transition(1.0))
        assert len(buf) == 1

    def test_capacity_eviction(self) -> None:
        buf = PrioritizedReplayBuffer(capacity=3)
        for i in range(5):
            buf.add(self._make_transition(float(i)), priority=float(i + 1))
        assert len(buf) == 3

    def test_sample_returns_transitions(self) -> None:
        buf = PrioritizedReplayBuffer(capacity=10)
        for i in range(5):
            buf.add(self._make_transition(float(i)))
        result = buf.sample(batch_size=3)
        assert len(result) == 3

    def test_sample_with_weights_returns_tuple(self) -> None:
        buf = PrioritizedReplayBuffer(capacity=10)
        for i in range(5):
            buf.add(self._make_transition(float(i)))
        transitions, weights, indices = buf.sample_with_weights(batch_size=3)
        assert len(transitions) == 3
        assert len(weights) == 3
        assert len(indices) == 3

    def test_weights_are_positive(self) -> None:
        buf = PrioritizedReplayBuffer(capacity=10, alpha=0.6, beta=0.4)
        for i in range(5):
            buf.add(self._make_transition(float(i)), priority=float(i + 1))
        _, weights, _ = buf.sample_with_weights(batch_size=3)
        for w in weights:
            assert w > 0.0

    def test_update_priorities(self) -> None:
        buf = PrioritizedReplayBuffer(capacity=10)
        for i in range(5):
            buf.add(self._make_transition(float(i)))
        _, _, indices = buf.sample_with_weights(batch_size=2)
        buf.update_priorities(indices, [100.0, 100.0])
        # No crash; priorities updated

    def test_clear(self) -> None:
        buf = PrioritizedReplayBuffer(capacity=10)
        for i in range(5):
            buf.add(self._make_transition(float(i)))
        buf.clear()
        assert len(buf) == 0

    def test_sample_with_weights_from_empty_raises(self) -> None:
        buf = PrioritizedReplayBuffer(capacity=10)
        try:
            buf.sample_with_weights(batch_size=1)
            assert False, "Should raise"
        except ValueError:
            pass

    def test_sample_from_empty_returns_empty(self) -> None:
        buf = PrioritizedReplayBuffer(capacity=10)
        result = buf.sample(batch_size=1)
        assert result == []

    def test_beta_annealing(self) -> None:
        buf = PrioritizedReplayBuffer(capacity=10, beta=0.4, beta_increment=0.1)
        for i in range(5):
            buf.add(self._make_transition(float(i)))
        buf.sample_with_weights(batch_size=2)
        assert buf._beta >= 0.5

    def test_max_weight_normalization(self) -> None:
        buf = PrioritizedReplayBuffer(capacity=10, alpha=0.6, beta=1.0)
        for i in range(5):
            buf.add(self._make_transition(float(i)), priority=float(i + 1))
        _, weights, _ = buf.sample_with_weights(batch_size=3)
        for w in weights:
            assert w <= 1.0 + 1e-9  # IS weights normalized by max

    def test_high_priority_sampled_more(self) -> None:
        """Items with higher priority should be sampled more frequently."""
        buf = PrioritizedReplayBuffer(capacity=100, alpha=1.0, beta=1.0)
        # Add one high-priority and many low-priority items
        buf.add(self._make_transition(999.0), priority=100.0)
        for i in range(20):
            buf.add(self._make_transition(float(i)), priority=0.01)
        high_count = 0
        for _ in range(100):
            transitions = buf.sample(batch_size=1)
            if transitions[0].observation == 999.0:
                high_count += 1
        assert high_count > 50  # high priority should dominate
