from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from .release_checks import (
    DEFAULT_REVIEW_BACKLOG_LIMIT,
    MINIMUM_QUALITY_TEST_SENTINELS,
    MINIMUM_STRUCTURE_PATHS,
    run_validation_matrix,
    validate_docs_sync,
)


def _result_by_key(results: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["key"]): item for item in results}


def evaluate_rollout_readiness(
    matrix: dict[str, Any],
    docs_sync: dict[str, Any],
    *,
    review_backlog_limit: int = DEFAULT_REVIEW_BACKLOG_LIMIT,
) -> dict[str, Any]:
    """Evaluate codebase readiness and conservative active-rollout status."""

    by_key = _result_by_key(matrix.get("results", []))

    def passed(key: str) -> bool:
        return by_key.get(key, {}).get("status") == "passed"

    doctor_shadow = by_key.get("doctor_shadow_max0", {}).get("payload") or {}
    doctor_rl = by_key.get("doctor_shadow_rl_control", {}).get("payload") or {}
    e2e = by_key.get("e2e_mcp_reuse_harness", {}).get("payload") or {}
    benchmark = by_key.get("benchmark_rl_control_reporting", {}).get("payload") or {}

    shadow_doctor_clean = (
        passed("doctor_shadow_max0")
        and doctor_shadow.get("status") == "ok"
        and doctor_shadow.get("summary", {}).get("errors") == 0
        and doctor_shadow.get("summary", {}).get("warnings") == 0
    )
    rl_shadow_doctor_clean = (
        passed("doctor_shadow_rl_control")
        and doctor_rl.get("status") == "ok"
        and doctor_rl.get("summary", {}).get("errors") == 0
        and doctor_rl.get("summary", {}).get("warnings") == 0
    )

    verdict = e2e.get("verdict", {}) if isinstance(e2e, dict) else {}
    reuse_behavior_ok = all(
        bool(verdict.get(key))
        for key in (
            "main_started",
            "subagent_resolved_to_main",
            "duplicate_launch_rejected",
            "duplicate_preserved_single_owner_slot",
            "distinct_main_conversations_coexist",
            "reuse_signal_emitted",
        )
    ) and int((e2e.get("duplicate_launch") or {}).get("returncode", -1)) == 75

    benchmark_stable = (
        passed("benchmark_rl_control_reporting")
        and benchmark.get("failures") == []
        and float(benchmark.get("search_top1_accuracy", 0.0)) >= 1.0
        and float(benchmark.get("read_only_summary_coverage", 0.0)) >= 1.0
        and float(benchmark.get("pattern_audit_report_coverage", 0.0)) >= 1.0
        and float(benchmark.get("review_queue_report_coverage", 0.0)) >= 1.0
        and bool(benchmark.get("rl_metrics_present"))
    )
    pending_review_count = int(benchmark.get("pending_review_count", review_backlog_limit + 1) or 0)
    review_backlog_managed = pending_review_count <= review_backlog_limit

    codebase_ready = (
        matrix.get("overall_status") == "passed"
        and docs_sync.get("status") == "passed"
        and shadow_doctor_clean
        and rl_shadow_doctor_clean
        and reuse_behavior_ok
        and benchmark_stable
        and review_backlog_managed
    )

    active_go = False
    blockers: list[str] = []
    if not shadow_doctor_clean:
        blockers.append("shadow-doctor-not-clean")
    if not rl_shadow_doctor_clean:
        blockers.append("rl-shadow-doctor-not-clean")
    if not reuse_behavior_ok:
        blockers.append("owner-reuse-contract-not-proven")
    if not benchmark_stable:
        blockers.append("rl-reporting-benchmark-not-stable")
    if not review_backlog_managed:
        blockers.append("review-backlog-not-manageable")
    if docs_sync.get("status") != "passed":
        blockers.append("docs-cli-mcp-sync-failed")
    if codebase_ready:
        blockers.append("active-rollout-requires-live-shadow-soak-and-review-backlog-signoff")

    return {
        "codebase_readiness": "passed" if codebase_ready else "failed",
        "checks": {
            "shadow_doctor_clean": shadow_doctor_clean,
            "rl_shadow_doctor_clean": rl_shadow_doctor_clean,
            "reuse_behavior_ok": reuse_behavior_ok,
            "benchmark_stable": benchmark_stable,
            "review_backlog_managed": review_backlog_managed,
            "pending_review_count": pending_review_count,
            "review_backlog_limit": review_backlog_limit,
            "docs_sync_ok": docs_sync.get("status") == "passed",
        },
        "active_rollout_decision": "go" if active_go else "no-go",
        "active_rollout_reason": (
            "all automated and operational checks passed"
            if active_go
            else "automated codebase checks may pass, but active rollout still requires live shadow soak evidence and explicit review-backlog signoff"
        ),
        "blockers": blockers,
    }


def evaluate_minimum_quality_gate(
    repo_root: Path,
    matrix: dict[str, Any],
    docs_sync: dict[str, Any],
    rollout_readiness: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate the minimum RL engineering quality gate checklist."""

    by_key = _result_by_key(matrix.get("results", []))

    def passed(key: str) -> bool:
        return by_key.get(key, {}).get("status") == "passed"

    missing_structure = [path for path in MINIMUM_STRUCTURE_PATHS if not (repo_root / path).exists()]
    structure_ok = not missing_structure

    has_mcp_policy = (repo_root / "docs" / "MCP_RL_INTEGRATION_POLICY.md").exists()
    has_repo_agents = (repo_root / "AGENTS.md").exists()
    mcp_hygiene_ok = has_mcp_policy and has_repo_agents and docs_sync.get("status") == "passed"

    sentinel_status: dict[str, bool] = {}
    for key, paths in MINIMUM_QUALITY_TEST_SENTINELS.items():
        sentinel_status[key] = all((repo_root / path).exists() for path in paths)

    benchmark_payload = by_key.get("benchmark_rl_control_reporting", {}).get("payload") or {}
    logging_metrics_ok = passed("benchmark_rl_control_reporting") and bool(benchmark_payload.get("rl_metrics_present"))

    checklist = [
        {
            "id": "1",
            "name": "repository structure compliance",
            "status": "passed" if structure_ok else "failed",
            "evidence": {
                "required_paths": list(MINIMUM_STRUCTURE_PATHS),
                "missing_paths": missing_structure,
            },
        },
        {
            "id": "2",
            "name": "import/compile safety",
            "status": "passed" if (passed("pyright") and passed("pytest") and passed("maintenance_smoke") and passed("build")) else "failed",
            "evidence": {
                "pyright": by_key.get("pyright", {}).get("status", "not_configured"),
                "pytest": by_key.get("pytest", {}).get("status", "not_configured"),
                "maintenance_smoke": by_key.get("maintenance_smoke", {}).get("status", "not_configured"),
                "build": by_key.get("build", {}).get("status", "not_configured"),
            },
        },
        {
            "id": "3",
            "name": "typing discipline",
            "status": "passed" if passed("pyright") else "failed",
            "evidence": {"pyright": by_key.get("pyright", {}).get("status", "not_configured")},
        },
        {
            "id": "4",
            "name": "lint discipline",
            "status": "passed" if passed("ruff") else "failed",
            "evidence": {"ruff": by_key.get("ruff", {}).get("status", "not_configured")},
        },
        {
            "id": "5",
            "name": "unit tests",
            "status": "passed" if (passed("pytest") and (repo_root / "tests/unit").exists()) else "failed",
            "evidence": {
                "pytest": by_key.get("pytest", {}).get("status", "not_configured"),
                "unit_dir_exists": (repo_root / "tests/unit").exists(),
            },
        },
        {
            "id": "6",
            "name": "smoke tests",
            "status": "passed" if passed("maintenance_smoke") else "failed",
            "evidence": {"maintenance_smoke": by_key.get("maintenance_smoke", {}).get("status", "not_configured")},
        },
        {
            "id": "7",
            "name": "kısa runtime tests",
            "status": "passed" if (passed("maintenance_smoke") and passed("maintenance_smoke_learning")) else "failed",
            "evidence": {
                "maintenance_smoke": by_key.get("maintenance_smoke", {}).get("status", "not_configured"),
                "smoke_learning": by_key.get("maintenance_smoke_learning", {}).get("status", "not_configured"),
            },
        },
        {
            "id": "8",
            "name": "deterministic behavior checks",
            "status": "passed" if (passed("pytest") and sentinel_status["deterministic_behavior"]) else "failed",
            "evidence": {
                "pytest": by_key.get("pytest", {}).get("status", "not_configured"),
                "sentinel_files_present": sentinel_status["deterministic_behavior"],
            },
        },
        {
            "id": "9",
            "name": "checkpoint/reload checks",
            "status": "passed" if (passed("pytest") and sentinel_status["checkpoint_reload"]) else "failed",
            "evidence": {
                "pytest": by_key.get("pytest", {}).get("status", "not_configured"),
                "sentinel_files_present": sentinel_status["checkpoint_reload"],
            },
        },
        {
            "id": "10",
            "name": "config validation",
            "status": "passed" if (passed("pytest") and sentinel_status["config_validation"]) else "failed",
            "evidence": {
                "pytest": by_key.get("pytest", {}).get("status", "not_configured"),
                "sentinel_files_present": sentinel_status["config_validation"],
            },
        },
        {
            "id": "11",
            "name": "logging/metrics minimum standardı",
            "status": "passed" if logging_metrics_ok else "failed",
            "evidence": {
                "benchmark_rl_control_reporting": by_key.get("benchmark_rl_control_reporting", {}).get("status", "not_configured"),
                "rl_metrics_present": bool(benchmark_payload.get("rl_metrics_present")),
            },
        },
        {
            "id": "12",
            "name": "docs sync",
            "status": "passed" if docs_sync.get("status") == "passed" else "failed",
            "evidence": {"docs_sync": docs_sync.get("status", "not_configured")},
        },
        {
            "id": "13",
            "name": "theorem-to-code sync",
            "status": "passed" if (passed("pytest") and sentinel_status["theorem_to_code"]) else "failed",
            "evidence": {
                "pytest": by_key.get("pytest", {}).get("status", "not_configured"),
                "sentinel_files_present": sentinel_status["theorem_to_code"],
            },
        },
        {
            "id": "14",
            "name": "MCP memory write-back hygiene",
            "status": "passed" if mcp_hygiene_ok else "failed",
            "evidence": {
                "mcp_policy_doc": has_mcp_policy,
                "repo_agents_contract": has_repo_agents,
                "docs_sync": docs_sync.get("status", "not_configured"),
            },
        },
        {
            "id": "15",
            "name": "rollout safety checks",
            "status": "passed"
            if (
                rollout_readiness.get("checks", {}).get("shadow_doctor_clean")
                and rollout_readiness.get("checks", {}).get("rl_shadow_doctor_clean")
                and rollout_readiness.get("checks", {}).get("reuse_behavior_ok")
                and rollout_readiness.get("checks", {}).get("benchmark_stable")
            )
            else "failed",
            "evidence": rollout_readiness.get("checks", {}),
        },
    ]

    failed_items = [item for item in checklist if item["status"] != "passed"]
    return {
        "status": "passed" if not failed_items else "failed",
        "items": checklist,
        "failed_items": failed_items,
    }


def generate_release_acceptance_report(
    repo_root: Path,
    *,
    python_bin: str,
    include_core: bool = True,
    include_extended: bool = True,
) -> dict[str, Any]:
    """Run the full standardized release-acceptance flow."""

    matrix = run_validation_matrix(
        repo_root,
        python_bin=python_bin,
        include_core=include_core,
        include_extended=include_extended,
    )
    docs_sync = validate_docs_sync(repo_root)
    readiness = evaluate_rollout_readiness(matrix, docs_sync)
    minimum_quality_gate = evaluate_minimum_quality_gate(repo_root, matrix, docs_sync, readiness)
    return {
        "validation_matrix": matrix,
        "docs_sync": docs_sync,
        "rollout_readiness": readiness,
        "minimum_quality_gate": minimum_quality_gate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the standardized rl-developer-memory release acceptance matrix.")
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    parser.add_argument("--core-only", action="store_true", help="Run only the mandatory core validation commands.")
    parser.add_argument("--extended-only", action="store_true", help="Run only rollout-specific extended checks.")
    parser.add_argument("--python-bin", default=sys.executable, help="Python interpreter used for subprocess commands.")
    args = parser.parse_args()

    include_core = not args.extended_only
    include_extended = not args.core_only
    repo_root = Path(__file__).resolve().parents[2]
    report = generate_release_acceptance_report(
        repo_root,
        python_bin=args.python_bin,
        include_core=include_core,
        include_extended=include_extended,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))

    if report["validation_matrix"]["overall_status"] != "passed" or report["docs_sync"]["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
