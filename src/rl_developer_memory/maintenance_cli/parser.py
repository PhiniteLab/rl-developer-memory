from __future__ import annotations

import argparse

from .commands import (
    cmd_backup,
    cmd_benchmark_dense_bandit,
    cmd_benchmark_failure_taxonomy,
    cmd_benchmark_hard_negatives,
    cmd_benchmark_merge_stress,
    cmd_benchmark_real_world,
    cmd_benchmark_rl_control_reporting,
    cmd_benchmark_user_domains,
    cmd_calibrate_thresholds,
    cmd_doctor,
    cmd_e2e_mcp_reuse_harness,
    cmd_export_dashboard,
    cmd_init_db,
    cmd_list_backups,
    cmd_metrics,
    cmd_migrate_v2,
    cmd_prune_retention,
    cmd_recommended_config,
    cmd_resolve_review,
    cmd_restore_backup,
    cmd_review_queue,
    cmd_rl_audit_health,
    cmd_runtime_diagnostics,
    cmd_schema_version,
    cmd_server_status,
    cmd_smoke,
    cmd_smoke_learning,
    cmd_verify_backup,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintenance commands for rl-developer-memory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db")
    subparsers.add_parser("migrate-v2")
    subparsers.add_parser("schema-version")
    subparsers.add_parser("backup")
    list_backups = subparsers.add_parser("list-backups")
    list_backups.add_argument("--limit", type=int, default=20)
    verify_backup = subparsers.add_parser("verify-backup")
    verify_backup.add_argument("path")
    restore_backup = subparsers.add_parser("restore-backup")
    restore_backup.add_argument("path")
    restore_backup.add_argument("--no-safety-backup", action="store_true")
    metrics = subparsers.add_parser("metrics")
    metrics.add_argument("--window-days", type=int, default=30)
    subparsers.add_parser("server-status")
    recommended = subparsers.add_parser("recommended-config")
    recommended.add_argument("--mode", choices=("shadow", "active", "single"), default="shadow")
    recommended.add_argument("--format", choices=("json", "toml", "env"), default="json")
    recommended.add_argument("--max-instances", type=int, default=0)
    recommended.add_argument("--profile", choices=("default", "rl-control-shadow", "rl-control-active"), default="default")
    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--mode", choices=("shadow", "active", "single"), default="shadow")
    doctor.add_argument("--max-instances", type=int, default=0)
    doctor.add_argument("--codex-home", default=None)
    doctor.add_argument("--profile", choices=("default", "rl-control-shadow", "rl-control-active"), default="default")
    prune = subparsers.add_parser("prune-retention")
    prune.add_argument("--telemetry-days", type=int, default=90)
    prune.add_argument("--review-days", type=int, default=120)
    review_queue = subparsers.add_parser("review-queue")
    review_queue.add_argument("--status", default="pending")
    review_queue.add_argument("--limit", type=int, default=20)
    resolve_review = subparsers.add_parser("resolve-review")
    resolve_review.add_argument("review_id", type=int)
    resolve_review.add_argument("decision")
    resolve_review.add_argument("--note", default="")
    subparsers.add_parser("smoke")
    subparsers.add_parser("smoke-learning")
    subparsers.add_parser("benchmark-user-domains")
    subparsers.add_parser("benchmark-rl-control-reporting")
    subparsers.add_parser("benchmark-failure-taxonomy")
    subparsers.add_parser("runtime-diagnostics")
    rl_health = subparsers.add_parser("rl-audit-health")
    rl_health.add_argument("--window-days", type=int, default=30)
    rl_health.add_argument("--limit", type=int, default=10)
    e2e_reuse = subparsers.add_parser("e2e-mcp-reuse-harness")
    e2e_reuse.add_argument("--timeout", type=float, default=10.0)
    e2e_reuse.add_argument("--json", action="store_true")
    subparsers.add_parser("benchmark-dense-bandit")
    subparsers.add_parser("benchmark-real-world")
    subparsers.add_parser("benchmark-hard-negatives")
    subparsers.add_parser("benchmark-merge-stress")
    calibrate = subparsers.add_parser("calibrate-thresholds")
    calibrate.add_argument("--write-profile", action="store_true")
    dashboard = subparsers.add_parser("export-dashboard")
    dashboard.add_argument("--output", required=True)
    dashboard.add_argument("--format", choices=("json", "html"), default="json")
    dashboard.add_argument("--window-days", type=int, default=30)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init-db":
        cmd_init_db()
    elif args.command == "migrate-v2":
        cmd_migrate_v2()
    elif args.command == "schema-version":
        cmd_schema_version()
    elif args.command == "backup":
        cmd_backup()
    elif args.command == "list-backups":
        cmd_list_backups(limit=args.limit)
    elif args.command == "verify-backup":
        cmd_verify_backup(args.path)
    elif args.command == "restore-backup":
        cmd_restore_backup(args.path, create_safety_backup=not args.no_safety_backup)
    elif args.command == "metrics":
        cmd_metrics(window_days=args.window_days)
    elif args.command == "server-status":
        cmd_server_status()
    elif args.command == "recommended-config":
        cmd_recommended_config(mode=args.mode, fmt=args.format, max_instances=args.max_instances, profile=args.profile)
    elif args.command == "doctor":
        cmd_doctor(mode=args.mode, max_instances=args.max_instances, codex_home=args.codex_home, profile=args.profile)
    elif args.command == "prune-retention":
        cmd_prune_retention(telemetry_days=args.telemetry_days, review_days=args.review_days)
    elif args.command == "review-queue":
        cmd_review_queue(status=args.status, limit=args.limit)
    elif args.command == "resolve-review":
        cmd_resolve_review(review_id=args.review_id, decision=args.decision, note=args.note)
    elif args.command == "smoke":
        cmd_smoke()
    elif args.command == "smoke-learning":
        cmd_smoke_learning()
    elif args.command == "benchmark-user-domains":
        cmd_benchmark_user_domains()
    elif args.command == "benchmark-rl-control-reporting":
        cmd_benchmark_rl_control_reporting()
    elif args.command == "benchmark-failure-taxonomy":
        cmd_benchmark_failure_taxonomy()
    elif args.command == "runtime-diagnostics":
        cmd_runtime_diagnostics()
    elif args.command == "rl-audit-health":
        cmd_rl_audit_health(window_days=args.window_days, limit=args.limit)
    elif args.command == "e2e-mcp-reuse-harness":
        cmd_e2e_mcp_reuse_harness(timeout=args.timeout, json_output=bool(args.json))
    elif args.command == "benchmark-dense-bandit":
        cmd_benchmark_dense_bandit()
    elif args.command == "benchmark-real-world":
        cmd_benchmark_real_world()
    elif args.command == "benchmark-hard-negatives":
        cmd_benchmark_hard_negatives()
    elif args.command == "benchmark-merge-stress":
        cmd_benchmark_merge_stress()
    elif args.command == "calibrate-thresholds":
        cmd_calibrate_thresholds(write_profile=bool(args.write_profile))
    elif args.command == "export-dashboard":
        cmd_export_dashboard(output=args.output, fmt=args.format, window_days=args.window_days)
    else:
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
