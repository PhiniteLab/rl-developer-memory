# Theory to code

Machine-checkable theorem-to-code mapping and training blueprint for the RL backbone.

This document is not just narrative documentation. It mirrors code-level anchors used by:
- `rl_developer_memory.theory.sync`
- `rl_developer_memory.theory.validators`
- `rl_developer_memory.experiments.runner.ExperimentRunner`

The goal is that any future RL algorithm added to the repo follows the same professional flow:
1. env/problem definition
2. observation/action interface
3. network/parameter configuration
4. objective/loss decomposition
5. update equations and code anchors
6. stabilization layer
7. evaluation metrics
8. failure-mode audit
9. ablation hooks
10. reporting template

## Assumptions registry

| assumption_id | type | description | validator_anchor |
| --- | --- | --- | --- |
| markov_transition | explicit | Transitions satisfy the Markov property at the selected observation boundary. | rl_developer_memory.theory.registry.validate_assumption_bindings |
| bounded_reward | explicit | Rewards are bounded or appropriately scaled before updates accumulate. | rl_developer_memory.theory.registry.validate_assumption_bindings |
| differentiable_policy | explicit | Policy loss is differentiable under the chosen actor parameterization. | rl_developer_memory.theory.registry.validate_assumption_bindings |
| stationary_rollout | explicit | Rollout data comes from a controlled, seed-tracked data-collection regime. | rl_developer_memory.theory.registry.validate_assumption_bindings |
| lyapunov_candidate_documented | explicit | Stability-style claims identify a Lyapunov or surrogate energy function. | rl_developer_memory.theory.registry.validate_assumption_bindings |
| observation_sufficiency | hidden | The observation interface contains enough state for the selected theorem/objective family. | rl_developer_memory.theory.validators.validate_experiment_assumptions |
| replay_distribution_matched | hidden | Replay-distribution shift is controlled well enough for off-policy learning. | rl_developer_memory.theory.validators.validate_experiment_assumptions |
| control_objective_well_posed | hidden | The control objective and action constraints are consistent with the stated theorem claim. | rl_developer_memory.theory.validators.validate_experiment_assumptions |
| target_network_lag_controlled | hidden | Target-network lag remains within the regime assumed by bootstrap-based updates. | rl_developer_memory.theory.validators.validate_experiment_assumptions |
| terminal_boundary_condition_documented | hidden | HJB/value-boundary assumptions are documented whenever control-optimality claims are made. | rl_developer_memory.theory.validators.validate_experiment_assumptions |

## Notation registry

| symbol | meaning | code_anchor |
| --- | --- | --- |
| s_t | Observation/state at time t | rl_developer_memory.envs.base.StepResult.observation |
| a_t | Action emitted by the policy | rl_developer_memory.agents.base.ActorCriticAgent.act |
| r_t | Reward observed after action execution | rl_developer_memory.envs.base.StepResult.reward |
| V_theta | Value function parameterized by theta | rl_developer_memory.networks.base.ScalarValueNetwork |
| pi_theta | Policy parameterized by theta | rl_developer_memory.networks.base.ScalarPolicyNetwork |

## Theorem mapping table

| mapping_id | equation_family | code_anchor | assumption_ids | validator_anchor | metric_keys | risk_description |
| --- | --- | --- | --- | --- | --- | --- |
| bellman_residual | bellman | rl_developer_memory.agents.base.ActorCriticAgent.compute_bellman_residual | markov_transition, bounded_reward | rl_developer_memory.theory.registry.validate_assumption_bindings | bellman_residual_abs_mean | Unbounded Bellman residuals indicate critic drift or target leakage. |
| td_target | temporal_difference | rl_developer_memory.agents.base.ActorCriticAgent.compute_td_target | markov_transition, bounded_reward | rl_developer_memory.theory.registry.validate_assumption_bindings | td_target_mean | TD targets drift when bootstrapping or reward scaling are inconsistent. |
| actor_objective | policy_loss | rl_developer_memory.agents.base.ActorCriticAgent.compute_actor_objective | differentiable_policy, stationary_rollout | rl_developer_memory.theory.registry.validate_assumption_bindings | actor_objective_mean | Large actor objectives correlate with unstable policy improvement. |
| critic_objective | critic_loss | rl_developer_memory.agents.base.ActorCriticAgent.compute_critic_objective | bounded_reward | rl_developer_memory.theory.registry.validate_assumption_bindings | critic_objective_mean | Critic objective spikes indicate unstable value learning. |
| entropy_temperature | entropy_regularization | rl_developer_memory.agents.base.ActorCriticAgent.compute_entropy_temperature_loss | differentiable_policy | rl_developer_memory.theory.registry.validate_assumption_bindings | entropy_temperature | Entropy collapse can cause premature exploitation and narrow policy support. |
| advantage_estimator | gae_like | rl_developer_memory.trainers.pipeline.TrainerPipeline.compute_advantage_estimate | stationary_rollout | rl_developer_memory.theory.registry.validate_assumption_bindings | advantage_abs_mean | Noisy advantages amplify actor update variance. |
| lyapunov_hook | lyapunov_like | rl_developer_memory.trainers.pipeline.TrainerPipeline.run_stability_audit | lyapunov_candidate_documented | rl_developer_memory.theory.registry.validate_assumption_bindings | lyapunov_margin | Missing or negative Lyapunov margins indicate unsafe control updates. |
| hjb_hook | hjb_residual | rl_developer_memory.trainers.pipeline.TrainerPipeline.run_hjb_audit | control_objective_well_posed, terminal_boundary_condition_documented | rl_developer_memory.theory.registry.validate_assumption_bindings | hjb_residual_abs_mean | Large HJB residual proxies indicate control-optimality drift or inconsistent value targets. |
| constraint_hook | constraint_barrier | rl_developer_memory.trainers.pipeline.TrainerPipeline.run_constraint_audit | control_objective_well_posed, stationary_rollout | rl_developer_memory.theory.registry.validate_assumption_bindings | constraint_margin_mean | Constraint margins near zero indicate safety or feasibility erosion. |

## Loss decomposition

| component_id | equation_family | code_anchor | metric_keys | description |
| --- | --- | --- | --- | --- |
| td_target | temporal_difference | rl_developer_memory.agents.base.ActorCriticAgent.compute_td_target | td_target_mean | Bootstrapped target used by value-based and actor-critic updates. |
| bellman_residual | bellman | rl_developer_memory.agents.base.ActorCriticAgent.compute_bellman_residual | bellman_residual_abs_mean | Residual between current value prediction and TD target. |
| critic_objective | critic_loss | rl_developer_memory.agents.base.ActorCriticAgent.compute_critic_objective | critic_objective_mean | Squared residual critic loss. |
| actor_objective | policy_loss | rl_developer_memory.agents.base.ActorCriticAgent.compute_actor_objective | actor_objective_mean | Policy improvement objective driven by an advantage-like signal. |
| entropy_temperature | entropy_regularization | rl_developer_memory.agents.base.ActorCriticAgent.compute_entropy_temperature_loss | entropy_temperature_mean | Exploration-preserving entropy/temperature regularizer. |
| hjb_hook | hjb_residual | rl_developer_memory.trainers.pipeline.TrainerPipeline.run_hjb_audit | hjb_residual_abs_mean | HJB-style residual proxy for control-oriented actor-critic audits. |
| constraint_hook | constraint_barrier | rl_developer_memory.trainers.pipeline.TrainerPipeline.run_constraint_audit | constraint_margin_mean | Safety and feasibility margin audit for constrained control. |

## Update equations and code anchors

| update_id | equation_summary | code_anchor | stabilization_hooks |
| --- | --- | --- | --- |
| td_backup | y_t = r_t + γ V_target(s_{t+1}) | rl_developer_memory.agents.base.ActorCriticAgent.compute_td_target | reward_scaling |
| critic_update | L_critic = (y_t - V(s_t))^2 | rl_developer_memory.agents.base.ActorCriticAgent.compute_critic_objective | gradient_clipping, nan_guard |
| actor_update | L_actor = -π(a_t\|s_t) · A_t | rl_developer_memory.agents.base.ActorCriticAgent.compute_actor_objective | advantage_scaling, gradient_clipping |
| entropy_update | L_α = α (H_target - H(π)) | rl_developer_memory.agents.base.ActorCriticAgent.compute_entropy_temperature_loss | entropy_tuning |
| target_network_update | θ_target ← (1-τ) θ_target + τ θ_online | rl_developer_memory.agents.base.ActorCriticAgent.update_target_network | target_network |

## Control-oriented audit hooks

| hook_id | theorem_family | code_anchor | validator_anchor | when_to_enable |
| --- | --- | --- | --- | --- |
| lyapunov_hook | stability_audit | rl_developer_memory.trainers.pipeline.TrainerPipeline.run_stability_audit | rl_developer_memory.theory.validators.validate_experiment_assumptions | Safe RL / stability claims |
| constraint_hook | constraint_satisfaction | rl_developer_memory.trainers.pipeline.TrainerPipeline.run_constraint_audit | rl_developer_memory.theory.validators.validate_result_artifacts | Bounded-action or constrained control setups |
| hjb_hook | hjb_optimality | rl_developer_memory.trainers.pipeline.TrainerPipeline.run_hjb_audit | rl_developer_memory.theory.validators.validate_experiment_assumptions | HJB / control-optimality style value updates |

## Generic 10-step training blueprint

| step_id | order | title | code_anchor |
| --- | --- | --- | --- |
| problem_definition | 1 | env/problem tanımı | rl_developer_memory.trainers.pipeline.TrainerPipeline.define_problem_context |
| interface_contract | 2 | observation-action interface | rl_developer_memory.trainers.pipeline.TrainerPipeline.prepare_interfaces |
| network_setup | 3 | network ve parameter config | rl_developer_memory.trainers.pipeline.TrainerPipeline.build_model_components |
| objective_definition | 4 | objective/loss tanımı | rl_developer_memory.trainers.pipeline.TrainerPipeline.define_loss_objectives |
| theory_binding | 5 | update equations ve theorem binding | rl_developer_memory.trainers.pipeline.TrainerPipeline.bind_theory |
| training_loop | 6 | training loop | rl_developer_memory.trainers.pipeline.TrainerPipeline.train |
| stabilization | 7 | stabilization layer | rl_developer_memory.trainers.pipeline.TrainerPipeline.apply_stabilization |
| evaluation | 8 | evaluation metrics | rl_developer_memory.evaluation.base.Evaluator.evaluate |
| failure_analysis | 9 | failure modes | rl_developer_memory.trainers.pipeline.TrainerPipeline.describe_failure_modes |
| reporting | 10 | ablation/reporting template | rl_developer_memory.experiments.runner.ExperimentRunner.run |

## Failure modes and ablations

| failure_id | detection_anchor | trigger_metrics | mitigation_hooks |
| --- | --- | --- | --- |
| critic_drift | rl_developer_memory.trainers.pipeline.TrainerPipeline.describe_failure_modes | bellman_residual_abs_mean, critic_objective_mean | gradient_clipping, target_network, reward_scaling |
| variance_explosion | rl_developer_memory.trainers.pipeline.TrainerPipeline.describe_failure_modes | advantage_abs_mean, return_std | advantage_scaling, seed_audit, early_stop |
| constraint_erosion | rl_developer_memory.trainers.pipeline.TrainerPipeline.describe_failure_modes | constraint_margin_mean, constraint_violation_rate | constraint_hook, rollback, action_clamp |

| ablation_id | config_key | code_anchor | hypothesis |
| --- | --- | --- | --- |
| seed_sweep | training.seed | rl_developer_memory.trainers.pipeline.TrainerPipeline.suggest_ablation_hooks | Performance should remain directionally stable across seed changes. |
| reward_scale_sweep | training.reward_scale | rl_developer_memory.trainers.pipeline.TrainerPipeline.suggest_ablation_hooks | Reward scaling should not flip the learning signal. |
| gradient_clip_sweep | training.gradient_clip | rl_developer_memory.trainers.pipeline.TrainerPipeline.suggest_ablation_hooks | Clipping trades off learning speed and stability predictably. |
| entropy_temperature_sweep | training.entropy_temperature | rl_developer_memory.trainers.pipeline.TrainerPipeline.suggest_ablation_hooks | Entropy tuning changes exploration breadth without invalidating assumptions. |

## Reporting template and artifact validation

| section | field_name | source_anchor | rationale |
| --- | --- | --- | --- |
| problem_profile | assumptions | rl_developer_memory.experiments.runner.ExperimentRunner.run | Makes theorem assumptions explicit for review. |
| problem_profile | documented_hidden_assumptions | rl_developer_memory.experiments.runner.ExperimentRunner.run | Exposes previously implicit assumptions to validator surfaces. |
| run_manifest | training_blueprint_id | rl_developer_memory.experiments.runner.ExperimentRunner.run | Identifies the reusable RL blueprint contract. |
| run_manifest | audit_hooks | rl_developer_memory.experiments.runner.ExperimentRunner.run | Shows which theory/control audits were active. |
| metrics_payload | bellman_residual_abs_mean | rl_developer_memory.experiments.runner.ExperimentRunner.run | Tracks Bellman drift risk. |
| metrics_payload | hjb_residual_abs_mean | rl_developer_memory.experiments.runner.ExperimentRunner.run | Tracks HJB-style residual proxy risk. |
| validation_payload | artifact_validated | rl_developer_memory.experiments.runner.ExperimentRunner.run | Connects artifact checks to rollout review readiness. |
| validation_payload | variance_audited | rl_developer_memory.experiments.runner.ExperimentRunner.run | Connects seed/variance evidence to validation posture. |
| theory_sync | audit_findings | rl_developer_memory.experiments.runner.ExperimentRunner.run | Carries assumption, theorem, artifact, and blueprint findings. |

| artifact_id | producer_anchor | validator_anchor | required |
| --- | --- | --- | --- |
| checkpoint_state | rl_developer_memory.experiments.checkpoints.CheckpointManager.save | rl_developer_memory.theory.validators.validate_result_artifacts | true |
| checkpoint_metadata | rl_developer_memory.experiments.checkpoints.CheckpointManager.save | rl_developer_memory.theory.validators.validate_result_artifacts | true |
| theory_mapping_doc | docs/theory_to_code.md | rl_developer_memory.theory.sync.validate_theorem_code_sync | true |
| training_report | rl_developer_memory.experiments.runner.ExperimentRunner.run | rl_developer_memory.theory.validators.validate_result_artifacts | true |
| evaluation_report | rl_developer_memory.evaluation.base.Evaluator.evaluate | rl_developer_memory.theory.validators.validate_result_artifacts | true |


## Related contributor guidance

When theorem/objective mappings change, also follow `docs/RL_CODING_STANDARDS.md` and `docs/RL_QUALITY_GATE.md`.
