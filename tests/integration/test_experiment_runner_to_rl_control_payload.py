from pathlib import Path

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


def test_experiment_runner_emits_rl_control_compatible_payloads(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    config = RLExperimentConfig.load(repo_root / "configs" / "rl_backbone.shadow.json")
    config.checkpoint.root_dir = str(tmp_path / "artifacts")
    report = ExperimentRunner(config).run()

    assert report.training_blueprint["algorithm_key"] == "sac"
    assert report.theory_sync["status"] == "ok"
    assert report.run_manifest["training_blueprint_id"] == "sac"
    assert report.artifact_refs
    assert not [item for item in report.theory_sync["audit_findings"] if item["severity"] == "error"]

    assert not [item for item in validate_problem_profile(report.problem_profile) if item.severity == "error"]
    assert not [item for item in validate_run_manifest(report.run_manifest, required_seed_count=3) if item.severity == "error"]
    assert not [item for item in validate_metrics_payload(report.metrics_payload) if item.severity == "error"]
    assert not [item for item in validate_validation_payload(report.validation_payload, required_seed_count=3) if item.severity == "error"]
    assert not [
        item
        for item in validate_experiment_consistency(
            problem_family=str(report.problem_profile.get("problem_family", "")),
            algorithm_family=str(report.run_manifest.get("algorithm_family", "")),
            runtime_stage=str(report.run_manifest.get("runtime_stage", "")),
            run_manifest=report.run_manifest,
            metrics_payload=report.metrics_payload,
            validation_payload=report.validation_payload,
            required_seed_count=3,
        )
        if item.severity == "error"
    ]
    assert not [
        item
        for item in validate_theory_consistency(
            problem_family=str(report.problem_profile.get("problem_family", "")),
            theorem_claim_type=str(report.problem_profile.get("theorem_claim_type", "")),
            problem_profile=report.problem_profile,
            validation_payload=report.validation_payload,
            algorithm_family=str(report.run_manifest.get("algorithm_family", "")),
            run_manifest=report.run_manifest,
        )
        if item.severity == "error"
    ]
