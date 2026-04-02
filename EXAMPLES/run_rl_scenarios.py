#!/usr/bin/env python3
# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
PYTHON_BIN = sys.executable
OWNER_KEY = "examples-main-thread"
MANIFEST_PATH = REPO_ROOT / "EXAMPLES" / "scenario_manifest.json"


@dataclass(frozen=True)
class ScenarioSpec:
    case_id: str
    title: str
    kind: str
    script_name: str
    command: str
    file_path: str
    error_context: str = ""
    expected_title: str | None = None
    expected_fix_snippet: str | None = None
    seed_payload: dict[str, Any] | None = None

    @property
    def script_path(self) -> Path:
        return REPO_ROOT / "EXAMPLES" / "scenarios" / self.script_name


def load_manifest() -> tuple[str, tuple[ScenarioSpec, ...]]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    scope = str(payload["project_scope"])
    cases = tuple(ScenarioSpec(**case) for case in payload["cases"])
    return scope, cases


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run hard RL coding scenarios through the real MCP stdio surface.")
    parser.add_argument("--output-json", type=Path, default=REPO_ROOT / "EXAMPLES" / "results" / "rl_scenarios_metrics.json")
    parser.add_argument("--output-markdown", type=Path, default=REPO_ROOT / "EXAMPLES" / "results" / "rl_scenarios_summary.md")
    return parser


def _runtime_env(base: Path) -> dict[str, str]:
    env = {
        "PYTHONPATH": str(SRC_ROOT),
        "RL_DEVELOPER_MEMORY_HOME": str(base / "share"),
        "RL_DEVELOPER_MEMORY_DB_PATH": str(base / "share" / "rl_developer_memory.sqlite3"),
        "RL_DEVELOPER_MEMORY_STATE_DIR": str(base / "state"),
        "RL_DEVELOPER_MEMORY_BACKUP_DIR": str(base / "share" / "backups"),
        "RL_DEVELOPER_MEMORY_LOG_DIR": str(base / "state" / "log"),
        "RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL": "1",
        "RL_DEVELOPER_MEMORY_DOMAIN_MODE": "hybrid",
        "RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT": "1",
        "RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT": "1",
        "RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION": "1",
        "RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY": "1",
        "RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV": "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY",
        "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY": OWNER_KEY,
        "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_ROLE": "main",
        "RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES": "0",
        "RL_DEVELOPER_MEMORY_ENFORCE_SINGLE_MCP_INSTANCE": "1",
    }
    for key in ("RL_DEVELOPER_MEMORY_HOME", "RL_DEVELOPER_MEMORY_STATE_DIR", "RL_DEVELOPER_MEMORY_BACKUP_DIR", "RL_DEVELOPER_MEMORY_LOG_DIR"):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    return env


def _extract_error_excerpt(proc: subprocess.CompletedProcess[str]) -> str:
    stderr_lines = [line.strip() for line in (proc.stderr or "").splitlines() if line.strip()]
    for line in reversed(stderr_lines):
        if "AssertionError:" in line:
            return line
    if stderr_lines:
        return stderr_lines[-1]
    stdout_lines = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
    return stdout_lines[-1] if stdout_lines else "unknown scenario failure"


def _run_python_script(spec: ScenarioSpec) -> dict[str, Any]:
    proc = subprocess.run([PYTHON_BIN, str(spec.script_path)], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    return {"returncode": proc.returncode, "failed": proc.returncode != 0, "error_excerpt": _extract_error_excerpt(proc) if proc.returncode != 0 else ""}


async def _call_tool_json(session: ClientSession, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = await session.call_tool(name, arguments)
    if result.isError:
        raise RuntimeError(f"tool {name} failed: {result}")
    if result.structuredContent is not None:
        return dict(result.structuredContent)
    texts = [item.text for item in result.content if hasattr(item, "text")]
    return json.loads(texts[0]) if texts else {}


async def _seed_memory(session: ClientSession, project_scope: str, buggy_specs: tuple[ScenarioSpec, ...]) -> dict[str, int]:
    seeded: dict[str, int] = {}
    for spec in buggy_specs:
        payload = dict(spec.seed_payload or {})
        payload.update({"project_scope": project_scope, "command": spec.command, "file_path": spec.file_path, "validation_tier": "validated", "runtime_stage": "train"})
        result = await _call_tool_json(session, "issue_record_resolution", payload)
        seeded[spec.case_id] = int(result["pattern_id"])
    return seeded


async def _evaluate_buggy_case(session: ClientSession, project_scope: str, spec: ScenarioSpec, expected_pattern_id: int) -> dict[str, Any]:
    failure = _run_python_script(spec)
    started = time.perf_counter()
    match = await _call_tool_json(session, "issue_match", {"error_text": failure["error_excerpt"], "context": spec.error_context, "command": spec.command, "file_path": spec.file_path, "project_scope": project_scope, "session_id": spec.case_id, "limit": 3})
    latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
    top_match = match["matches"][0] if match.get("matches") else None
    bundle = await _call_tool_json(session, "issue_get", {"pattern_id": int(top_match["pattern_id"]), "include_examples": False, "examples_limit": 0}) if top_match else {"found": False}
    guardrails = await _call_tool_json(session, "issue_guardrails", {"error_text": failure["error_excerpt"], "command": spec.command, "file_path": spec.file_path, "project_scope": project_scope, "limit": 3})
    feedback = await _call_tool_json(session, "issue_feedback", {"retrieval_event_id": int(match["retrieval_event_id"]), "feedback_type": "fix_verified", "candidate_rank": 1, "notes": f"Verified via deterministic hard example scenario {spec.case_id}."})
    after_feedback = await _call_tool_json(session, "issue_match", {"error_text": failure["error_excerpt"], "context": spec.error_context, "command": spec.command, "file_path": spec.file_path, "project_scope": project_scope, "session_id": f"{spec.case_id}-after-feedback", "limit": 3})
    top_after = after_feedback["matches"][0] if after_feedback.get("matches") else None
    score_before = float(top_match.get("score", 0.0)) if top_match else 0.0
    score_after = float(top_after.get("score", 0.0)) if top_after else 0.0
    pattern_payload = bundle.get("pattern")
    pattern = pattern_payload if isinstance(pattern_payload, dict) else {}
    found_pattern = bool(bundle.get("found", False))
    route_ok = bool(
        failure["failed"]
        and top_match is not None
        and top_after is not None
        and match["decision"]["status"] == "match"
        and after_feedback["decision"]["status"] == "match"
        and int(top_match["pattern_id"]) == int(expected_pattern_id)
        and int(top_after["pattern_id"]) == int(expected_pattern_id)
        and str(spec.expected_title) == str(top_match.get("title"))
        and str(spec.expected_fix_snippet).lower() in str(top_match.get("canonical_fix", "")).lower()
        and score_after >= score_before
    )
    return {
        "case_id": spec.case_id,
        "kind": spec.kind,
        "scenario_title": spec.title,
        "failure": failure,
        "mcp_triggered": True,
        "route_ok": route_ok,
        "latency_ms": latency_ms,
        "mcp_match": {
            "decision": match["decision"],
            "retrieval_event_id": match.get("retrieval_event_id"),
            "top_match": top_match,
            "next_action": match.get("next_action"),
        },
        "issue_get": {
            "found": found_pattern,
            "title": pattern.get("title") if found_pattern else None,
            "canonical_fix": pattern.get("canonical_fix") if found_pattern else None,
            "prevention_rule": pattern.get("prevention_rule") if found_pattern else None,
        },
        "guardrails": guardrails,
        "feedback": {
            "feedback_type": feedback.get("feedback_type"),
            "global_update_applied": feedback.get("global_update_applied"),
            "confidence_before": feedback.get("variant_update", {}).get("confidence_before"),
            "confidence_after": feedback.get("variant_update", {}).get("confidence_after"),
        },
        "score_before_feedback": round(score_before, 6),
        "score_after_feedback": round(score_after, 6),
        "score_uplift_after_feedback": round(score_after - score_before, 6),
    }


def _evaluate_fixed_case(spec: ScenarioSpec) -> dict[str, Any]:
    failure = _run_python_script(spec)
    return {"case_id": spec.case_id, "kind": spec.kind, "scenario_title": spec.title, "failure": failure, "mcp_triggered": False, "route_ok": not failure["failed"]}


async def _run_async() -> dict[str, Any]:
    project_scope, scenarios = load_manifest()
    buggy_specs = tuple(spec for spec in scenarios if spec.kind == "buggy")
    fixed_specs = tuple(spec for spec in scenarios if spec.kind == "fixed")
    with tempfile.TemporaryDirectory(prefix="rl-mcp-hard-scenarios-") as temp_dir:
        env = _runtime_env(Path(temp_dir))
        params = StdioServerParameters(command=PYTHON_BIN, args=["-m", "rl_developer_memory.server"], cwd=str(REPO_ROOT), env=env)
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                initialize_result = await session.initialize()
                tools = await session.list_tools()
                seeded = await _seed_memory(session, project_scope, buggy_specs)
                cases = [await _evaluate_buggy_case(session, project_scope, spec, seeded[spec.case_id]) for spec in buggy_specs]
                cases.extend(_evaluate_fixed_case(spec) for spec in fixed_specs)
    buggy_cases = [case for case in cases if case["kind"] == "buggy"]
    fixed_cases = [case for case in cases if case["kind"] == "fixed"]
    buggy_detection_recall = sum(1 for case in buggy_cases if case["route_ok"]) / max(len(buggy_cases), 1)
    fixed_non_trigger_rate = sum(1 for case in fixed_cases if case["route_ok"] and not case["mcp_triggered"]) / max(len(fixed_cases), 1)
    routing_accuracy = sum(1 for case in buggy_cases if case["route_ok"]) / max(len(buggy_cases), 1)
    mean_latency = sum(case["latency_ms"] for case in buggy_cases) / max(len(buggy_cases), 1)
    mean_uplift = sum(case["score_uplift_after_feedback"] for case in buggy_cases) / max(len(buggy_cases), 1)
    summary = {"status": "passed" if buggy_detection_recall == 1.0 and fixed_non_trigger_rate == 1.0 and routing_accuracy == 1.0 else "failed", "buggy_cases": len(buggy_cases), "fixed_cases": len(fixed_cases), "buggy_detection_recall": round(buggy_detection_recall, 3), "fixed_non_trigger_rate": round(fixed_non_trigger_rate, 3), "routing_accuracy": round(routing_accuracy, 3), "mean_issue_match_latency_ms": round(mean_latency, 3), "mean_score_uplift_after_feedback": round(mean_uplift, 6), "passed_cases": sum(1 for case in cases if case["route_ok"]), "total_cases": len(cases)}
    return {"generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "transport": {"mode": "mcp_stdio", "server_name": initialize_result.serverInfo.name, "tool_count": len(tools.tools), "tool_names": sorted(tool.name for tool in tools.tools)}, "seeded_patterns": seeded, "cases": cases, "summary": summary}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        return value.replace(str(REPO_ROOT), "<repo>").replace(str(PYTHON_BIN), "<python>").replace("/tmp/", "<tmp>/")
    return value


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# RL MCP hard scenario demo",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Transport: `{payload['transport']['mode']}` via `{payload['transport']['server_name']}`",
        f"- Overall status: **{payload['summary']['status']}**",
        f"- Buggy cases: `{payload['summary']['buggy_cases']}`",
        f"- Fixed cases: `{payload['summary']['fixed_cases']}`",
        f"- Buggy detection recall: `{payload['summary']['buggy_detection_recall']}`",
        f"- Fixed non-trigger rate: `{payload['summary']['fixed_non_trigger_rate']}`",
        f"- Routing accuracy: `{payload['summary']['routing_accuracy']}`",
        f"- Mean issue_match latency (ms): `{payload['summary']['mean_issue_match_latency_ms']}`",
        f"- Mean score uplift after feedback: `{payload['summary']['mean_score_uplift_after_feedback']}`",
        "",
        "## Cases",
    ]
    for case in payload["cases"]:
        lines.append(f"### {case['scenario_title']}")
        lines.append(f"- Kind: `{case['kind']}`")
        lines.append(f"- Failure detected: `{case['failure']['failed']}`")
        if case["failure"]["failed"]:
            lines.append(f"- Error excerpt: `{case['failure']['error_excerpt']}`")
        lines.append(f"- MCP triggered: `{case['mcp_triggered']}`")
        if case.get("mcp_match"):
            lines.append(f"- MCP decision: `{case['mcp_match']['decision']['status']}`")
            top = case["mcp_match"].get("top_match") or {}
            lines.append(f"- Top title: `{top.get('title', 'none')}`")
            lines.append(f"- Canonical fix: `{top.get('canonical_fix', 'none')}`")
            lines.append(f"- Guardrail count: `{len(case.get('guardrails', {}).get('guardrails', []))}`")
            lines.append(f"- Score before feedback: `{case.get('score_before_feedback')}`")
            lines.append(f"- Score after feedback: `{case.get('score_after_feedback')}`")
        lines.append(f"- Route OK: **{case['route_ok']}**")
        lines.append("")
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], output_json: Path, output_markdown: Path) -> None:
    clean = _sanitize(payload)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(clean, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    output_markdown.write_text(_render_markdown(clean), encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    payload = anyio.run(_run_async)
    write_outputs(payload, args.output_json, args.output_markdown)
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    return 0 if payload["summary"]["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
