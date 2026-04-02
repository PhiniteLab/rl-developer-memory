from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import RLAuditFinding
from .taxonomy import (
    normalize_algorithm_family,
    normalize_dynamics_class,
    normalize_problem_family,
    normalize_runtime_stage,
    normalize_sim2real_stage,
    normalize_theorem_claim_type,
    normalize_validation_tier,
)


def _finding(audit_type: str, severity: str, summary: str, **payload: Any) -> RLAuditFinding:
    return RLAuditFinding(audit_type=audit_type, severity=severity, summary=summary, payload=payload)


_STABILITY_CLAIMS = {"stability", "asymptotic_stability", "exponential_stability", "iss", "iiss", "uub", "practical_stability"}
_CONTROL_PROBLEM_FAMILIES = {"mpc", "lqr_ilqr", "actuator_control", "observer_controller", "uav_vtol_control", "safe_rl", "robust_rl"}
_RL_ALGORITHM_FAMILIES = {"actor_critic", "policy_gradient", "ppo", "sac", "td3", "ddpg", "a2c", "a3c", "trpo", "cql", "iql"}


def validate_problem_profile(problem_profile: Mapping[str, Any] | None) -> list[RLAuditFinding]:
    findings: list[RLAuditFinding] = []
    if not problem_profile:
        return [_finding("experiment", "warning", "Problem profile is missing.")]

    problem_family = normalize_problem_family(str(problem_profile.get("problem_family", "")), default="")
    if problem_profile.get("problem_family") and not problem_family:
        findings.append(_finding("experiment", "error", "Problem family is not recognized.", field="problem_family"))

    dynamics_class = normalize_dynamics_class(str(problem_profile.get("dynamics_class", "")), default="")
    if problem_profile.get("dynamics_class") and not dynamics_class:
        findings.append(_finding("experiment", "error", "Dynamics class is not recognized.", field="dynamics_class"))

    theorem_claim_type = normalize_theorem_claim_type(str(problem_profile.get("theorem_claim_type", "")), default="")
    if problem_profile.get("theorem_claim_type") and not theorem_claim_type:
        findings.append(_finding("theory", "error", "Theorem claim type is not recognized.", field="theorem_claim_type"))

    for field_name in ("state_dimension", "action_dimension"):
        value = problem_profile.get(field_name)
        if value is None:
            continue
        try:
            numeric_value = int(value)
        except (TypeError, ValueError):
            findings.append(_finding("experiment", "error", f"{field_name} must be an integer.", field=field_name))
        else:
            if numeric_value <= 0:
                findings.append(_finding("experiment", "error", f"{field_name} must be positive.", field=field_name))

    sampling_time = problem_profile.get("sampling_time")
    if sampling_time is not None:
        try:
            numeric_sampling = float(sampling_time)
        except (TypeError, ValueError):
            findings.append(_finding("experiment", "error", "sampling_time must be numeric.", field="sampling_time"))
        else:
            if numeric_sampling <= 0:
                findings.append(_finding("experiment", "error", "sampling_time must be positive.", field="sampling_time"))

    assumptions = problem_profile.get("assumptions")
    if theorem_claim_type and not assumptions:
        findings.append(_finding("theory", "warning", "Theory claim is present but assumptions are not documented."))

    if theorem_claim_type in _STABILITY_CLAIMS and not str(problem_profile.get("lyapunov_candidate", "")).strip():
        findings.append(_finding("theory", "warning", "Stability-style claim is missing a Lyapunov candidate reference."))

    return findings


def validate_run_manifest(run_manifest: Mapping[str, Any] | None, *, required_seed_count: int = 3) -> list[RLAuditFinding]:
    findings: list[RLAuditFinding] = []
    if not run_manifest:
        return [_finding("experiment", "warning", "Run manifest is missing.")]

    algorithm_family = normalize_algorithm_family(str(run_manifest.get("algorithm_family", "")), default="")
    if run_manifest.get("algorithm_family") and not algorithm_family:
        findings.append(_finding("runtime", "error", "Algorithm family is not recognized.", field="algorithm_family"))

    runtime_stage = normalize_runtime_stage(str(run_manifest.get("runtime_stage", "")), default="")
    if run_manifest.get("runtime_stage") and not runtime_stage:
        findings.append(_finding("runtime", "error", "Runtime stage is not recognized.", field="runtime_stage"))

    seed_count = run_manifest.get("seed_count")
    if seed_count is None:
        findings.append(_finding("experiment", "warning", "seed_count is missing from the run manifest."))
    else:
        try:
            seed_count_value = int(seed_count)
        except (TypeError, ValueError):
            findings.append(_finding("experiment", "error", "seed_count must be an integer.", field="seed_count"))
        else:
            if seed_count_value < required_seed_count:
                findings.append(
                    _finding(
                        "experiment",
                        "warning",
                        f"seed_count is below the recommended threshold of {required_seed_count}.",
                        field="seed_count",
                        required_seed_count=required_seed_count,
                    )
                )

    if not str(run_manifest.get("train_env_id", "")).strip():
        findings.append(_finding("experiment", "warning", "train_env_id is missing from the run manifest."))
    if not str(run_manifest.get("eval_env_id", "")).strip():
        findings.append(_finding("experiment", "warning", "eval_env_id is missing from the run manifest."))

    baseline_names = run_manifest.get("baseline_names")
    if not baseline_names:
        findings.append(_finding("experiment", "warning", "baseline_names are missing from the run manifest."))
    elif not isinstance(baseline_names, Sequence) or isinstance(baseline_names, (str, bytes)):
        findings.append(_finding("experiment", "error", "baseline_names must be a sequence of baseline identifiers."))

    action_bounds = run_manifest.get("action_bounds")
    if action_bounds is not None:
        if not isinstance(action_bounds, Sequence) or isinstance(action_bounds, (str, bytes)) or len(action_bounds) != 2:
            findings.append(_finding("runtime", "error", "action_bounds must contain exactly two numeric limits."))
        else:
            try:
                lower = float(action_bounds[0])
                upper = float(action_bounds[1])
            except (TypeError, ValueError):
                findings.append(_finding("runtime", "error", "action_bounds must be numeric."))
            else:
                if lower >= upper:
                    findings.append(_finding("runtime", "error", "action_bounds lower limit must be smaller than the upper limit."))

    return findings


def validate_metrics_payload(metrics_payload: Mapping[str, Any] | None) -> list[RLAuditFinding]:
    findings: list[RLAuditFinding] = []
    if not metrics_payload:
        return [_finding("experiment", "warning", "Metrics payload is missing.")]

    scalar_fields = ("return_std", "tracking_rmse", "control_effort")
    for field_name in scalar_fields:
        value = metrics_payload.get(field_name)
        if value is None:
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            findings.append(_finding("experiment", "error", f"{field_name} must be numeric.", field=field_name))
        else:
            if numeric_value < 0:
                findings.append(_finding("experiment", "error", f"{field_name} must be non-negative.", field=field_name))

    for bounded_field in ("constraint_violation_rate", "crash_rate"):
        value = metrics_payload.get(bounded_field)
        if value is None:
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            findings.append(_finding("experiment", "error", f"{bounded_field} must be numeric.", field=bounded_field))
        else:
            if not 0.0 <= numeric_value <= 1.0:
                findings.append(_finding("experiment", "error", f"{bounded_field} must be within [0, 1].", field=bounded_field))

    interval = metrics_payload.get("confidence_interval")
    if interval is not None:
        if not isinstance(interval, Sequence) or isinstance(interval, (str, bytes)) or len(interval) != 2:
            findings.append(_finding("experiment", "error", "confidence_interval must contain exactly two numeric bounds."))
        else:
            try:
                lower = float(interval[0])
                upper = float(interval[1])
            except (TypeError, ValueError):
                findings.append(_finding("experiment", "error", "confidence_interval must be numeric."))
            else:
                if lower > upper:
                    findings.append(_finding("experiment", "error", "confidence_interval lower bound must not exceed the upper bound."))

    if not any(key in metrics_payload for key in ("return_mean", "tracking_rmse", "control_effort", "constraint_violation_rate", "crash_rate")):
        findings.append(_finding("experiment", "warning", "Metrics payload does not include any primary evaluation metrics."))

    return findings


def validate_validation_payload(validation_payload: Mapping[str, Any] | None, *, required_seed_count: int = 3) -> list[RLAuditFinding]:
    findings: list[RLAuditFinding] = []
    if not validation_payload:
        return [_finding("review", "warning", "Validation payload is missing.")]

    tier = validation_payload.get("validation_tier")
    if tier and not normalize_validation_tier(str(tier), default=""):
        findings.append(_finding("review", "error", "validation_tier is not recognized.", field="validation_tier"))

    if validation_payload.get("theory_reviewed") and not str(validation_payload.get("reviewed_by", "")).strip():
        findings.append(_finding("theory", "warning", "theory_reviewed is true but reviewed_by is missing."))

    seed_count = validation_payload.get("seed_count")
    if seed_count is not None:
        try:
            numeric_seed_count = int(seed_count)
        except (TypeError, ValueError):
            findings.append(_finding("review", "error", "seed_count in validation payload must be an integer."))
        else:
            if numeric_seed_count < required_seed_count and (validation_payload.get("hardware_validated") or validation_payload.get("production_verified")):
                findings.append(
                    _finding(
                        "review",
                        "warning",
                        f"Validation evidence uses fewer than {required_seed_count} seeds for a high-confidence tier.",
                        field="seed_count",
                        required_seed_count=required_seed_count,
                    )
                )

    if validation_payload.get("production_verified") and not validation_payload.get("hardware_validated"):
        findings.append(_finding("review", "warning", "production_verified is true while hardware_validated is false."))

    if validation_payload.get("seed_count") and not validation_payload.get("baseline_comparison"):
        findings.append(_finding("review", "warning", "Validation payload records seed_count but does not confirm baseline comparison."))

    return findings


def validate_artifact_refs(artifact_refs: Sequence[Mapping[str, Any]] | None, *, max_refs: int = 12) -> list[RLAuditFinding]:
    findings: list[RLAuditFinding] = []
    if artifact_refs is None:
        return findings

    if len(artifact_refs) > max_refs:
        findings.append(_finding("runtime", "error", f"artifact_refs exceeds the configured limit of {max_refs}.", max_refs=max_refs))

    for index, artifact in enumerate(artifact_refs):
        if not isinstance(artifact, Mapping):
            findings.append(_finding("runtime", "error", "artifact_refs entries must be mapping objects.", index=index))
            continue
        if not str(artifact.get("kind", "")).strip():
            findings.append(_finding("runtime", "warning", "artifact reference is missing kind.", index=index))
        if not str(artifact.get("uri", "")).strip():
            findings.append(_finding("runtime", "warning", "artifact reference is missing uri.", index=index))
        if artifact.get("bytes") is not None:
            try:
                size = int(artifact["bytes"])
            except (TypeError, ValueError):
                findings.append(_finding("runtime", "error", "artifact bytes must be an integer.", index=index))
            else:
                if size < 0:
                    findings.append(_finding("runtime", "error", "artifact bytes must be non-negative.", index=index))

    return findings


def _safe_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, *, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _assumption_blob(problem_profile: Mapping[str, Any] | None) -> str:
    if not isinstance(problem_profile, Mapping):
        return ""
    assumptions = problem_profile.get("assumptions")
    if isinstance(assumptions, Sequence) and not isinstance(assumptions, (str, bytes)):
        parts = [str(item).strip().lower() for item in assumptions if str(item).strip()]
    else:
        parts = [str(assumptions).strip().lower()] if assumptions else []
    return " ".join(parts)


def validate_experiment_consistency(
    *,
    problem_family: str,
    algorithm_family: str,
    runtime_stage: str,
    run_manifest: Mapping[str, Any] | None,
    metrics_payload: Mapping[str, Any] | None,
    validation_payload: Mapping[str, Any] | None,
    sim2real_profile: Mapping[str, Any] | None = None,
    required_seed_count: int = 3,
) -> list[RLAuditFinding]:
    findings: list[RLAuditFinding] = []
    run_manifest = run_manifest or {}
    metrics_payload = metrics_payload or {}
    validation_payload = validation_payload or {}
    sim2real_profile = sim2real_profile or {}

    normalized_problem_family = normalize_problem_family(str(problem_family or run_manifest.get("problem_family", "")), default="generic")
    normalized_algorithm_family = normalize_algorithm_family(str(algorithm_family or run_manifest.get("algorithm_family", "")), default="")
    normalized_runtime_stage = normalize_runtime_stage(str(runtime_stage or run_manifest.get("runtime_stage", "")), default="")
    sim2real_stage = normalize_sim2real_stage(str(sim2real_profile.get("stage", "")), default="")

    run_seed_count = _safe_int(run_manifest.get("seed_count"), default=0)
    validation_seed_count = _safe_int(validation_payload.get("seed_count"), default=0)
    if run_seed_count and validation_seed_count and run_seed_count != validation_seed_count:
        findings.append(
            _finding(
                "experiment",
                "warning",
                "run_manifest seed_count does not match validation seed_count.",
                run_seed_count=run_seed_count,
                validation_seed_count=validation_seed_count,
            )
        )

    baseline_names = run_manifest.get("baseline_names")
    baseline_comparison = bool(validation_payload.get("baseline_comparison") or validation_payload.get("baseline_results"))
    if baseline_comparison and not baseline_names:
        findings.append(_finding("experiment", "error", "Validation claims baseline_comparison but run_manifest does not list baseline_names."))

    requested_tier = normalize_validation_tier(str(validation_payload.get("validation_tier", "")), default="")
    if requested_tier in {"validated", "production_validated"}:
        crash_rate = _safe_float(metrics_payload.get("crash_rate"))
        if crash_rate is not None and crash_rate > 0.0:
            findings.append(_finding("experiment", "warning", "High-confidence validation tier is requested while crash_rate is non-zero.", crash_rate=crash_rate))
        constraint_violation_rate = _safe_float(metrics_payload.get("constraint_violation_rate"))
        if constraint_violation_rate is not None and constraint_violation_rate > 0.05:
            findings.append(
                _finding(
                    "experiment",
                    "warning",
                    "High-confidence validation tier is requested while constraint_violation_rate exceeds 0.05.",
                    constraint_violation_rate=constraint_violation_rate,
                )
            )

    if run_seed_count >= required_seed_count and metrics_payload.get("return_mean") is not None:
        if metrics_payload.get("return_std") is None and metrics_payload.get("confidence_interval") is None:
            findings.append(_finding("experiment", "warning", "Seeded evaluation reports return_mean without return_std or confidence_interval."))

    if normalized_problem_family in _CONTROL_PROBLEM_FAMILIES:
        if metrics_payload and metrics_payload.get("tracking_rmse") is None:
            findings.append(_finding("experiment", "warning", "Control-oriented experiment is missing tracking_rmse."))
        if metrics_payload and metrics_payload.get("control_effort") is None:
            findings.append(_finding("experiment", "warning", "Control-oriented experiment is missing control_effort."))

    if normalized_algorithm_family in _RL_ALGORITHM_FAMILIES and normalized_runtime_stage == "train":
        normalization = run_manifest.get("normalization")
        if not isinstance(normalization, Mapping) or not normalization:
            findings.append(_finding("runtime", "warning", "Training manifest does not document normalization settings for the RL algorithm."))

    if normalized_runtime_stage in {"sil", "hil", "deployment", "production"} and not sim2real_stage:
        findings.append(_finding("sim2real", "warning", f"runtime_stage '{normalized_runtime_stage}' is recorded without sim2real stage metadata."))

    if validation_payload.get("production_verified") and normalized_runtime_stage not in {"hil", "deployment", "production"}:
        findings.append(_finding("sim2real", "warning", "production_verified is set while runtime_stage is not deployment-like."))

    return findings


def validate_theory_consistency(
    *,
    problem_family: str,
    theorem_claim_type: str,
    problem_profile: Mapping[str, Any] | None,
    validation_payload: Mapping[str, Any] | None,
    algorithm_family: str = "",
    run_manifest: Mapping[str, Any] | None = None,
) -> list[RLAuditFinding]:
    findings: list[RLAuditFinding] = []
    problem_profile = problem_profile or {}
    validation_payload = validation_payload or {}
    run_manifest = run_manifest or {}

    normalized_problem_family = normalize_problem_family(str(problem_family or problem_profile.get("problem_family", "")), default="generic")
    normalized_theorem = normalize_theorem_claim_type(str(theorem_claim_type or problem_profile.get("theorem_claim_type", "")), default="none") or "none"
    normalized_algorithm_family = normalize_algorithm_family(str(algorithm_family or run_manifest.get("algorithm_family", "")), default="")
    dynamics_class = normalize_dynamics_class(str(problem_profile.get("dynamics_class", "")), default="")
    assumptions_blob = _assumption_blob(problem_profile)

    if normalized_theorem in {"", "none"}:
        if validation_payload.get("theory_reviewed"):
            findings.append(_finding("theory", "warning", "theory_reviewed is set but theorem_claim_type is missing."))
        return findings

    if normalized_theorem in _STABILITY_CLAIMS and not dynamics_class:
        findings.append(_finding("theory", "warning", "Stability-style claim is missing dynamics_class metadata."))

    if normalized_theorem == "hjb_optimality":
        if normalized_problem_family not in {"hjb", "bellman_dp", "mpc", "lqr_ilqr"}:
            findings.append(_finding("theory", "warning", f"HJB optimality claim is unusual for problem_family '{normalized_problem_family}'."))
        if not any(token in assumptions_blob for token in ("terminal", "boundary", "value function boundary", "terminal set")):
            findings.append(_finding("theory", "warning", "HJB optimality claim does not document terminal or boundary assumptions."))

    if normalized_theorem == "bellman_consistency":
        if not normalized_algorithm_family and normalized_problem_family not in {"bellman_dp", "actor_critic", "policy_gradient", "offline_rl", "safe_rl", "robust_rl", "meta_rl"}:
            findings.append(_finding("theory", "warning", "Bellman consistency claim is missing an RL/DP algorithm or matching problem family."))

    if normalized_theorem in {"recursive_feasibility", "constraint_satisfaction"} and normalized_problem_family != "mpc":
        findings.append(_finding("theory", "warning", f"{normalized_theorem} is usually associated with MPC, but problem_family is '{normalized_problem_family}'."))

    if normalized_theorem not in {"", "none"} and not validation_payload.get("theory_reviewed"):
        findings.append(_finding("theory", "warning", "Theory claim is stored without explicit theory_reviewed evidence."))

    return findings
