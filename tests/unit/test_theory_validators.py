from rl_developer_memory.theory import (
    audit_seed_variance,
    build_default_theory_registry,
    build_training_blueprint_catalog,
    validate_experiment_assumptions,
    validate_result_artifacts,
)


def test_experiment_assumption_validator_tracks_hidden_assumption_gaps() -> None:
    registry = build_default_theory_registry()
    blueprint = build_training_blueprint_catalog(registry)["sac"]
    findings = validate_experiment_assumptions(
        blueprint=blueprint,
        registry=registry,
        documented_assumptions=["markov_transition", "bounded_reward", "stationary_rollout"],
        documented_hidden_assumptions=["observation_sufficiency"],
        theorem_claim_type="bellman_consistency",
        lyapunov_candidate="quadratic_energy",
        audit_hooks=["lyapunov_hook"],
    )
    assert any("hidden assumptions" in item.summary.lower() for item in findings)


def test_seed_variance_audit_flags_large_variance() -> None:
    findings = audit_seed_variance(
        seed_count=5,
        required_seed_count=3,
        production_min_seed_count=5,
        return_std=2.0,
        confidence_interval=[-1.0, 3.5],
        variance_budget=0.5,
    )
    assert any(item.audit_type == "experiment" for item in findings)


def test_result_artifact_validation_requires_blueprint_artifacts() -> None:
    registry = build_default_theory_registry()
    blueprint = build_training_blueprint_catalog(registry)["ppo"]
    findings = validate_result_artifacts(
        [{"kind": "checkpoint_state", "uri": "memory://state"}],
        blueprint=blueprint,
        expected_artifacts=["training_report"],
    )
    assert any("missing" in item.summary.lower() for item in findings)
