"""Release validation, rollout readiness, and documentation synchronization checks."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "ValidationCommand",
    "build_validation_commands",
    "run_validation_matrix",
    "validate_docs_sync",
]

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
    "python scripts/release_readiness.py --json",
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

    mcp_surface_present = "- **MCP surface:**" in readme_text
    tool_count_match = re.search(r"MCP surface:\*\*\s*\*\*(\d+) tools\*\*", readme_text)
    tool_count_ok = mcp_surface_present and (
        tool_count_match is None or int(tool_count_match.group(1)) == len(tool_names)
    )
    checks.append(
        {
            "name": "readme-mcp-surface",
            "ok": tool_count_ok,
            "detail": (
                f"surface-present={mcp_surface_present}, count={tool_count_match.group(1) if tool_count_match else 'descriptive'}, "
                f"actual={len(tool_names)}"
            ),
        }
    )

    cli_surface_present = "- **Maintenance surface:**" in readme_text
    cli_count_match = re.search(r"Maintenance surface:\*\*\s*\*\*(\d+) CLI subcommands\*\*", readme_text)
    cli_count_ok = cli_surface_present and (
        cli_count_match is None or int(cli_count_match.group(1)) == len(cli_subcommands)
    )
    checks.append(
        {
            "name": "readme-cli-surface",
            "ok": cli_count_ok,
            "detail": (
                f"surface-present={cli_surface_present}, count={cli_count_match.group(1) if cli_count_match else 'descriptive'}, "
                f"actual={len(cli_subcommands)}"
            ),
        }
    )

    checks.extend(
        {"name": f"docs-command:{command}", "ok": command in combined_docs, "detail": command}
        for command in (*DOC_EXPECTED_CORE_COMMANDS, *DOC_EXPECTED_EXTENDED_COMMANDS)
    )

    checks.extend(
        {"name": f"docs-tool:{tool_name}", "ok": tool_name in combined_docs, "detail": tool_name}
        for tool_name in DOC_EXPECTED_MCP_TOOLS
    )

    checks.append(
        {
            "name": "docs-readme-links-validation-matrix",
            "ok": "VALIDATION_MATRIX.md" in docs_readme_text,
            "detail": "docs/README.md should link the rollout validation matrix document.",
        }
    )
    checks.extend(
        {"name": f"docs-policy-doc:{doc_name}", "ok": doc_name in docs_readme_text and doc_name in readme_text, "detail": doc_name}
        for doc_name in DOC_EXPECTED_POLICY_DOCS
    )

    checks.extend(
        {"name": f"docs-install-toggle:{snippet}", "ok": snippet in installation_text or snippet in readme_text, "detail": snippet}
        for snippet in DOC_EXPECTED_INSTALL_TOGGLES
    )

    checks.extend(
        {"name": f"docs-register-rollout:{snippet}", "ok": snippet in combined_docs, "detail": snippet}
        for snippet in DOC_EXPECTED_REGISTER_FLAGS
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

