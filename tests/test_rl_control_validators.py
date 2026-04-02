from __future__ import annotations

from rl_developer_memory.domains.rl_control.promotion import recommend_validation_tier
from rl_developer_memory.domains.rl_control.validators import (
    validate_artifact_refs,
    validate_metrics_payload,
    validate_problem_profile,
    validate_run_manifest,
    validate_validation_payload,
)


def test_rl_validators_surface_missing_metadata() -> None:
    problem_findings = validate_problem_profile({"problem_family": "hjb", "theorem_claim_type": "stability"})
    run_findings = validate_run_manifest({"algorithm_family": "sac", "seed_count": 1}, required_seed_count=3)
    metric_findings = validate_metrics_payload({"constraint_violation_rate": 1.4})
    validation_findings = validate_validation_payload({"theory_reviewed": True}, required_seed_count=3)
    artifact_findings = validate_artifact_refs([{"kind": "tensorboard"}] * 13, max_refs=12)

    assert any("Lyapunov" in finding.summary for finding in problem_findings)
    assert any("seed_count" in finding.summary for finding in run_findings)
    assert any(finding.severity == "error" for finding in metric_findings)
    assert any("reviewed_by" in finding.summary for finding in validation_findings)
    assert any(finding.severity == "error" for finding in artifact_findings)


def test_recommend_validation_tier_respects_theory_review() -> None:
    findings = validate_validation_payload(
        {
            "theory_reviewed": True,
            "reviewed_by": "reviewer-1",
            "baseline_comparison": True,
            "seed_count": 4,
        },
        required_seed_count=3,
    )

    tier = recommend_validation_tier(findings, {"theory_reviewed": True, "reviewed_by": "reviewer-1", "seed_count": 4})

    assert tier == "theory_reviewed"
