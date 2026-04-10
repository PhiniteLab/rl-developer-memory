"""Unit tests for beta posterior computation and cold-start floor."""

from __future__ import annotations

from datetime import datetime, timezone

from rl_developer_memory.learning.posteriors import (
    build_beta_posterior,
    decay_beta_parameters,
    effective_observations,
    posterior_mean,
    posterior_std,
    shrinkage_weight,
)


class TestPosteriorMean:
    def test_uniform_prior(self) -> None:
        assert abs(posterior_mean(1.0, 1.0) - 0.5) < 1e-9

    def test_skewed(self) -> None:
        assert abs(posterior_mean(9.0, 1.0) - 0.9) < 1e-9

    def test_zero_total_returns_half(self) -> None:
        assert posterior_mean(0.0, 0.0) == 0.5


class TestPosteriorStd:
    def test_uniform_prior(self) -> None:
        std = posterior_std(1.0, 1.0)
        assert 0.0 < std < 0.5

    def test_low_total_returns_default(self) -> None:
        assert posterior_std(0.5, 0.5) == 0.25


class TestEffectiveObservations:
    def test_basic(self) -> None:
        eff = effective_observations(5.0, 5.0, prior_alpha=1.0, prior_beta=1.0)
        assert abs(eff - 8.0) < 1e-9

    def test_no_observations(self) -> None:
        eff = effective_observations(1.0, 1.0, prior_alpha=1.0, prior_beta=1.0)
        assert eff == 0.0


class TestDecayBetaParameters:
    def test_zero_half_life_returns_max_prior(self) -> None:
        a, b, decay = decay_beta_parameters(
            alpha=5.0, beta=5.0, updated_at="", half_life_days=0,
            prior_alpha=1.0, prior_beta=1.0,
        )
        assert a == 5.0
        assert b == 5.0
        assert decay == 1.0

    def test_empty_updated_at_returns_max_prior(self) -> None:
        a, b, decay = decay_beta_parameters(
            alpha=5.0, beta=5.0, updated_at="", half_life_days=30,
            prior_alpha=1.0, prior_beta=1.0,
        )
        assert a == 5.0
        assert decay == 1.0


class TestBuildBetaPosterior:
    def test_sample_within_zero_one(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        p = build_beta_posterior(
            alpha=2.0, beta=2.0, updated_at=now,
            half_life_days=30, prior_alpha=1.0, prior_beta=1.0,
            seed_parts=("test",),
        )
        assert 0.0 <= p.sample <= 1.0

    def test_cold_start_floor_prevents_extreme_samples(self) -> None:
        """P1-6 fix: near-zero params floor at 0.5 instead of 1e-6."""
        now = datetime.now(timezone.utc).isoformat()
        # With alpha, beta near zero, the floor should produce moderate samples
        samples = []
        for i in range(20):
            p = build_beta_posterior(
                alpha=0.001, beta=0.001, updated_at=now,
                half_life_days=30, prior_alpha=0.001, prior_beta=0.001,
                seed_parts=("cold_start", i),
            )
            samples.append(p.sample)
        # With floor=0.5 (uniform prior), samples should be spread, not all 0/1
        extreme_count = sum(1 for s in samples if s < 0.01 or s > 0.99)
        assert extreme_count < len(samples) // 2, (
            f"Too many extreme samples ({extreme_count}/{len(samples)}): cold-start floor too low"
        )

    def test_posterior_attributes(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        p = build_beta_posterior(
            alpha=3.0, beta=3.0, updated_at=now,
            half_life_days=30, prior_alpha=1.0, prior_beta=1.0,
            seed_parts=("attrs",),
        )
        assert abs(p.mean - 0.5) < 0.1
        assert p.std > 0.0
        assert p.effective_observations >= 0.0


class TestShrinkageWeight:
    def test_zero_observations(self) -> None:
        assert shrinkage_weight(0.0, lambda_value=10.0) == 0.0

    def test_high_observations(self) -> None:
        w = shrinkage_weight(1000.0, lambda_value=10.0)
        assert w > 0.99

    def test_moderate(self) -> None:
        w = shrinkage_weight(10.0, lambda_value=10.0)
        assert abs(w - 0.5) < 1e-9
