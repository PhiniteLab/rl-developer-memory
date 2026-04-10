"""Unit tests for RunningNormalizer, verifying update-after-normalize semantics."""

from __future__ import annotations

from rl_developer_memory.trainers.stability import (
    ObservationNormalizer,
    RewardNormalizer,
    RunningNormalizer,
)


class TestRunningNormalizer:
    def test_first_normalize_uses_initial_stats(self) -> None:
        """First call should normalize against initial mean=0, before updating stats."""
        norm = RunningNormalizer(enabled=True, clip_range=10.0)
        result = norm.normalize(5.0)
        # Before update, mean=0 variance=1 → (5-0)/1 = 5.0
        assert abs(result - 5.0) < 1e-6
        assert norm.count == 1

    def test_normalize_update_false_does_not_change_stats(self) -> None:
        norm = RunningNormalizer(enabled=True, clip_range=10.0)
        norm.normalize(5.0, update=False)
        assert norm.count == 0
        assert norm.mean == 0.0

    def test_normalize_disabled_passthrough(self) -> None:
        norm = RunningNormalizer(enabled=False)
        assert norm.normalize(42.0) == 42.0
        assert norm.count == 0

    def test_welford_stats_converge(self) -> None:
        norm = RunningNormalizer(enabled=True, clip_range=10.0)
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for v in values:
            norm.normalize(v)
        assert abs(norm.mean - 3.0) < 1e-6
        assert norm.count == 5

    def test_clip_range_enforced(self) -> None:
        norm = RunningNormalizer(enabled=True, clip_range=1.0)
        # After initial normalize, extremely large value should clip
        norm.normalize(0.0)  # seed with zero
        result = norm.normalize(1000.0)
        assert result <= 1.0
        assert result >= -1.0

    def test_normalize_nan_passthrough(self) -> None:
        norm = RunningNormalizer(enabled=True, clip_range=10.0)
        result = norm.normalize(float("nan"))
        # NaN should be returned unchanged
        import math

        assert math.isnan(result)
        assert norm.count == 0

    def test_normalize_inf_passthrough(self) -> None:
        norm = RunningNormalizer(enabled=True, clip_range=10.0)
        result = norm.normalize(float("inf"))
        assert result == float("inf")
        assert norm.count == 0

    def test_state_dict_roundtrip(self) -> None:
        norm = RunningNormalizer(enabled=True, clip_range=5.0)
        for v in [1.0, 2.0, 3.0]:
            norm.normalize(v)
        state = norm.state_dict()
        norm2 = RunningNormalizer(enabled=True)
        norm2.load_state_dict(state)
        assert norm2.count == norm.count
        assert abs(norm2.mean - norm.mean) < 1e-9

    def test_update_before_normalize_bias_is_fixed(self) -> None:
        """The P1-1 fix: normalize should use stats BEFORE updating, not after."""
        norm = RunningNormalizer(enabled=True, clip_range=100.0)
        # First value: mean=0, var=1(default)
        # If we normalize THEN update: (10-0)/sqrt(1) = 10, then update mean to 10
        # If we update THEN normalize (old bug): mean becomes 10, then (10-10)/sqrt(1) = 0
        result = norm.normalize(10.0)
        assert result != 0.0, "Normalizer is updating stats before normalizing (bias bug)"
        assert abs(result - 10.0) < 1e-6


class TestObservationAndRewardNormalizer:
    def test_observation_normalizer_inherits(self) -> None:
        obs = ObservationNormalizer(enabled=True)
        obs.normalize(5.0)
        assert obs.count == 1

    def test_reward_normalizer_inherits(self) -> None:
        rew = RewardNormalizer(enabled=True)
        rew.normalize(5.0)
        assert rew.count == 1
