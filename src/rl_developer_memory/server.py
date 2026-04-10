from __future__ import annotations

import functools
import logging
import os
import sys
import time
import uuid
from functools import lru_cache
from typing import Any, Callable, TypeVar

_logger = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP  # pyright: ignore[reportMissingImports,reportAssignmentType]
except ImportError:  # pragma: no cover - exercised in lightweight test environments
    F = TypeVar("F", bound=Callable[..., Any])

    class FastMCP:  # type: ignore[override]
        """Small import-time shim so lifecycle tests can load the server module without MCP installed."""

        def __init__(self, _name: str, json_response: bool = True) -> None:
            self.json_response = json_response

        def tool(self) -> Callable[[F], F]:
            def decorator(func: F) -> F:
                return func

            return decorator

        def run(self) -> None:
            """Lightweight fallback loop for test environments without the MCP package.

            This keeps the lifecycle process alive so owner-key reuse and rollout diagnostics
            can still be exercised under subprocess-based tests. The real MCP server should
            always run with the `mcp` package installed.
            """
            if sys.stdin is None:
                while True:
                    time.sleep(1.0)
            for _ in sys.stdin:
                pass

from .app import RLDeveloperMemoryApp  # noqa: E402
from .lifecycle import MCPServerLifecycle, MCPServerOwnerConflict, read_server_lifecycle_status  # noqa: E402
from .settings import Settings  # noqa: E402

__all__ = ["main", "mcp"]

mcp = FastMCP("rl-developer-memory", json_response=True)

# --- Input validation constants ---
_MAX_TEXT_LEN = 32_000       # General text fields (error_text, context, etc.)
_MAX_JSON_LEN = 64_000       # JSON payload fields
_MAX_TITLE_LEN = 1_000       # Title fields
_MAX_SHORT_TEXT_LEN = 4_000   # Short fields (command, file_path, tags, etc.)
_MAX_NOTES_LEN = 8_000       # Notes / resolution_notes
_MAX_LIMIT = 200              # Maximum limit parameter


def _clamp_limit(value: int, *, default: int = 5, ceiling: int = _MAX_LIMIT) -> int:
    """Clamp a limit parameter to a safe range."""
    return max(1, min(int(value), ceiling))


def _truncate(value: str, max_len: int) -> str:
    """Truncate a string to max_len, preserving information about truncation."""
    if len(value) <= max_len:
        return value
    return value[:max_len]


# ---------------------------------------------------------------------------
# Error-boundary decorator with structured logging
# ---------------------------------------------------------------------------

def _tool_boundary(func: Callable[..., dict]) -> Callable[..., dict]:
    """Wrap an MCP tool so that (1) every call is logged with timing and
    (2) unhandled exceptions become structured JSON error responses instead
    of crashing the server process."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict:
        trace_id = uuid.uuid4().hex[:12]
        tool_name = func.__name__
        t0 = time.monotonic()
        _logger.info("tool_call_start trace=%s tool=%s", trace_id, tool_name)
        try:
            result = func(*args, **kwargs)
            elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
            _logger.info(
                "tool_call_ok trace=%s tool=%s elapsed_ms=%.1f",
                trace_id, tool_name, elapsed_ms,
            )
            if isinstance(result, dict):
                result["_trace_id"] = trace_id
            return result
        except Exception:
            elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
            _logger.exception(
                "tool_call_error trace=%s tool=%s elapsed_ms=%.1f",
                trace_id, tool_name, elapsed_ms,
            )
            return {
                "error": True,
                "code": "internal_error",
                "message": f"An internal error occurred while executing {tool_name}.",
                "_trace_id": trace_id,
            }

    return wrapper


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


@lru_cache(maxsize=1)
def get_lifecycle() -> MCPServerLifecycle:
    return MCPServerLifecycle(get_settings())


@lru_cache(maxsize=1)
def get_app() -> RLDeveloperMemoryApp:
    app = RLDeveloperMemoryApp()
    get_lifecycle().mark_initialized()
    return app


@mcp.tool()
@_tool_boundary
def issue_match(
    error_text: str,
    context: str = "",
    command: str = "",
    file_path: str = "",
    stack_excerpt: str = "",
    env_json: str = "",
    repo_name: str = "",
    git_commit: str = "",
    session_id: str = "",
    project_scope: str = "global",
    user_scope: str = "",
    limit: int = 3,
) -> dict:
    """Find the most similar known issue patterns for a failure."""
    return get_app().issue_match(
        error_text=_truncate(error_text, _MAX_TEXT_LEN),
        context=_truncate(context, _MAX_TEXT_LEN),
        command=_truncate(command, _MAX_SHORT_TEXT_LEN),
        file_path=_truncate(file_path, _MAX_SHORT_TEXT_LEN),
        stack_excerpt=_truncate(stack_excerpt, _MAX_TEXT_LEN),
        env_json=_truncate(env_json, _MAX_JSON_LEN),
        repo_name=_truncate(repo_name, _MAX_SHORT_TEXT_LEN),
        git_commit=_truncate(git_commit, _MAX_SHORT_TEXT_LEN),
        session_id=_truncate(session_id, _MAX_SHORT_TEXT_LEN),
        project_scope=_truncate(project_scope, _MAX_SHORT_TEXT_LEN),
        user_scope=_truncate(user_scope, _MAX_SHORT_TEXT_LEN),
        limit=_clamp_limit(limit),
    )


@mcp.tool()
@_tool_boundary
def issue_record_resolution(
    title: str,
    raw_error: str,
    canonical_fix: str,
    prevention_rule: str,
    project_scope: str = "global",
    user_scope: str = "",
    canonical_symptom: str = "",
    verification_steps: str = "",
    tags: str = "",
    error_family: str = "auto",
    root_cause_class: str = "auto",
    context: str = "",
    file_path: str = "",
    command: str = "",
    domain: str = "generic",
    stack_excerpt: str = "",
    env_json: str = "",
    repo_name: str = "",
    git_commit: str = "",
    session_id: str = "",
    verification_command: str = "",
    verification_output: str = "",
    resolution_notes: str = "",
    patch_summary: str = "",
    patch_hash: str = "",
    memory_kind: str = "",
    problem_family: str = "",
    theorem_claim_type: str = "",
    validation_tier: str = "",
    algorithm_family: str = "",
    runtime_stage: str = "",
    problem_profile_json: dict[str, Any] | str = "",
    variant_profile_json: dict[str, Any] | str = "",
    run_manifest_json: dict[str, Any] | str = "",
    metrics_json: dict[str, Any] | str = "",
    validation_json: dict[str, Any] | str = "",
    artifact_refs_json: list[dict[str, Any]] | str = "",
    sim2real_profile_json: dict[str, Any] | str = "",
) -> dict:
    """Store a verified reusable fix as pattern + variant + episode."""
    return get_app().issue_record_resolution(
        title=_truncate(title, _MAX_TITLE_LEN),
        raw_error=_truncate(raw_error, _MAX_TEXT_LEN),
        canonical_fix=_truncate(canonical_fix, _MAX_TEXT_LEN),
        prevention_rule=_truncate(prevention_rule, _MAX_TEXT_LEN),
        project_scope=_truncate(project_scope, _MAX_SHORT_TEXT_LEN),
        user_scope=_truncate(user_scope, _MAX_SHORT_TEXT_LEN),
        canonical_symptom=_truncate(canonical_symptom, _MAX_TEXT_LEN),
        verification_steps=_truncate(verification_steps, _MAX_TEXT_LEN),
        tags=_truncate(tags, _MAX_SHORT_TEXT_LEN),
        error_family=_truncate(error_family, _MAX_SHORT_TEXT_LEN),
        root_cause_class=_truncate(root_cause_class, _MAX_SHORT_TEXT_LEN),
        context=_truncate(context, _MAX_TEXT_LEN),
        file_path=_truncate(file_path, _MAX_SHORT_TEXT_LEN),
        command=_truncate(command, _MAX_SHORT_TEXT_LEN),
        domain=_truncate(domain, _MAX_SHORT_TEXT_LEN),
        stack_excerpt=_truncate(stack_excerpt, _MAX_TEXT_LEN),
        env_json=_truncate(env_json, _MAX_JSON_LEN),
        repo_name=_truncate(repo_name, _MAX_SHORT_TEXT_LEN),
        git_commit=_truncate(git_commit, _MAX_SHORT_TEXT_LEN),
        session_id=_truncate(session_id, _MAX_SHORT_TEXT_LEN),
        verification_command=_truncate(verification_command, _MAX_SHORT_TEXT_LEN),
        verification_output=_truncate(verification_output, _MAX_TEXT_LEN),
        resolution_notes=_truncate(resolution_notes, _MAX_NOTES_LEN),
        patch_summary=_truncate(patch_summary, _MAX_TEXT_LEN),
        patch_hash=_truncate(patch_hash, _MAX_SHORT_TEXT_LEN),
        memory_kind=_truncate(memory_kind, _MAX_SHORT_TEXT_LEN) if isinstance(memory_kind, str) else memory_kind,
        problem_family=_truncate(problem_family, _MAX_SHORT_TEXT_LEN) if isinstance(problem_family, str) else problem_family,
        theorem_claim_type=_truncate(theorem_claim_type, _MAX_SHORT_TEXT_LEN) if isinstance(theorem_claim_type, str) else theorem_claim_type,
        validation_tier=_truncate(validation_tier, _MAX_SHORT_TEXT_LEN) if isinstance(validation_tier, str) else validation_tier,
        algorithm_family=_truncate(algorithm_family, _MAX_SHORT_TEXT_LEN) if isinstance(algorithm_family, str) else algorithm_family,
        runtime_stage=_truncate(runtime_stage, _MAX_SHORT_TEXT_LEN) if isinstance(runtime_stage, str) else runtime_stage,
        problem_profile_json=_truncate(problem_profile_json, _MAX_JSON_LEN) if isinstance(problem_profile_json, str) else problem_profile_json,
        variant_profile_json=_truncate(variant_profile_json, _MAX_JSON_LEN) if isinstance(variant_profile_json, str) else variant_profile_json,
        run_manifest_json=_truncate(run_manifest_json, _MAX_JSON_LEN) if isinstance(run_manifest_json, str) else run_manifest_json,
        metrics_json=_truncate(metrics_json, _MAX_JSON_LEN) if isinstance(metrics_json, str) else metrics_json,
        validation_json=_truncate(validation_json, _MAX_JSON_LEN) if isinstance(validation_json, str) else validation_json,
        artifact_refs_json=_truncate(artifact_refs_json, _MAX_JSON_LEN) if isinstance(artifact_refs_json, str) else artifact_refs_json,
        sim2real_profile_json=_truncate(sim2real_profile_json, _MAX_JSON_LEN) if isinstance(sim2real_profile_json, str) else sim2real_profile_json,
    )


@mcp.tool()
@_tool_boundary
def issue_feedback(
    retrieval_event_id: int,
    feedback_type: str,
    retrieval_candidate_id: int = 0,
    candidate_rank: int = 0,
    pattern_id: int = 0,
    variant_id: int = 0,
    actor: str = "user",
    reward: float | None = None,
    notes: str = "",
) -> dict:
    """Record retrieval feedback so the matcher can learn from accepted and rejected candidates."""
    return get_app().issue_feedback(
        retrieval_event_id=retrieval_event_id,
        feedback_type=_truncate(feedback_type, _MAX_SHORT_TEXT_LEN),
        retrieval_candidate_id=retrieval_candidate_id,
        candidate_rank=candidate_rank,
        pattern_id=pattern_id,
        variant_id=variant_id,
        actor=_truncate(actor, _MAX_SHORT_TEXT_LEN),
        reward=reward,
        notes=_truncate(notes, _MAX_NOTES_LEN),
    )


@mcp.tool()
@_tool_boundary
def issue_set_preference(
    instruction: str,
    project_scope: str = "global",
    user_scope: str = "",
    repo_name: str = "",
    error_family: str = "auto",
    strategy_key: str = "auto",
    command: str = "",
    file_path: str = "",
    mode: str = "prefer",
    weight: float | None = None,
    source: str = "user_prompt",
) -> dict:
    """Store a prompt-driven strategy preference without duplicating pattern memory."""
    return get_app().issue_set_preference(
        instruction=_truncate(instruction, _MAX_TEXT_LEN),
        project_scope=_truncate(project_scope, _MAX_SHORT_TEXT_LEN),
        user_scope=_truncate(user_scope, _MAX_SHORT_TEXT_LEN),
        repo_name=_truncate(repo_name, _MAX_SHORT_TEXT_LEN),
        error_family=_truncate(error_family, _MAX_SHORT_TEXT_LEN),
        strategy_key=_truncate(strategy_key, _MAX_SHORT_TEXT_LEN),
        command=_truncate(command, _MAX_SHORT_TEXT_LEN),
        file_path=_truncate(file_path, _MAX_SHORT_TEXT_LEN),
        mode=_truncate(mode, _MAX_SHORT_TEXT_LEN),
        weight=weight,
        source=_truncate(source, _MAX_SHORT_TEXT_LEN),
    )


@mcp.tool()
@_tool_boundary
def issue_list_preferences(
    scope_type: str = "",
    scope_key: str = "",
    project_scope: str = "",
    repo_name: str = "",
    active_only: bool = True,
    limit: int = 20,
) -> dict:
    """List stored prompt-driven preference rules."""
    return get_app().issue_list_preferences(
        scope_type=_truncate(scope_type, _MAX_SHORT_TEXT_LEN),
        scope_key=_truncate(scope_key, _MAX_SHORT_TEXT_LEN),
        project_scope=_truncate(project_scope, _MAX_SHORT_TEXT_LEN),
        repo_name=_truncate(repo_name, _MAX_SHORT_TEXT_LEN),
        active_only=active_only,
        limit=_clamp_limit(limit, default=20),
    )


@mcp.tool()
@_tool_boundary
def issue_guardrails(
    error_text: str = "",
    context: str = "",
    command: str = "",
    file_path: str = "",
    repo_name: str = "",
    project_scope: str = "global",
    user_scope: str = "",
    limit: int = 5,
) -> dict:
    """Return proactive prevention rules and preferred strategies before an issue repeats."""
    return get_app().issue_guardrails(
        error_text=_truncate(error_text, _MAX_TEXT_LEN),
        context=_truncate(context, _MAX_TEXT_LEN),
        command=_truncate(command, _MAX_SHORT_TEXT_LEN),
        file_path=_truncate(file_path, _MAX_SHORT_TEXT_LEN),
        repo_name=_truncate(repo_name, _MAX_SHORT_TEXT_LEN),
        project_scope=_truncate(project_scope, _MAX_SHORT_TEXT_LEN),
        user_scope=_truncate(user_scope, _MAX_SHORT_TEXT_LEN),
        limit=_clamp_limit(limit),
    )


@mcp.tool()
@_tool_boundary
def issue_metrics(window_days: int = 30) -> dict:
    """Return operational metrics for observability and production monitoring."""
    return get_app().issue_metrics(window_days=max(1, min(int(window_days), 3650)))


@mcp.tool()
@_tool_boundary
def issue_review_queue(status: str = "pending", limit: int = 20) -> dict:
    """List pending or resolved review items created by conservative consolidation."""
    return get_app().issue_review_queue(status=_truncate(status, _MAX_SHORT_TEXT_LEN), limit=_clamp_limit(limit, default=20))


@mcp.tool()
@_tool_boundary
def issue_review_resolve(review_id: int, decision: str, note: str = "") -> dict:
    """Resolve a review queue item and activate or archive its provisional variant."""
    return get_app().issue_review_resolve(review_id=review_id, decision=_truncate(decision, _MAX_SHORT_TEXT_LEN), note=_truncate(note, _MAX_NOTES_LEN))


@mcp.tool()
@_tool_boundary
def issue_get(
    pattern_id: int,
    include_examples: bool = True,
    examples_limit: int = 5,
    include_audit_findings: bool = True,
    audit_limit: int = 25,
    include_artifact_refs: bool = True,
    artifact_limit: int = 25,
) -> dict:
    """Return the full stored details for one issue pattern, including variants and episodes."""
    return get_app().issue_get(
        pattern_id=pattern_id,
        include_examples=include_examples,
        examples_limit=_clamp_limit(examples_limit),
        include_audit_findings=include_audit_findings,
        audit_limit=_clamp_limit(audit_limit, default=25),
        include_artifact_refs=include_artifact_refs,
        artifact_limit=_clamp_limit(artifact_limit, default=25),
    )


@mcp.tool()
@_tool_boundary
def issue_recent(limit: int = 5, project_scope: str = "") -> dict:
    """Return recent issue patterns in compact form."""
    return get_app().issue_recent(limit=_clamp_limit(limit), project_scope=_truncate(project_scope, _MAX_SHORT_TEXT_LEN))


@mcp.tool()
@_tool_boundary
def issue_search(query: str, project_scope: str = "", limit: int = 5, session_id: str = "") -> dict:
    """Keyword search across stored issue patterns."""
    return get_app().issue_search(
        query=_truncate(query, _MAX_TEXT_LEN),
        project_scope=_truncate(project_scope, _MAX_SHORT_TEXT_LEN),
        limit=_clamp_limit(limit),
        session_id=_truncate(session_id, _MAX_SHORT_TEXT_LEN),
    )


@mcp.tool()
@_tool_boundary
def issue_health() -> dict:
    """Return server health: uptime, DB size, pattern count, lifecycle status."""
    settings = get_settings()
    lifecycle_status = read_server_lifecycle_status(settings)
    db_bytes = settings.db_path.stat().st_size if settings.db_path.exists() else 0
    uptime_seconds = round(time.monotonic() - _SERVER_START_MONOTONIC, 1)
    app = get_app()
    with app.store.managed_connection() as conn:
        total_patterns = int(conn.execute("SELECT COUNT(*) FROM issue_patterns").fetchone()[0])
        total_variants = int(conn.execute("SELECT COUNT(*) FROM issue_variants").fetchone()[0])
    return {
        "healthy": True,
        "uptime_seconds": uptime_seconds,
        "pid": os.getpid(),
        "db_path": str(settings.db_path),
        "db_bytes": db_bytes,
        "patterns": total_patterns,
        "variants": total_variants,
        "lifecycle": lifecycle_status.to_dict(),
    }


_SERVER_START_MONOTONIC = time.monotonic()


def main() -> None:
    lifecycle = get_lifecycle()
    try:
        lifecycle.start()
        _logger.info("MCP server started (pid=%d)", os.getpid())
    except MCPServerOwnerConflict as exc:
        _logger.error("Owner conflict: %s", exc)
        print(str(exc), file=sys.stderr)
        raise SystemExit(exc.exit_code) from exc
    except RuntimeError as exc:
        _logger.error("Server startup failed: %s", exc)
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    try:
        mcp.run()
    except KeyboardInterrupt:
        if not lifecycle.shutdown_reason:
            raise
    finally:
        _logger.info("MCP server shutting down")
        lifecycle.release()


if __name__ == "__main__":
    main()
