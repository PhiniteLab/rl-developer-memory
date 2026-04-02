from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .backup import BackupManager
from .maintenance import build_parser
from .storage import RLDeveloperMemoryStore


@dataclass(frozen=True, slots=True)
class ValidationCommand:
    """A single validation or rollout-readiness command."""

    key: str
    label: str
    command: tuple[str, ...]
    category: str
    required: bool = True
    produces_json: bool = False


CORE_COMMAND_KEYS = (
    "ruff",
    "pyright",
    "pytest",
    "maintenance_smoke",
    "build",
)

EXTENDED_COMMAND_KEYS = (
    "maintenance_smoke_learning",
    "doctor_shadow_max0",
    "doctor_shadow_rl_control",
    "e2e_mcp_reuse_harness",
    "benchmark_rl_control_reporting",
)

DOC_EXPECTED_CORE_COMMANDS = (
    "ruff check .",
    "pyright",
    "python -m pytest",
    "python -m rl_developer_memory.maintenance smoke",
    "python -m build",
)

DOC_EXPECTED_EXTENDED_COMMANDS = (
    "python -m rl_developer_memory.maintenance smoke-learning",
    "python -m rl_developer_memory.maintenance doctor --mode shadow --max-instances 0",
    "python -m rl_developer_memory.maintenance doctor --mode shadow --profile rl-control-shadow",
    "python -m rl_developer_memory.maintenance e2e-mcp-reuse-harness --json",
    "python -m rl_developer_memory.maintenance benchmark-rl-control-reporting",
    "python scripts/release_acceptance.py --json",
    "python scripts/rl_quality_gate.py --json",
    "python scripts/validate_theory_code_sync.py",
    "python scripts/run_rl_backbone_smoke.py",
    "python scripts/install_skill.py --mode copy",
)

DOC_EXPECTED_MCP_TOOLS = (
    "issue_match",
    "issue_get",
    "issue_search",
    "issue_recent",
    "issue_record_resolution",
    "issue_feedback",
    "issue_set_preference",
    "issue_list_preferences",
    "issue_guardrails",
    "issue_metrics",
    "issue_review_queue",
    "issue_review_resolve",
)

INVALID_DOC_SNIPPETS = (
    "rl-developer-memory-maint resolve-review 17 accept",
    "python -m rl_developer_memory.maintenance resolve-review 17 accept",
)

DEFAULT_REVIEW_BACKLOG_LIMIT = 10

DOC_EXPECTED_INSTALL_TOGGLES = (
    "ENABLE_RL_CONTROL=1",
    "RL_ROLLOUT_MODE=shadow|active",
    "SKIP_DEP_INSTALL=1",
    "REQUIRE_CRON_INSTALL=1",
)

DOC_EXPECTED_REGISTER_FLAGS = (
    "--enable-rl-control",
    "--rl-rollout-mode shadow",
    "--rl-rollout-mode active",
    "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY",
)

DOC_EXPECTED_POLICY_DOCS = (
    "RL_CODING_STANDARDS.md",
    "MEMORY_SCOPE_OPERATIONS_NOTE.md",
    "RL_QUALITY_GATE.md",
    "SKILL_INSTALL_SYNC.md",
)

MINIMUM_STRUCTURE_PATHS = (
    "src/rl_developer_memory/algorithms",
    "src/rl_developer_memory/agents",
    "src/rl_developer_memory/envs",
    "src/rl_developer_memory/networks",
    "src/rl_developer_memory/buffers",
    "src/rl_developer_memory/trainers",
    "src/rl_developer_memory/evaluation",
    "src/rl_developer_memory/experiments",
    "src/rl_developer_memory/theory",
    "src/rl_developer_memory/callbacks",
    "src/rl_developer_memory/utils",
    "configs",
    "scripts",
    "docs",
    "tests/unit",
    "tests/integration",
    "tests/smoke",
    "tests/regression",
)

MINIMUM_QUALITY_TEST_SENTINELS = {
    "deterministic_behavior": (
        "tests/regression/test_seed_determinism.py",
        "tests/unit/test_training_stability_components.py",
    ),
    "checkpoint_reload": (
        "tests/regression/test_checkpoint_resume_regression.py",
        "tests/integration/test_trainer_checkpoint_resume_flow.py",
    ),
    "config_validation": (
        "tests/unit/test_config_schemas.py",
    ),
    "theorem_to_code": (
        "tests/regression/test_theorem_code_sync_regression.py",
        "scripts/validate_theory_code_sync.py",
    ),
}


def _resolve_executable(name: str, python_bin: str) -> str:
    """Resolve a tool from PATH or next to the selected Python interpreter."""

    if shutil.which(name):
        return name
    sibling = Path(python_bin).resolve().parent / name
    if sibling.exists():
        return str(sibling)
    return name


def build_validation_commands(
    *,
    python_bin: str,
    include_core: bool = True,
    include_extended: bool = True,
    codex_home: Path | None = None,
) -> list[ValidationCommand]:
    """Return the standardized validation matrix command list."""

    commands: list[ValidationCommand] = []
    if include_core:
        commands.extend(
            [
                ValidationCommand(
                    key="ruff",
                    label="ruff check .",
                    command=(_resolve_executable("ruff", python_bin), "check", "."),
                    category="core",
                ),
                ValidationCommand(
                    key="pyright",
                    label="pyright",
                    command=(_resolve_executable("pyright", python_bin),),
                    category="core",
                ),
                ValidationCommand(
                    key="pytest",
                    label="python -m pytest",
                    command=(python_bin, "-m", "pytest"),
                    category="core",
                ),
                ValidationCommand(
                    key="maintenance_smoke",
                    label="python -m rl_developer_memory.maintenance smoke",
                    command=(python_bin, "-m", "rl_developer_memory.maintenance", "smoke"),
                    category="core",
                ),
                ValidationCommand(
                    key="build",
                    label="python -m build",
                    command=(python_bin, "-m", "build"),
                    category="core",
                ),
            ]
        )
    if include_extended:
        commands.extend(
            [
                ValidationCommand(
                    key="maintenance_smoke_learning",
                    label="python -m rl_developer_memory.maintenance smoke-learning",
                    command=(python_bin, "-m", "rl_developer_memory.maintenance", "smoke-learning"),
                    category="extended",
                ),
                ValidationCommand(
                    key="doctor_shadow_max0",
                    label="python -m rl_developer_memory.maintenance doctor --mode shadow --max-instances 0",
                    command=(
                        python_bin,
                        "-m",
                        "rl_developer_memory.maintenance",
                        "doctor",
                        "--mode",
                        "shadow",
                        "--max-instances",
                        "0",
                        *(("--codex-home", str(codex_home)) if codex_home is not None else ()),
                    ),
                    category="extended",
                    produces_json=True,
                ),
                ValidationCommand(
                    key="doctor_shadow_rl_control",
                    label="python -m rl_developer_memory.maintenance doctor --mode shadow --profile rl-control-shadow",
                    command=(
                        python_bin,
                        "-m",
                        "rl_developer_memory.maintenance",
                        "doctor",
                        "--mode",
                        "shadow",
                        "--max-instances",
                        "0",
                        *(("--codex-home", str(codex_home)) if codex_home is not None else ()),
                        "--profile",
                        "rl-control-shadow",
                    ),
                    category="extended",
                    produces_json=True,
                ),
                ValidationCommand(
                    key="e2e_mcp_reuse_harness",
                    label="python -m rl_developer_memory.maintenance e2e-mcp-reuse-harness --json",
                    command=(python_bin, "-m", "rl_developer_memory.maintenance", "e2e-mcp-reuse-harness", "--json"),
                    category="extended",
                    produces_json=True,
                ),
                ValidationCommand(
                    key="benchmark_rl_control_reporting",
                    label="python -m rl_developer_memory.maintenance benchmark-rl-control-reporting",
                    command=(python_bin, "-m", "rl_developer_memory.maintenance", "benchmark-rl-control-reporting"),
                    category="extended",
                    produces_json=True,
                ),
            ]
        )
    return commands


def _redacted_summary(stdout: str, stderr: str, *, limit: int = 240) -> str:
    """Return a compact, path-light summary snippet without full logs."""

    combined = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
    if not combined:
        return ""
    normalized = re.sub(r"/home/[^\s]+", "<home-path>", combined)
    normalized = re.sub(r"/mnt/c/[^\s]+", "<windows-mount-path>", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized[:limit]


def _bootstrap_validation_environment(repo_root: Path, python_bin: str) -> tuple[tempfile.TemporaryDirectory[str], dict[str, str], Path]:
    """Create a disposable Linux/WSL-safe runtime for rollout validation."""

    temp_dir = tempfile.TemporaryDirectory(prefix="rl-developer-memory-release-acceptance-")
    base = Path(temp_dir.name)
    share = base / "share"
    state = base / "state"
    backups = share / "backups"
    log_dir = state / "log"
    codex_home = base / ".codex"
    for path in (share, state, backups, log_dir, codex_home):
        path.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env.update(
        {
            "RL_DEVELOPER_MEMORY_HOME": str(share),
            "RL_DEVELOPER_MEMORY_DB_PATH": str(share / "rl_developer_memory.sqlite3"),
            "RL_DEVELOPER_MEMORY_STATE_DIR": str(state),
            "RL_DEVELOPER_MEMORY_BACKUP_DIR": str(backups),
            "RL_DEVELOPER_MEMORY_LOG_DIR": str(log_dir),
            "PYTHONPATH": str(repo_root / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""),
        }
    )

    backup = {key: os.environ.get(key) for key in env if key.startswith("RL_DEVELOPER_MEMORY_")}
    try:
        os.environ.update({key: value for key, value in env.items() if key.startswith("RL_DEVELOPER_MEMORY_")})
        RLDeveloperMemoryStore.from_env().initialize()
        (state / "calibration_profile.json").write_text(
            json.dumps({"global": {"accept_threshold": 0.68, "weak_threshold": 0.40, "ambiguity_margin": 0.09}}),
            encoding="utf-8",
        )
        BackupManager.from_env().create_backup()
    finally:
        for key, value in backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    subprocess.run(
        [
            python_bin,
            "scripts/register_codex.py",
            "--install-root",
            str(repo_root),
            "--data-root",
            str(share),
            "--state-root",
            str(state),
            "--codex-home",
            str(codex_home),
            "--enable-rl-control",
            "--rl-rollout-mode",
            "shadow",
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return temp_dir, env, codex_home


def run_validation_matrix(
    repo_root: Path,
    *,
    python_bin: str,
    include_core: bool = True,
    include_extended: bool = True,
) -> dict[str, Any]:
    """Execute the standardized validation matrix and collect structured results."""

    results: list[dict[str, Any]] = []
    overall_passed = True
    temp_dir, env, codex_home = _bootstrap_validation_environment(repo_root, python_bin)
    try:
        for step in build_validation_commands(
            python_bin=python_bin,
            include_core=include_core,
            include_extended=include_extended,
            codex_home=codex_home,
        ):
            started = time.monotonic()
            proc = subprocess.run(
                step.command,
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            duration = round(time.monotonic() - started, 3)
            payload: dict[str, Any] | None = None
            if step.produces_json and proc.stdout.strip():
                try:
                    payload = json.loads(proc.stdout)
                except json.JSONDecodeError:
                    payload = None
            status = "passed" if proc.returncode == 0 else "failed"
            overall_passed = overall_passed and status == "passed"
            results.append(
                {
                    "key": step.key,
                    "label": step.label,
                    "category": step.category,
                    "required": step.required,
                    "status": status,
                    "returncode": proc.returncode,
                    "duration_sec": duration,
                    "summary": _redacted_summary(proc.stdout, proc.stderr),
                    "payload": payload,
                }
            )
    finally:
        temp_dir.cleanup()

    return {
        "repo_root": str(repo_root),
        "python_bin": python_bin,
        "temporary_codex_home": str(codex_home),
        "overall_status": "passed" if overall_passed else "failed",
        "results": results,
    }


def _extract_mcp_tool_names(server_path: Path) -> list[str]:
    module = ast.parse(server_path.read_text(encoding="utf-8"))
    tool_names: list[str] = []
    for node in module.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if any(
            isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "tool"
            for dec in node.decorator_list
        ):
            tool_names.append(node.name)
    return tool_names


def _extract_cli_subcommands() -> list[str]:
    parser = build_parser()
    subcommands: list[str] = []
    for action in parser._actions:  # pragma: no cover - exercised indirectly in tests
        if isinstance(action, argparse._SubParsersAction):
            subcommands.extend(sorted(action.choices.keys()))
    return sorted(subcommands)


def validate_docs_sync(repo_root: Path) -> dict[str, Any]:
    """Check doc/code/CLI/MCP surface synchronization for the public rollout contract."""

    readme_path = repo_root / "README.md"
    usage_path = repo_root / "docs" / "USAGE.md"
    development_path = repo_root / "docs" / "DEVELOPMENT.md"
    operations_path = repo_root / "docs" / "OPERATIONS.md"
    installation_path = repo_root / "docs" / "INSTALLATION.md"
    rollout_path = repo_root / "docs" / "ROLLOUT.md"
    policy_path = repo_root / "docs" / "MCP_RL_INTEGRATION_POLICY.md"
    coding_standards_path = repo_root / "docs" / "RL_CODING_STANDARDS.md"
    memory_note_path = repo_root / "docs" / "MEMORY_SCOPE_OPERATIONS_NOTE.md"
    quality_gate_path = repo_root / "docs" / "RL_QUALITY_GATE.md"
    docs_readme_path = repo_root / "docs" / "README.md"
    validation_doc_path = repo_root / "docs" / "VALIDATION_MATRIX.md"
    agents_path = repo_root / "AGENTS.md"
    server_path = repo_root / "src" / "rl_developer_memory" / "server.py"

    readme_text = readme_path.read_text(encoding="utf-8")
    usage_text = usage_path.read_text(encoding="utf-8")
    development_text = development_path.read_text(encoding="utf-8")
    operations_text = operations_path.read_text(encoding="utf-8")
    installation_text = installation_path.read_text(encoding="utf-8") if installation_path.exists() else ""
    rollout_text = rollout_path.read_text(encoding="utf-8") if rollout_path.exists() else ""
    policy_text = policy_path.read_text(encoding="utf-8")
    coding_standards_text = coding_standards_path.read_text(encoding="utf-8") if coding_standards_path.exists() else ""
    memory_note_text = memory_note_path.read_text(encoding="utf-8") if memory_note_path.exists() else ""
    quality_gate_text = quality_gate_path.read_text(encoding="utf-8") if quality_gate_path.exists() else ""
    docs_readme_text = docs_readme_path.read_text(encoding="utf-8")
    validation_doc_text = validation_doc_path.read_text(encoding="utf-8") if validation_doc_path.exists() else ""
    agents_text = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
    combined_docs = "\n".join(
        (
            readme_text,
            usage_text,
            development_text,
            operations_text,
            installation_text,
            rollout_text,
            policy_text,
            coding_standards_text,
            memory_note_text,
            quality_gate_text,
            docs_readme_text,
            validation_doc_text,
            agents_text,
        )
    )

    tool_names = _extract_mcp_tool_names(server_path)
    cli_subcommands = _extract_cli_subcommands()

    checks: list[dict[str, Any]] = []

    tool_count_match = re.search(r"MCP surface:\*\*\s*\*\*(\d+) tools\*\*", readme_text)
    tool_count_ok = tool_count_match is not None and int(tool_count_match.group(1)) == len(tool_names)
    checks.append(
        {
            "name": "readme-mcp-tool-count",
            "ok": tool_count_ok,
            "detail": f"readme={tool_count_match.group(1) if tool_count_match else 'missing'}, actual={len(tool_names)}",
        }
    )

    cli_count_match = re.search(r"Maintenance surface:\*\*\s*\*\*(\d+) CLI subcommands\*\*", readme_text)
    cli_count_ok = cli_count_match is not None and int(cli_count_match.group(1)) == len(cli_subcommands)
    checks.append(
        {
            "name": "readme-cli-count",
            "ok": cli_count_ok,
            "detail": f"readme={cli_count_match.group(1) if cli_count_match else 'missing'}, actual={len(cli_subcommands)}",
        }
    )

    for command in (*DOC_EXPECTED_CORE_COMMANDS, *DOC_EXPECTED_EXTENDED_COMMANDS):
        checks.append(
            {
                "name": f"docs-command:{command}",
                "ok": command in combined_docs,
                "detail": command,
            }
        )

    for tool_name in DOC_EXPECTED_MCP_TOOLS:
        checks.append(
            {
                "name": f"docs-tool:{tool_name}",
                "ok": tool_name in combined_docs,
                "detail": tool_name,
            }
        )

    checks.append(
        {
            "name": "docs-readme-links-validation-matrix",
            "ok": "VALIDATION_MATRIX.md" in docs_readme_text,
            "detail": "docs/README.md should link the rollout validation matrix document.",
        }
    )
    for doc_name in DOC_EXPECTED_POLICY_DOCS:
        checks.append(
            {
                "name": f"docs-policy-doc:{doc_name}",
                "ok": doc_name in docs_readme_text and doc_name in readme_text,
                "detail": doc_name,
            }
        )

    for snippet in DOC_EXPECTED_INSTALL_TOGGLES:
        checks.append(
            {
                "name": f"docs-install-toggle:{snippet}",
                "ok": snippet in installation_text or snippet in readme_text,
                "detail": snippet,
            }
        )

    for snippet in DOC_EXPECTED_REGISTER_FLAGS:
        checks.append(
            {
                "name": f"docs-register-rollout:{snippet}",
                "ok": snippet in combined_docs,
                "detail": snippet,
            }
        )
    checks.append(
        {
            "name": "docs-invalid-resolve-review-example",
            "ok": not any(snippet in combined_docs for snippet in INVALID_DOC_SNIPPETS),
            "detail": "docs must use approve/reject/archive for resolve-review decisions.",
        }
    )

    ok = all(bool(item["ok"]) for item in checks)
    return {
        "status": "passed" if ok else "failed",
        "mcp_tool_count": len(tool_names),
        "maintenance_subcommand_count": len(cli_subcommands),
        "mcp_tools": tool_names,
        "maintenance_subcommands": cli_subcommands,
        "checks": checks,
    }


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
