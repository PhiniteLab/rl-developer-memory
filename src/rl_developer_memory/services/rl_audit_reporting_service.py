from __future__ import annotations

from typing import Any

from ..domains.rl_control import (
    build_pattern_audit_report,
    build_review_item_audit_report,
    summarize_review_queue_reports,
)
from ..models import PatternBundle
from ..storage import RLDeveloperMemoryStore


class RLAuditReportingService:
    """Build reviewer-facing RL/control audit summaries for stored records and review items."""

    def __init__(self, store: RLDeveloperMemoryStore) -> None:
        self.store = store

    def bundle_report(self, bundle: PatternBundle) -> dict[str, Any]:
        return build_pattern_audit_report(bundle.pattern, bundle.audit_findings, bundle.artifact_refs)

    def pattern_report(self, pattern_id: int, *, audit_limit: int = 25, artifact_limit: int = 25) -> dict[str, Any]:
        bundle = self.store.get_pattern(
            pattern_id,
            include_examples=False,
            examples_limit=0,
            include_variants=False,
            variants_limit=0,
            include_episodes=False,
            episodes_limit=0,
            include_audit_findings=True,
            audit_limit=max(audit_limit, 1),
            include_artifact_refs=True,
            artifact_limit=max(artifact_limit, 1),
        )
        if bundle is None:
            return {"enabled": False}
        return self.bundle_report(bundle)

    def enrich_review_item(self, item: dict[str, Any], *, audit_limit: int = 10, artifact_limit: int = 10) -> dict[str, Any]:
        enriched = dict(item)
        pattern_id = int(enriched.get("pattern_id", 0) or 0)
        if pattern_id > 0:
            bundle = self.store.get_pattern(
                pattern_id,
                include_examples=False,
                examples_limit=0,
                include_variants=False,
                variants_limit=0,
                include_episodes=False,
                episodes_limit=0,
                include_audit_findings=True,
                audit_limit=max(audit_limit, 1),
                include_artifact_refs=True,
                artifact_limit=max(artifact_limit, 1),
            )
            if bundle is not None:
                enriched["audit_report"] = build_review_item_audit_report(
                    enriched,
                    pattern=bundle.pattern,
                    findings=bundle.audit_findings,
                    artifact_refs=bundle.artifact_refs,
                )
                return enriched
        enriched["audit_report"] = build_review_item_audit_report(enriched)
        return enriched

    def enrich_review_queue(self, items: list[dict[str, Any]], *, audit_limit: int = 10, artifact_limit: int = 10) -> dict[str, Any]:
        enriched = [self.enrich_review_item(item, audit_limit=audit_limit, artifact_limit=artifact_limit) for item in items]
        return {"items": enriched, "summary": summarize_review_queue_reports(enriched)}
