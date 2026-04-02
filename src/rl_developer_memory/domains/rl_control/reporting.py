from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import coerce_json_value

_SEVERITY_ORDER = {"clean": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}


def _normalize_severity(value: object, *, default: str = "info") -> str:
    severity = str(value or default).strip().lower()
    if severity not in {"clean", "info", "warning", "error", "critical"}:
        return default
    return severity


def _max_severity(levels: Sequence[str]) -> str:
    if not levels:
        return "clean"
    return max((_normalize_severity(level) for level in levels), key=lambda item: _SEVERITY_ORDER.get(item, 0))


def summarize_audit_findings(findings: Sequence[Mapping[str, Any]] | None, *, limit: int = 5) -> dict[str, Any]:
    rows = [item for item in (findings or []) if isinstance(item, Mapping)]
    severity_counts: Counter[str] = Counter()
    audit_type_counts: Counter[str] = Counter()
    normalized_rows: list[dict[str, Any]] = []
    for item in rows:
        severity = _normalize_severity(item.get("severity"), default="info")
        audit_type = str(item.get("audit_type", "unknown") or "unknown")
        status = str(item.get("status", "open") or "open")
        summary = str(item.get("summary", "") or "")
        payload = item.get("payload") if isinstance(item.get("payload"), Mapping) else coerce_json_value(item.get("payload_json"), fallback={})
        normalized_rows.append(
            {
                "audit_type": audit_type,
                "severity": severity,
                "status": status,
                "summary": summary,
                "payload": payload,
            }
        )
        severity_counts[severity] += 1
        audit_type_counts[audit_type] += 1

    ordered = sorted(normalized_rows, key=lambda item: (-_SEVERITY_ORDER.get(item["severity"], 0), item["audit_type"], item["summary"]))
    blockers = [item["summary"] for item in ordered if item["severity"] in {"critical", "error"}][: max(limit, 1)]
    warnings = [item["summary"] for item in ordered if item["severity"] == "warning"][: max(limit, 1)]
    highlights = ordered[: max(limit, 1)]
    max_level = _max_severity([item["severity"] for item in ordered])
    return {
        "total": len(rows),
        "max_severity": max_level,
        "severity_counts": {key: int(severity_counts.get(key, 0)) for key in ("info", "warning", "error", "critical")},
        "audit_type_counts": dict(sorted(audit_type_counts.items())),
        "blockers": blockers,
        "warnings": warnings,
        "highlights": highlights,
    }


def summarize_artifact_refs(artifact_refs: Sequence[Mapping[str, Any]] | None, *, limit: int = 5) -> dict[str, Any]:
    rows = [item for item in (artifact_refs or []) if isinstance(item, Mapping)]
    kind_counts: Counter[str] = Counter()
    total_bytes = 0
    highlights: list[dict[str, Any]] = []
    for item in rows:
        kind = str(item.get("kind", "unknown") or "unknown")
        kind_counts[kind] += 1
        try:
            total_bytes += max(int(item.get("bytes", 0) or 0), 0)
        except (TypeError, ValueError):
            total_bytes += 0
        if len(highlights) < max(limit, 1):
            highlights.append(
                {
                    "kind": kind,
                    "uri": str(item.get("uri", "") or ""),
                    "description": str(item.get("description", "") or ""),
                    "bytes": max(int(item.get("bytes", 0) or 0), 0) if str(item.get("bytes", "")).strip() else 0,
                }
            )
    return {
        "total": len(rows),
        "kinds": dict(sorted(kind_counts.items())),
        "total_bytes": total_bytes,
        "highlights": highlights,
    }


def summarize_promotion_state(
    *,
    pattern: Mapping[str, Any] | None = None,
    validation_payload: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pattern_payload = pattern or {}
    validation = validation_payload or (pattern_payload.get("validation_json") if isinstance(pattern_payload.get("validation_json"), Mapping) else {}) or {}
    meta = metadata or {}
    requested = str(
        meta.get("promotion_requested_tier")
        or validation.get("promotion_requested_tier")
        or validation.get("validation_tier")
        or pattern_payload.get("validation_tier")
        or "observed"
    )
    applied = str(
        meta.get("promotion_applied_tier")
        or validation.get("validation_tier")
        or pattern_payload.get("validation_tier")
        or "observed"
    )
    status = str(meta.get("promotion_status") or validation.get("promotion_status") or "applied")
    blockers_raw = meta.get("promotion_blockers") or validation.get("promotion_blockers") or []
    reasons_raw = meta.get("promotion_reasons") or validation.get("promotion_reasons") or []
    blockers = [str(item) for item in blockers_raw if str(item).strip()]
    reasons = [str(item) for item in reasons_raw if str(item).strip()]
    review_required = bool(validation.get("promotion_review_required")) or str(status) == "pending_review"
    review_reason = str(meta.get("review_reason") or validation.get("promotion_review_reason") or "")
    review_mode = str(meta.get("review_mode") or ("promotion" if review_required else ""))
    finding_counts = meta.get("finding_counts") or validation.get("finding_counts") or {}
    if not isinstance(finding_counts, Mapping):
        finding_counts = {}
    return {
        "requested_tier": requested,
        "applied_tier": applied,
        "status": status,
        "review_required": review_required,
        "review_mode": review_mode,
        "review_reason": review_reason,
        "blockers": blockers,
        "reasons": reasons,
        "finding_counts": {
            "info": int(finding_counts.get("info", 0) or 0),
            "warning": int(finding_counts.get("warning", 0) or 0),
            "error": int(finding_counts.get("error", 0) or 0),
            "critical": int(finding_counts.get("critical", 0) or 0),
        },
    }


def build_pattern_audit_report(
    pattern: Mapping[str, Any] | None,
    findings: Sequence[Mapping[str, Any]] | None,
    artifact_refs: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    pattern_payload = pattern or {}
    validation_payload = pattern_payload.get("validation_json") if isinstance(pattern_payload.get("validation_json"), Mapping) else {}
    finding_summary = summarize_audit_findings(findings)
    artifact_summary = summarize_artifact_refs(artifact_refs)
    promotion = summarize_promotion_state(pattern=pattern_payload, validation_payload=validation_payload)
    memory_kind = str(pattern_payload.get("memory_kind", "") or "")
    problem_family = str(pattern_payload.get("problem_family", "") or "")
    theorem_claim_type = str(pattern_payload.get("theorem_claim_type", "") or "")
    validation_tier = str(pattern_payload.get("validation_tier", promotion["applied_tier"]) or promotion["applied_tier"])

    descriptor = [part for part in (memory_kind, problem_family if problem_family != "generic" else "", theorem_claim_type if theorem_claim_type != "none" else "", validation_tier) if part]
    headline = " / ".join(descriptor) if descriptor else str(pattern_payload.get("title", "pattern")).strip() or "pattern"
    return {
        "enabled": bool(memory_kind or finding_summary["total"] or artifact_summary["total"] or promotion["status"] != "applied"),
        "headline": headline,
        "memory_kind": memory_kind,
        "problem_family": problem_family,
        "theorem_claim_type": theorem_claim_type,
        "validation_tier": validation_tier,
        "finding_summary": finding_summary,
        "promotion": promotion,
        "artifact_summary": artifact_summary,
    }


def build_review_item_audit_report(
    review_item: Mapping[str, Any],
    *,
    pattern: Mapping[str, Any] | None = None,
    findings: Sequence[Mapping[str, Any]] | None = None,
    artifact_refs: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    metadata = review_item.get("metadata_json") if isinstance(review_item.get("metadata_json"), Mapping) else {}
    pattern_report = build_pattern_audit_report(pattern, findings, artifact_refs)
    promotion = summarize_promotion_state(pattern=pattern, metadata=metadata)
    return {
        "enabled": bool(pattern_report.get("enabled") or metadata),
        "review_id": int(review_item.get("id", 0) or 0),
        "status": str(review_item.get("status", "pending") or "pending"),
        "review_reason": str(review_item.get("review_reason", "") or ""),
        "review_mode": str(metadata.get("review_mode", promotion.get("review_mode", "") or "consolidation") or "consolidation"),
        "pattern_id": int(review_item.get("pattern_id", 0) or 0) or None,
        "variant_id": int(review_item.get("variant_id", 0) or 0) or None,
        "headline": pattern_report.get("headline") or str(review_item.get("review_reason", "review") or "review"),
        "promotion": promotion,
        "finding_summary": pattern_report["finding_summary"],
        "artifact_summary": pattern_report["artifact_summary"],
    }


def summarize_read_only_audit(matches: Sequence[Mapping[str, Any]] | None) -> dict[str, Any]:
    rows = [item for item in (matches or []) if isinstance(item, Mapping)]
    severity_counts: Counter[str] = Counter()
    memory_kind_counts: Counter[str] = Counter()
    top_risky_pattern_id: int | None = None
    top_clean_pattern_id: int | None = None
    max_risk = "clean"
    for item in rows:
        severity = _normalize_severity(item.get("severity"), default="clean")
        severity_counts[severity] += 1
        candidate_profile = item.get("candidate_domain_profile") if isinstance(item.get("candidate_domain_profile"), Mapping) else {}
        memory_kind = str(candidate_profile.get("memory_kind") or item.get("memory_kind") or "")
        if memory_kind:
            memory_kind_counts[memory_kind] += 1
        if top_clean_pattern_id is None and severity in {"clean", "info"}:
            try:
                top_clean_pattern_id = int(item.get("pattern_id", 0) or 0)
            except (TypeError, ValueError):
                top_clean_pattern_id = None
        if _SEVERITY_ORDER[severity] > _SEVERITY_ORDER[max_risk]:
            max_risk = severity
            try:
                top_risky_pattern_id = int(item.get("pattern_id", 0) or 0) or None
            except (TypeError, ValueError):
                top_risky_pattern_id = None
    return {
        "total_matches": len(rows),
        "by_severity": {key: int(severity_counts.get(key, 0)) for key in ("clean", "info", "warning", "error", "critical")},
        "by_memory_kind": dict(sorted(memory_kind_counts.items())),
        "max_severity": _max_severity([_normalize_severity(item.get("severity"), default="clean") for item in rows]),
        "top_clean_pattern_id": top_clean_pattern_id,
        "top_risky_pattern_id": top_risky_pattern_id,
    }


def summarize_review_queue_reports(items: Sequence[Mapping[str, Any]] | None) -> dict[str, Any]:
    rows = [item for item in (items or []) if isinstance(item, Mapping)]
    status_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    requested_tier_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    for item in rows:
        status_counts[str(item.get("status", "pending") or "pending")] += 1
        report = item.get("audit_report") if isinstance(item.get("audit_report"), Mapping) else {}
        mode_counts[str(report.get("review_mode", "consolidation") or "consolidation")] += 1
        promotion = report.get("promotion") if isinstance(report.get("promotion"), Mapping) else {}
        requested = str(promotion.get("requested_tier", "") or "")
        if requested:
            requested_tier_counts[requested] += 1
        finding_summary = report.get("finding_summary") if isinstance(report.get("finding_summary"), Mapping) else {}
        max_severity = _normalize_severity(finding_summary.get("max_severity"), default="clean")
        severity_counts[max_severity] += 1
    return {
        "enabled": bool(rows),
        "total_items": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "review_mode_counts": dict(sorted(mode_counts.items())),
        "requested_tier_counts": dict(sorted(requested_tier_counts.items())),
        "max_severity_counts": {key: int(severity_counts.get(key, 0)) for key in ("clean", "info", "warning", "error", "critical")},
    }

