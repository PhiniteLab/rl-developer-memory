from __future__ import annotations

from rl_developer_memory.domains.rl_control.taxonomy import (
    infer_problem_family,
    normalize_algorithm_family,
    normalize_domain_mode,
    normalize_memory_kind,
    normalize_problem_family,
    normalize_runtime_stage,
    normalize_sim2real_stage,
    normalize_theorem_claim_type,
    normalize_validation_tier,
)


def test_rl_control_taxonomy_normalization() -> None:
    assert normalize_domain_mode("RL-Control") == "rl_control"
    assert normalize_memory_kind("experiment") == "experiment_pattern"
    assert normalize_problem_family("Bellman") == "bellman_dp"
    assert normalize_algorithm_family("soft actor critic") == "sac"
    assert normalize_theorem_claim_type("HJB") == "hjb_optimality"
    assert normalize_runtime_stage("hardware in loop") == "hil"
    assert normalize_sim2real_stage("flight") == "flight_test"
    assert normalize_validation_tier("prod") == "production_validated"


def test_infer_problem_family_prefers_domain_terms() -> None:
    assert infer_problem_family("Hamilton-Jacobi-Bellman equation for nonlinear optimal control") == "hjb"
    assert infer_problem_family("safe RL with control barrier filtering and SAC") == "safe_rl"
