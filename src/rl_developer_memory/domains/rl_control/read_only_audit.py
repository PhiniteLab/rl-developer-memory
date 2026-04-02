from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, Callable

from ...models import QueryProfile
from .contracts import RLAuditFinding, coerce_json_value
from .taxonomy import (
    infer_problem_family,
    normalize_algorithm_family,
    normalize_dynamics_class,
    normalize_memory_kind,
    normalize_problem_family,
    normalize_runtime_stage,
    normalize_sim2real_stage,
    normalize_theorem_claim_type,
)
from .validators import (
    validate_experiment_consistency,
    validate_metrics_payload,
    validate_problem_profile,
    validate_run_manifest,
    validate_theory_consistency,
    validate_validation_payload,
)

_ALGORITHM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "sac": ("sac", "soft actor critic", "soft-actor-critic"),
    "td3": ("td3", "twin delayed ddpg"),
    "ddpg": ("ddpg", "deep deterministic policy gradient"),
    "ppo": ("ppo", "proximal policy optimization"),
    "trpo": ("trpo",),
    "a2c": ("a2c",),
    "a3c": ("a3c",),
    "cql": ("cql", "conservative q learning", "conservative q-learning"),
    "iql": ("iql", "implicit q learning", "implicit q-learning"),
    "mpc": ("mpc", "model predictive control"),
    "value_iteration": ("value iteration",),
    "policy_iteration": ("policy iteration",),
    "actor_critic": ("actor critic", "actor-critic", "critic update", "policy update"),
    "policy_gradient": ("policy gradient",),
}

_THEOREM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "hjb_optimality": ("hamilton jacobi bellman", "hamilton-jacobi-bellman", "hjb"),
    "bellman_consistency": ("bellman", "bellman residual", "bellman backup"),
    "iss": ("iss", "input to state stable", "input-to-state stable"),
    "iiss": ("iiss",),
    "uub": ("uub", "uniformly ultimately bounded", "ultimate bound"),
    "asymptotic_stability": ("asymptotic stability",),
    "exponential_stability": ("exponential stability",),
    "practical_stability": ("practical stability",),
    "recursive_feasibility": ("recursive feasibility", "recursively feasible"),
    "constraint_satisfaction": ("constraint satisfaction",),
    "performance_bound": ("performance bound",),
    "stability": ("lyapunov", "stability proof", "stability guarantee", "stable"),
}

_DYNAMICS_KEYWORDS: dict[str, tuple[str, ...]] = {
    "lti": ("lti", "linear time invariant", "linear time-invariant"),
    "nonlinear_ct": ("continuous time", "continuous-time", "nonlinear continuous", "ode"),
    "nonlinear_dt": ("discrete time", "discrete-time", "sampled", "sampled-data"),
    "stochastic": ("stochastic",),
    "pomdp": ("pomdp", "partial observation", "partially observed"),
    "hybrid": ("hybrid system", "hybrid dynamics"),
    "delay_system": ("delay", "delayed sensing", "time delay", "latency"),
    "switched_system": ("switched system", "switching"),
}

_RUNTIME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "train": ("train", "training", "optimizer", "backprop", "critic loss", "actor loss", "replay buffer", "seed"),
    "eval": ("eval", "evaluation", "benchmark", "rollout evaluation"),
    "deployment": ("deployment", "deployed", "runtime", "embedded", "real time", "real-time"),
    "sil": ("sil", "software in loop", "software-in-loop"),
    "hil": ("hil", "hardware in loop", "hardware-in-loop"),
    "production": ("production", "flight test", "hardware test", "hardware validation"),
    "design": ("architecture", "controller design", "design choice"),
}

_SIM2REAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "sim_only": ("simulation", "simulator", "sim-only", "sim only"),
    "sil": ("sil", "software in loop", "software-in-loop"),
    "hil": ("hil", "hardware in loop", "hardware-in-loop"),
    "hardware": ("hardware", "bench", "actuator bench", "embedded"),
    "flight_test": ("flight test", "flight-test", "real flight"),
    "production": ("production",),
}


def _text_blob(profile: QueryProfile) -> str:
    return " ".join(
        part
        for part in (
            profile.raw_text,
            profile.normalized_text,
            " ".join(profile.tokens),
            " ".join(profile.exception_types),
            " ".join(profile.strategy_hints),
        )
        if part
    ).lower()


def _normalize_match_text(text: str) -> str:
    return " ".join(str(text or "").lower().replace("_", " ").replace("-", " ").split())


def _phrase_in_text(text: str, phrase: str) -> bool:
    normalized_text = _normalize_match_text(text)
    normalized_phrase = _normalize_match_text(phrase)
    if not normalized_text or not normalized_phrase:
        return False
    pattern = r"(?<!\w)" + re.escape(normalized_phrase).replace(r"\ ", r"\s+") + r"(?!\w)"
    return re.search(pattern, normalized_text) is not None


def _contains_any(text: str, phrases: Sequence[str]) -> bool:
    return any(_phrase_in_text(text, phrase) for phrase in phrases)


def _infer_from_keywords(text: str, keyword_map: Mapping[str, Sequence[str]], *, default: str = "") -> str:
    for normalized, phrases in keyword_map.items():
        if _contains_any(text, phrases):
            return normalized
    return default


def _infer_query_algorithm_family(text: str) -> str:
    return normalize_algorithm_family(_infer_from_keywords(text, _ALGORITHM_KEYWORDS), default="")


def _infer_query_theorem_claim_type(text: str) -> str:
    return normalize_theorem_claim_type(_infer_from_keywords(text, _THEOREM_KEYWORDS), default="")


def _infer_query_dynamics_class(text: str) -> str:
    return normalize_dynamics_class(_infer_from_keywords(text, _DYNAMICS_KEYWORDS), default="")


def _infer_query_runtime_stage(text: str) -> str:
    return normalize_runtime_stage(_infer_from_keywords(text, _RUNTIME_KEYWORDS), default="")


def _infer_query_sim2real_stage(text: str) -> str:
    return normalize_sim2real_stage(_infer_from_keywords(text, _SIM2REAL_KEYWORDS), default="")


def _infer_query_memory_kind(
    *,
    text: str,
    problem_family: str,
    theorem_claim_type: str,
    runtime_stage: str,
    sim2real_stage: str,
    algorithm_family: str,
) -> str:
    if theorem_claim_type and theorem_claim_type != "none":
        return "theory_pattern"
    if sim2real_stage:
        return "sim2real_pattern"
    if runtime_stage in {"train", "eval", "sil", "hil", "production"}:
        return "experiment_pattern"
    if runtime_stage == "deployment":
        return "sim2real_pattern"
    if problem_family in {"sim2real", "actuator_control"}:
        return "sim2real_pattern"
    if _contains_any(text, ("architecture", "design", "observer", "controller structure", "policy head", "critic head")):
        return "design_pattern"
    if algorithm_family or problem_family not in {"", "generic"}:
        return "experiment_pattern"
    return "failure_pattern"


def infer_query_domain_profile(profile: QueryProfile) -> dict[str, Any]:
    text = _text_blob(profile)
    problem_family = normalize_problem_family(infer_problem_family(text, fallback="generic"), default="generic")
    theorem_claim_type = _infer_query_theorem_claim_type(text)
    algorithm_family = _infer_query_algorithm_family(text)
    dynamics_class = _infer_query_dynamics_class(text)
    runtime_stage = _infer_query_runtime_stage(text)
    sim2real_stage = _infer_query_sim2real_stage(text)
    memory_kind = normalize_memory_kind(
        _infer_query_memory_kind(
            text=text,
            problem_family=problem_family,
            theorem_claim_type=theorem_claim_type,
            runtime_stage=runtime_stage,
            sim2real_stage=sim2real_stage,
            algorithm_family=algorithm_family,
        ),
        default="failure_pattern",
    )
    is_rl_control_query = any(
        [
            problem_family not in {"", "generic"},
            bool(theorem_claim_type and theorem_claim_type != "none"),
            bool(algorithm_family),
            bool(runtime_stage),
            bool(sim2real_stage),
            bool(dynamics_class),
            _contains_any(text, ("quadrotor", "vtol", "uav", "lyapunov", "bellman", "hjb", "mpc", "actor critic", "control")),
        ]
    )
    if not is_rl_control_query:
        memory_kind = ""
        problem_family = "generic"
        theorem_claim_type = "none"
        algorithm_family = ""
        dynamics_class = ""
        runtime_stage = ""
        sim2real_stage = ""
    return {
        "enabled": is_rl_control_query,
        "memory_kind_hint": memory_kind,
        "problem_family_hint": problem_family,
        "theorem_claim_type_hint": theorem_claim_type or "none",
        "algorithm_family_hint": algorithm_family,
        "dynamics_class_hint": dynamics_class,
        "runtime_stage_hint": runtime_stage,
        "sim2real_stage_hint": sim2real_stage,
        "query_terms": [
            value
            for value in (
                memory_kind,
                problem_family if problem_family != "generic" else "",
                theorem_claim_type if theorem_claim_type != "none" else "",
                algorithm_family,
                dynamics_class,
                runtime_stage,
                sim2real_stage,
            )
            if value
        ],
    }


def extract_candidate_domain_profile(candidate: Mapping[str, Any]) -> dict[str, Any]:
    variant = candidate.get("best_variant") or {}
    if not isinstance(variant, Mapping):
        variant = {}
    pattern_problem_profile = coerce_json_value(candidate.get("problem_profile_json"), fallback={})
    validation_payload = coerce_json_value(candidate.get("validation_json"), fallback={})
    variant_profile = coerce_json_value(variant.get("variant_profile_json"), fallback={})
    sim2real_profile = coerce_json_value(variant.get("sim2real_profile_json"), fallback={})
    return {
        "memory_kind": normalize_memory_kind(str(candidate.get("memory_kind", "failure_pattern")), default="failure_pattern"),
        "problem_family": normalize_problem_family(str(candidate.get("problem_family", "generic")), default="generic"),
        "theorem_claim_type": normalize_theorem_claim_type(str(candidate.get("theorem_claim_type", "none")), default="none") or "none",
        "validation_tier": str(candidate.get("validation_tier", "observed") or "observed"),
        "algorithm_family": normalize_algorithm_family(str(variant.get("algorithm_family", candidate.get("algorithm_family", ""))), default=""),
        "runtime_stage": normalize_runtime_stage(str(variant.get("runtime_stage", candidate.get("runtime_stage", ""))), default=""),
        "dynamics_class": normalize_dynamics_class(str(pattern_problem_profile.get("dynamics_class", "")), default=""),
        "sim2real_stage": normalize_sim2real_stage(str(sim2real_profile.get("stage", "")), default=""),
        "problem_profile_json": pattern_problem_profile,
        "validation_json": validation_payload,
        "variant_profile_json": variant_profile,
        "sim2real_profile_json": sim2real_profile,
    }


def _group_of_problem_family(problem_family: str) -> str:
    if problem_family in {"hjb", "bellman_dp", "mpc", "lqr_ilqr"}:
        return "optimal_control"
    if problem_family in {"actor_critic", "policy_gradient", "offline_rl", "safe_rl", "robust_rl", "meta_rl"}:
        return "rl"
    if problem_family in {"sim2real", "actuator_control", "observer_controller", "uav_vtol_control"}:
        return "systems"
    return ""


def _group_of_theorem(theorem_claim_type: str) -> str:
    if theorem_claim_type in {"stability", "asymptotic_stability", "exponential_stability", "iss", "iiss", "uub", "practical_stability"}:
        return "stability"
    if theorem_claim_type in {"recursive_feasibility", "constraint_satisfaction"}:
        return "constraints"
    if theorem_claim_type in {"performance_bound", "bellman_consistency", "hjb_optimality"}:
        return "optimality"
    return ""


def _group_of_algorithm(algorithm_family: str) -> str:
    if algorithm_family in {"actor_critic", "sac", "td3", "ddpg", "a2c", "a3c"}:
        return "actor_critic"
    if algorithm_family in {"policy_gradient", "ppo", "trpo"}:
        return "policy_gradient"
    if algorithm_family in {"cql", "iql"}:
        return "offline_rl"
    if algorithm_family in {"mpc", "value_iteration", "policy_iteration"}:
        return "control_planning"
    return ""


def _category_match(
    *,
    label: str,
    query_value: str,
    candidate_value: str,
    reasons: list[str],
    findings: list[RLAuditFinding],
    blank_values: set[str] | None = None,
    groups: Callable[[str], str] | None = None,
    partial_pairs: set[tuple[str, str]] | None = None,
    missing_severity: str = "warning",
    mismatch_penalty: float = 0.30,
) -> tuple[float, float]:
    blanks = blank_values or {"", "generic", "none"}
    normalized_query = str(query_value or "")
    normalized_candidate = str(candidate_value or "")
    if normalized_query in blanks:
        return 0.0, 0.0
    if normalized_candidate in blanks:
        findings.append(
            RLAuditFinding(
                audit_type="compatibility",
                severity=missing_severity,
                summary=f"Candidate does not declare {label} while the query expects '{normalized_query}'.",
                payload={"label": label, "expected": normalized_query},
            )
        )
        return 0.0, mismatch_penalty * 0.45
    if normalized_query == normalized_candidate:
        reasons.append(f"rl-{label}:{normalized_query}")
        return 1.0, 0.0
    if partial_pairs and ((normalized_query, normalized_candidate) in partial_pairs or (normalized_candidate, normalized_query) in partial_pairs):
        reasons.append(f"rl-{label}-near:{normalized_query}->{normalized_candidate}")
        return 0.55, mismatch_penalty * 0.30
    if groups is not None and groups(normalized_query) and groups(normalized_query) == groups(normalized_candidate):
        reasons.append(f"rl-{label}-family:{normalized_query}->{normalized_candidate}")
        return 0.45, mismatch_penalty * 0.35
    findings.append(
        RLAuditFinding(
            audit_type="compatibility",
            severity="warning",
            summary=f"Candidate {label} '{normalized_candidate}' does not align with query expectation '{normalized_query}'.",
            payload={"label": label, "expected": normalized_query, "actual": normalized_candidate},
        )
    )
    return 0.0, mismatch_penalty


_RUNTIME_PARTIAL_PAIRS = {
    ("train", "eval"),
    ("eval", "train"),
    ("deployment", "production"),
    ("production", "deployment"),
    ("sil", "hil"),
}

_SIM2REAL_PARTIAL_PAIRS = {
    ("sil", "sim_only"),
    ("hil", "hardware"),
    ("hardware", "flight_test"),
}

_DYNAMICS_PARTIAL_PAIRS = {
    ("nonlinear_ct", "nonlinear_dt"),
    ("nonlinear_dt", "nonlinear_ct"),
    ("delay_system", "stochastic"),
}


def build_domain_compatibility(
    query_profile: Mapping[str, Any],
    candidate_profile: Mapping[str, Any],
) -> tuple[dict[str, float], list[str], list[RLAuditFinding]]:
    reasons: list[str] = []
    findings: list[RLAuditFinding] = []
    negative_penalty = 0.0

    memory_kind_score, penalty = _category_match(
        label="memory-kind",
        query_value=str(query_profile.get("memory_kind_hint", "")),
        candidate_value=str(candidate_profile.get("memory_kind", "")),
        reasons=reasons,
        findings=findings,
        blank_values={""},
        mismatch_penalty=0.20,
        partial_pairs={
            ("failure_pattern", "experiment_pattern"),
            ("experiment_pattern", "failure_pattern"),
            ("experiment_pattern", "design_pattern"),
            ("sim2real_pattern", "experiment_pattern"),
        },
    )
    negative_penalty += penalty

    problem_family_score, penalty = _category_match(
        label="problem-family",
        query_value=str(query_profile.get("problem_family_hint", "")),
        candidate_value=str(candidate_profile.get("problem_family", "")),
        reasons=reasons,
        findings=findings,
        groups=_group_of_problem_family,
        mismatch_penalty=0.36,
    )
    negative_penalty += penalty

    theorem_score, penalty = _category_match(
        label="theorem-claim",
        query_value=str(query_profile.get("theorem_claim_type_hint", "")),
        candidate_value=str(candidate_profile.get("theorem_claim_type", "")),
        reasons=reasons,
        findings=findings,
        groups=_group_of_theorem,
        mismatch_penalty=0.42,
    )
    negative_penalty += penalty

    algorithm_family_score, penalty = _category_match(
        label="algorithm-family",
        query_value=str(query_profile.get("algorithm_family_hint", "")),
        candidate_value=str(candidate_profile.get("algorithm_family", "")),
        reasons=reasons,
        findings=findings,
        groups=_group_of_algorithm,
        mismatch_penalty=0.34,
    )
    negative_penalty += penalty

    runtime_stage_score, penalty = _category_match(
        label="runtime-stage",
        query_value=str(query_profile.get("runtime_stage_hint", "")),
        candidate_value=str(candidate_profile.get("runtime_stage", "")),
        reasons=reasons,
        findings=findings,
        partial_pairs=_RUNTIME_PARTIAL_PAIRS,
        mismatch_penalty=0.26,
    )
    negative_penalty += penalty

    dynamics_score, penalty = _category_match(
        label="dynamics-class",
        query_value=str(query_profile.get("dynamics_class_hint", "")),
        candidate_value=str(candidate_profile.get("dynamics_class", "")),
        reasons=reasons,
        findings=findings,
        partial_pairs=_DYNAMICS_PARTIAL_PAIRS,
        mismatch_penalty=0.22,
    )
    negative_penalty += penalty

    sim2real_score, penalty = _category_match(
        label="sim2real-stage",
        query_value=str(query_profile.get("sim2real_stage_hint", "")),
        candidate_value=str(candidate_profile.get("sim2real_stage", "")),
        reasons=reasons,
        findings=findings,
        partial_pairs=_SIM2REAL_PARTIAL_PAIRS,
        mismatch_penalty=0.40,
    )
    negative_penalty += penalty

    validation_tier = str(candidate_profile.get("validation_tier", "observed") or "observed")
    validation_tier_score = 0.0
    if query_profile.get("theorem_claim_type_hint") not in {"", "none"}:
        if validation_tier in {"theory_reviewed", "production_validated"}:
            validation_tier_score = 1.0
            reasons.append(f"rl-validation:{validation_tier}")
        elif validation_tier in {"validated", "candidate"}:
            validation_tier_score = 0.55
            findings.append(
                RLAuditFinding(
                    audit_type="review",
                    severity="warning",
                    summary=f"Candidate has '{validation_tier}' validation but not explicit theory_reviewed evidence.",
                    payload={"validation_tier": validation_tier},
                )
            )
        else:
            findings.append(
                RLAuditFinding(
                    audit_type="review",
                    severity="warning",
                    summary="Theory-oriented query matched a candidate without theory-reviewed validation tier.",
                    payload={"validation_tier": validation_tier},
                )
            )
            negative_penalty += 0.18
    elif query_profile.get("sim2real_stage_hint"):
        if validation_tier == "production_validated":
            validation_tier_score = 1.0
            reasons.append("rl-validation:production_validated")
        elif validation_tier in {"validated", "theory_reviewed"}:
            validation_tier_score = 0.45
            findings.append(
                RLAuditFinding(
                    audit_type="review",
                    severity="warning",
                    summary=f"Sim2real/deployment query matched a candidate validated as '{validation_tier}', not production_validated.",
                    payload={"validation_tier": validation_tier},
                )
            )
            negative_penalty += 0.12
    elif query_profile.get("runtime_stage_hint") in {"train", "eval"}:
        validation_tier_score = {
            "validated": 0.8,
            "theory_reviewed": 0.75,
            "candidate": 0.45,
            "observed": 0.20,
            "production_validated": 0.95,
        }.get(validation_tier, 0.15)
        if validation_tier == "observed":
            findings.append(
                RLAuditFinding(
                    audit_type="review",
                    severity="warning",
                    summary="Experiment-oriented query matched a candidate that is only observed-level validated.",
                    payload={"validation_tier": validation_tier},
                )
            )

    return {
        "memory_kind_score": memory_kind_score,
        "problem_family_score": problem_family_score,
        "algorithm_family_score": algorithm_family_score,
        "theory_score": theorem_score,
        "runtime_stage_score": runtime_stage_score,
        "dynamics_score": dynamics_score,
        "sim2real_score": sim2real_score,
        "validation_tier_score": validation_tier_score,
        "negative_applicability_penalty_score": max(0.0, min(negative_penalty, 1.0)),
    }, reasons, findings


def build_candidate_read_only_audit(
    profile: QueryProfile,
    candidate: Mapping[str, Any],
    *,
    required_seed_count: int,
    enable_theory_audit: bool,
    enable_experiment_audit: bool,
) -> dict[str, Any]:
    query_domain_profile = infer_query_domain_profile(profile)
    candidate_domain_profile = extract_candidate_domain_profile(candidate)
    compatibility, compatibility_reasons, findings = build_domain_compatibility(query_domain_profile, candidate_domain_profile)

    episodes = candidate.get("episodes") if isinstance(candidate.get("episodes"), list) else []
    first_episode = episodes[0] if episodes and isinstance(episodes[0], Mapping) else {}

    if enable_theory_audit and (
        query_domain_profile.get("theorem_claim_type_hint") not in {"", "none"}
        or candidate_domain_profile.get("theorem_claim_type") not in {"", "none"}
    ):
        findings.extend(validate_problem_profile(candidate_domain_profile.get("problem_profile_json") or {}))
        findings.extend(validate_validation_payload(candidate_domain_profile.get("validation_json") or {}, required_seed_count=required_seed_count))
        findings.extend(
            validate_theory_consistency(
                problem_family=str(candidate_domain_profile.get("problem_family", "generic")),
                theorem_claim_type=str(candidate_domain_profile.get("theorem_claim_type", "none")),
                problem_profile=candidate_domain_profile.get("problem_profile_json") or {},
                validation_payload=candidate_domain_profile.get("validation_json") or {},
                algorithm_family=str(candidate_domain_profile.get("algorithm_family", "")),
                run_manifest=first_episode.get("run_manifest_json") or {},
            )
        )

    if enable_experiment_audit and (
        query_domain_profile.get("runtime_stage_hint") or query_domain_profile.get("algorithm_family_hint") or query_domain_profile.get("sim2real_stage_hint")
    ):
        if first_episode:
            findings.extend(validate_run_manifest(first_episode.get("run_manifest_json") or {}, required_seed_count=required_seed_count))
            findings.extend(validate_metrics_payload(first_episode.get("metrics_json") or {}))
            findings.extend(
                validate_experiment_consistency(
                    problem_family=str(candidate_domain_profile.get("problem_family", "generic")),
                    algorithm_family=str(candidate_domain_profile.get("algorithm_family", "")),
                    runtime_stage=str(candidate_domain_profile.get("runtime_stage", "")),
                    run_manifest=first_episode.get("run_manifest_json") or {},
                    metrics_payload=first_episode.get("metrics_json") or {},
                    validation_payload=candidate_domain_profile.get("validation_json") or {},
                    sim2real_profile=candidate_domain_profile.get("sim2real_profile_json") or {},
                    required_seed_count=required_seed_count,
                )
            )
        findings.extend(validate_validation_payload(candidate_domain_profile.get("validation_json") or {}, required_seed_count=required_seed_count))

    severity_counts = Counter(str(finding.severity).lower() for finding in findings)
    compact_findings = [
        {
            "audit_type": finding.audit_type,
            "severity": finding.severity,
            "status": finding.status,
            "summary": finding.summary,
            "payload": finding.payload,
        }
        for finding in findings[:8]
    ]

    severity_label = "clean"
    if severity_counts.get("critical"):
        severity_label = "critical"
    elif severity_counts.get("error"):
        severity_label = "error"
    elif severity_counts.get("warning"):
        severity_label = "warning"
    elif compact_findings:
        severity_label = "info"

    summary_parts: list[str] = []
    if candidate_domain_profile.get("problem_family") not in {"", "generic"}:
        summary_parts.append(str(candidate_domain_profile["problem_family"]))
    if candidate_domain_profile.get("algorithm_family"):
        summary_parts.append(str(candidate_domain_profile["algorithm_family"]))
    if candidate_domain_profile.get("theorem_claim_type") not in {"", "none"}:
        summary_parts.append(str(candidate_domain_profile["theorem_claim_type"]))
    if candidate_domain_profile.get("runtime_stage"):
        summary_parts.append(str(candidate_domain_profile["runtime_stage"]))
    summary = " / ".join(summary_parts) if summary_parts else str(candidate.get("title", "candidate")).strip()

    return {
        "query_domain_profile": query_domain_profile,
        "candidate_domain_profile": candidate_domain_profile,
        "compatibility": {key: round(float(value), 4) for key, value in compatibility.items()},
        "compatibility_reasons": compatibility_reasons[:8],
        "severity": severity_label,
        "severity_counts": dict(severity_counts),
        "summary": summary,
        "findings": compact_findings,
    }
