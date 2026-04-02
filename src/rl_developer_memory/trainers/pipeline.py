from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from rl_developer_memory.agents.base import ActorCriticAgent
from rl_developer_memory.buffers.base import InMemoryReplayBuffer, InMemoryRolloutBuffer, Transition
from rl_developer_memory.callbacks.base import CallbackManager
from rl_developer_memory.envs.base import Environment
from rl_developer_memory.experiments.metrics import MetricsCollector
from rl_developer_memory.experiments.recovery import RecoveryManager, RecoveryResult
from rl_developer_memory.trainers.stability import (
    EarlyStoppingController,
    EntropyTemperatureController,
    HardTargetUpdatePolicy,
    ObservationNormalizer,
    PlateauDetector,
    RewardNormalizer,
    SoftTargetUpdatePolicy,
    TargetUpdatePolicy,
    UpdateController,
)
from rl_developer_memory.utils.diagnostics import FailureSignatureCapture, TrainingDiagnosticsCollector
from rl_developer_memory.utils.numeric_guards import ensure_finite_metrics
from rl_developer_memory.utils.reproducibility import DeterministicSeedDiscipline


@dataclass(slots=True)
class StabilizationPolicy:
    deterministic_seed: int
    reward_scale: float
    advantage_scale: float
    target_update_tau: float
    entropy_temperature: float
    gradient_clip: float
    plateau_patience: int
    early_stop_min_delta: float
    checkpoint_rollbacks_enabled: bool = True
    reward_normalization: bool = True
    observation_normalization: bool = True
    normalization_clip: float = 5.0
    target_update_strategy: str = "soft"
    target_update_interval: int = 2
    entropy_autotune: bool = True
    entropy_min_temperature: float = 0.01
    entropy_max_temperature: float = 1.0
    entropy_learning_rate: float = 0.05
    exploding_update_ratio: float = 10.0
    exploding_update_abs_threshold: float = 1_000.0
    max_anomalies: int = 1
    anomaly_keys: tuple[str, ...] = ("bellman_residual", "critic_objective", "actor_objective")


@dataclass(slots=True)
class TrainerRuntime:
    seed_discipline: DeterministicSeedDiscipline
    reward_normalizer: RewardNormalizer
    observation_normalizer: ObservationNormalizer
    update_controller: UpdateController
    target_update_policy: TargetUpdatePolicy
    entropy_controller: EntropyTemperatureController
    early_stopping: EarlyStoppingController
    diagnostics: TrainingDiagnosticsCollector = field(default_factory=TrainingDiagnosticsCollector)
    failure_signatures: FailureSignatureCapture = field(default_factory=FailureSignatureCapture)


@dataclass(slots=True)
class TrainerPipeline:
    """Explicit, theory-aware trainer pipeline with separated stabilization responsibilities."""

    stabilization: StabilizationPolicy
    metrics: MetricsCollector = field(default_factory=MetricsCollector)
    replay_buffer: InMemoryReplayBuffer = field(default_factory=InMemoryReplayBuffer)
    rollout_buffer: InMemoryRolloutBuffer = field(default_factory=InMemoryRolloutBuffer)
    runtime: TrainerRuntime = field(init=False)

    def __post_init__(self) -> None:
        target_policy: TargetUpdatePolicy
        if self.stabilization.target_update_strategy == "hard":
            target_policy = HardTargetUpdatePolicy(interval=self.stabilization.target_update_interval)
        else:
            target_policy = SoftTargetUpdatePolicy(tau=self.stabilization.target_update_tau)
        self.runtime = TrainerRuntime(
            seed_discipline=DeterministicSeedDiscipline(self.stabilization.deterministic_seed),
            reward_normalizer=RewardNormalizer(
                enabled=self.stabilization.reward_normalization,
                clip_range=self.stabilization.normalization_clip,
            ),
            observation_normalizer=ObservationNormalizer(
                enabled=self.stabilization.observation_normalization,
                clip_range=self.stabilization.normalization_clip,
            ),
            update_controller=UpdateController(
                max_norm=self.stabilization.gradient_clip,
                ratio_threshold=self.stabilization.exploding_update_ratio,
                absolute_threshold=self.stabilization.exploding_update_abs_threshold,
            ),
            target_update_policy=target_policy,
            entropy_controller=EntropyTemperatureController(
                initial_temperature=self.stabilization.entropy_temperature,
                min_temperature=self.stabilization.entropy_min_temperature,
                max_temperature=self.stabilization.entropy_max_temperature,
                learning_rate=self.stabilization.entropy_learning_rate,
                target_entropy=0.5,
                enabled=self.stabilization.entropy_autotune,
            ),
            early_stopping=EarlyStoppingController(
                plateau_detector=PlateauDetector(
                    patience=self.stabilization.plateau_patience,
                    min_delta=self.stabilization.early_stop_min_delta,
                ),
                max_anomalies=self.stabilization.max_anomalies,
            ),
        )

    def define_problem_context(self, *, env: Environment) -> dict[str, Any]:
        return {"problem_family": "safe_rl", "env_id": env.spec.env_id, "reward_scale": env.spec.reward_scale}

    def prepare_interfaces(self, *, env: Environment) -> dict[str, Any]:
        return {"observation_shape": env.spec.observation_shape, "action_shape": env.spec.action_shape}

    def build_model_components(self, *, agent: ActorCriticAgent) -> dict[str, Any]:
        return {"policy": agent.policy.state_dict(), "value": agent.value.state_dict()}

    def define_loss_objectives(self) -> tuple[str, ...]:
        return ("td_target", "bellman_residual", "critic_objective", "actor_objective", "entropy_temperature")

    def bind_theory(self) -> tuple[str, ...]:
        return ("bellman_residual", "td_target", "critic_objective", "actor_objective", "entropy_temperature", "advantage_estimator", "lyapunov_hook")

    def decompose_loss_terms(self) -> dict[str, tuple[str, ...]]:
        return {
            "critic_path": ("td_target", "bellman_residual", "critic_objective"),
            "actor_path": ("advantage_estimator", "actor_objective"),
            "entropy_path": ("entropy_temperature",),
        }

    def map_update_equations(self) -> dict[str, str]:
        return {
            "td_backup": "rl_developer_memory.agents.base.ActorCriticAgent.compute_td_target",
            "critic_update": "rl_developer_memory.agents.base.ActorCriticAgent.compute_critic_objective",
            "actor_update": "rl_developer_memory.agents.base.ActorCriticAgent.compute_actor_objective",
            "target_network_update": f"{type(self.runtime.target_update_policy).__module__}.{type(self.runtime.target_update_policy).__name__}.apply",
        }

    def compute_td_target(self, *, reward: float, next_value: float, done: bool, discount: float) -> float:
        return reward if done else reward + discount * next_value

    def compute_advantage_estimate(self, *, td_target: float, value_prediction: float) -> float:
        return (td_target - value_prediction) * self.stabilization.advantage_scale

    def run_stability_audit(self, *, action: float, reward: float) -> dict[str, float]:
        lyapunov_margin = max(0.0, 1.0 - abs(action) * 0.5 + reward * 0.1)
        return {"lyapunov_margin": lyapunov_margin, "nan_inf_guard": 1.0}

    def run_hjb_audit(self, *, td_target: float, value_prediction: float) -> dict[str, float]:
        return {"hjb_residual_abs": abs(float(td_target) - float(value_prediction))}

    def run_constraint_audit(self, *, action: float) -> dict[str, float]:
        return {"constraint_margin": max(0.0, 1.0 - abs(float(action)))}

    def _normalize_step_inputs(self, *, observation: float, next_observation: float, reward: float) -> tuple[float, float, float]:
        normalized_observation = self.runtime.observation_normalizer.normalize(observation)
        normalized_next_observation = self.runtime.observation_normalizer.normalize(next_observation)
        normalized_reward = self.runtime.reward_normalizer.normalize(reward) * self.stabilization.reward_scale
        self.runtime.diagnostics.record_normalizer("observation", self.runtime.observation_normalizer.state_dict())
        self.runtime.diagnostics.record_normalizer("reward", self.runtime.reward_normalizer.state_dict())
        return normalized_observation, normalized_next_observation, normalized_reward

    def apply_stabilization(self, *, advantage: float, reward: float, step: int) -> dict[str, float]:
        controlled = self.runtime.update_controller.control("advantage", advantage)
        self.runtime.diagnostics.record_guard(
            step=step,
            name=controlled.name,
            payload={
                "clipped_update": controlled.guard.clipped_update,
                "gradient_norm": controlled.guard.gradient_norm,
                "finite": controlled.guard.finite,
                "exploded": controlled.explosion.exploded,
                "ratio": controlled.explosion.ratio,
            },
        )
        return {
            "clipped_update": controlled.guard.clipped_update,
            "gradient_norm": controlled.guard.gradient_norm,
            "exploding_update_guard": 1.0 if controlled.explosion.exploded else 0.0,
            "scaled_reward": reward,
            "update_ratio": controlled.explosion.ratio,
        }

    def describe_failure_modes(self) -> tuple[dict[str, Any], ...]:
        return (
            {
                "failure_id": "critic_drift",
                "trigger_metrics": ("bellman_residual_abs_mean", "critic_objective_mean"),
                "mitigation_hooks": ("gradient_clipping", "target_network", "reward_scaling"),
            },
            {
                "failure_id": "variance_explosion",
                "trigger_metrics": ("advantage_abs_mean", "return_std"),
                "mitigation_hooks": ("advantage_scaling", "seed_audit", "early_stop"),
            },
            {
                "failure_id": "constraint_erosion",
                "trigger_metrics": ("constraint_margin_mean", "constraint_violation_rate"),
                "mitigation_hooks": ("constraint_hook", "rollback", "action_clamp"),
            },
        )

    def suggest_ablation_hooks(self) -> tuple[dict[str, str], ...]:
        return (
            {"ablation_id": "seed_sweep", "config_key": "training.seed"},
            {"ablation_id": "reward_scale_sweep", "config_key": "training.reward_scale"},
            {"ablation_id": "gradient_clip_sweep", "config_key": "training.gradient_clip"},
            {"ablation_id": "entropy_temperature_sweep", "config_key": "training.entropy_temperature"},
        )

    def build_reporting_template(self) -> dict[str, tuple[str, ...]]:
        return {
            "problem_profile": ("problem_family", "env_id", "reward_scale"),
            "run_manifest": ("training_blueprint_id", "audit_hooks", "ablation_axes"),
            "metrics_payload": ("return_mean", "bellman_residual_abs_mean", "hjb_residual_abs_mean"),
            "validation_payload": ("seed_count", "artifact_validated", "variance_audited"),
            "theory_sync": ("audit_findings", "mapping_ids", "blueprint_id"),
            "artifact_refs": ("checkpoint_state", "checkpoint_metadata", "training_report", "evaluation_report"),
            "diagnostics": ("checkpoint_count", "rollback_count", "failure_signature_count"),
        }

    def _record_failure(self, *, step: int, family: str, values: dict[str, Any], message: str) -> None:
        self.runtime.diagnostics.record_anomaly(step=step, category=family, message=message, values=values)
        signature = self.runtime.failure_signatures.capture(family=family, step=step, details=values)
        self.runtime.diagnostics.record_failure_signature(signature)
        self.runtime.early_stopping.register_anomaly()

    def _handle_runtime_safety(
        self,
        *,
        step: int,
        metrics: dict[str, float],
        callbacks: CallbackManager,
        recovery_manager: RecoveryManager | None,
    ) -> tuple[bool, RecoveryResult | None]:
        finite_check = ensure_finite_metrics(metrics)
        if finite_check.finite:
            return False, None
        self._record_failure(
            step=step,
            family="nan_or_inf_instability",
            values={"invalid_keys": list(finite_check.invalid_keys), **finite_check.invalid_values},
            message="Non-finite metrics detected during training.",
        )
        callbacks.state.should_stop = True
        callbacks.state.metadata.setdefault("anomalies", []).append({"step": step, "keys": list(finite_check.invalid_keys)})
        if recovery_manager is not None and self.stabilization.checkpoint_rollbacks_enabled:
            result = recovery_manager.rollback_to_last_stable(agent=callbacks.state.metadata["agent"])
            if result.restored:
                self.runtime.diagnostics.record_rollback(step=step, restored_path=result.checkpoint)
                self.runtime.diagnostics.record_stop_reason("rollback-to-last-stable-checkpoint")
            return True, result
        self.runtime.diagnostics.record_stop_reason("non-finite-metrics")
        return True, None

    def train(
        self,
        *,
        agent: ActorCriticAgent,
        env: Environment,
        max_steps: int,
        callbacks: CallbackManager,
        recovery_manager: RecoveryManager | None = None,
        checkpoint_saver: Callable[[int, dict[str, float], bool], Any] | None = None,
    ) -> dict[str, Any]:
        self.runtime.diagnostics.record_seed(self.runtime.seed_discipline.apply().seed)
        callbacks.state.metadata["agent"] = agent
        observation = env.reset()
        step_metrics: dict[str, float] = {}
        problem_context = self.define_problem_context(env=env)
        interfaces = self.prepare_interfaces(env=env)
        model_components = self.build_model_components(agent=agent)
        loss_decomposition = self.decompose_loss_terms()
        update_equations = self.map_update_equations()
        ablation_hooks = self.suggest_ablation_hooks()
        reporting_template = self.build_reporting_template()
        step = 0
        for step in range(1, max(int(max_steps), 1) + 1):
            normalized_observation = self.runtime.observation_normalizer.normalize(observation)
            action = agent.act(normalized_observation)
            step_result = env.step(action)
            normalized_observation, normalized_next_observation, reward = self._normalize_step_inputs(
                observation=observation,
                next_observation=step_result.observation,
                reward=step_result.reward,
            )
            next_value = agent.target_value(normalized_next_observation)
            td_target = self.compute_td_target(
                reward=reward,
                next_value=next_value,
                done=step_result.terminated or step_result.truncated,
                discount=agent.context.discount,
            )
            advantage = self.compute_advantage_estimate(td_target=td_target, value_prediction=agent.value(normalized_observation))
            entropy_temperature = self.runtime.entropy_controller.update(abs(action))
            agent.context.entropy_temperature = entropy_temperature
            self.runtime.diagnostics.record_temperature(entropy_temperature)
            update_payload = agent.learn(
                observation=normalized_observation,
                reward=reward,
                next_observation=normalized_next_observation,
                done=step_result.terminated or step_result.truncated,
            )
            target_update = self.runtime.target_update_policy.apply(agent, step=step)
            self.runtime.diagnostics.record_target_update(target_update)
            transition = Transition(
                observation=normalized_observation,
                action=action,
                reward=reward,
                next_observation=normalized_next_observation,
                done=step_result.terminated or step_result.truncated,
            )
            self.replay_buffer.add(transition)
            self.rollout_buffer.add(transition)
            stability = self.run_stability_audit(action=action, reward=reward)
            hjb_audit = self.run_hjb_audit(td_target=td_target, value_prediction=agent.value(normalized_observation))
            constraint_audit = self.run_constraint_audit(action=action)
            guards = self.apply_stabilization(advantage=advantage, reward=reward, step=step)
            step_metrics = {
                **update_payload,
                **stability,
                **hjb_audit,
                **constraint_audit,
                **guards,
                **target_update,
                "advantage": advantage,
                "reward": reward,
                "return": reward,
                "entropy_temperature": entropy_temperature,
            }
            self.metrics.log(**step_metrics)
            stable_step = ensure_finite_metrics(step_metrics).finite and guards["exploding_update_guard"] == 0.0
            if checkpoint_saver is not None:
                checkpoint_record = checkpoint_saver(step, step_metrics, stable_step)
                if checkpoint_record is not None:
                    self.runtime.diagnostics.record_checkpoint(step=step, path=str(checkpoint_record.state_path), stable=stable_step)
            callback_state = callbacks.on_step(step=step, metrics=step_metrics)
            anomaly_stop, _rollback = self._handle_runtime_safety(
                step=step,
                metrics=step_metrics,
                callbacks=callbacks,
                recovery_manager=recovery_manager,
            )
            plateau_detected = self.runtime.early_stopping.plateau_detector.update(reward)
            if plateau_detected:
                self.runtime.diagnostics.record_stop_reason("plateau-detected")
            if callback_state.should_stop or anomaly_stop or self.runtime.early_stopping.should_stop(latest_return=reward, plateau=plateau_detected):
                break
            observation = env.reset() if step_result.terminated or step_result.truncated else step_result.observation
        callbacks.on_train_end(step=step, metrics=step_metrics)
        summary = self.metrics.summary()
        summary["steps_completed"] = float(step)
        diagnostics_summary = self.runtime.diagnostics.summary()
        return {
            "training_summary": summary,
            "callback_state": callbacks.state.metadata,
            "problem_context": problem_context,
            "interfaces": interfaces,
            "model_components": model_components,
            "loss_decomposition": loss_decomposition,
            "update_equations": update_equations,
            "failure_modes": self.describe_failure_modes(),
            "failure_findings": self.analyze_failure_modes(summary=summary),
            "ablation_hooks": ablation_hooks,
            "reporting_template": reporting_template,
            "diagnostics": diagnostics_summary,
        }

    def analyze_failure_modes(self, *, summary: dict[str, float]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        if summary.get("bellman_residual_abs_mean", 0.0) > 0.75:
            findings.append({"failure_id": "critic_drift", "severity": "warning"})
        if summary.get("advantage_abs_mean", 0.0) > 0.75 or summary.get("gradient_norm_mean", 0.0) > self.stabilization.gradient_clip:
            findings.append({"failure_id": "variance_explosion", "severity": "warning"})
        if summary.get("constraint_margin_mean", 1.0) < 0.1 or summary.get("lyapunov_margin", 1.0) <= 0.0:
            findings.append({"failure_id": "constraint_erosion", "severity": "warning"})
        if summary.get("entropy_temperature_mean", 0.1) < 0.02:
            findings.append({"failure_id": "entropy_collapse", "severity": "warning"})
        if self.runtime.diagnostics.rollbacks:
            findings.append({"failure_id": "runtime_rollback", "severity": "warning"})
        return findings
