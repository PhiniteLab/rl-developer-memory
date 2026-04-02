from pathlib import Path

from rl_developer_memory.experiments.config import CheckpointConfig, RLExperimentConfig


def test_shadow_config_loads_and_validates() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    config = RLExperimentConfig.load(repo_root / "configs" / "rl_backbone.shadow.json")
    assert config.algorithm == "sac"
    assert "observation_sufficiency" in config.theory.documented_hidden_assumptions
    assert "checkpoint_state" in config.theory.artifact_expectations
    assert config.validate() == []


def test_shadow_toml_config_loads_and_validates() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    config = RLExperimentConfig.load(repo_root / "configs" / "rl_backbone.shadow.toml")
    assert config.algorithm == "sac"
    assert "hjb_hook" in config.theory.audit_hooks
    assert config.validate() == []


def test_legacy_template_payload_is_normalized() -> None:
    payload = {
        "experiment": {
            "name": "legacy-shadow",
            "algorithm": "dqn",
            "env_id": "legacy-env-v0",
            "seed": 13,
            "train_steps": 9,
            "eval_episodes": 2,
            "required_seed_count": 3,
            "discount": 0.9,
        },
        "stabilization": {"gradient_clip": 0.7, "plateau_patience": 3},
        "checkpoint": {"save_every_steps": 2},
    }
    config = RLExperimentConfig.from_dict(payload)
    assert config.experiment_name == "legacy-shadow"
    assert config.algorithm == "dqn"
    assert config.train_env_id == "legacy-env-v0"
    assert config.training.max_steps == 9
    assert config.checkpoint.save_every_steps == 2
    assert config.validate() == []


def test_active_requires_rollout_gates() -> None:
    config = RLExperimentConfig(
        experiment_name="active-without-gates",
        algorithm="ppo",
        rollout_posture="active",
        checkpoint=CheckpointConfig(root_dir=".artifacts"),
    )
    assert any("active rollout requires" in item for item in config.validate())


def test_theory_variance_budget_must_be_positive() -> None:
    config = RLExperimentConfig(
        experiment_name="invalid-variance-budget",
        algorithm="sac",
        checkpoint=CheckpointConfig(root_dir=".artifacts"),
    )
    config.theory.variance_budget = 0.0
    assert any("variance_budget" in item for item in config.validate())


def test_training_safety_config_fields_validate() -> None:
    config = RLExperimentConfig(
        experiment_name="invalid-safety-fields",
        algorithm="sac",
        checkpoint=CheckpointConfig(root_dir=".artifacts"),
    )
    config.training.target_update_strategy = "weird"
    config.training.max_anomalies = 0
    config.training.entropy_min_temperature = 2.0
    config.training.entropy_max_temperature = 1.0
    errors = config.validate()
    assert any("target_update_strategy" in item for item in errors)
    assert any("max_anomalies" in item for item in errors)
    assert any("entropy_min_temperature" in item for item in errors)
