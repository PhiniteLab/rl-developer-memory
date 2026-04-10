from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

try:
    import tomllib  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - Python < 3.11
    tomllib = None  # type: ignore[assignment]

from ..app import RLDeveloperMemoryApp
from ..backup import BackupManager
from ..benchmarks import (
    run_dense_bandit_benchmark,
    run_failure_taxonomy_benchmark,
    run_hard_negative_benchmark,
    run_merge_correctness_stress,
    run_real_world_eval,
    run_rl_control_reporting_benchmark,
    run_runtime_diagnostics,
    run_threshold_calibration,
    run_user_domain_benchmark,
    seed_dense_bandit_memory,
    seed_hard_negative_memory,
    seed_real_world_memory,
    seed_user_domain_memory,
)
from ..lifecycle import read_server_lifecycle_status
from ..mcp_reuse_harness import (
    harness_succeeded as e2e_mcp_reuse_harness_succeeded,
)
from ..mcp_reuse_harness import (
    render_human as render_e2e_mcp_reuse_harness,
)
from ..mcp_reuse_harness import (
    run_harness as run_e2e_mcp_reuse_harness,
)
from ..settings import Settings
from ..storage import RLDeveloperMemoryStore

_ENV_KEYS = (
    "RL_DEVELOPER_MEMORY_HOME",
    "RL_DEVELOPER_MEMORY_DB_PATH",
    "RL_DEVELOPER_MEMORY_STATE_DIR",
    "RL_DEVELOPER_MEMORY_BACKUP_DIR",
    "RL_DEVELOPER_MEMORY_LOG_DIR",
)


def _apply_rl_control_profile_env(env: dict[str, str], *, settings: Settings, profile: str) -> dict[str, str]:
    if profile == "default":
        return env
    if profile not in {"rl-control-shadow", "rl-control-active"}:
        raise ValueError(f"unsupported profile: {profile}")
    env = dict(env)
    env.update(
        {
            "RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL": "1",
            "RL_DEVELOPER_MEMORY_DOMAIN_MODE": "hybrid" if profile == "rl-control-shadow" else "rl_control",
            "RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT": "1",
            "RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT": "1",
            "RL_DEVELOPER_MEMORY_RL_STRICT_PROMOTION": "1" if settings.rl_strict_promotion else "0",
            "RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION": "1" if settings.rl_review_gated_promotion else "0",
            "RL_DEVELOPER_MEMORY_RL_CANDIDATE_WARNING_BUDGET": str(settings.rl_candidate_warning_budget),
            "RL_DEVELOPER_MEMORY_RL_REQUIRED_SEED_COUNT": str(settings.rl_required_seed_count),
            "RL_DEVELOPER_MEMORY_RL_PRODUCTION_MIN_SEED_COUNT": str(settings.rl_production_min_seed_count),
            "RL_DEVELOPER_MEMORY_RL_MAX_ARTIFACT_REFS": str(settings.rl_max_artifact_refs),
        }
    )
    return env


def cmd_init_db() -> None:
    store = RLDeveloperMemoryStore.from_env()
    store.initialize()
    print(
        json.dumps(
            {
                "status": "ok",
                "db_path": str(store.settings.db_path),
                "schema": store.schema_state().to_dict(),
            },
            indent=2,
        )
    )


def cmd_migrate_v2() -> None:
    store = RLDeveloperMemoryStore.from_env()
    state = store.migrate()
    print(
        json.dumps(
            {
                "status": "ok",
                "db_path": str(store.settings.db_path),
                "schema": state.to_dict(),
            },
            indent=2,
        )
    )


def cmd_schema_version() -> None:
    store = RLDeveloperMemoryStore.from_env()
    store.initialize()
    print(json.dumps({"status": "ok", "schema": store.schema_state().to_dict()}, indent=2))


def cmd_backup() -> None:
    manager = BackupManager.from_env()
    result = manager.create_backup()
    print(json.dumps(result.to_dict(), indent=2))


def cmd_list_backups(limit: int) -> None:
    manager = BackupManager.from_env()
    print(json.dumps({"backups": manager.list_backups(limit=limit)}, indent=2))


def cmd_verify_backup(path: str) -> None:
    manager = BackupManager.from_env()
    print(json.dumps(manager.verify_backup(path), indent=2))


def cmd_restore_backup(path: str, *, create_safety_backup: bool) -> None:
    manager = BackupManager.from_env()
    print(json.dumps(manager.restore_backup(path, create_safety_backup=create_safety_backup), indent=2))


def cmd_metrics(window_days: int) -> None:
    app = RLDeveloperMemoryApp()
    print(json.dumps(app.issue_metrics(window_days=window_days), indent=2))


def cmd_server_status() -> None:
    settings = Settings.from_env()
    print(json.dumps(read_server_lifecycle_status(settings).to_dict(), indent=2))


def _recommended_env(*, settings: Settings, mode: str, max_instances: int, profile: str = "default") -> dict[str, str]:
    if mode not in {"shadow", "active", "single"}:
        raise ValueError(f"unsupported rollout mode: {mode}")
    resolved_max = 1 if mode == "single" else (None if int(max_instances) <= 0 else max(int(max_instances), 1))
    env = {
        "RL_DEVELOPER_MEMORY_HOME": str(settings.rl_developer_memory_home),
        "RL_DEVELOPER_MEMORY_DB_PATH": str(settings.db_path),
        "RL_DEVELOPER_MEMORY_STATE_DIR": str(settings.state_dir),
        "RL_DEVELOPER_MEMORY_BACKUP_DIR": str(settings.backup_dir),
        "RL_DEVELOPER_MEMORY_LOG_DIR": str(settings.log_dir),
        "RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR": str(settings.server_lock_dir),
        "RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE": str(settings.server_duplicate_exit_code),
        "RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY": "1" if resolved_max is None else "0",
        "RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV": "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY",
        "RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY": "1" if resolved_max is None else "0",
        "RL_DEVELOPER_MEMORY_ENFORCE_SINGLE_MCP_INSTANCE": "0" if resolved_max is None or resolved_max > 1 else "1",
        "RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES": "0" if resolved_max is None else str(resolved_max),
        "RL_DEVELOPER_MEMORY_SERVER_ENFORCE_PARENT_SINGLETON": "1",
        "RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_IDLE_TIMEOUT_SECONDS": "0",
        "RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_MONITOR_INTERVAL_SECONDS": "1.0",
        "RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT": "1",
        "RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE": "1" if mode == "shadow" else "0",
        "RL_DEVELOPER_MEMORY_ENABLE_PREFERENCE_RULES": "1",
        "RL_DEVELOPER_MEMORY_ENABLE_REDACTION": "1",
        "RL_DEVELOPER_MEMORY_ENABLE_CALIBRATION_PROFILE": "1",
        "RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH": str(settings.calibration_profile_path),
        "RL_DEVELOPER_MEMORY_MATCH_ACCEPT_THRESHOLD": f"{settings.match_accept_threshold:.2f}",
        "RL_DEVELOPER_MEMORY_MATCH_WEAK_THRESHOLD": f"{settings.match_weak_threshold:.2f}",
        "RL_DEVELOPER_MEMORY_AMBIGUITY_MARGIN": f"{settings.ambiguity_margin:.2f}",
        "RL_DEVELOPER_MEMORY_DEFAULT_USER_SCOPE": settings.default_user_scope,
    }
    return _apply_rl_control_profile_env(env, settings=settings, profile=profile)


def _format_env_block(env: dict[str, str], *, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(env, indent=2, ensure_ascii=False, sort_keys=True)
    if fmt == "env":
        return "\n".join(f"export {key}={json.dumps(value)}" for key, value in env.items())
    if fmt == "toml":
        lines = ["[mcp_servers.rl_developer_memory.env]"]
        lines.extend(f"{key} = {json.dumps(value)}" for key, value in env.items())
        return "\n".join(lines)
    raise ValueError(f"unsupported format: {fmt}")


def cmd_recommended_config(mode: str, fmt: str, max_instances: int, profile: str = "default") -> None:
    settings = Settings.from_env()
    env = _recommended_env(settings=settings, mode=mode, max_instances=max_instances, profile=profile)
    rendered_max = env["RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES"]
    payload = {
        "mode": mode,
        "profile": profile,
        "max_instances": None if rendered_max == "0" else int(rendered_max),
        "format": fmt,
        "env": env,
        "rendered": _format_env_block(env, fmt=fmt),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _load_codex_config_metadata(codex_home: Path) -> dict[str, Any]:
    config_path = codex_home / "config.toml"
    if not config_path.exists():
        return {"config_path": str(config_path), "exists": False, "block_count": 0, "env": {}, "parse_error": None}
    raw = config_path.read_text(encoding="utf-8")
    block_count = len(re.findall(r"^\[mcp_servers\.rl_developer_memory\]\s*$", raw, flags=re.MULTILINE))
    env: dict[str, Any] = {}
    parse_error: str | None = None
    if tomllib is not None:
        try:
            parsed = tomllib.loads(raw)
            env = dict((parsed.get("mcp_servers", {}).get("rl_developer_memory", {}) or {}).get("env", {}) or {})
        except tomllib.TOMLDecodeError as exc:  # type: ignore[union-attr]
            parse_error = str(exc)
    else:
        env_match = re.search(r'\[mcp_servers\.rl_developer_memory\.env\]\s*(?P<body>(?:[A-Z0-9_]+\s*=\s*"[^"]*"\s*)+)', raw, flags=re.MULTILINE)
        if env_match is None:
            env_match = re.search(r"\[mcp_servers\.rl_developer_memory\].*?env\s*=\s*\{(?P<body>.*?)\}\s*$", raw, flags=re.DOTALL | re.MULTILINE)
        if env_match is not None:
            body = env_match.group("body")
            for key, value in re.findall(r'([A-Z0-9_]+)\s*=\s*"([^"]*)"', body):
                env[key] = value
        else:
            parse_error = "unable to parse rl_developer_memory env block without tomllib"
    return {
        "config_path": str(config_path),
        "exists": True,
        "block_count": block_count,
        "env": env,
        "parse_error": parse_error,
    }


def _check(name: str, ok: bool, detail: str, *, severity: str = "error") -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "severity": severity, "detail": detail}


def cmd_doctor(mode: str, max_instances: int, codex_home: str | None, profile: str = "default") -> None:
    settings = Settings.from_env()
    expected_env = _recommended_env(settings=settings, mode=mode, max_instances=max_instances, profile=profile)
    lifecycle = read_server_lifecycle_status(settings).to_dict()
    codex_path = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    config_meta = _load_codex_config_metadata(codex_path)
    checks: list[dict[str, Any]] = []
    checks.append(_check(
        "codex-config-exists",
        bool(config_meta["exists"]),
        "config.toml found" if config_meta["exists"] else f'missing: {config_meta["config_path"]}',
    ))
    if config_meta["exists"]:
        checks.append(_check(
            "single-rl-developer-memory-block",
            int(config_meta["block_count"]) == 1,
            f'found {config_meta["block_count"]} [mcp_servers.rl_developer_memory] block(s)',
        ))
        checks.append(_check(
            "config-parse",
            config_meta["parse_error"] is None,
            "parsed successfully" if config_meta["parse_error"] is None else str(config_meta["parse_error"]),
        ))
    env = config_meta.get("env", {}) or {}
    if env:
        base_keys = (
            "RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR",
            "RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE",
            "RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY",
            "RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV",
            "RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES",
            "RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT",
            "RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE",
            "RL_DEVELOPER_MEMORY_ENABLE_PREFERENCE_RULES",
            "RL_DEVELOPER_MEMORY_ENABLE_REDACTION",
            "RL_DEVELOPER_MEMORY_SERVER_ENFORCE_PARENT_SINGLETON",
            "RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_IDLE_TIMEOUT_SECONDS",
            "RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_MONITOR_INTERVAL_SECONDS",
        )
        rl_keys = (
            "RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL",
            "RL_DEVELOPER_MEMORY_DOMAIN_MODE",
            "RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT",
            "RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT",
            "RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION",
        ) if profile != "default" else ()
        for key in (*base_keys, *rl_keys):
            expected = expected_env.get(key, "")
            actual = str(env.get(key, ""))
            checks.append(_check(
                f"env:{key}",
                actual == expected,
                f"actual={actual!r}, expected={expected!r}",
                severity="warning" if key.endswith("SHADOW_MODE") else "error",
            ))
    expected_cap_raw = str(expected_env["RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES"])
    if expected_cap_raw == "0":
        checks.append(_check(
            "owner-key-required",
            str(env.get("RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY", "")) == "1",
            f"actual={env.get('RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY', '')!r}, expected='1'",
        ))
        active_slots = lifecycle.get("active_slots", []) or []
        ownerless = [slot.get("pid") for slot in active_slots if not str(slot.get("owner_key") or "").strip()]
        checks.append(_check(
            "active-slots-have-owner-keys",
            not ownerless,
            "all active slots have owner keys" if not ownerless else f"ownerless_pids={ownerless}",
            severity="warning",
        ))
    else:
        checks.append(_check(
            "instance-cap",
            int(lifecycle.get("active_count", 0) or 0) <= int(expected_cap_raw),
            f"active_count={lifecycle.get('active_count', 0)}, max_instances={expected_cap_raw}",
        ))
    checks.append(_check(
        "paths-exist",
        settings.rl_developer_memory_home.exists() and settings.state_dir.exists() and settings.backup_dir.exists(),
        f'home={settings.rl_developer_memory_home}, state={settings.state_dir}, backup={settings.backup_dir}',
    ))
    configured_db_path = str(env.get("RL_DEVELOPER_MEMORY_DB_PATH", settings.db_path))
    configured_db_posix = Path(configured_db_path).expanduser().as_posix().rstrip("/")
    checks.append(_check(
        "db-path-local-linux",
        not (configured_db_posix == "/mnt/c" or configured_db_posix.startswith("/mnt/c/")),
        f"path={configured_db_path!r}",
    ))
    checks.append(_check(
        "calibration-profile",
        settings.calibration_profile_path.exists(),
        f'path={settings.calibration_profile_path}',
        severity="warning",
    ))
    backup_manager = BackupManager.from_env()
    backups = backup_manager.list_backups(limit=1)
    if backups:
        created_raw = backups[0].get("created_at_utc") or backups[0].get("created_at")
        fresh = False
        if created_raw:
            try:
                created_at = datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
                fresh = created_at >= datetime.now(timezone.utc) - timedelta(days=7)
            except ValueError:
                fresh = False
        checks.append(_check("backup-freshness", fresh, f'latest_backup={created_raw}', severity="warning"))
    else:
        checks.append(_check("backup-freshness", False, "no backups found", severity="warning"))

    error_count = sum(1 for item in checks if not item["ok"] and item["severity"] == "error")
    warning_count = sum(1 for item in checks if not item["ok"] and item["severity"] != "error")
    status = "ok" if error_count == 0 and warning_count == 0 else ("warn" if error_count == 0 else "fail")
    payload = {
        "status": status,
        "mode": mode,
        "profile": profile,
        "expected_max_instances": None if expected_cap_raw == "0" else int(expected_cap_raw),
        "codex_home": str(codex_path),
        "server_status": lifecycle,
        "checks": checks,
        "summary": {"errors": error_count, "warnings": warning_count},
        "recommended_env": expected_env,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_prune_retention(telemetry_days: int, review_days: int) -> None:
    store = RLDeveloperMemoryStore.from_env()
    store.initialize()
    result = store.prune_operational_data(
        telemetry_retention_days=telemetry_days,
        resolved_review_retention_days=review_days,
    )
    print(json.dumps(result, indent=2))


def cmd_review_queue(status: str, limit: int) -> None:
    app = RLDeveloperMemoryApp()
    print(json.dumps(app.issue_review_queue(status=status, limit=limit), indent=2))


def cmd_resolve_review(review_id: int, decision: str, note: str) -> None:
    app = RLDeveloperMemoryApp()
    print(json.dumps(app.issue_review_resolve(review_id=review_id, decision=decision, note=note), indent=2))


def _configure_temp_environment(temp_dir: str) -> None:
    base = Path(temp_dir)
    os.environ["RL_DEVELOPER_MEMORY_HOME"] = str(base / "share")
    os.environ["RL_DEVELOPER_MEMORY_DB_PATH"] = str(base / "share" / "rl_developer_memory.sqlite3")
    os.environ["RL_DEVELOPER_MEMORY_STATE_DIR"] = str(base / "state")
    os.environ["RL_DEVELOPER_MEMORY_BACKUP_DIR"] = str(base / "share" / "backups")
    os.environ["RL_DEVELOPER_MEMORY_LOG_DIR"] = str(base / "state" / "log")


def _with_temp_rl_developer_memory(fn: Callable[[RLDeveloperMemoryApp], dict[str, Any]]) -> dict[str, Any]:
    env_backup = {key: os.environ.get(key) for key in _ENV_KEYS}
    try:
        with tempfile.TemporaryDirectory(prefix="rl-developer-memory-maint-") as temp_dir:
            _configure_temp_environment(temp_dir)
            app = RLDeveloperMemoryApp()
            return fn(app)
    finally:
        for key, value in env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _persist_report(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    store = RLDeveloperMemoryStore.from_env()
    store.initialize()
    report_path = store.save_report(name, payload)
    payload = dict(payload)
    payload["report_path"] = str(report_path)
    return payload


def cmd_smoke() -> None:
    def runner(app: RLDeveloperMemoryApp) -> dict[str, Any]:
        app.issue_record_resolution(
            title="Relative sqlite path breaks outside repo root",
            raw_error="FileNotFoundError: references/contractsDatabase.sqlite3",
            canonical_fix="Resolve the SQLite path relative to the module file instead of runtime cwd.",
            prevention_rule="No production file path may depend on runtime cwd.",
            project_scope="global",
            canonical_symptom="sqlite database path fails when the module is run from outside the repository root",
            verification_steps="Run the failing module from the repo root and from an external cwd.",
            tags="sqlite,path,cwd,repo-root",
            error_family="sqlite_error",
            root_cause_class="cwd_relative_path_bug",
            command="python -m app.main",
            file_path="services/db_loader.py",
            domain="python",
        )

        result = app.issue_match(
            error_text="FileNotFoundError: config/contractsDatabase.sqlite3 while running python -m app.main from another directory",
            command="python -m app.main",
            file_path="services/db_loader.py",
            project_scope="global",
            limit=3,
        )
        matches = result["matches"]
        assert matches, "Expected at least one match from smoke test"
        assert matches[0]["pattern_id"] >= 1, "Expected a valid pattern id"
        assert result["retrieval_event_id"] is not None, "Expected telemetry event id"
        return {"status": "ok", "top_match": matches[0], "retrieval_event_id": result["retrieval_event_id"]}

    print(json.dumps(_with_temp_rl_developer_memory(runner), indent=2))


def cmd_smoke_learning() -> None:
    def runner(app: RLDeveloperMemoryApp) -> dict[str, Any]:
        app.issue_record_resolution(
            title="Requests missing in API worker",
            raw_error="ModuleNotFoundError: No module named requests while starting API worker",
            canonical_fix="Install requests into the active environment used by the API worker.",
            prevention_rule="Pin and install runtime dependencies in the worker environment.",
            project_scope="global",
            canonical_symptom="requests import fails during api worker startup",
            verification_steps="Run the API worker import check inside the same environment.",
            tags="python,import,requests,api",
            error_family="import_error",
            root_cause_class="missing_python_module",
            command="python worker.py",
            file_path="api/worker.py",
            domain="python",
        )
        app.issue_record_resolution(
            title="Requests missing in CLI utility",
            raw_error="ImportError: cannot import name requests from CLI utility bootstrap",
            canonical_fix="Install requests into the environment used by the CLI entrypoint.",
            prevention_rule="Keep CLI dependencies synchronized with runtime requirements.",
            project_scope="global",
            canonical_symptom="requests import fails during cli bootstrap",
            verification_steps="Run the CLI import check inside the same environment.",
            tags="python,import,requests,cli",
            error_family="import_error",
            root_cause_class="missing_python_module",
            command="python cli.py",
            file_path="cli/bootstrap.py",
            domain="python",
        )

        first = app.issue_match(
            error_text="ModuleNotFoundError: No module named requests",
            project_scope="global",
            session_id="smoke-session",
            limit=3,
        )
        assert first["decision"]["status"] == "ambiguous", "Expected close candidates before feedback"
        first_top = first["matches"][0]["pattern_id"]

        feedback = app.issue_feedback(
            retrieval_event_id=int(first["retrieval_event_id"]),
            feedback_type="candidate_rejected",
            candidate_rank=1,
            notes="Synthetic smoke rejection",
        )
        assert feedback["resolved_candidate"]["pattern_id"] == first_top, "Feedback resolved wrong top candidate"

        second = app.issue_match(
            error_text="ModuleNotFoundError: No module named requests",
            project_scope="global",
            session_id="smoke-session",
            limit=3,
        )
        assert second["matches"][0]["pattern_id"] != first_top, "Rejected candidate should be demoted within session"

        verify = app.issue_feedback(
            retrieval_event_id=int(second["retrieval_event_id"]),
            feedback_type="fix_verified",
            candidate_rank=1,
            notes="Synthetic smoke verification",
        )
        snapshot = app.session_service.snapshot("smoke-session")
        return {
            "status": "ok",
            "initial_top_pattern_id": first_top,
            "reranked_top_pattern_id": second["matches"][0]["pattern_id"],
            "retrieval_event_ids": [first["retrieval_event_id"], second["retrieval_event_id"]],
            "session_memory": snapshot,
            "last_learning_update": verify["learning"],
        }

    print(json.dumps(_with_temp_rl_developer_memory(runner), indent=2))


def cmd_benchmark_user_domains() -> None:
    def runner(app: RLDeveloperMemoryApp) -> dict[str, Any]:
        seed_user_domain_memory(app)
        return run_user_domain_benchmark(app, repeats=20)

    print(json.dumps(_persist_report("benchmark_user_domains", _with_temp_rl_developer_memory(runner)), indent=2, ensure_ascii=False))


def _with_temp_rl_developer_memory_rl_control(fn: Callable[[RLDeveloperMemoryApp], dict[str, Any]], *, profile: str = "rl-control-shadow") -> dict[str, Any]:
    env_backup = {key: os.environ.get(key) for key in _ENV_KEYS}
    rl_keys = {
        "RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL": os.environ.get("RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL"),
        "RL_DEVELOPER_MEMORY_DOMAIN_MODE": os.environ.get("RL_DEVELOPER_MEMORY_DOMAIN_MODE"),
        "RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT": os.environ.get("RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT"),
        "RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT": os.environ.get("RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT"),
        "RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION": os.environ.get("RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION"),
    }
    try:
        with tempfile.TemporaryDirectory(prefix="rl-developer-memory-maint-rlc-") as temp_dir:
            _configure_temp_environment(temp_dir)
            os.environ["RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL"] = "1"
            os.environ["RL_DEVELOPER_MEMORY_DOMAIN_MODE"] = "hybrid" if profile == "rl-control-shadow" else "rl_control"
            os.environ["RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT"] = "1"
            os.environ["RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT"] = "1"
            os.environ["RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION"] = "1"
            app = RLDeveloperMemoryApp()
            return fn(app)
    finally:
        for key, value in env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        for key, value in rl_keys.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def cmd_benchmark_rl_control_reporting() -> None:
    def runner(app: RLDeveloperMemoryApp) -> dict[str, Any]:
        return run_rl_control_reporting_benchmark(app, repeats=3)

    print(json.dumps(_persist_report("benchmark_rl_control_reporting", _with_temp_rl_developer_memory_rl_control(runner)), indent=2, ensure_ascii=False))


def cmd_rl_audit_health(window_days: int, limit: int) -> None:
    store = RLDeveloperMemoryStore.from_env()
    store.initialize()
    print(json.dumps(store.rl_audit_health_summary(window_days=window_days, limit=limit), indent=2, ensure_ascii=False))


def cmd_benchmark_failure_taxonomy() -> None:
    def runner(app: RLDeveloperMemoryApp) -> dict[str, Any]:
        seed_user_domain_memory(app)
        return run_failure_taxonomy_benchmark(app, repeats=10)

    print(json.dumps(_persist_report("benchmark_failure_taxonomy", _with_temp_rl_developer_memory(runner)), indent=2, ensure_ascii=False))


def cmd_runtime_diagnostics() -> None:
    def runner(app: RLDeveloperMemoryApp) -> dict[str, Any]:
        return run_runtime_diagnostics(app, repeats=8)

    print(json.dumps(_persist_report("runtime_diagnostics", _with_temp_rl_developer_memory(runner)), indent=2, ensure_ascii=False))


def cmd_e2e_mcp_reuse_harness(timeout: float, *, json_output: bool) -> None:
    payload = run_e2e_mcp_reuse_harness(timeout=timeout)
    if json_output:
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(render_e2e_mcp_reuse_harness(payload))
    if not e2e_mcp_reuse_harness_succeeded(payload):
        raise SystemExit(1)


def cmd_benchmark_dense_bandit() -> None:
    def runner(app: RLDeveloperMemoryApp) -> dict[str, Any]:
        seed_dense_bandit_memory(app)
        return run_dense_bandit_benchmark(app, repeats=8)

    print(json.dumps(_persist_report("benchmark_dense_bandit", _with_temp_rl_developer_memory(runner)), indent=2, ensure_ascii=False))


def cmd_benchmark_real_world() -> None:
    def runner(app: RLDeveloperMemoryApp) -> dict[str, Any]:
        seed_real_world_memory(app)
        return run_real_world_eval(app, repeats=1)

    print(json.dumps(_persist_report("benchmark_real_world_eval", _with_temp_rl_developer_memory(runner)), indent=2, ensure_ascii=False))


def cmd_benchmark_hard_negatives() -> None:
    def runner(app: RLDeveloperMemoryApp) -> dict[str, Any]:
        seed_hard_negative_memory(app)
        return run_hard_negative_benchmark(app, repeats=1)

    print(json.dumps(_persist_report("benchmark_hard_negatives", _with_temp_rl_developer_memory(runner)), indent=2, ensure_ascii=False))


def cmd_benchmark_merge_stress() -> None:
    def runner(app: RLDeveloperMemoryApp) -> dict[str, Any]:
        return run_merge_correctness_stress(app)

    print(json.dumps(_persist_report("benchmark_merge_correctness_stress", _with_temp_rl_developer_memory(runner)), indent=2, ensure_ascii=False))


def cmd_calibrate_thresholds(write_profile: bool) -> None:
    def runner(app: RLDeveloperMemoryApp) -> dict[str, Any]:
        seed_real_world_memory(app)
        return run_threshold_calibration(app)

    report = _persist_report("threshold_calibration", _with_temp_rl_developer_memory(runner))
    if write_profile:
        store = RLDeveloperMemoryStore.from_env()
        store.initialize()
        profile_payload = {key: report[key] for key in ("version", "generated_at", "global", "families", "metrics", "datasets") if key in report}
        store.settings.calibration_profile_path.write_text(json.dumps(profile_payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        report["calibration_profile_path"] = str(store.settings.calibration_profile_path)
    print(json.dumps(report, indent=2, ensure_ascii=False))


def _render_dashboard_html(payload: dict[str, Any]) -> str:
    def block(title: str, content: Any) -> str:
        escaped = json.dumps(content, indent=2, ensure_ascii=False)
        return f"<section><h2>{title}</h2><pre>{escaped}</pre></section>"

    parts = [
        "<html><head><meta charset='utf-8'><title>RL Developer Memory Dashboard</title></head><body>",
        "<h1>RL Developer Memory Dashboard</h1>",
        block("metrics", payload.get("metrics", {})),
        block("calibration_profile", payload.get("calibration_profile", {})),
        block("reports", payload.get("reports", {})),
        "</body></html>",
    ]
    return "\n".join(parts)


def cmd_export_dashboard(output: str, fmt: str, window_days: int) -> None:
    store = RLDeveloperMemoryStore.from_env()
    store.initialize()
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "hostname": Settings.from_env().hostname,
        "metrics": store.metrics_summary(window_days=window_days),
        "calibration_profile": store.load_calibration_profile(),
        "reports": {
            item["name"]: store.load_saved_report(item["name"]) or item
            for item in store.list_saved_reports()[:8]
        },
    }
    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "html":
        output_path.write_text(_render_dashboard_html(payload), encoding="utf-8")
    else:
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": "ok", "format": fmt, "path": str(output_path)}, indent=2))

