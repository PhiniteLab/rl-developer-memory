from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from rl_developer_memory.algorithms.catalog import AlgorithmBlueprint, build_algorithm_catalog

from .registry import TheoryRegistry, build_default_theory_registry


@dataclass(slots=True, frozen=True)
class BlueprintStepSpec:
    step_id: str
    order: int
    title: str
    description: str
    code_anchor: str


@dataclass(slots=True, frozen=True)
class LossDecompositionSpec:
    component_id: str
    equation_family: str
    description: str
    code_anchor: str
    metric_keys: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class UpdateEquationSpec:
    update_id: str
    equation_family: str
    equation_summary: str
    code_anchor: str
    input_terms: tuple[str, ...]
    stabilization_hooks: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class AuditHookSpec:
    hook_id: str
    theorem_family: str
    description: str
    code_anchor: str
    validator_anchor: str
    required_for: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class FailureModeSpec:
    failure_id: str
    description: str
    trigger_metrics: tuple[str, ...]
    mitigation_hooks: tuple[str, ...]
    detection_anchor: str


@dataclass(slots=True, frozen=True)
class AblationHookSpec:
    ablation_id: str
    config_key: str
    hypothesis: str
    code_anchor: str


@dataclass(slots=True, frozen=True)
class ReportingFieldSpec:
    section: str
    field_name: str
    source_anchor: str
    rationale: str


@dataclass(slots=True, frozen=True)
class ArtifactExpectationSpec:
    artifact_id: str
    kind: str
    producer_anchor: str
    validator_anchor: str
    required: bool = True


@dataclass(slots=True, frozen=True)
class AlgorithmTrainingBlueprint:
    algorithm_key: str
    algorithm_family: str
    theorem_mapping_ids: tuple[str, ...]
    hidden_assumptions: tuple[str, ...]
    steps: tuple[BlueprintStepSpec, ...]
    loss_decomposition: tuple[LossDecompositionSpec, ...]
    update_equations: tuple[UpdateEquationSpec, ...]
    audit_hooks: tuple[AuditHookSpec, ...]
    evaluation_metrics: tuple[str, ...]
    failure_modes: tuple[FailureModeSpec, ...]
    ablation_hooks: tuple[AblationHookSpec, ...]
    reporting_template: tuple[ReportingFieldSpec, ...]
    artifact_expectations: tuple[ArtifactExpectationSpec, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _common_steps() -> tuple[BlueprintStepSpec, ...]:
    return (
        BlueprintStepSpec(
            step_id="problem_definition",
            order=1,
            title="env/problem tanımı",
            description="Problem family, dynamics, reward scale, and rollout posture are fixed before updates begin.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.define_problem_context",
        ),
        BlueprintStepSpec(
            step_id="interface_contract",
            order=2,
            title="observation-action interface",
            description="Observation and action contracts are documented before network or optimizer decisions.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.prepare_interfaces",
        ),
        BlueprintStepSpec(
            step_id="network_setup",
            order=3,
            title="network ve parameter config",
            description="The algorithm-specific network roles are materialized and checkpointed.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.build_model_components",
        ),
        BlueprintStepSpec(
            step_id="objective_definition",
            order=4,
            title="objective/loss tanımı",
            description="Loss decomposition is explicit and tied to named objective terms.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.define_loss_objectives",
        ),
        BlueprintStepSpec(
            step_id="theory_binding",
            order=5,
            title="update equations ve theorem binding",
            description="Named theorem mappings are bound to code anchors before training proceeds.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.bind_theory",
        ),
        BlueprintStepSpec(
            step_id="training_loop",
            order=6,
            title="training loop",
            description="The core update loop logs theory-aware metrics at every step.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.train",
        ),
        BlueprintStepSpec(
            step_id="stabilization",
            order=7,
            title="stabilization layer",
            description="Gradient, entropy, reward, target-network, and anomaly guards are applied consistently.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.apply_stabilization",
        ),
        BlueprintStepSpec(
            step_id="evaluation",
            order=8,
            title="evaluation metrics",
            description="Evaluation emits control- and RL-aware summary metrics over seeded episodes.",
            code_anchor="rl_developer_memory.evaluation.base.Evaluator.evaluate",
        ),
        BlueprintStepSpec(
            step_id="failure_analysis",
            order=9,
            title="failure modes",
            description="Known failure modes and mitigations are available to audits and reviewers.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.describe_failure_modes",
        ),
        BlueprintStepSpec(
            step_id="reporting",
            order=10,
            title="ablation/reporting template",
            description="Every run emits a standard report package for audits, ablations, and memory storage.",
            code_anchor="rl_developer_memory.experiments.runner.ExperimentRunner.run",
        ),
    )


def _hidden_assumptions_for(spec: AlgorithmBlueprint) -> tuple[str, ...]:
    assumptions = ["observation_sufficiency", "control_objective_well_posed"]
    if spec.spec.data_strategy == "off_policy_replay":
        assumptions.append("replay_distribution_matched")
    if "target_network" in spec.spec.stabilization_stack:
        assumptions.append("target_network_lag_controlled")
    return tuple(dict.fromkeys(assumptions))


def _build_loss_decomposition(spec: AlgorithmBlueprint, registry: TheoryRegistry) -> tuple[LossDecompositionSpec, ...]:
    objective_index = {item.term_id: item for item in registry.objectives}
    mapping_index = {item.mapping_id: item for item in registry.mappings}
    components: list[LossDecompositionSpec] = []
    for term_id in spec.spec.objective_terms:
        objective = objective_index[term_id]
        mapping = mapping_index.get(term_id)
        components.append(
            LossDecompositionSpec(
                component_id=term_id,
                equation_family=objective.equation_family,
                description=objective.description,
                code_anchor=objective.code_anchor,
                metric_keys=mapping.metric_keys if mapping is not None else (),
            )
        )
    return tuple(components)


def _build_update_equations(spec: AlgorithmBlueprint) -> tuple[UpdateEquationSpec, ...]:
    equations: list[UpdateEquationSpec] = [
        UpdateEquationSpec(
            update_id="td_backup",
            equation_family="temporal_difference",
            equation_summary="y_t = r_t + γ V_target(s_{t+1})",
            code_anchor="rl_developer_memory.agents.base.ActorCriticAgent.compute_td_target",
            input_terms=("reward", "next_value", "discount"),
            stabilization_hooks=("reward_scaling",),
        ),
        UpdateEquationSpec(
            update_id="critic_update",
            equation_family="critic_loss",
            equation_summary="L_critic = || y_t - V(s_t) ||^2",
            code_anchor="rl_developer_memory.agents.base.ActorCriticAgent.compute_critic_objective",
            input_terms=("td_target", "value_prediction"),
            stabilization_hooks=("gradient_clipping", "nan_guard"),
        ),
    ]
    if "actor_objective" in spec.spec.objective_terms:
        equations.append(
            UpdateEquationSpec(
                update_id="actor_update",
                equation_family="policy_loss",
                equation_summary="L_actor = - π(a_t|s_t) · A_t",
                code_anchor="rl_developer_memory.agents.base.ActorCriticAgent.compute_actor_objective",
                input_terms=("action", "advantage"),
                stabilization_hooks=("advantage_scaling", "gradient_clipping"),
            )
        )
    if "entropy_temperature" in spec.spec.objective_terms:
        equations.append(
            UpdateEquationSpec(
                update_id="entropy_update",
                equation_family="entropy_regularization",
                equation_summary="L_α = α (H_target - H(π))",
                code_anchor="rl_developer_memory.agents.base.ActorCriticAgent.compute_entropy_temperature_loss",
                input_terms=("entropy", "target_entropy"),
                stabilization_hooks=("entropy_tuning",),
            )
        )
    if "target_network" in spec.spec.stabilization_stack:
        equations.append(
            UpdateEquationSpec(
                update_id="target_network_update",
                equation_family="soft_update",
                equation_summary="θ_target ← (1-τ) θ_target + τ θ_online",
                code_anchor="rl_developer_memory.agents.base.ActorCriticAgent.update_target_network",
                input_terms=("target_params", "online_params", "tau"),
                stabilization_hooks=("target_network",),
            )
        )
    return tuple(equations)


def _build_audit_hooks(spec: AlgorithmBlueprint) -> tuple[AuditHookSpec, ...]:
    hooks = [
        AuditHookSpec(
            hook_id="lyapunov_hook",
            theorem_family="stability_audit",
            description="Checks Lyapunov-style stability margins during the update loop.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.run_stability_audit",
            validator_anchor="rl_developer_memory.theory.validators.validate_experiment_assumptions",
            required_for=("safe_rl", "robust_rl", "mpc"),
        ),
        AuditHookSpec(
            hook_id="constraint_hook",
            theorem_family="constraint_satisfaction",
            description="Tracks control-constraint margins for safe RL style experiments.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.run_constraint_audit",
            validator_anchor="rl_developer_memory.theory.validators.validate_result_artifacts",
            required_for=("safe_rl", "robust_rl", "mpc"),
        ),
    ]
    if spec.spec.family in {"actor_critic", "value_based"}:
        hooks.append(
            AuditHookSpec(
                hook_id="hjb_hook",
                theorem_family="hjb_optimality",
                description="Audits HJB-style residual proxies for control-oriented value updates.",
                code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.run_hjb_audit",
                validator_anchor="rl_developer_memory.theory.validators.validate_experiment_assumptions",
                required_for=("safe_rl", "robust_rl", "hjb", "bellman_dp"),
            )
        )
    return tuple(hooks)


def _build_failure_modes(spec: AlgorithmBlueprint) -> tuple[FailureModeSpec, ...]:
    modes = [
        FailureModeSpec(
            failure_id="critic_drift",
            description="Bellman residuals or critic objectives grow without bound.",
            trigger_metrics=("bellman_residual_abs_mean", "critic_objective_mean"),
            mitigation_hooks=("gradient_clipping", "reward_scaling", "target_network"),
            detection_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.describe_failure_modes",
        ),
        FailureModeSpec(
            failure_id="variance_explosion",
            description="Advantages or seeded returns become too noisy for stable improvement.",
            trigger_metrics=("advantage_abs_mean", "return_std"),
            mitigation_hooks=("advantage_scaling", "seed_audit", "early_stop"),
            detection_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.describe_failure_modes",
        ),
    ]
    if "entropy_temperature" in spec.spec.objective_terms:
        modes.append(
            FailureModeSpec(
                failure_id="entropy_collapse",
                description="Policy support collapses and exploration vanishes.",
                trigger_metrics=("entropy_temperature_mean",),
                mitigation_hooks=("entropy_tuning",),
                detection_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.describe_failure_modes",
            )
        )
    return tuple(modes)


def _build_ablation_hooks(spec: AlgorithmBlueprint) -> tuple[AblationHookSpec, ...]:
    return (
        AblationHookSpec(
            ablation_id="seed_sweep",
            config_key="training.seed",
            hypothesis="Performance remains directionally stable across seed changes.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.suggest_ablation_hooks",
        ),
        AblationHookSpec(
            ablation_id="reward_scale_sweep",
            config_key="training.reward_scale",
            hypothesis="Reward scaling should not change the sign of the learning signal.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.suggest_ablation_hooks",
        ),
        AblationHookSpec(
            ablation_id="gradient_clip_sweep",
            config_key="training.gradient_clip",
            hypothesis="Gradient clip selection should trade off speed and stability predictably.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.suggest_ablation_hooks",
        ),
        AblationHookSpec(
            ablation_id="entropy_temperature_sweep",
            config_key="training.entropy_temperature",
            hypothesis="Entropy tuning changes exploration breadth without invalidating theory assumptions.",
            code_anchor="rl_developer_memory.trainers.pipeline.TrainerPipeline.suggest_ablation_hooks",
        ),
    )


def _build_reporting_template() -> tuple[ReportingFieldSpec, ...]:
    return (
        ReportingFieldSpec("problem_profile", "problem_family", "rl_developer_memory.experiments.runner.ExperimentRunner.run", "States the task family and control context."),
        ReportingFieldSpec("problem_profile", "assumptions", "rl_developer_memory.experiments.runner.ExperimentRunner.run", "Documents explicit theorem assumptions."),
        ReportingFieldSpec("run_manifest", "training_blueprint_id", "rl_developer_memory.experiments.runner.ExperimentRunner.run", "Identifies the reusable training blueprint contract."),
        ReportingFieldSpec("run_manifest", "audit_hooks", "rl_developer_memory.experiments.runner.ExperimentRunner.run", "Shows which theory/control audits were active."),
        ReportingFieldSpec("metrics_payload", "return_mean", "rl_developer_memory.experiments.runner.ExperimentRunner.run", "Primary performance summary."),
        ReportingFieldSpec("metrics_payload", "bellman_residual_abs_mean", "rl_developer_memory.experiments.runner.ExperimentRunner.run", "Tracks critic consistency risk."),
        ReportingFieldSpec("metrics_payload", "hjb_residual_abs_mean", "rl_developer_memory.experiments.runner.ExperimentRunner.run", "Tracks HJB/control optimality proxy risk."),
        ReportingFieldSpec("validation_payload", "seed_count", "rl_developer_memory.experiments.runner.ExperimentRunner.run", "Links evaluation to seed/variance evidence."),
        ReportingFieldSpec("theory_sync", "audit_findings", "rl_developer_memory.experiments.runner.ExperimentRunner.run", "Captures theorem/code, assumption, and artifact audit findings."),
    )


def _build_artifact_expectations() -> tuple[ArtifactExpectationSpec, ...]:
    return (
        ArtifactExpectationSpec(
            artifact_id="checkpoint_state",
            kind="checkpoint_state",
            producer_anchor="rl_developer_memory.experiments.checkpoints.CheckpointManager.save",
            validator_anchor="rl_developer_memory.theory.validators.validate_result_artifacts",
        ),
        ArtifactExpectationSpec(
            artifact_id="checkpoint_metadata",
            kind="checkpoint_metadata",
            producer_anchor="rl_developer_memory.experiments.checkpoints.CheckpointManager.save",
            validator_anchor="rl_developer_memory.theory.validators.validate_result_artifacts",
        ),
        ArtifactExpectationSpec(
            artifact_id="theory_mapping_doc",
            kind="theory_mapping_doc",
            producer_anchor="docs/THEORY_TO_CODE.md",
            validator_anchor="rl_developer_memory.theory.sync.validate_theorem_code_sync",
        ),
        ArtifactExpectationSpec(
            artifact_id="training_report",
            kind="training_report",
            producer_anchor="rl_developer_memory.experiments.runner.ExperimentRunner.run",
            validator_anchor="rl_developer_memory.theory.validators.validate_result_artifacts",
        ),
        ArtifactExpectationSpec(
            artifact_id="evaluation_report",
            kind="evaluation_report",
            producer_anchor="rl_developer_memory.evaluation.base.Evaluator.evaluate",
            validator_anchor="rl_developer_memory.theory.validators.validate_result_artifacts",
        ),
    )


def build_training_blueprint_catalog(registry: TheoryRegistry | None = None) -> dict[str, AlgorithmTrainingBlueprint]:
    registry = registry or build_default_theory_registry()
    catalog = build_algorithm_catalog()
    steps = _common_steps()
    reporting_template = _build_reporting_template()
    artifact_expectations = _build_artifact_expectations()
    blueprints: dict[str, AlgorithmTrainingBlueprint] = {}
    for key, spec in catalog.items():
        blueprints[key] = AlgorithmTrainingBlueprint(
            algorithm_key=key,
            algorithm_family=spec.spec.family,
            theorem_mapping_ids=spec.theorem_mapping_ids,
            hidden_assumptions=_hidden_assumptions_for(spec),
            steps=steps,
            loss_decomposition=_build_loss_decomposition(spec, registry),
            update_equations=_build_update_equations(spec),
            audit_hooks=_build_audit_hooks(spec),
            evaluation_metrics=spec.evaluation_focus,
            failure_modes=_build_failure_modes(spec),
            ablation_hooks=_build_ablation_hooks(spec),
            reporting_template=reporting_template,
            artifact_expectations=artifact_expectations,
        )
    return blueprints
