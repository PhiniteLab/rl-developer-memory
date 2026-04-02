from __future__ import annotations

from pathlib import Path

from rl_developer_memory.release_acceptance import (
    evaluate_minimum_quality_gate,
    evaluate_rollout_readiness,
    validate_docs_sync,
)

ROOT = Path(__file__).resolve().parents[1]


def test_docs_sync_report_matches_public_surface() -> None:
    report = validate_docs_sync(ROOT)
    assert report["status"] == "passed"
    assert report["mcp_tool_count"] == 12
    assert report["maintenance_subcommand_count"] == 28


def test_active_rollout_requires_more_than_automated_passes() -> None:
    matrix = {
        "overall_status": "passed",
        "results": [
            {
                "key": "doctor_shadow_max0",
                "status": "passed",
                "payload": {"status": "ok", "summary": {"errors": 0, "warnings": 0}},
            },
            {
                "key": "doctor_shadow_rl_control",
                "status": "passed",
                "payload": {"status": "ok", "summary": {"errors": 0, "warnings": 0}},
            },
            {
                "key": "e2e_mcp_reuse_harness",
                "status": "passed",
                "payload": {
                    "duplicate_launch": {"returncode": 75},
                    "verdict": {
                        "main_started": True,
                        "subagent_resolved_to_main": True,
                        "duplicate_launch_rejected": True,
                        "duplicate_preserved_single_owner_slot": True,
                        "distinct_main_conversations_coexist": True,
                        "reuse_signal_emitted": True,
                    },
                },
            },
            {
                "key": "benchmark_rl_control_reporting",
                "status": "passed",
                "payload": {
                    "failures": [],
                    "pending_review_count": 2,
                    "search_top1_accuracy": 1.0,
                    "read_only_summary_coverage": 1.0,
                    "pattern_audit_report_coverage": 1.0,
                    "review_queue_report_coverage": 1.0,
                    "rl_metrics_present": True,
                },
            },
        ],
    }
    docs_sync = {"status": "passed"}

    readiness = evaluate_rollout_readiness(matrix, docs_sync)

    assert readiness["codebase_readiness"] == "passed"
    assert readiness["active_rollout_decision"] == "no-go"
    assert "active-rollout-requires-live-shadow-soak-and-review-backlog-signoff" in readiness["blockers"]


def test_minimum_quality_gate_maps_to_checklist() -> None:
    matrix = {
        "overall_status": "passed",
        "results": [
            {"key": "ruff", "status": "passed"},
            {"key": "pyright", "status": "passed"},
            {"key": "pytest", "status": "passed"},
            {"key": "maintenance_smoke", "status": "passed"},
            {"key": "maintenance_smoke_learning", "status": "passed"},
            {"key": "build", "status": "passed"},
            {
                "key": "benchmark_rl_control_reporting",
                "status": "passed",
                "payload": {"rl_metrics_present": True},
            },
        ],
    }
    docs_sync = {"status": "passed"}
    readiness = {
        "checks": {
            "shadow_doctor_clean": True,
            "rl_shadow_doctor_clean": True,
            "reuse_behavior_ok": True,
            "benchmark_stable": True,
            "review_backlog_managed": True,
        }
    }

    checklist = evaluate_minimum_quality_gate(ROOT, matrix, docs_sync, readiness)
    assert checklist["status"] == "passed"
    assert len(checklist["items"]) == 15
    assert checklist["failed_items"] == []
