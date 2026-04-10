"""Unit tests for StrategyThompsonBandit and related utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

from rl_developer_memory.learning.posteriors import (
    BetaPosterior,
    build_beta_posterior,
    shrinkage_weight,
)
from rl_developer_memory.learning.safe_override import SafeOverridePolicy
from rl_developer_memory.learning.strategy_bandit import (
    _SCOPE_LAMBDAS,
    StrategyBanditOutcome,
    StrategyThompsonBandit,
)
from rl_developer_memory.models import QueryProfile
from rl_developer_memory.storage import (
    STRATEGY_PRIOR_ALPHA,
    STRATEGY_PRIOR_BETA,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_profile(**overrides: Any) -> QueryProfile:
    defaults: dict[str, Any] = dict(
        raw_text="test error message",
        normalized_text="test error message",
        tokens=["test", "error", "message"],
        exception_types=[],
        error_family="",
        root_cause_class="",
        tags=[],
        evidence=[],
        symptom_tokens=[],
        context_tokens=[],
        command_tokens=[],
        path_tokens=[],
        stack_signature="",
        env_fingerprint="",
        repo_fingerprint="",
        repo_name="my-repo",
        project_scope="global",
        user_scope="user1",
        entity_slots={},
        strategy_hints=[],
        command_signature="",
        path_signature="",
        pattern_key="",
        variant_key="",
    )
    defaults.update(overrides)
    return QueryProfile(**defaults)  # type: ignore[arg-type]


@dataclass
class _FakeRankedItem:
    candidate: dict[str, Any]
    score: float


def _make_settings(**overrides: Any) -> MagicMock:
    settings = MagicMock()
    settings.strategy_overlay_scale = overrides.get("strategy_overlay_scale", 0.20)
    settings.variant_overlay_scale = overrides.get("variant_overlay_scale", 0.08)
    settings.safe_override_margin = overrides.get("safe_override_margin", 0.03)
    settings.minimum_strategy_evidence = overrides.get("minimum_strategy_evidence", 3)
    settings.strategy_half_life_days = overrides.get("strategy_half_life_days", 75)
    settings.variant_half_life_days = overrides.get("variant_half_life_days", 35)
    return settings


def _make_store(snapshot: dict[str, Any] | None = None) -> MagicMock:
    store = MagicMock()
    store.load_strategy_bandit_stats.return_value = snapshot or {
        "global": {},
        "repo": {},
        "user": {},
        "variants": {},
    }
    return store


def _make_bandit(store: Any = None, settings: Any = None) -> StrategyThompsonBandit:
    return StrategyThompsonBandit(
        store=store or _make_store(),
        settings=settings or _make_settings(),
    )


def _prior_posterior(prior_alpha: float = STRATEGY_PRIOR_ALPHA, prior_beta: float = STRATEGY_PRIOR_BETA) -> BetaPosterior:
    return build_beta_posterior(
        alpha=prior_alpha,
        beta=prior_beta,
        updated_at="",
        half_life_days=75,
        prior_alpha=prior_alpha,
        prior_beta=prior_beta,
        seed_parts=("test",),
    )


# ---------------------------------------------------------------------------
# Tests: clamp
# ---------------------------------------------------------------------------


class TestClamp:
    def test_within_range(self) -> None:
        assert StrategyThompsonBandit._clamp(0.5) == 0.5

    def test_below_low(self) -> None:
        assert StrategyThompsonBandit._clamp(-1.0) == 0.0

    def test_above_high(self) -> None:
        assert StrategyThompsonBandit._clamp(2.0) == 0.999

    def test_custom_bounds(self) -> None:
        assert StrategyThompsonBandit._clamp(0.1, low=0.2, high=0.8) == 0.2
        assert StrategyThompsonBandit._clamp(0.9, low=0.2, high=0.8) == 0.8


# ---------------------------------------------------------------------------
# Tests: center
# ---------------------------------------------------------------------------


class TestCenter:
    def test_midpoint(self) -> None:
        assert StrategyThompsonBandit._center(0.5) == 0.0

    def test_full_positive(self) -> None:
        assert StrategyThompsonBandit._center(1.0) == 1.0

    def test_full_negative(self) -> None:
        assert StrategyThompsonBandit._center(0.0) == -1.0

    def test_clamp_above(self) -> None:
        assert StrategyThompsonBandit._center(1.5) == 1.0

    def test_clamp_below(self) -> None:
        assert StrategyThompsonBandit._center(-0.5) == -1.0


# ---------------------------------------------------------------------------
# Tests: candidate_key
# ---------------------------------------------------------------------------


class TestCandidateKey:
    def test_pattern_and_variant(self) -> None:
        candidate = {"pattern_id": 42, "variant_id": 7}
        assert StrategyThompsonBandit.candidate_key(candidate) == "42:7"

    def test_fallback_to_id(self) -> None:
        candidate = {"id": 10, "best_variant": {"id": 3}}
        assert StrategyThompsonBandit.candidate_key(candidate) == "10:3"

    def test_zero_ids(self) -> None:
        candidate = {}
        assert StrategyThompsonBandit.candidate_key(candidate) == "0:0"


# ---------------------------------------------------------------------------
# Tests: scope_signal
# ---------------------------------------------------------------------------


class TestScopeSignal:
    def test_user_exploration_rate(self) -> None:
        posterior = _prior_posterior()
        signal = StrategyThompsonBandit._scope_signal(posterior, scope_name="user")
        expected = 0.70 * posterior.mean + 0.30 * posterior.sample
        assert abs(signal - expected) < 1e-9

    def test_repo_exploration_rate(self) -> None:
        posterior = _prior_posterior()
        signal = StrategyThompsonBandit._scope_signal(posterior, scope_name="repo")
        expected = 0.75 * posterior.mean + 0.25 * posterior.sample
        assert abs(signal - expected) < 1e-9

    def test_global_exploration_rate(self) -> None:
        posterior = _prior_posterior()
        signal = StrategyThompsonBandit._scope_signal(posterior, scope_name="global")
        expected = 0.80 * posterior.mean + 0.20 * posterior.sample
        assert abs(signal - expected) < 1e-9


# ---------------------------------------------------------------------------
# Tests: combined_strategy_signal
# ---------------------------------------------------------------------------


class TestCombinedStrategySignal:
    def test_prior_only_produces_near_half(self) -> None:
        bandit = _make_bandit()
        g = _prior_posterior()
        r = _prior_posterior()
        u = _prior_posterior()
        mean, sample, std = bandit._combined_strategy_signal(
            global_posterior=g, repo_posterior=r, user_posterior=u,
        )
        assert 0.3 <= mean <= 0.7
        assert 0.3 <= sample <= 0.7

    def test_zero_observations_uses_global(self) -> None:
        bandit = _make_bandit()
        g = _prior_posterior()
        r = _prior_posterior()
        u = _prior_posterior()
        assert g.effective_observations == 0.0
        mean, sample, std = bandit._combined_strategy_signal(
            global_posterior=g, repo_posterior=r, user_posterior=u,
        )
        # With zero observations the shrinkage weight is 0 for all → fallback to global=1.0
        expected_mean = g.mean
        assert abs(mean - expected_mean) < 1e-9


# ---------------------------------------------------------------------------
# Tests: negative_applicability_penalty
# ---------------------------------------------------------------------------


class TestNegativeApplicabilityPenalty:
    def test_no_payload(self) -> None:
        bandit = _make_bandit()
        profile = _default_profile()
        penalty, reasons = bandit._negative_applicability_penalty(profile, {})
        assert penalty == 0.0
        assert reasons == []

    def test_false_positive_count_caps(self) -> None:
        bandit = _make_bandit()
        profile = _default_profile()
        variant = {"negative_applicability_json": {"false_positive_count": 10}}
        penalty, _ = bandit._negative_applicability_penalty(profile, variant)
        # 10 * 0.03 = 0.30, capped by base at 0.15, total at 0.30
        assert penalty <= 0.30

    def test_scope_penalty_project(self) -> None:
        bandit = _make_bandit()
        profile = _default_profile(project_scope="my-project")
        variant = {"negative_applicability_json": {"project_scopes": ["my-project"]}}
        penalty, reasons = bandit._negative_applicability_penalty(profile, variant)
        assert penalty == 0.08
        assert "negative-applicability-project-scope" in reasons

    def test_repo_name_penalty(self) -> None:
        bandit = _make_bandit()
        profile = _default_profile(repo_name="bad-repo")
        variant = {"negative_applicability_json": {"repo_names": ["bad-repo"]}}
        penalty, reasons = bandit._negative_applicability_penalty(profile, variant)
        assert penalty == 0.12
        assert "negative-applicability-repo-name" in reasons

    def test_total_cap_at_030(self) -> None:
        bandit = _make_bandit()
        profile = _default_profile(project_scope="p", user_scope="u", repo_name="r", command_tokens=["cmd"], path_tokens=["path"])
        variant = {"negative_applicability_json": {
            "false_positive_count": 10,
            "project_scopes": ["p"],
            "user_scopes": ["u"],
            "repo_names": ["r"],
            "commands": ["cmd"],
            "file_paths": ["path"],
        }}
        penalty, _ = bandit._negative_applicability_penalty(profile, variant)
        assert penalty == 0.30


# ---------------------------------------------------------------------------
# Tests: score_candidates
# ---------------------------------------------------------------------------


class TestScoreCandidates:
    def test_empty_items(self) -> None:
        bandit = _make_bandit()
        assert bandit.score_candidates(_default_profile(), [], project_scope="global") == {}

    def test_neutral_strategy_key(self) -> None:
        bandit = _make_bandit()
        profile = _default_profile()
        candidate = {"pattern_id": 1, "variant_id": 0, "best_variant": {"strategy_key": ""}}
        results = bandit.score_candidates(
            profile,
            [_FakeRankedItem(candidate=candidate, score=0.80)],
            project_scope="global",
        )
        assert len(results) == 1
        outcome = next(iter(results.values()))
        assert outcome.strategy_mean == 0.5
        assert outcome.strategy_sample == 0.5
        assert outcome.strategy_std == 0.0

    def test_general_reusable_fix_is_neutral(self) -> None:
        bandit = _make_bandit()
        profile = _default_profile()
        candidate = {"pattern_id": 1, "variant_id": 0, "best_variant": {"strategy_key": "general_reusable_fix"}}
        results = bandit.score_candidates(
            profile,
            [_FakeRankedItem(candidate=candidate, score=0.80)],
            project_scope="global",
        )
        outcome = next(iter(results.values()))
        assert outcome.strategy_mean == 0.5
        assert outcome.strategy_std == 0.0

    def test_prior_baseline_produces_near_original_score(self) -> None:
        """With no observations at all, the adjustment should be near zero."""
        bandit = _make_bandit()
        profile = _default_profile()
        candidate = {"pattern_id": 1, "variant_id": 0, "best_variant": {"strategy_key": "some-strategy"}}
        results = bandit.score_candidates(
            profile,
            [_FakeRankedItem(candidate=candidate, score=0.75)],
            project_scope="global",
        )
        outcome = next(iter(results.values()))
        # Prior mean ≈ 0.5, center(0.5) ≈ 0, evidence_scale < 1 → adjustment ≈ 0
        assert abs(outcome.final_score - 0.75) < 0.05

    def test_multiple_candidates(self) -> None:
        bandit = _make_bandit()
        profile = _default_profile()
        c1 = {"pattern_id": 1, "variant_id": 0, "best_variant": {"strategy_key": "s1"}}
        c2 = {"pattern_id": 2, "variant_id": 0, "best_variant": {"strategy_key": "s2"}}
        results = bandit.score_candidates(
            profile,
            [_FakeRankedItem(candidate=c1, score=0.8), _FakeRankedItem(candidate=c2, score=0.6)],
            project_scope="global",
        )
        assert len(results) == 2
        assert "1:0" in results
        assert "2:0" in results


# ---------------------------------------------------------------------------
# Tests: posteriors module
# ---------------------------------------------------------------------------


class TestPosteriors:
    def test_build_returns_correct_prior(self) -> None:
        p = build_beta_posterior(
            alpha=2.0, beta=2.0, updated_at="",
            half_life_days=75, prior_alpha=2.0, prior_beta=2.0,
            seed_parts=("a",),
        )
        assert p.effective_observations == 0.0
        assert abs(p.mean - 0.5) < 1e-6
        assert p.decay_factor == 1.0

    def test_build_with_observations(self) -> None:
        p = build_beta_posterior(
            alpha=10.0, beta=2.0, updated_at="",
            half_life_days=75, prior_alpha=2.0, prior_beta=2.0,
            seed_parts=("b",),
        )
        assert p.effective_observations == 8.0
        assert p.mean > 0.7

    def test_shrinkage_weight_zero_obs(self) -> None:
        assert shrinkage_weight(0.0, lambda_value=6.0) == 0.0

    def test_shrinkage_weight_positive(self) -> None:
        w = shrinkage_weight(6.0, lambda_value=6.0)
        assert abs(w - 0.5) < 1e-9

    def test_shrinkage_weight_large_obs(self) -> None:
        w = shrinkage_weight(100.0, lambda_value=6.0)
        assert w > 0.9


# ---------------------------------------------------------------------------
# Tests: SafeOverridePolicy
# ---------------------------------------------------------------------------


class TestSafeOverridePolicy:
    def _make_outcome(self, *, final_score: float = 0.80,
                       conservative_score: float = 0.78,
                       effective_evidence: float = 5.0,
                       negative_penalty: float = 0.0) -> StrategyBanditOutcome:
        return StrategyBanditOutcome(
            candidate_key="1:0",
            strategy_key="s1",
            strategy_mean=0.6,
            strategy_sample=0.65,
            strategy_std=0.1,
            variant_mean=0.5,
            variant_sample=0.5,
            variant_std=0.1,
            effective_evidence=effective_evidence,
            negative_penalty=negative_penalty,
            adjustment=0.0,
            final_score=final_score,
            conservative_score=conservative_score,
            reasons=[],
        )

    def test_baseline_missing(self) -> None:
        policy = SafeOverridePolicy(_make_settings())
        result = policy.choose(baseline_key="1:0", baseline_score=0.75, analyses={})
        assert result.promoted is False
        assert result.reason == "baseline-missing-bandit-analysis"

    def test_baseline_remains_best(self) -> None:
        policy = SafeOverridePolicy(_make_settings())
        outcome = self._make_outcome(final_score=0.80)
        result = policy.choose(baseline_key="1:0", baseline_score=0.75, analyses={"1:0": outcome})
        assert result.promoted is False
        assert result.reason == "baseline-remains-best"

    def test_insufficient_evidence(self) -> None:
        policy = SafeOverridePolicy(_make_settings(minimum_strategy_evidence=10))
        baseline = self._make_outcome(final_score=0.70, conservative_score=0.68, effective_evidence=2.0)
        challenger = self._make_outcome(final_score=0.85, conservative_score=0.82, effective_evidence=2.0)
        challenger.candidate_key = "2:0"
        result = policy.choose(baseline_key="1:0", baseline_score=0.70, analyses={"1:0": baseline, "2:0": challenger})
        assert result.promoted is False
        assert result.reason == "insufficient-strategy-evidence"

    def test_conservative_below_margin(self) -> None:
        policy = SafeOverridePolicy(_make_settings(safe_override_margin=0.10))
        baseline = self._make_outcome(final_score=0.70, conservative_score=0.68)
        challenger = self._make_outcome(final_score=0.80, conservative_score=0.75, effective_evidence=5.0)
        challenger.candidate_key = "2:0"
        result = policy.choose(baseline_key="1:0", baseline_score=0.70, analyses={"1:0": baseline, "2:0": challenger})
        assert result.promoted is False
        assert result.reason == "conservative-score-below-margin"

    def test_negative_penalty_blocks(self) -> None:
        policy = SafeOverridePolicy(_make_settings())
        baseline = self._make_outcome(final_score=0.70, conservative_score=0.68)
        challenger = self._make_outcome(final_score=0.90, conservative_score=0.85, effective_evidence=5.0, negative_penalty=0.22)
        challenger.candidate_key = "2:0"
        result = policy.choose(baseline_key="1:0", baseline_score=0.70, analyses={"1:0": baseline, "2:0": challenger})
        assert result.promoted is False
        assert result.reason == "negative-applicability-penalty"

    def test_approved_override(self) -> None:
        policy = SafeOverridePolicy(_make_settings())
        baseline = self._make_outcome(final_score=0.70, conservative_score=0.68)
        challenger = self._make_outcome(final_score=0.90, conservative_score=0.85, effective_evidence=5.0)
        challenger.candidate_key = "2:0"
        result = policy.choose(baseline_key="1:0", baseline_score=0.70, analyses={"1:0": baseline, "2:0": challenger})
        assert result.promoted is True
        assert result.chosen_key == "2:0"
        assert result.reason == "safe-override-approved"


# ---------------------------------------------------------------------------
# Tests: SCOPE_LAMBDAS
# ---------------------------------------------------------------------------


class TestScopeLambdas:
    def test_values(self) -> None:
        assert _SCOPE_LAMBDAS["global"] == 6.0
        assert _SCOPE_LAMBDAS["repo"] == 3.5
        assert _SCOPE_LAMBDAS["user"] == 2.5
