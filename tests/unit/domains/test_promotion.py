"""Unit tests for promotion logic (decide_promotion, recommend_validation_tier)."""

from __future__ import annotations

from rl_developer_memory.domains.rl_control.contracts import RLAuditFinding
from rl_developer_memory.domains.rl_control.promotion import (
    _count_findings,
    decide_promotion,
    recommend_validation_tier,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finding(severity: str = "info", summary: str = "") -> RLAuditFinding:
    return RLAuditFinding(audit_type="test_audit", severity=severity, summary=summary)


# ---------------------------------------------------------------------------
# Tests: _count_findings
# ---------------------------------------------------------------------------


class TestCountFindings:
    def test_empty(self) -> None:
        counts = _count_findings([])
        assert counts == {"info": 0, "warning": 0, "error": 0, "critical": 0}

    def test_mixed(self) -> None:
        findings = [_finding("info"), _finding("warning"), _finding("error"), _finding("critical"), _finding("info")]
        counts = _count_findings(findings)
        assert counts == {"info": 2, "warning": 1, "error": 1, "critical": 1}

    def test_dict_input(self) -> None:
        findings = [{"severity": "warning"}, {"severity": "error"}]
        counts = _count_findings(findings)
        assert counts["warning"] == 1
        assert counts["error"] == 1


# ---------------------------------------------------------------------------
# Tests: recommend_validation_tier
# ---------------------------------------------------------------------------


class TestRecommendValidationTier:
    def test_production_validated(self) -> None:
        tier = recommend_validation_tier(
            [],
            {"seed_count": 5, "hardware_validated": True},
            production_min_seed_count=5,
        )
        assert tier == "production_validated"

    def test_theory_reviewed(self) -> None:
        tier = recommend_validation_tier(
            [],
            {"theory_reviewed": True},
        )
        assert tier == "theory_reviewed"

    def test_validated(self) -> None:
        tier = recommend_validation_tier(
            [],
            {"seed_count": 3, "baseline_comparison": True},
            required_seed_count=3,
        )
        assert tier == "validated"

    def test_candidate(self) -> None:
        tier = recommend_validation_tier([], {"seed_count": 1})
        assert tier == "candidate"

    def test_observed_fallback_on_critical(self) -> None:
        tier = recommend_validation_tier(
            [_finding("critical")],
            {"seed_count": 1},
        )
        assert tier == "observed"

    def test_production_blocked_by_critical(self) -> None:
        tier = recommend_validation_tier(
            [_finding("critical")],
            {"seed_count": 10, "hardware_validated": True},
            production_min_seed_count=5,
        )
        assert tier == "observed"

    def test_production_blocked_by_low_seed(self) -> None:
        tier = recommend_validation_tier(
            [],
            {"seed_count": 3, "hardware_validated": True},
            production_min_seed_count=5,
        )
        # Falls through to validated (seed≥3, but needs baseline for fullly validated)
        assert tier in {"candidate", "validated", "theory_reviewed"}


# ---------------------------------------------------------------------------
# Tests: decide_promotion
# ---------------------------------------------------------------------------


class TestDecidePromotion:
    def test_applied_observed(self) -> None:
        decision = decide_promotion(
            [],
            {"seed_count": 1},
            memory_kind="pattern",
            theorem_claim_type="none",
            requested_tier="observed",
            review_gated=False,
        )
        assert decision.status == "applied"
        assert decision.applied_tier == "observed"
        assert not decision.blockers

    def test_applied_candidate(self) -> None:
        decision = decide_promotion(
            [],
            {"seed_count": 1},
            memory_kind="pattern",
            theorem_claim_type="none",
            requested_tier="candidate",
            review_gated=False,
        )
        assert decision.status == "applied"
        assert decision.applied_tier == "candidate"

    def test_candidate_blocked_by_warnings(self) -> None:
        decision = decide_promotion(
            [_finding("warning"), _finding("warning"), _finding("warning")],
            {"seed_count": 1},
            memory_kind="pattern",
            theorem_claim_type="none",
            requested_tier="candidate",
            candidate_warning_budget=2,
            review_gated=False,
        )
        assert decision.applied_tier == "observed"

    def test_blocked_by_critical(self) -> None:
        decision = decide_promotion(
            [_finding("critical")],
            {"seed_count": 5, "baseline_comparison": True},
            memory_kind="pattern",
            theorem_claim_type="none",
            requested_tier="validated",
            review_gated=False,
        )
        assert decision.status == "blocked"
        assert "critical-audit-findings" in decision.blockers

    def test_blocked_by_error_strict(self) -> None:
        decision = decide_promotion(
            [_finding("error")],
            {"seed_count": 5, "baseline_comparison": True},
            memory_kind="pattern",
            theorem_claim_type="none",
            requested_tier="validated",
            strict=True,
            review_gated=False,
        )
        assert decision.status == "blocked"
        assert "error-audit-findings" in decision.blockers

    def test_validated_blocked_by_low_seed(self) -> None:
        decision = decide_promotion(
            [],
            {"seed_count": 1, "baseline_comparison": True},
            memory_kind="pattern",
            theorem_claim_type="none",
            requested_tier="validated",
            required_seed_count=3,
            review_gated=False,
        )
        assert decision.status == "blocked"
        assert "seed-count-below-validated-threshold" in decision.blockers

    def test_validated_blocked_by_missing_baseline(self) -> None:
        decision = decide_promotion(
            [],
            {"seed_count": 5},
            memory_kind="pattern",
            theorem_claim_type="none",
            requested_tier="validated",
            review_gated=False,
        )
        assert decision.status == "blocked"
        assert "missing-baseline-comparison" in decision.blockers

    def test_production_blocked_by_missing_hw(self) -> None:
        decision = decide_promotion(
            [],
            {"seed_count": 5, "baseline_comparison": True},
            memory_kind="pattern",
            theorem_claim_type="none",
            requested_tier="production_validated",
            review_gated=False,
        )
        assert decision.status == "blocked"
        assert "missing-hardware-validation" in decision.blockers

    def test_theory_reviewed_blocked_by_missing_claim(self) -> None:
        decision = decide_promotion(
            [],
            {"seed_count": 3, "theory_reviewed": True},
            memory_kind="theory_pattern",
            theorem_claim_type="none",
            requested_tier="theory_reviewed",
            review_gated=False,
        )
        assert decision.status == "blocked"
        assert "missing-theorem-claim" in decision.blockers

    def test_review_gated_validated(self) -> None:
        decision = decide_promotion(
            [],
            {"seed_count": 5, "baseline_comparison": True},
            memory_kind="pattern",
            theorem_claim_type="none",
            requested_tier="validated",
            review_gated=True,
        )
        assert decision.status == "pending_review"
        assert decision.applied_tier == "candidate"
        assert decision.review_required is True

    def test_review_gated_production(self) -> None:
        decision = decide_promotion(
            [],
            {"seed_count": 5, "baseline_comparison": True, "hardware_validated": True},
            memory_kind="pattern",
            theorem_claim_type="none",
            requested_tier="production_validated",
            review_gated=True,
        )
        assert decision.status == "pending_review"
        assert decision.applied_tier == "validated"

    def test_review_gated_theory(self) -> None:
        decision = decide_promotion(
            [],
            {"seed_count": 3, "theory_reviewed": True},
            memory_kind="theory_pattern",
            theorem_claim_type="convergence_theorem",
            requested_tier="theory_reviewed",
            review_gated=True,
        )
        assert decision.status == "pending_review"
        assert decision.applied_tier == "candidate"

    def test_production_blocked_for_theory_pattern(self) -> None:
        decision = decide_promotion(
            [],
            {"seed_count": 10, "hardware_validated": True},
            memory_kind="theory_pattern",
            theorem_claim_type="convergence_theorem",
            requested_tier="production_validated",
            review_gated=False,
        )
        assert decision.status == "blocked"
        assert "production-tier-not-applicable-to-theory-pattern" in decision.blockers

    def test_to_record(self) -> None:
        decision = decide_promotion(
            [],
            {"seed_count": 1},
            memory_kind="pattern",
            theorem_claim_type="none",
            requested_tier="observed",
            review_gated=False,
        )
        record = decision.to_record()
        assert isinstance(record, dict)
        assert record["applied_tier"] == "observed"
