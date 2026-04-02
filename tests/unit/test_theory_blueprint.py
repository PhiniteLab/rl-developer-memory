from rl_developer_memory.theory import (
    build_default_theory_registry,
    build_training_blueprint_catalog,
    validate_blueprint_registry_alignment,
)


def test_all_supported_algorithms_have_complete_training_blueprints() -> None:
    registry = build_default_theory_registry()
    blueprints = build_training_blueprint_catalog(registry)
    assert set(blueprints) == {"dqn", "ppo", "a2c", "ddpg", "td3", "sac"}
    for blueprint in blueprints.values():
        assert len(blueprint.steps) == 10
        assert blueprint.loss_decomposition
        assert blueprint.update_equations
        assert blueprint.audit_hooks
        assert blueprint.failure_modes
        assert blueprint.ablation_hooks
        assert blueprint.reporting_template
        assert blueprint.artifact_expectations
        findings = validate_blueprint_registry_alignment(blueprint, registry=registry)
        assert not [item for item in findings if item.severity == "error"], findings
