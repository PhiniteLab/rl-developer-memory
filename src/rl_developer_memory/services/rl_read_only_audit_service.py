from __future__ import annotations

from typing import Any

from ..domains.rl_control import build_candidate_read_only_audit, infer_query_domain_profile, summarize_read_only_audit
from ..models import QueryProfile
from ..retrieval.ranker import RankedCandidate
from ..settings import Settings


class RLReadOnlyAuditService:
    """Build non-persistent RL/control audit summaries for retrieval results."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def enabled_for_profile(self, profile: QueryProfile) -> bool:
        if not self.settings.enable_rl_control:
            return False
        if self.settings.domain_mode not in {"hybrid", "rl_control"}:
            return False
        domain_profile = infer_query_domain_profile(profile)
        return bool(domain_profile.get("enabled"))

    def audit_ranked_candidates(
        self,
        profile: QueryProfile,
        ranked: list[RankedCandidate],
        *,
        limit: int,
    ) -> dict[str, Any]:
        query_domain_profile = infer_query_domain_profile(profile)
        if not self.settings.enable_rl_control or self.settings.domain_mode not in {"hybrid", "rl_control"}:
            return {"enabled": False, "query_domain_profile": query_domain_profile, "matches": []}

        if not (query_domain_profile.get("enabled") or any(str(item.candidate.get("problem_family", "")) not in {"", "generic"} for item in ranked[: max(limit, 1)])):
            return {"enabled": False, "query_domain_profile": query_domain_profile, "matches": []}

        audits: list[dict[str, Any]] = []
        for item in ranked[: max(limit, 1)]:
            report = build_candidate_read_only_audit(
                profile,
                item.candidate,
                required_seed_count=self.settings.rl_required_seed_count,
                enable_theory_audit=self.settings.enable_theory_audit,
                enable_experiment_audit=self.settings.enable_experiment_audit,
            )
            report.update(
                {
                    "pattern_id": int(item.candidate.get("pattern_id", item.candidate.get("id", 0)) or 0),
                    "variant_id": int(item.candidate.get("variant_id") or (item.candidate.get("best_variant") or {}).get("id") or 0) or None,
                    "score": round(float(item.score), 4),
                    "title": str((item.candidate.get("best_variant") or {}).get("title") or item.candidate.get("title", "")),
                    "rank_reasons": item.reasons[:8],
                }
            )
            audits.append(report)
        return {
            "enabled": True,
            "query_domain_profile": query_domain_profile,
            "matches": audits,
            "summary": summarize_read_only_audit(audits),
        }
