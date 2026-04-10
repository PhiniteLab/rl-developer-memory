"""Unit tests for learning-rate and exploration schedules."""

from __future__ import annotations

from rl_developer_memory.trainers.schedules import (
    ConstantLR,
    CosineAnnealingLR,
    ExponentialDecayLR,
    ExponentialEpsilonDecay,
    LinearDecayLR,
    LinearEpsilonDecay,
    WarmupLR,
)


class TestConstantLR:
    def test_always_returns_same(self) -> None:
        s = ConstantLR(lr=0.01)
        assert s.get_lr(0) == 0.01
        assert s.get_lr(100) == 0.01
        assert s.get_lr(9999) == 0.01


class TestLinearDecayLR:
    def test_start_value(self) -> None:
        s = LinearDecayLR(initial_lr=0.1, final_lr=0.01, total_steps=100)
        assert abs(s.get_lr(0) - 0.1) < 1e-9

    def test_end_value(self) -> None:
        s = LinearDecayLR(initial_lr=0.1, final_lr=0.01, total_steps=100)
        assert abs(s.get_lr(100) - 0.01) < 1e-9

    def test_midpoint(self) -> None:
        s = LinearDecayLR(initial_lr=0.1, final_lr=0.0, total_steps=100)
        assert abs(s.get_lr(50) - 0.05) < 1e-9

    def test_beyond_total_stays_at_final(self) -> None:
        s = LinearDecayLR(initial_lr=0.1, final_lr=0.01, total_steps=100)
        assert abs(s.get_lr(200) - 0.01) < 1e-9


class TestCosineAnnealingLR:
    def test_start_value(self) -> None:
        s = CosineAnnealingLR(initial_lr=0.1, final_lr=0.0, total_steps=100)
        assert abs(s.get_lr(0) - 0.1) < 1e-9

    def test_end_value(self) -> None:
        s = CosineAnnealingLR(initial_lr=0.1, final_lr=0.0, total_steps=100)
        assert abs(s.get_lr(100) - 0.0) < 1e-9

    def test_midpoint_is_half(self) -> None:
        s = CosineAnnealingLR(initial_lr=1.0, final_lr=0.0, total_steps=100)
        # At mid, cosine factor = 0.5*(1+cos(pi/2)) = 0.5
        assert abs(s.get_lr(50) - 0.5) < 1e-9


class TestExponentialDecayLR:
    def test_start_value(self) -> None:
        s = ExponentialDecayLR(initial_lr=0.1, decay_rate=0.5, decay_steps=10)
        assert abs(s.get_lr(0) - 0.1) < 1e-9

    def test_half_life(self) -> None:
        s = ExponentialDecayLR(initial_lr=0.1, decay_rate=0.5, decay_steps=10)
        assert abs(s.get_lr(10) - 0.05) < 1e-9

    def test_min_lr_enforced(self) -> None:
        s = ExponentialDecayLR(initial_lr=0.1, decay_rate=0.1, decay_steps=1, min_lr=0.001)
        assert s.get_lr(100) >= 0.001


class TestWarmupLR:
    def test_warmup_ramp(self) -> None:
        s = WarmupLR(warmup_steps=10, base_schedule=ConstantLR(lr=0.1))
        assert s.get_lr(0) < 0.1
        assert s.get_lr(5) < 0.1

    def test_after_warmup_delegates(self) -> None:
        s = WarmupLR(warmup_steps=10, base_schedule=ConstantLR(lr=0.1))
        assert abs(s.get_lr(10) - 0.1) < 1e-9

    def test_warmup_first_step(self) -> None:
        s = WarmupLR(warmup_steps=10, base_schedule=ConstantLR(lr=0.1))
        # step=0 → lr = 0.1 * (1/10) = 0.01
        assert abs(s.get_lr(0) - 0.01) < 1e-9


class TestLinearEpsilonDecay:
    def test_start(self) -> None:
        s = LinearEpsilonDecay(start=1.0, end=0.01, decay_steps=100)
        assert abs(s.get_epsilon(0) - 1.0) < 1e-9

    def test_end(self) -> None:
        s = LinearEpsilonDecay(start=1.0, end=0.01, decay_steps=100)
        assert abs(s.get_epsilon(100) - 0.01) < 1e-9

    def test_monotonic_decrease(self) -> None:
        s = LinearEpsilonDecay(start=1.0, end=0.01, decay_steps=100)
        prev = s.get_epsilon(0)
        for step in range(1, 101, 10):
            curr = s.get_epsilon(step)
            assert curr <= prev
            prev = curr


class TestExponentialEpsilonDecay:
    def test_start(self) -> None:
        s = ExponentialEpsilonDecay(start=1.0, end=0.01, decay_rate=0.99)
        assert abs(s.get_epsilon(0) - 1.0) < 1e-9

    def test_decreases(self) -> None:
        s = ExponentialEpsilonDecay(start=1.0, end=0.01, decay_rate=0.99)
        assert s.get_epsilon(100) < s.get_epsilon(0)

    def test_floor(self) -> None:
        s = ExponentialEpsilonDecay(start=1.0, end=0.01, decay_rate=0.5, decay_steps=1)
        assert s.get_epsilon(10000) >= 0.01
