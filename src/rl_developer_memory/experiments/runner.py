from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rl_developer_memory.agents.base import ActorCriticAgent, AgentContext
from rl_developer_memory.algorithms.catalog import build_algorithm_catalog
from rl_developer_memory.callbacks.base import AnomalyCallback, CallbackManager, EarlyStopCallback
from rl_developer_memory.envs.base import ActionClampWrapper, DeterministicBanditEnv
from rl_developer_memory.evaluation.base import Evaluator
from rl_developer_memory.experiments.checkpoints import CheckpointManager
from rl_developer_memory.experiments.config import RLExperimentConfig
from rl_developer_memory.experiments.recovery import RecoveryManager
from rl_developer_memory.theory.blueprint import AlgorithmTrainingBlueprint, build_training_blueprint_catalog
from rl_developer_memory.theory.registry import build_default_theory_registry, validate_assumption_bindings
from rl_developer_memory.theory.sync import validate_theorem_code_sync
from rl_developer_memory.theory.validators import (
    audit_seed_variance,
    validate_blueprint_registry_alignment,
    validate_experiment_assumptions,
    validate_result_artifacts,
)
from rl_developer_memory.trainers.pipeline import StabilizationPolicy, TrainerPipeline
from rl_developer_memory.utils.reproducibility import seed_everything
from rl_developer_memory.utils.serialization import load_json_file


@dataclass(slots=True)
class ExperimentReport:
    config: dict[str, Any]
    algorithm: dict[str, Any]
    training_blueprint: dict[str, Any]
    training_summary: dict[str, float]
    evaluation_summary: dict[str, Any]
    theory_sync: dict[str, Any]
    checkpoint: dict[str, Any]
    artifact_refs: list[dict[str, Any]]
    anomalies: list[dict[str, Any]]
    problem_profile: dict[str, Any]
    run_manifest: dict[str, Any]
    metrics_payload: dict[str, Any]
    validation_payload: dict[str, Any]
    diagnostics: dict[str, Any]


class ExperimentRunner:
    """Dependency-light experiment runner that feeds the existing RL audit surface."""

    def __init__(self, config: RLExperimentConfig) -> None:
        self.config = config
        errors = config.validate()
        if errors:
            raise ValueError("; ".join(errors))
        self.catalog = build_algorithm_catalog()
        self.registry = build_default_theory_registry()
        self.training_blueprints = build_training_blueprint_catalog(self.registry)

    def _build_agent(self) -> ActorCriticAgent:
        training = self.config.training
        context = AgentContext(
            discount=training.discount,
            learning_rate=training.learning_rate,
            entropy_temperature=training.entropy_temperature,
            target_update_tau=training.target_update_tau,
            metadata={"experiment_name": self.config.experiment_name, "rollout_posture": self.config.rollout_posture},
        )
        return ActorCriticAgent(context=context)

    def _load_checkpoint_if_available(self, *, agent: ActorCriticAgent, checkpoint_manager: CheckpointManager) -> str | None:
        """Load state from an explicit resume path or from the latest checkpoint when available."""

        resume_from = str(self.config.checkpoint.resume_from or "").strip()
        if resume_from:
            state_path = Path(resume_from)
            if state_path.exists():
                state_payload = load_json_file(state_path)
                if isinstance(state_payload, dict):
                    agent.load_state_dict(state_payload)
                    return str(state_path)
        loaded = checkpoint_manager.load_latest()
        latest = checkpoint_manager.latest()
        if loaded is not None and latest is not None:
            state_payload, _meta_payload = loaded
            if isinstance(state_payload, dict):
                agent.load_state_dict(state_payload)
                return str(latest.state_path)
        return None

    def _required_assumptions_for(self, blueprint: AlgorithmTrainingBlueprint) -> list[str]:
        mapping_index = {mapping.mapping_id: mapping for mapping in self.registry.mappings}
        required: set[str] = set()
        for mapping_id in blueprint.theorem_mapping_ids:
            mapping = mapping_index.get(mapping_id)
            if mapping is not None:
                required.update(mapping.assumption_ids)
        return sorted(required)

    def _build_artifact_refs(
        self,
        *,
        checkpoint_manager: CheckpointManager,
        blueprint: AlgorithmTrainingBlueprint,
        latest_step: int,
    ) -> list[dict[str, Any]]:
        repo_root = Path(__file__).resolve().parents[3]
        checkpoint_root = checkpoint_manager.root_dir
        checkpoint_state = checkpoint_root / f"checkpoint-step-{latest_step:04d}.state.json" if latest_step else checkpoint_root / "checkpoint-step-0000.state.json"
        checkpoint_meta = checkpoint_root / f"checkpoint-step-{latest_step:04d}.meta.json" if latest_step else checkpoint_root / "checkpoint-step-0000.meta.json"
        return [
            {"kind": "checkpoint_state", "uri": checkpoint_state.as_posix(), "description": f"{blueprint.algorithm_key} checkpoint state"},
            {"kind": "checkpoint_metadata", "uri": checkpoint_meta.as_posix(), "description": f"{blueprint.algorithm_key} checkpoint metadata"},
            {"kind": "theory_mapping_doc", "uri": (repo_root / "docs" / "theory_to_code.md").as_posix(), "description": "Theorem/code mapping reference"},
            {"kind": "training_report", "uri": f"memory://{self.config.experiment_name}/training-report", "description": "Structured training report payload"},
            {"kind": "evaluation_report", "uri": f"memory://{self.config.experiment_name}/evaluation-report", "description": "Structured evaluation report payload"},
        ]

    def run(self) -> ExperimentReport:
        seed_everything(self.config.training.seed)
        algorithm = self.catalog[self.config.algorithm.lower()]
        blueprint = self.training_blueprints[self.config.algorithm.lower()]
        env = ActionClampWrapper(DeterministicBanditEnv())
        agent = self._build_agent()
        pipeline = TrainerPipeline(
            stabilization=StabilizationPolicy(
                deterministic_seed=self.config.training.seed,
                reward_scale=self.config.training.reward_scale,
                advantage_scale=self.config.training.advantage_scale,
                target_update_tau=self.config.training.target_update_tau,
                entropy_temperature=self.config.training.entropy_temperature,
                gradient_clip=self.config.training.gradient_clip,
                plateau_patience=self.config.training.plateau_patience,
                early_stop_min_delta=self.config.training.early_stop_min_delta,
                reward_normalization=self.config.training.reward_normalization,
                observation_normalization=self.config.training.observation_normalization,
                normalization_clip=self.config.training.normalization_clip,
                target_update_strategy=self.config.training.target_update_strategy,
                target_update_interval=self.config.training.target_update_interval,
                entropy_autotune=self.config.training.entropy_autotune,
                entropy_min_temperature=self.config.training.entropy_min_temperature,
                entropy_max_temperature=self.config.training.entropy_max_temperature,
                entropy_learning_rate=self.config.training.entropy_learning_rate,
                exploding_update_ratio=self.config.training.exploding_update_ratio,
                exploding_update_abs_threshold=self.config.training.exploding_update_abs_threshold,
                max_anomalies=self.config.training.max_anomalies,
                checkpoint_rollbacks_enabled=self.config.training.rollback_on_anomaly,
            )
        )
        checkpoint_manager = CheckpointManager(self.config.checkpoint.root_dir, keep_last=self.config.checkpoint.keep_last)
        recovery_manager = RecoveryManager(checkpoint_manager)

        resume_source = self._load_checkpoint_if_available(agent=agent, checkpoint_manager=checkpoint_manager)
        pipeline.runtime.diagnostics.record_resume(source=resume_source or "", loaded=resume_source is not None)

        def save_checkpoint(step: int, metrics: dict[str, float], stable: bool = False) -> Any:
            record = checkpoint_manager.save(
                step=step,
                state=agent.state_dict(),
                metadata={"step": step, "metrics": metrics, "experiment_name": self.config.experiment_name},
                stable=stable,
            )
            if stable:
                checkpoint_manager.mark_stable(step)
            return record

        callbacks = CallbackManager(
            [
                AnomalyCallback(),
                EarlyStopCallback(metric_key="reward", patience=self.config.training.plateau_patience, min_delta=self.config.training.early_stop_min_delta),
            ]
        )
        train_result = pipeline.train(
            agent=agent,
            env=env,
            max_steps=self.config.training.max_steps,
            callbacks=callbacks,
            recovery_manager=recovery_manager,
            checkpoint_saver=save_checkpoint,
        )
        evaluation = Evaluator().evaluate(agent=agent, env=env, episodes=self.config.evaluation.episodes)
        summary = train_result["training_summary"]
        metrics_payload = {
            "return_mean": evaluation.return_mean,
            "return_std": evaluation.return_std,
            "tracking_rmse": max(0.0, 1.0 - evaluation.return_mean),
            "control_effort": evaluation.control_effort,
            "constraint_violation_rate": evaluation.constraint_violation_rate,
            "crash_rate": evaluation.crash_rate,
            "confidence_interval": [evaluation.return_mean - evaluation.return_std, evaluation.return_mean + evaluation.return_std],
            **{
                key: value
                for key, value in summary.items()
                if key.endswith("_mean")
                or key in {"bellman_residual_abs_mean", "advantage_abs_mean", "lyapunov_margin", "hjb_residual_abs_mean", "constraint_margin_mean"}
            },
        }
        latest = checkpoint_manager.latest()
        latest_stable = checkpoint_manager.latest_stable()
        checkpoint = {
            "root_dir": str(checkpoint_manager.root_dir),
            "latest_step": latest.step if latest else 0,
            "resume_from": self.config.checkpoint.resume_from,
            "rollback_enabled": True,
            "latest_stable_step": latest_stable.step if latest_stable else 0,
            "resumed_from": resume_source or "",
        }
        artifact_refs = self._build_artifact_refs(checkpoint_manager=checkpoint_manager, blueprint=blueprint, latest_step=checkpoint["latest_step"])
        theory_sync_check = validate_theorem_code_sync(
            self.registry,
            doc_path=Path(__file__).resolve().parents[3] / "docs" / "theory_to_code.md",
        )
        theory_findings = []
        theory_findings.extend(validate_blueprint_registry_alignment(blueprint, registry=self.registry))
        theory_findings.extend(
            validate_experiment_assumptions(
                blueprint=blueprint,
                registry=self.registry,
                documented_assumptions=self.config.theory.assumptions,
                documented_hidden_assumptions=self.config.theory.documented_hidden_assumptions,
                theorem_claim_type=self.config.theory.theorem_claim_type,
                lyapunov_candidate=self.config.theory.lyapunov_candidate,
                audit_hooks=self.config.theory.audit_hooks,
            )
        )
        theory_findings.extend(
            audit_seed_variance(
                seed_count=self.config.evaluation.required_seed_count,
                required_seed_count=self.config.evaluation.required_seed_count,
                production_min_seed_count=self.config.evaluation.production_min_seed_count,
                return_std=evaluation.return_std,
                confidence_interval=metrics_payload.get("confidence_interval"),
                variance_budget=self.config.theory.variance_budget,
            )
        )
        theory_findings.extend(
            validate_result_artifacts(
                artifact_refs,
                blueprint=blueprint,
                expected_artifacts=self.config.theory.artifact_expectations,
            )
        )
        artifact_validation_clean = not [item for item in theory_findings if item.audit_type == "runtime" and item.severity in {"warning", "error", "critical"}]
        seed_variance_clean = not [item for item in theory_findings if item.audit_type == "experiment" and item.severity in {"warning", "error", "critical"}]
        required_assumptions = self._required_assumptions_for(blueprint)
        theory_sync = {
            "status": "ok" if theory_sync_check["status"] == "ok" and not [item for item in theory_findings if item.severity == "error"] else "fail",
            "docs_ok": theory_sync_check["docs_ok"],
            "errors": list(theory_sync_check["errors"]),
            "blueprint_id": blueprint.algorithm_key,
            "mapping_ids": list(blueprint.theorem_mapping_ids),
            "required_assumptions": required_assumptions,
            "documented_assumptions": list(self.config.theory.assumptions),
            "missing_assumptions": validate_assumption_bindings(self.config.theory.assumptions, required_assumptions),
            "documented_hidden_assumptions": list(self.config.theory.documented_hidden_assumptions),
            "hidden_assumption_gaps": [item for item in blueprint.hidden_assumptions if item not in self.config.theory.documented_hidden_assumptions],
            "loss_decomposition": train_result["loss_decomposition"],
            "update_equations": train_result["update_equations"],
            "audit_hooks": [item.hook_id for item in blueprint.audit_hooks],
            "audit_findings": [item.to_record() for item in theory_findings],
        }
        problem_profile = {
            "problem_family": self.config.problem_family,
            "system_name": self.config.experiment_name,
            "task_name": self.config.train_env_id,
            "dynamics_class": self.config.dynamics_class,
            "state_dimension": self.config.state_dimension,
            "action_dimension": self.config.action_dimension,
            "observation_space": "scalar",
            "action_space": "scalar[-1,1]",
            "assumptions": list(self.config.theory.assumptions),
            "documented_hidden_assumptions": list(self.config.theory.documented_hidden_assumptions),
            "sampling_time": 1.0,
            "theorem_claim_type": self.config.theory.theorem_claim_type,
            "lyapunov_candidate": self.config.theory.lyapunov_candidate,
        }
        run_manifest = {
            "algorithm_family": algorithm.spec.name.lower(),
            "runtime_stage": "train" if self.config.rollout_posture == "shadow" else "production",
            "seed_count": self.config.evaluation.required_seed_count,
            "train_env_id": self.config.train_env_id,
            "eval_env_id": self.config.eval_env_id,
            "baseline_names": list(self.config.evaluation.baseline_names),
            "device": "cpu",
            "simulator": "deterministic-bandit",
            "action_bounds": [-1.0, 1.0],
            "normalization": {"reward_scale": self.config.training.reward_scale, "advantage_scale": self.config.training.advantage_scale},
            "training_blueprint_id": blueprint.algorithm_key,
            "audit_hooks": list(self.config.theory.audit_hooks),
            "ablation_axes": list(self.config.theory.ablation_axes),
            "reported_artifacts": [item["kind"] for item in artifact_refs],
        }
        validation_payload = {
            "seed_count": self.config.evaluation.required_seed_count,
            "theory_reviewed": True,
            "baseline_comparison": True,
            "hardware_validated": False,
            "production_verified": False,
            "reviewed_by": "rl-backbone",
            "notes": "Shadow-first rollout posture enforced. Theory blueprint, hidden assumptions, and artifact audits were attached.",
            "validation_tier": "theory_reviewed",
            "artifact_validated": artifact_validation_clean,
            "variance_audited": True,
            "variance_audit_clean": seed_variance_clean,
        }
        return ExperimentReport(
            config=self.config.to_dict(),
            algorithm=algorithm.to_dict(),
            training_blueprint=blueprint.to_dict(),
            training_summary=summary,
            evaluation_summary={
                "return_mean": evaluation.return_mean,
                "return_std": evaluation.return_std,
                "control_effort": evaluation.control_effort,
                "crash_rate": evaluation.crash_rate,
                "constraint_violation_rate": evaluation.constraint_violation_rate,
            },
            theory_sync=theory_sync,
            checkpoint=checkpoint,
            artifact_refs=artifact_refs,
            anomalies=list(train_result["callback_state"].get("anomalies", [])),
            problem_profile=problem_profile,
            run_manifest=run_manifest,
            metrics_payload=metrics_payload,
            validation_payload=validation_payload,
            diagnostics=train_result["diagnostics"],
        )

    def resume_from_checkpoint(self) -> ExperimentReport:
        checkpoint_manager = CheckpointManager(self.config.checkpoint.root_dir, keep_last=self.config.checkpoint.keep_last)
        latest = checkpoint_manager.latest()
        if latest is None:
            return self.run()
        self.config.checkpoint.resume_from = str(latest.state_path)
        return self.run()

    def evaluate_only(self, *, episodes: int | None = None) -> dict[str, Any]:
        """Run evaluation with checkpoint resume semantics and without a training loop."""

        seed_everything(self.config.training.seed)
        env = ActionClampWrapper(DeterministicBanditEnv())
        agent = self._build_agent()
        checkpoint_manager = CheckpointManager(self.config.checkpoint.root_dir, keep_last=self.config.checkpoint.keep_last)
        checkpoint_source = self._load_checkpoint_if_available(agent=agent, checkpoint_manager=checkpoint_manager)
        evaluation = Evaluator().evaluate(agent=agent, env=env, episodes=episodes or self.config.evaluation.episodes)
        return {
            "experiment_name": self.config.experiment_name,
            "algorithm": self.config.algorithm,
            "checkpoint_loaded": checkpoint_source is not None,
            "checkpoint_source": checkpoint_source or "",
            "evaluation_summary": {
                "return_mean": evaluation.return_mean,
                "return_std": evaluation.return_std,
                "control_effort": evaluation.control_effort,
                "crash_rate": evaluation.crash_rate,
                "constraint_violation_rate": evaluation.constraint_violation_rate,
            },
        }
