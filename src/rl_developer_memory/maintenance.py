"""Public maintenance module façade.

This keeps the stable import/entrypoint surface:
- python -m rl_developer_memory.maintenance
- rl_developer_memory.maintenance:main
"""

from .maintenance_cli.cli import (
    build_parser,
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
    main,
)

__all__ = [
    "build_parser",
    "cmd_backup",
    "cmd_benchmark_dense_bandit",
    "cmd_benchmark_failure_taxonomy",
    "cmd_benchmark_hard_negatives",
    "cmd_benchmark_merge_stress",
    "cmd_benchmark_real_world",
    "cmd_benchmark_rl_control_reporting",
    "cmd_benchmark_user_domains",
    "cmd_calibrate_thresholds",
    "cmd_doctor",
    "cmd_e2e_mcp_reuse_harness",
    "cmd_export_dashboard",
    "cmd_init_db",
    "cmd_list_backups",
    "cmd_metrics",
    "cmd_migrate_v2",
    "cmd_prune_retention",
    "cmd_recommended_config",
    "cmd_resolve_review",
    "cmd_restore_backup",
    "cmd_review_queue",
    "cmd_rl_audit_health",
    "cmd_runtime_diagnostics",
    "cmd_schema_version",
    "cmd_server_status",
    "cmd_smoke",
    "cmd_smoke_learning",
    "cmd_verify_backup",
    "main",
]


if __name__ == "__main__":
    main()
