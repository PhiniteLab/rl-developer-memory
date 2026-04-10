"""End-to-end test: experiment → validation → promotion lifecycle."""

from __future__ import annotations

from pathlib import Path

from rl_developer_memory.domains.rl_control.contracts import RLAuditFinding
from rl_developer_memory.domains.rl_control.promotion import decide_promotion, recommend_validation_tier
from rl_developer_memory.domains.rl_control.validators import (
    validate_experiment_consistency,
    validate_metrics_payload,
    validate_problem_profile,
    validate_run_manifest,
    validate_theory_consistency,
    validate_validation_payload,
)
from rl_developer_memory.experiments.config import RLExperimentConfig
from rl_developer_memory.experiments.runner import ExperimentRunner


def test_experiment_candidate_to_validated_promotion(tmp_path: Path) -> None:
    """Full lifecycle: run experiment → collect audit findings → promote through tiers."""
    repo_root = Path(__file__).resolve().parents[2]
    config = RLExperimentConfig.load(repo_root / "configs" / "rl_backbone.shadow.json")
    config.checkpoint.root_dir = str(tmp_path / "artifacts")

    report = ExperimentRunner(config).run()

    # Collect all audit findings
    findings: list[RLAuditFinding] = []
    findings.extend(validate_problem_profile(report.problem_profile))
    findings.extend(validate_run_manifest(report.run_manifest, required_seed_count=3))
    findings.extend(validate_metrics_payload(report.metrics_payload))
    findings.extend(validate_validation_payload(report.validation_payload, required_seed_count=3))
    findings.extend(validate_experiment_consistency(
        problem_family=str(report.problem_profile.get("problem_family", "")),
        algorithm_family=str(report.run_manifest.get("algorithm_family", "")),
        runtime_stage=str(report.run_manifest.get("runtime_stage", "")),
        run_manifest=report.run_manifest,
        metrics_payload=report.metrics_payload,
        validation_payload=report.validation_payload,
        required_seed_count=3,
    ))
    findings.extend(validate_theory_consistency(
        problem_family=str(report.problem_profile.get("problem_family", "")),
        theorem_claim_type=str(report.problem_profile.get("theorem_claim_type", "")),
        problem_profile=report.problem_profile,
        validation_payload=report.validation_payload,
        algorithm_family=str(report.run_manifest.get("algorithm_family", "")),
        run_manifest=report.run_manifest,
    ))

    # Phase 1: recommend tier from experiment output
    recommended = recommend_validation_tier(
        findings,
        report.validation_payload,
        required_seed_count=3,
        production_min_seed_count=5,
    )
    assert recommended in {"observed", "candidate", "validated", "theory_reviewed", "production_validated"}

    # Phase 2: candidate promotion (no review gate)
    decision_candidate = decide_promotion(
        findings,
        report.validation_payload,
        memory_kind="pattern",
        theorem_claim_type="none",
        requested_tier="candidate",
        review_gated=False,
        candidate_warning_budget=5,
    )
    critical_count = sum(1 for f in findings if f.severity == "critical")
    error_count = sum(1 for f in findings if f.severity == "error")
    if critical_count == 0 and error_count == 0:
        assert decision_candidate.status == "applied"
        assert decision_candidate.applied_tier == "candidate"
    else:
        assert decision_candidate.status == "blocked"

    # Phase 3: validated promotion (review gated)
    decision_validated = decide_promotion(
        findings,
        report.validation_payload,
        memory_kind="pattern",
        theorem_claim_type="none",
        requested_tier="validated",
        review_gated=True,
        required_seed_count=3,
    )
    if not decision_validated.blockers:
        assert decision_validated.status == "pending_review"
        assert decision_validated.applied_tier == "candidate"
        assert decision_validated.review_required is True
    else:
        assert decision_validated.status == "blocked"

    # Phase 4: production promotion (should be blocked — no hardware validation)
    decision_production = decide_promotion(
        findings,
        report.validation_payload,
        memory_kind="pattern",
        theorem_claim_type="none",
        requested_tier="production_validated",
        review_gated=False,
        production_min_seed_count=5,
    )
    assert "missing-hardware-validation" in decision_production.blockers

    # Phase 5: candidate→validated without review gate
    decision_direct = decide_promotion(
        findings,
        report.validation_payload,
        memory_kind="pattern",
        theorem_claim_type="none",
        requested_tier="validated",
        review_gated=False,
        required_seed_count=3,
    )
    if not decision_direct.blockers:
        assert decision_direct.status == "applied"
        assert decision_direct.applied_tier == "validated"


def test_checkpoint_lifecycle_through_promotion(tmp_path: Path) -> None:
    """Verify checkpoint save/mark_stable flows before promotion."""
    repo_root = Path(__file__).resolve().parents[2]
    config = RLExperimentConfig.load(repo_root / "configs" / "rl_backbone.shadow.json")
    config.checkpoint.root_dir = str(tmp_path / "artifacts")

    report = ExperimentRunner(config).run()

    # Checkpoint must exist
    assert report.checkpoint["latest_step"] >= 1
    assert report.checkpoint.get("root_dir")

    # Resume and verify continuity
    resumed = ExperimentRunner(config).resume_from_checkpoint()
    assert resumed.checkpoint["resumed_from"] != ""
    assert resumed.diagnostics["resume_count"] >= 1

    # Both reports should produce valid payloads for promotion
    for r in (report, resumed):
        decision = decide_promotion(
            [],
            r.validation_payload,
            memory_kind="pattern",
            theorem_claim_type="none",
            requested_tier="candidate",
            review_gated=False,
        )
        assert decision.applied_tier == "candidate"
