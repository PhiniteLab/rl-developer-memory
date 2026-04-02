from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib as _toml  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - Python 3.10 fallback
    try:
        import tomli as _toml  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover - fallback depends on runtime deps
        _toml = None  # type: ignore[assignment]


def _coerce_str_list(value: Any, *, default: list[str]) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return list(default)


def _normalize_legacy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy helper templates into the RLExperimentConfig schema."""

    if "experiment_name" in payload and "algorithm" in payload:
        return payload
    experiment = payload.get("experiment")
    if not isinstance(experiment, dict):
        return payload

    stabilization = payload.get("stabilization", {})
    if not isinstance(stabilization, dict):
        stabilization = {}
    checkpoint = payload.get("checkpoint", {})
    if not isinstance(checkpoint, dict):
        checkpoint = {}

    inferred_posture = str(
        experiment.get("rollout_posture")
        or ("active" if "active" in str(experiment.get("name", "")).lower() else "shadow")
    ).lower()
    if inferred_posture not in {"shadow", "active"}:
        inferred_posture = "shadow"

    required_seed_count = int(experiment.get("required_seed_count", 3))
    normalized_checkpoint_root = str(checkpoint.get("root_dir") or f".artifacts/rl_backbone/{inferred_posture}")
    normalized: dict[str, Any] = {
        "experiment_name": str(experiment.get("name", "rl-backbone-legacy")),
        "algorithm": str(experiment.get("algorithm", "ppo")),
        "rollout_posture": inferred_posture,
        "project_scope": str(experiment.get("project_scope", "rl-developer-memory")),
        "user_scope": str(experiment.get("user_scope", "")),
        "train_env_id": str(experiment.get("env_id", "deterministic-bandit-v0")),
        "eval_env_id": str(experiment.get("eval_env_id", experiment.get("env_id", "deterministic-bandit-v0"))),
        "problem_family": str(experiment.get("problem_family", "safe_rl")),
        "dynamics_class": str(experiment.get("dynamics_class", "discrete_time")),
        "state_dimension": int(experiment.get("state_dimension", 1)),
        "action_dimension": int(experiment.get("action_dimension", 1)),
        "training": {
            "seed": int(experiment.get("seed", 7)),
            "discount": float(experiment.get("discount", 0.95)),
            "learning_rate": float(experiment.get("learning_rate", 0.1)),
            "max_steps": int(experiment.get("train_steps", 12)),
            "plateau_patience": int(stabilization.get("plateau_patience", 4)),
            "early_stop_min_delta": float(stabilization.get("early_stop_min_delta", 1e-3)),
            "gradient_clip": float(stabilization.get("gradient_clip", 0.5)),
            "reward_scale": float(stabilization.get("reward_scale", 1.0)),
            "advantage_scale": float(stabilization.get("advantage_scale", 1.0)),
            "reward_normalization": bool(stabilization.get("reward_normalization", True)),
            "observation_normalization": bool(stabilization.get("observation_normalization", True)),
            "normalization_clip": float(stabilization.get("normalization_clip", 5.0)),
            "target_update_tau": float(stabilization.get("target_update_tau", 0.5)),
            "target_update_strategy": str(stabilization.get("target_update_strategy", "soft")),
            "target_update_interval": int(stabilization.get("target_update_interval", 2)),
            "entropy_temperature": float(stabilization.get("entropy_temperature", 0.1)),
            "entropy_autotune": bool(stabilization.get("entropy_autotune", True)),
            "entropy_min_temperature": float(stabilization.get("entropy_min_temperature", 0.01)),
            "entropy_max_temperature": float(stabilization.get("entropy_max_temperature", 1.0)),
            "entropy_learning_rate": float(stabilization.get("entropy_learning_rate", 0.05)),
            "exploding_update_ratio": float(stabilization.get("exploding_update_ratio", 10.0)),
            "exploding_update_abs_threshold": float(stabilization.get("exploding_update_abs_threshold", 1_000.0)),
            "max_anomalies": int(stabilization.get("max_anomalies", 1)),
            "rollback_on_anomaly": bool(stabilization.get("rollback_on_anomaly", True)),
        },
        "evaluation": {
            "episodes": int(experiment.get("eval_episodes", 3)),
            "required_seed_count": required_seed_count,
            "production_min_seed_count": int(experiment.get("production_min_seed_count", max(required_seed_count, 5))),
            "baseline_names": _coerce_str_list(experiment.get("baseline_names"), default=["scalar-baseline"]),
        },
        "theory": {
            "theorem_claim_type": str(experiment.get("theorem_claim_type", "bellman_consistency")),
            "assumptions": _coerce_str_list(
                experiment.get("assumptions"),
                default=["markov_transition", "bounded_reward", "stationary_rollout"],
            ),
            "documented_hidden_assumptions": _coerce_str_list(
                experiment.get("documented_hidden_assumptions"),
                default=["observation_sufficiency", "control_objective_well_posed"],
            ),
            "lyapunov_candidate": str(experiment.get("lyapunov_candidate", "quadratic_energy")),
            "notation_profile": str(experiment.get("notation_profile", "default")),
            "audit_hooks": _coerce_str_list(
                experiment.get("audit_hooks"),
                default=["lyapunov_hook", "constraint_hook"],
            ),
            "artifact_expectations": _coerce_str_list(
                experiment.get("artifact_expectations"),
                default=["checkpoint_state", "checkpoint_metadata", "theory_mapping_doc", "training_report", "evaluation_report"],
            ),
            "ablation_axes": _coerce_str_list(
                experiment.get("ablation_axes"),
                default=["training.seed", "training.reward_scale", "training.gradient_clip"],
            ),
            "variance_budget": float(experiment.get("variance_budget", 1.0)),
        },
        "checkpoint": {
            "root_dir": normalized_checkpoint_root,
            "save_every_steps": int(checkpoint.get("save_every_steps", 3)),
            "keep_last": int(checkpoint.get("keep_last", 3)),
            "resume_from": str(checkpoint.get("resume_from", "")),
        },
        "rollout_gate_status": {
            "shadow_health_clean": bool(payload.get("rollout_gate_status", {}).get("shadow_health_clean", False)),
            "benchmarks_stable": bool(payload.get("rollout_gate_status", {}).get("benchmarks_stable", False)),
            "review_backlog_managed": bool(payload.get("rollout_gate_status", {}).get("review_backlog_managed", False)),
        },
        "metadata": {"normalized_from_legacy_template": "1"},
    }
    return normalized


@dataclass(slots=True)
class RolloutGateStatus:
    shadow_health_clean: bool = False
    benchmarks_stable: bool = False
    review_backlog_managed: bool = False


@dataclass(slots=True)
class TrainingConfig:
    seed: int = 7
    discount: float = 0.95
    learning_rate: float = 0.1
    max_steps: int = 12
    plateau_patience: int = 4
    early_stop_min_delta: float = 1e-3
    gradient_clip: float = 0.5
    reward_scale: float = 1.0
    advantage_scale: float = 1.0
    reward_normalization: bool = True
    observation_normalization: bool = True
    normalization_clip: float = 5.0
    target_update_tau: float = 0.5
    target_update_strategy: str = "soft"
    target_update_interval: int = 2
    entropy_temperature: float = 0.1
    entropy_autotune: bool = True
    entropy_min_temperature: float = 0.01
    entropy_max_temperature: float = 1.0
    entropy_learning_rate: float = 0.05
    exploding_update_ratio: float = 10.0
    exploding_update_abs_threshold: float = 1000.0
    max_anomalies: int = 1
    rollback_on_anomaly: bool = True


@dataclass(slots=True)
class EvaluationConfig:
    episodes: int = 3
    required_seed_count: int = 3
    production_min_seed_count: int = 5
    baseline_names: list[str] = field(default_factory=lambda: ["scalar-baseline"])


@dataclass(slots=True)
class TheoryConfig:
    theorem_claim_type: str = "bellman_consistency"
    assumptions: list[str] = field(default_factory=lambda: ["markov_transition", "bounded_reward", "stationary_rollout"])
    documented_hidden_assumptions: list[str] = field(default_factory=lambda: ["observation_sufficiency", "control_objective_well_posed"])
    lyapunov_candidate: str = "quadratic_energy"
    notation_profile: str = "default"
    audit_hooks: list[str] = field(default_factory=lambda: ["lyapunov_hook", "constraint_hook"])
    artifact_expectations: list[str] = field(
        default_factory=lambda: ["checkpoint_state", "checkpoint_metadata", "theory_mapping_doc", "training_report", "evaluation_report"]
    )
    ablation_axes: list[str] = field(default_factory=lambda: ["training.seed", "training.reward_scale", "training.gradient_clip"])
    variance_budget: float = 1.0


@dataclass(slots=True)
class CheckpointConfig:
    root_dir: str
    save_every_steps: int = 3
    keep_last: int = 3
    resume_from: str = ""


@dataclass(slots=True)
class RLExperimentConfig:
    experiment_name: str
    algorithm: str
    rollout_posture: str = "shadow"
    project_scope: str = "rl-developer-memory"
    user_scope: str = ""
    train_env_id: str = "deterministic-bandit-v0"
    eval_env_id: str = "deterministic-bandit-v0"
    problem_family: str = "safe_rl"
    dynamics_class: str = "discrete_time"
    state_dimension: int = 1
    action_dimension: int = 1
    training: TrainingConfig = field(default_factory=TrainingConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    theory: TheoryConfig = field(default_factory=TheoryConfig)
    checkpoint: CheckpointConfig = field(default_factory=lambda: CheckpointConfig(root_dir=".artifacts/rl_backbone"))
    rollout_gate_status: RolloutGateStatus = field(default_factory=RolloutGateStatus)
    metadata: dict[str, str] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.rollout_posture not in {"shadow", "active"}:
            errors.append("rollout_posture must be shadow or active")
        if self.training.max_steps <= 0:
            errors.append("training.max_steps must be positive")
        if self.training.gradient_clip <= 0:
            errors.append("training.gradient_clip must be positive")
        if self.training.normalization_clip <= 0:
            errors.append("training.normalization_clip must be positive")
        if self.training.discount <= 0 or self.training.discount > 1:
            errors.append("training.discount must be within (0, 1]")
        if self.training.target_update_strategy not in {"soft", "hard"}:
            errors.append("training.target_update_strategy must be soft or hard")
        if self.training.target_update_interval <= 0:
            errors.append("training.target_update_interval must be positive")
        if self.training.entropy_min_temperature <= 0 or self.training.entropy_max_temperature <= 0:
            errors.append("entropy temperature bounds must be positive")
        if self.training.entropy_min_temperature > self.training.entropy_max_temperature:
            errors.append("entropy_min_temperature must be <= entropy_max_temperature")
        if self.training.exploding_update_ratio <= 0:
            errors.append("training.exploding_update_ratio must be positive")
        if self.training.exploding_update_abs_threshold <= 0:
            errors.append("training.exploding_update_abs_threshold must be positive")
        if self.training.max_anomalies <= 0:
            errors.append("training.max_anomalies must be positive")
        if self.theory.variance_budget <= 0:
            errors.append("theory.variance_budget must be positive")
        if Path(self.checkpoint.root_dir).as_posix().startswith("/mnt/c/"):
            errors.append("checkpoint.root_dir must stay on the local Linux/WSL filesystem")
        if self.rollout_posture == "active":
            gates = self.rollout_gate_status
            if not (gates.shadow_health_clean and gates.benchmarks_stable and gates.review_backlog_managed):
                errors.append("active rollout requires clean shadow health, stable benchmarks, and manageable review backlog")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RLExperimentConfig":
        payload = _normalize_legacy_payload(payload)
        if "experiment_name" not in payload:
            raise ValueError("config must define 'experiment_name'")
        if "algorithm" not in payload:
            raise ValueError("config must define 'algorithm'")
        return cls(
            experiment_name=str(payload["experiment_name"]),
            algorithm=str(payload["algorithm"]),
            rollout_posture=str(payload.get("rollout_posture", "shadow")),
            project_scope=str(payload.get("project_scope", "rl-developer-memory")),
            user_scope=str(payload.get("user_scope", "")),
            train_env_id=str(payload.get("train_env_id", "deterministic-bandit-v0")),
            eval_env_id=str(payload.get("eval_env_id", "deterministic-bandit-v0")),
            problem_family=str(payload.get("problem_family", "safe_rl")),
            dynamics_class=str(payload.get("dynamics_class", "discrete_time")),
            state_dimension=int(payload.get("state_dimension", 1)),
            action_dimension=int(payload.get("action_dimension", 1)),
            training=TrainingConfig(**payload.get("training", {})),
            evaluation=EvaluationConfig(**payload.get("evaluation", {})),
            theory=TheoryConfig(**payload.get("theory", {})),
            checkpoint=CheckpointConfig(**payload.get("checkpoint", {"root_dir": ".artifacts/rl_backbone"})),
            rollout_gate_status=RolloutGateStatus(**payload.get("rollout_gate_status", {})),
            metadata={str(key): str(value) for key, value in payload.get("metadata", {}).items()},
        )

    @classmethod
    def load(cls, path: Path | str) -> "RLExperimentConfig":
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        if suffix == ".json":
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        elif suffix == ".toml":
            if _toml is None:  # pragma: no cover - Python 3.10 without TOML parser dependency
                raise RuntimeError("TOML loading requires Python 3.11+ or `tomli` on Python 3.10.")
            payload = _toml.loads(file_path.read_text(encoding="utf-8"))
        else:
            raise ValueError(f"Unsupported config format: {suffix}")
        return cls.from_dict(payload)
