from __future__ import annotations

from typing import Any

RL_CONTROL_REPORTING_CASES: list[dict[str, Any]] = [
    {
        "name": "experiment",
        "query": "SAC quadrotor tracking validated baselines normalized actions",
    },
    {
        "name": "theory",
        "query": "HJB boundary condition proof review nonlinear control",
    },
]


def seed_rl_control_reporting_memory(app: Any) -> dict[str, int]:
    experiment = app.issue_record_resolution(
        title="Validated SAC quadrotor tracking run pending experiment review",
        raw_error="SAC tracking run stabilized after target smoothing and normalized action clipping.",
        canonical_fix="Persist seed count, baselines, and normalization metadata before promotion.",
        prevention_rule="Validated RL/control promotions require reproducibility metadata and review.",
        project_scope="rl-lab",
        domain="rl_control",
        memory_kind="experiment_pattern",
        problem_family="safe_rl",
        theorem_claim_type="uub",
        algorithm_family="sac",
        runtime_stage="train",
        problem_profile_json={
            "problem_family": "safe_rl",
            "system_name": "quadrotor",
            "task_name": "tracking",
            "dynamics_class": "nonlinear_dt",
            "assumptions": ["bounded disturbance", "bounded reference"],
            "theorem_claim_type": "uub",
        },
        run_manifest_json={
            "algorithm_family": "sac",
            "runtime_stage": "train",
            "seed_count": 4,
            "train_env_id": "QuadTrain-v1",
            "eval_env_id": "QuadEval-v1",
            "baseline_names": ["mpc", "pid"],
            "normalization": {"observations": True, "actions": True},
            "action_bounds": [-1.0, 1.0],
        },
        metrics_json={
            "return_mean": 318.0,
            "return_std": 9.5,
            "tracking_rmse": 0.08,
            "control_effort": 0.21,
            "constraint_violation_rate": 0.0,
            "crash_rate": 0.0,
        },
        validation_json={
            "seed_count": 4,
            "baseline_comparison": True,
            "validation_tier": "validated",
        },
        artifact_refs_json=[
            {"kind": "run_manifest", "uri": "artifact://runs/sac-quadrotor/manifest.json", "description": "training manifest", "bytes": 2048},
            {"kind": "metrics", "uri": "artifact://runs/sac-quadrotor/metrics.json", "description": "evaluation metrics", "bytes": 1024},
        ],
        sim2real_profile_json={"stage": "sil", "latency_ms": 4.0},
    )
    theory = app.issue_record_resolution(
        title="HJB boundary-condition proof candidate pending theory review",
        raw_error="The HJB derivation omits the terminal boundary condition in nonlinear regulation.",
        canonical_fix="State the terminal boundary condition explicitly and reconcile the stationarity condition.",
        prevention_rule="Theory-reviewed HJB patterns require recorded assumptions and proof review.",
        project_scope="rl-lab",
        domain="rl_control",
        memory_kind="theory_pattern",
        problem_family="hjb",
        theorem_claim_type="hjb_optimality",
        algorithm_family="mpc",
        runtime_stage="design",
        problem_profile_json={
            "problem_family": "hjb",
            "system_name": "inverted_pendulum",
            "dynamics_class": "nonlinear_ct",
            "assumptions": ["smooth value function", "compact input set", "terminal boundary condition"],
            "theorem_claim_type": "hjb_optimality",
            "lyapunov_candidate": "V(x)",
        },
        validation_json={
            "validation_tier": "theory_reviewed",
            "theory_reviewed": True,
            "reviewed_by": "proof-reviewer",
        },
        artifact_refs_json=[
            {"kind": "proof_note", "uri": "artifact://proofs/hjb-boundary.md", "description": "proof review note", "bytes": 1536},
        ],
    )
    return {
        "experiment_pattern_id": int(experiment["pattern_id"]),
        "theory_pattern_id": int(theory["pattern_id"]),
    }


def run_rl_control_reporting_benchmark(app: Any, *, repeats: int = 3) -> dict[str, Any]:
    seeded = seed_rl_control_reporting_memory(app)
    failures: list[str] = []
    search_checks = 0
    search_hits = 0
    read_only_summary_hits = 0

    for _ in range(max(repeats, 1)):
        experiment_search = app.issue_search(
            query=RL_CONTROL_REPORTING_CASES[0]["query"],
            project_scope="rl-lab",
            limit=3,
        )
        search_checks += 1
        if experiment_search["patterns"] and int(experiment_search["patterns"][0]["pattern_id"]) == seeded["experiment_pattern_id"]:
            search_hits += 1
        else:
            failures.append("experiment-search-top1-mismatch")
        if experiment_search.get("read_only_audit", {}).get("summary", {}).get("total_matches", 0) >= 1:
            read_only_summary_hits += 1
        else:
            failures.append("experiment-read-only-summary-missing")

        theory_search = app.issue_search(
            query=RL_CONTROL_REPORTING_CASES[1]["query"],
            project_scope="rl-lab",
            limit=3,
        )
        search_checks += 1
        if theory_search["patterns"] and int(theory_search["patterns"][0]["pattern_id"]) == seeded["theory_pattern_id"]:
            search_hits += 1
        else:
            failures.append("theory-search-top1-mismatch")
        if theory_search.get("read_only_audit", {}).get("summary", {}).get("total_matches", 0) >= 1:
            read_only_summary_hits += 1
        else:
            failures.append("theory-read-only-summary-missing")

    experiment_bundle = app.issue_get(pattern_id=seeded["experiment_pattern_id"])
    theory_bundle = app.issue_get(pattern_id=seeded["theory_pattern_id"])
    pattern_report_coverage = sum(
        1 for bundle in (experiment_bundle, theory_bundle) if bundle.get("audit_report", {}).get("enabled")
    ) / 2.0
    if pattern_report_coverage < 1.0:
        failures.append("pattern-audit-report-missing")

    queue = app.issue_review_queue(status="pending", limit=10)
    queue_items = queue.get("items", [])
    queue_report_coverage = (
        sum(1 for item in queue_items if item.get("audit_report", {}).get("enabled")) / max(len(queue_items), 1)
    )
    if len(queue_items) < 2:
        failures.append("review-queue-too-small")
    if queue_report_coverage < 1.0:
        failures.append("review-queue-audit-report-missing")
    if not queue.get("audit_report", {}).get("enabled"):
        failures.append("review-queue-summary-missing")

    metrics = app.issue_metrics(window_days=30)
    rl_metrics_present = bool(metrics.get("rl_control", {}).get("enabled"))
    if not rl_metrics_present:
        failures.append("metrics-rl-control-section-missing")

    return {
        "benchmark": "rl_control_reporting",
        "repeats": max(repeats, 1),
        "search_top1_accuracy": round(search_hits / max(search_checks, 1), 6),
        "read_only_summary_coverage": round(read_only_summary_hits / max(search_checks, 1), 6),
        "pattern_audit_report_coverage": round(pattern_report_coverage, 6),
        "review_queue_report_coverage": round(queue_report_coverage, 6),
        "pending_review_count": int(queue.get("count", 0) or 0),
        "rl_metrics_present": rl_metrics_present,
        "failures": sorted(set(failures)),
    }
