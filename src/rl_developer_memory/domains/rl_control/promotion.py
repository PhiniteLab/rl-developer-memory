from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from .contracts import RLAuditFinding
from .taxonomy import normalize_validation_tier


@dataclass(slots=True)
class PromotionDecision:
    requested_tier: str
    applied_tier: str
    status: str
    review_required: bool = False
    review_mode: str = ""
    review_reason: str = ""
    reasons: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    finding_counts: dict[str, int] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def _safe_int(value: object, *, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return default
        try:
            return int(normalized)
        except ValueError:
            return default
    return default


def _count_findings(findings: Iterable[RLAuditFinding | Mapping[str, object]]) -> dict[str, int]:
    counts = {"info": 0, "warning": 0, "error": 0, "critical": 0}
    for item in findings:
        severity = str(item.severity if isinstance(item, RLAuditFinding) else item.get("severity", "info") or "info").lower()
        if severity not in counts:
            counts[severity] = 0
        counts[severity] += 1
    return counts


def recommend_validation_tier(
    findings: Iterable[RLAuditFinding | Mapping[str, object]],
    validation_payload: Mapping[str, object] | None,
    *,
    strict: bool = True,
    required_seed_count: int = 3,
    production_min_seed_count: int = 5,
) -> str:
    validation = validation_payload or {}
    findings_list = list(findings)
    counts = _count_findings(findings_list)
    critical_count = counts.get("critical", 0)
    error_count = counts.get("error", 0)
    warning_count = counts.get("warning", 0)

    seed_count = _safe_int(validation.get("seed_count"), default=0)
    baseline_ok = bool(validation.get("baseline_comparison") or validation.get("baseline_results"))

    if (validation.get("production_verified") or validation.get("hardware_validated")) and seed_count >= production_min_seed_count and critical_count == 0 and error_count == 0:
        return "production_validated"
    if validation.get("theory_reviewed") and critical_count == 0 and (error_count == 0 or not strict):
        return "theory_reviewed"
    if seed_count >= required_seed_count and baseline_ok and critical_count == 0 and (error_count == 0 or not strict):
        return "validated"
    if critical_count == 0 and error_count == 0 and (warning_count <= 2 or not strict):
        return "candidate"
    return normalize_validation_tier(str(validation.get("validation_tier", "observed")) or "observed")


def decide_promotion(
    findings: Iterable[RLAuditFinding | Mapping[str, object]],
    validation_payload: Mapping[str, object] | None,
    *,
    memory_kind: str,
    theorem_claim_type: str,
    requested_tier: str = "",
    strict: bool = True,
    required_seed_count: int = 3,
    production_min_seed_count: int = 5,
    candidate_warning_budget: int = 2,
    review_gated: bool = True,
) -> PromotionDecision:
    validation = validation_payload or {}
    findings_list = list(findings)
    counts = _count_findings(findings_list)
    critical_count = counts.get("critical", 0)
    error_count = counts.get("error", 0)
    warning_count = counts.get("warning", 0)
    seed_count = _safe_int(validation.get("seed_count"), default=0)
    baseline_ok = bool(validation.get("baseline_comparison") or validation.get("baseline_results"))
    theory_reviewed = bool(validation.get("theory_reviewed"))
    hardware_validated = bool(validation.get("hardware_validated"))
    production_verified = bool(validation.get("production_verified"))
    candidate_allowed = critical_count == 0 and error_count == 0 and (warning_count <= candidate_warning_budget or not strict)
    finding_summaries = [str(item.summary if isinstance(item, RLAuditFinding) else item.get("summary", "")).lower() for item in findings_list]

    normalized_requested = normalize_validation_tier(
        requested_tier
        or str(validation.get("validation_tier") or "")
        or recommend_validation_tier(
            findings_list,
            validation,
            strict=strict,
            required_seed_count=required_seed_count,
            production_min_seed_count=production_min_seed_count,
        ),
        default="observed",
    )

    reasons: list[str] = [f"requested-tier:{normalized_requested}"]
    blockers: list[str] = []

    if critical_count > 0:
        blockers.append("critical-audit-findings")
    if strict and error_count > 0:
        blockers.append("error-audit-findings")

    if normalized_requested in {"validated", "production_validated"}:
        if seed_count < required_seed_count:
            blockers.append("seed-count-below-validated-threshold")
        if memory_kind != "theory_pattern" and not baseline_ok:
            blockers.append("missing-baseline-comparison")
        if any("baseline_names" in summary and "baseline" in summary for summary in finding_summaries):
            blockers.append("missing-baseline-comparison")
    if normalized_requested == "production_validated":
        if seed_count < production_min_seed_count:
            blockers.append("seed-count-below-production-threshold")
        if not (hardware_validated or production_verified):
            blockers.append("missing-hardware-validation")
        if memory_kind == "theory_pattern":
            blockers.append("production-tier-not-applicable-to-theory-pattern")
    if normalized_requested == "theory_reviewed":
        if theorem_claim_type in {"", "none"}:
            blockers.append("missing-theorem-claim")
        if not theory_reviewed:
            blockers.append("missing-theory-review-flag")

    if blockers:
        blockers = list(dict.fromkeys(blockers))
        applied_tier = "candidate" if normalized_requested == "candidate" and candidate_allowed else "observed"
        reasons.extend(f"blocker:{item}" for item in blockers)
        if applied_tier != normalized_requested:
            reasons.append(f"applied-tier-capped:{applied_tier}")
        return PromotionDecision(
            requested_tier=normalized_requested,
            applied_tier=applied_tier,
            status="blocked",
            review_required=False,
            review_mode="",
            review_reason="",
            reasons=reasons,
            blockers=blockers,
            finding_counts=counts,
        )

    review_mode = ""
    review_reason = ""
    applied_tier = normalized_requested

    if normalized_requested in {"validated", "theory_reviewed", "production_validated"} and review_gated:
        review_mode = "promotion"
        if normalized_requested == "production_validated":
            applied_tier = "validated"
            review_reason = "Approve production_validated promotion after deployment review."
            reasons.append("review-gated-promotion:production_validated")
        elif normalized_requested == "theory_reviewed":
            applied_tier = "candidate"
            review_reason = "Approve theory_reviewed promotion after proof review."
            reasons.append("review-gated-promotion:theory_reviewed")
        else:
            applied_tier = "candidate"
            review_reason = "Approve validated promotion after experiment review."
            reasons.append("review-gated-promotion:validated")
        reasons.append(f"applied-tier-capped:{applied_tier}")
        return PromotionDecision(
            requested_tier=normalized_requested,
            applied_tier=applied_tier,
            status="pending_review",
            review_required=True,
            review_mode=review_mode,
            review_reason=review_reason,
            reasons=reasons,
            blockers=[],
            finding_counts=counts,
        )

    if normalized_requested == "candidate" and not candidate_allowed:
        applied_tier = "observed"
        reasons.append("applied-tier-capped:observed")

    return PromotionDecision(
        requested_tier=normalized_requested,
        applied_tier=applied_tier,
        status="applied",
        review_required=False,
        review_mode="",
        review_reason="",
        reasons=reasons,
        blockers=[],
        finding_counts=counts,
    )
