from __future__ import annotations

from typing import Iterable


DOMAIN_MODES = {"generic", "hybrid", "rl_control"}

MEMORY_KINDS = {
    "failure_pattern",
    "experiment_pattern",
    "theory_pattern",
    "design_pattern",
    "sim2real_pattern",
}

PROBLEM_FAMILIES = {
    "generic",
    "hjb",
    "bellman_dp",
    "mpc",
    "lqr_ilqr",
    "actor_critic",
    "policy_gradient",
    "offline_rl",
    "safe_rl",
    "robust_rl",
    "meta_rl",
    "sim2real",
    "actuator_control",
    "observer_controller",
    "uav_vtol_control",
}

DYNAMICS_CLASSES = {
    "generic",
    "lti",
    "nonlinear_ct",
    "nonlinear_dt",
    "stochastic",
    "pomdp",
    "hybrid",
    "delay_system",
    "switched_system",
}

ALGORITHM_FAMILIES = {
    "",
    "generic",
    "actor_critic",
    "policy_gradient",
    "ppo",
    "sac",
    "td3",
    "ddpg",
    "a2c",
    "a3c",
    "trpo",
    "cql",
    "iql",
    "mpc",
    "value_iteration",
    "policy_iteration",
}

THEOREM_CLAIM_TYPES = {
    "",
    "none",
    "stability",
    "asymptotic_stability",
    "exponential_stability",
    "iss",
    "iiss",
    "uub",
    "practical_stability",
    "recursive_feasibility",
    "constraint_satisfaction",
    "performance_bound",
    "bellman_consistency",
    "hjb_optimality",
}

VALIDATION_TIERS = {
    "observed",
    "candidate",
    "validated",
    "theory_reviewed",
    "production_validated",
}

RUNTIME_STAGES = {
    "",
    "generic",
    "design",
    "train",
    "eval",
    "deployment",
    "sil",
    "hil",
    "production",
}

SIM2REAL_STAGES = {
    "",
    "generic",
    "sim_only",
    "sil",
    "hil",
    "bench",
    "hardware",
    "flight_test",
    "production",
}

FAILURE_FAMILIES = {
    "nan_or_inf_instability",
    "reward_misspecification",
    "action_scaling_mismatch",
    "observation_normalization_mismatch",
    "target_network_misconfiguration",
    "critic_overestimation",
    "replay_buffer_corruption",
    "constraint_violation_hidden",
    "seed_fragility",
    "sim2real_latency_mismatch",
    "actuator_saturation_unmodeled",
    "estimator_controller_rate_mismatch",
}

_ALIASES = {
    "domain_mode": {
        "hybrid_mode": "hybrid",
        "rl": "rl_control",
        "rl_control_mode": "rl_control",
        "rl-control": "rl_control",
        "rlcontrol": "rl_control",
    },
    "memory_kind": {
        "failure": "failure_pattern",
        "experiment": "experiment_pattern",
        "theory": "theory_pattern",
        "design": "design_pattern",
        "sim2real": "sim2real_pattern",
    },
    "problem_family": {
        "bellman": "bellman_dp",
        "dynamic_programming": "bellman_dp",
        "dynamicprogramming": "bellman_dp",
        "dp": "bellman_dp",
        "hjb_control": "hjb",
        "optimal_control": "hjb",
        "safe": "safe_rl",
        "robust": "robust_rl",
        "uav": "uav_vtol_control",
        "vtol": "uav_vtol_control",
        "actuator": "actuator_control",
        "observer": "observer_controller",
    },
    "dynamics_class": {
        "continuous_time": "nonlinear_ct",
        "discrete_time": "nonlinear_dt",
        "nonlinear_continuous": "nonlinear_ct",
        "nonlinear_discrete": "nonlinear_dt",
    },
    "algorithm_family": {
        "soft_actor_critic": "sac",
        "twin_delayed_ddpg": "td3",
        "deep_deterministic_policy_gradient": "ddpg",
    },
    "theorem_claim_type": {
        "lyapunov_stability": "stability",
        "recursive_feasible": "recursive_feasibility",
        "hjb": "hjb_optimality",
        "bellman": "bellman_consistency",
    },
    "runtime_stage": {
        "training": "train",
        "evaluation": "eval",
        "deploy": "deployment",
        "hardware_in_loop": "hil",
        "software_in_loop": "sil",
    },
    "sim2real_stage": {
        "simulation": "sim_only",
        "software_in_loop": "sil",
        "hardware_in_loop": "hil",
        "hardware_test": "hardware",
        "flight": "flight_test",
    },
    "validation_tier": {
        "reviewed": "theory_reviewed",
        "prod": "production_validated",
    },
}


def _normalize(value: str, valid: Iterable[str], aliases: dict[str, str] | None = None, *, default: str = "") -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not raw:
        return default
    if aliases and raw in aliases:
        raw = aliases[raw]
    valid_values = set(valid)
    return raw if raw in valid_values else default


def normalize_domain_mode(value: str, *, default: str = "generic") -> str:
    return _normalize(value, DOMAIN_MODES, _ALIASES["domain_mode"], default=default)


def normalize_memory_kind(value: str, *, default: str = "failure_pattern") -> str:
    return _normalize(value, MEMORY_KINDS, _ALIASES["memory_kind"], default=default)


def normalize_problem_family(value: str, *, default: str = "generic") -> str:
    return _normalize(value, PROBLEM_FAMILIES, _ALIASES["problem_family"], default=default)


def normalize_dynamics_class(value: str, *, default: str = "generic") -> str:
    return _normalize(value, DYNAMICS_CLASSES, _ALIASES["dynamics_class"], default=default)


def normalize_algorithm_family(value: str, *, default: str = "") -> str:
    return _normalize(value, ALGORITHM_FAMILIES, _ALIASES["algorithm_family"], default=default)


def normalize_theorem_claim_type(value: str, *, default: str = "") -> str:
    return _normalize(value, THEOREM_CLAIM_TYPES, _ALIASES["theorem_claim_type"], default=default)


def normalize_validation_tier(value: str, *, default: str = "observed") -> str:
    return _normalize(value, VALIDATION_TIERS, _ALIASES["validation_tier"], default=default)


def normalize_runtime_stage(value: str, *, default: str = "") -> str:
    return _normalize(value, RUNTIME_STAGES, _ALIASES["runtime_stage"], default=default)


def normalize_sim2real_stage(value: str, *, default: str = "") -> str:
    return _normalize(value, SIM2REAL_STAGES, _ALIASES["sim2real_stage"], default=default)


def is_valid_memory_kind(value: str) -> bool:
    return normalize_memory_kind(value) in MEMORY_KINDS


def is_valid_problem_family(value: str) -> bool:
    return normalize_problem_family(value) in PROBLEM_FAMILIES


def infer_problem_family(text: str, *, fallback: str = "generic") -> str:
    normalized = " ".join(str(text or "").lower().replace("_", " ").replace("-", " ").split())
    if not normalized:
        return fallback

    keyword_groups = [
        ("safe_rl", ("safe rl", "control barrier", "barrier certificate", "shielded rl")),
        ("robust_rl", ("robust rl", "domain randomization", "worst-case")),
        ("meta_rl", ("meta rl", "meta-learning", "few-shot policy adaptation")),
        ("uav_vtol_control", ("uav", "quadrotor", "multirotor", "vtol")),
        ("actuator_control", ("actuator", "saturation", "dead-zone", "deadzone", "rate limit")),
        ("observer_controller", ("observer", "kalman filter", "output feedback", "state estimator")),
        ("sim2real", ("sim2real", "sim-to-real", "hil", "hardware in the loop", "software in the loop")),
        ("hjb", ("hamilton jacobi bellman", "hamilton-jacobi-bellman", "hjb")),
        ("bellman_dp", ("bellman", "dynamic programming", "value iteration", "policy iteration")),
        ("mpc", ("model predictive control", "mpc", "receding horizon")),
        ("lqr_ilqr", ("lqr", "ilqr", "dlqr")),
        ("offline_rl", ("offline rl", "batch rl", "conservative q learning", "cql", "implicit q learning", "iql")),
        ("policy_gradient", ("policy gradient", "reinforce", "trpo", "ppo")),
        ("actor_critic", ("actor critic", "actor-critic", "sac", "td3", "ddpg", "a2c", "a3c")),
    ]
    for family, needles in keyword_groups:
        if any(needle in normalized for needle in needles):
            return family
    return normalize_problem_family(fallback, default="generic")
