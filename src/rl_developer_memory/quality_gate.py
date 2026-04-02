from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .release_acceptance import generate_release_acceptance_report

REQUIRED_STRUCTURE: dict[str, tuple[str, ...]] = {
    "src_package": (
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
    ),
    "project_scaffolding": (
        "configs",
        "scripts",
        "docs",
        "tests/unit",
        "tests/integration",
        "tests/smoke",
        "tests/regression",
    ),
}

REQUIRED_MEMORY_HYGIENE_SNIPPETS: dict[str, tuple[str, ...]] = {
    "AGENTS.md": (
        "issue_match",
        "issue_feedback",
        "issue_record_resolution",
        "project_scope",
        "user_scope",
        "redacted",
    ),
    "docs/MCP_RL_INTEGRATION_POLICY.md": (
        "issue_match",
        "issue_get",
        "issue_guardrails",
        "issue_feedback",
        "issue_record_resolution",
        "project_scope",
        "global",
        "user_scope",
        "redacted",
    ),
}

LOGGING_AND_METRICS_FILES: tuple[str, ...] = (
    "src/rl_developer_memory/experiments/metrics.py",
    "src/rl_developer_memory/utils/diagnostics.py",
    "src/rl_developer_memory/callbacks/base.py",
)

DETERMINISM_TESTS: tuple[str, ...] = (
    "tests/regression/test_seed_determinism.py",
    "tests/unit/test_training_stability_components.py",
)

CHECKPOINT_TESTS: tuple[str, ...] = (
    "tests/regression/test_checkpoint_resume_regression.py",
    "tests/integration/test_trainer_checkpoint_resume_flow.py",
    "tests/integration/test_trainer_runtime_recovery.py",
)

CONFIG_VALIDATION_TESTS: tuple[str, ...] = (
    "tests/unit/test_config_schemas.py",
    "configs/rl_backbone.shadow.json",
    "configs/rl_backbone.shadow.toml",
)

THEORY_SYNC_ARTIFACTS: tuple[str, ...] = (
    "scripts/validate_theory_code_sync.py",
    "tests/regression/test_theorem_code_sync_regression.py",
    "docs/theory_to_code.md",
)

QUALITY_GATE_LABELS: tuple[tuple[str, str], ...] = (
    ("repository_structure_compliance", "repository structure compliance"),
    ("import_compile_safety", "import/compile safety"),
    ("typing_discipline", "typing discipline"),
    ("lint_discipline", "lint discipline"),
    ("unit_tests", "unit tests"),
    ("smoke_tests", "smoke tests"),
    ("short_runtime_tests", "kısa runtime tests"),
    ("deterministic_behavior_checks", "deterministic behavior checks"),
    ("checkpoint_reload_checks", "checkpoint/reload checks"),
    ("config_validation", "config validation"),
    ("logging_metrics_minimum_standard", "logging/metrics minimum standardı"),
    ("docs_sync", "docs sync"),
    ("theorem_to_code_sync", "theorem-to-code sync"),
    ("mcp_memory_write_back_hygiene", "MCP memory write-back hygiene"),
    ("rollout_safety_checks", "rollout safety checks"),
)


def _redacted_summary(stdout: str, stderr: str, *, limit: int = 280) -> str:
    combined = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
    if not combined:
        return ""
    normalized = combined.replace(str(Path.home()), "<home-path>")
    normalized = normalized.replace("/mnt/c/", "<windows-mount-path>/")
    normalized = " ".join(normalized.split())
    return normalized[:limit]


def _path_status(repo_root: Path, paths: tuple[str, ...]) -> tuple[bool, list[str], list[str]]:
    present: list[str] = []
    missing: list[str] = []
    for relative in paths:
        target = repo_root / relative
        if target.exists():
            present.append(relative)
        else:
            missing.append(relative)
    return not missing, present, missing


def _run_aux_command(repo_root: Path, *, python_bin: str, label: str, command: tuple[str, ...]) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run(
        command,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "label": label,
        "command": list(command),
        "status": "passed" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        "summary": _redacted_summary(proc.stdout, proc.stderr),
    }


def _build_check(*, name: str, passed: bool, evidence: dict[str, Any], target: str, remediation: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": "passed" if passed else "failed",
        "evidence": evidence,
        "target_acceptance_criteria": target,
        "remediation": remediation,
    }


def evaluate_repository_structure(repo_root: Path) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    overall_ok = True
    for group_name, paths in REQUIRED_STRUCTURE.items():
        ok, present, missing = _path_status(repo_root, paths)
        overall_ok = overall_ok and ok
        groups[group_name] = {"present": present, "missing": missing}
    return _build_check(
        name="repository structure compliance",
        passed=overall_ok,
        evidence=groups,
        target="Required RL package folders plus configs/, scripts/, docs/, and tiered tests/ directories all exist.",
        remediation="Create any missing RL package or test-layer directories before accepting repository-level RL work.",
    )


def evaluate_memory_hygiene(repo_root: Path) -> dict[str, Any]:
    file_checks: dict[str, Any] = {}
    overall_ok = True
    for relative, snippets in REQUIRED_MEMORY_HYGIENE_SNIPPETS.items():
        text = (repo_root / relative).read_text(encoding="utf-8")
        present = [snippet for snippet in snippets if snippet in text]
        missing = [snippet for snippet in snippets if snippet not in text]
        ok = not missing
        overall_ok = overall_ok and ok
        file_checks[relative] = {"present": present, "missing": missing}
    return _build_check(
        name="MCP memory write-back hygiene",
        passed=overall_ok,
        evidence=file_checks,
        target="Repo contracts explicitly require scoped, redacted, verified-only memory writes and expose issue_match/feedback/record_resolution workflow.",
        remediation="Update AGENTS/docs to restore scoped memory, redaction, and verified-only write-back rules before accepting RL outputs.",
    )


def generate_professional_quality_gate_report(
    repo_root: Path,
    *,
    python_bin: str,
) -> dict[str, Any]:
    release = generate_release_acceptance_report(repo_root, python_bin=python_bin, include_core=True, include_extended=True)
    matrix = release["validation_matrix"]
    docs_sync = release["docs_sync"]
    readiness = release["rollout_readiness"]
    by_key = {item["key"]: item for item in matrix.get("results", [])}

    theory_sync = _run_aux_command(
        repo_root,
        python_bin=python_bin,
        label="python scripts/validate_theory_code_sync.py",
        command=(python_bin, "scripts/validate_theory_code_sync.py"),
    )
    backbone_smoke = _run_aux_command(
        repo_root,
        python_bin=python_bin,
        label="python scripts/run_rl_backbone_smoke.py",
        command=(python_bin, "scripts/run_rl_backbone_smoke.py"),
    )
    import_probe = _run_aux_command(
        repo_root,
        python_bin=python_bin,
        label="python -c import probe",
        command=(
            python_bin,
            "-c",
            "import rl_developer_memory; import rl_developer_memory.experiments.runner; import rl_developer_memory.trainers.pipeline; import rl_developer_memory.theory.registry; print('import-ok')",
        ),
    )

    unit_files = sorted(str(path.relative_to(repo_root)) for path in (repo_root / "tests" / "unit").glob("test_*.py"))
    smoke_files = sorted(str(path.relative_to(repo_root)) for path in (repo_root / "tests" / "smoke").glob("test_*.py"))

    lint_ok = by_key.get("ruff", {}).get("status") == "passed"
    typing_ok = by_key.get("pyright", {}).get("status") == "passed"
    pytest_ok = by_key.get("pytest", {}).get("status") == "passed"
    smoke_ok = by_key.get("maintenance_smoke", {}).get("status") == "passed"
    smoke_learning_ok = by_key.get("maintenance_smoke_learning", {}).get("status") == "passed"
    build_ok = by_key.get("build", {}).get("status") == "passed"
    benchmark_ok = by_key.get("benchmark_rl_control_reporting", {}).get("status") == "passed"

    determinism_ok, determinism_present, determinism_missing = _path_status(repo_root, DETERMINISM_TESTS)
    checkpoint_ok, checkpoint_present, checkpoint_missing = _path_status(repo_root, CHECKPOINT_TESTS)
    config_ok, config_present, config_missing = _path_status(repo_root, CONFIG_VALIDATION_TESTS)
    metrics_ok, metrics_present, metrics_missing = _path_status(repo_root, LOGGING_AND_METRICS_FILES)
    theory_paths_ok, theory_present, theory_missing = _path_status(repo_root, THEORY_SYNC_ARTIFACTS)

    checklist = {
        "repository_structure_compliance": evaluate_repository_structure(repo_root),
        "import_compile_safety": _build_check(
            name="import/compile safety",
            passed=bool(import_probe["status"] == "passed" and build_ok),
            evidence={
                "import_probe": import_probe,
                "build": by_key.get("build", {}),
            },
            target="Representative package imports succeed and python -m build completes without failure.",
            remediation="Repair package import paths, editable install assumptions, or packaging metadata until import probe and build both pass.",
        ),
        "typing_discipline": _build_check(
            name="typing discipline",
            passed=typing_ok,
            evidence={"pyright": by_key.get("pyright", {})},
            target="pyright passes without errors on the repository's typed surfaces.",
            remediation="Resolve static typing errors before accepting RL deliverables.",
        ),
        "lint_discipline": _build_check(
            name="lint discipline",
            passed=lint_ok,
            evidence={"ruff": by_key.get("ruff", {})},
            target="ruff check . passes cleanly.",
            remediation="Fix lint/import-order/style violations before acceptance.",
        ),
        "unit_tests": _build_check(
            name="unit tests",
            passed=bool(pytest_ok and unit_files),
            evidence={"pytest": by_key.get("pytest", {}), "unit_test_files": unit_files},
            target="A non-empty unit test layer exists and full pytest passes.",
            remediation="Add or repair focused unit tests until the unit layer exists and full pytest passes.",
        ),
        "smoke_tests": _build_check(
            name="smoke tests",
            passed=bool(smoke_ok and smoke_files),
            evidence={"maintenance_smoke": by_key.get("maintenance_smoke", {}), "smoke_test_files": smoke_files},
            target="Smoke test coverage exists and maintenance smoke passes.",
            remediation="Add or fix lightweight smoke coverage and restore maintenance smoke before acceptance.",
        ),
        "short_runtime_tests": _build_check(
            name="kısa runtime tests",
            passed=bool(smoke_learning_ok and backbone_smoke["status"] == "passed"),
            evidence={
                "maintenance_smoke_learning": by_key.get("maintenance_smoke_learning", {}),
                "rl_backbone_smoke": backbone_smoke,
            },
            target="Short RL runtime checks pass for both maintenance smoke-learning and backbone smoke execution.",
            remediation="Repair short-run RL execution paths until both maintenance smoke-learning and backbone smoke complete successfully.",
        ),
        "deterministic_behavior_checks": _build_check(
            name="deterministic behavior checks",
            passed=bool(pytest_ok and determinism_ok),
            evidence={"determinism_tests_present": determinism_present, "missing": determinism_missing, "pytest": by_key.get("pytest", {})},
            target="Dedicated determinism tests exist and are covered by a passing pytest run.",
            remediation="Add or repair deterministic-seed checks before accepting RL training changes.",
        ),
        "checkpoint_reload_checks": _build_check(
            name="checkpoint/reload checks",
            passed=bool(pytest_ok and checkpoint_ok),
            evidence={"checkpoint_tests_present": checkpoint_present, "missing": checkpoint_missing, "pytest": by_key.get("pytest", {})},
            target="Checkpoint, resume, and recovery tests exist and are covered by a passing pytest run.",
            remediation="Add or repair checkpoint/reload/resume coverage before accepting RL runtime changes.",
        ),
        "config_validation": _build_check(
            name="config validation",
            passed=bool(pytest_ok and config_ok),
            evidence={"config_validation_artifacts": config_present, "missing": config_missing, "pytest": by_key.get("pytest", {})},
            target="Config schema tests and example configs exist and are validated by pytest.",
            remediation="Restore config schemas/examples and their tests before acceptance.",
        ),
        "logging_metrics_minimum_standard": _build_check(
            name="logging/metrics minimum standardı",
            passed=bool(metrics_ok and benchmark_ok),
            evidence={
                "metrics_files": metrics_present,
                "missing": metrics_missing,
                "benchmark_rl_control_reporting": by_key.get("benchmark_rl_control_reporting", {}),
            },
            target="Runtime diagnostics/metrics modules exist and RL reporting benchmark passes with metrics present.",
            remediation="Restore diagnostics/metrics surfaces and benchmark completeness before acceptance.",
        ),
        "docs_sync": _build_check(
            name="docs sync",
            passed=docs_sync.get("status") == "passed",
            evidence=docs_sync,
            target="Public docs stay synchronized with CLI commands, MCP tool names, and validation surfaces.",
            remediation="Fix docs drift until validate_docs_sync passes.",
        ),
        "theorem_to_code_sync": _build_check(
            name="theorem-to-code sync",
            passed=bool(theory_paths_ok and theory_sync["status"] == "passed"),
            evidence={"theory_artifacts": theory_present, "missing": theory_missing, "theory_sync_command": theory_sync},
            target="Theory mapping docs/artifacts exist and validate_theory_code_sync.py passes.",
            remediation="Repair theorem/code anchors or docs until theory sync validation passes.",
        ),
        "mcp_memory_write_back_hygiene": evaluate_memory_hygiene(repo_root),
        "rollout_safety_checks": _build_check(
            name="rollout safety checks",
            passed=readiness.get("codebase_readiness") == "passed",
            evidence={
                "rollout_readiness": readiness,
                "doctor_shadow_max0": by_key.get("doctor_shadow_max0", {}),
                "doctor_shadow_rl_control": by_key.get("doctor_shadow_rl_control", {}),
                "e2e_mcp_reuse_harness": by_key.get("e2e_mcp_reuse_harness", {}),
                "benchmark_rl_control_reporting": by_key.get("benchmark_rl_control_reporting", {}),
            },
            target="Shadow doctors are clean, reuse semantics are proven, RL reporting benchmark is stable, and docs sync passes. Active rollout may still remain no-go until live signoff.",
            remediation="Repair shadow posture, owner-key reuse, reporting, or docs-sync issues before calling the repo rollout-safe.",
        ),
    }

    failed_items = [key for key, item in checklist.items() if item["status"] != "passed"]
    return {
        "repo_root": str(repo_root),
        "python_bin": python_bin,
        "release_acceptance": release,
        "auxiliary_commands": {
            "theory_sync": theory_sync,
            "rl_backbone_smoke": backbone_smoke,
            "import_probe": import_probe,
        },
        "checklist": checklist,
        "failed_items": failed_items,
        "overall_status": "passed" if not failed_items else "failed",
    }


def render_human(report: dict[str, Any]) -> str:
    lines = [
        "Professional RL quality gate",
        f"overall_status: {report['overall_status']}",
    ]
    for key, label in QUALITY_GATE_LABELS:
        item = report["checklist"][key]
        lines.append(f"- {label}: {item['status']}")
    readiness = report["release_acceptance"]["rollout_readiness"]
    lines.append(f"active_rollout_decision: {readiness['active_rollout_decision']}")
    if report["failed_items"]:
        lines.append("failed_items: " + ", ".join(report["failed_items"]))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the professional RL quality gate for this repository.")
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    parser.add_argument("--python-bin", default=sys.executable, help="Python interpreter used for subprocess commands.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    report = generate_professional_quality_gate_report(repo_root, python_bin=args.python_bin)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(render_human(report))
    if report["overall_status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
