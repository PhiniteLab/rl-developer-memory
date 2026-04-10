from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..domains.rl_control import (
    coerce_json_value,
    decide_promotion,
    infer_problem_family,
    normalize_algorithm_family,
    normalize_memory_kind,
    normalize_problem_family,
    normalize_runtime_stage,
    normalize_sim2real_stage,
    normalize_theorem_claim_type,
    normalize_validation_tier,
    validate_artifact_refs,
    validate_experiment_consistency,
    validate_metrics_payload,
    validate_problem_profile,
    validate_run_manifest,
    validate_theory_consistency,
    validate_validation_payload,
)
from ..matching import IssueMatcher
from ..normalization import build_query_profile, derive_strategy_key, infer_strategy_hints, parse_tag_string
from ..retrieval import DenseEmbeddingIndex
from ..security import sanitize_json_text, sanitize_text
from ..storage import RLDeveloperMemoryStore
from .consolidation_service import ConsolidationService


class RecordResolutionService:
    """Write verified fixes into the pattern/variant/episode memory model."""

    def __init__(self, store: RLDeveloperMemoryStore, matcher: IssueMatcher) -> None:
        self.store = store
        self.matcher = matcher
        self.consolidation_service = ConsolidationService(store, matcher)
        self.dense_index = DenseEmbeddingIndex(store)

    @staticmethod
    def _coerce_mapping(value: Any) -> dict[str, Any]:
        payload = coerce_json_value(value, fallback={})
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _coerce_sequence(value: Any) -> list[dict[str, Any]]:
        payload = coerce_json_value(value, fallback=[])
        if not isinstance(payload, list):
            return []
        return [dict(item) for item in payload if isinstance(item, Mapping)]

    @staticmethod
    def _count_findings_by_severity(findings: Sequence[Mapping[str, Any]]) -> dict[str, int]:
        counts = {"info": 0, "warning": 0, "error": 0, "critical": 0}
        for finding in findings:
            severity = str(finding.get("severity", "info") or "info").lower()
            if severity not in counts:
                counts[severity] = 0
            counts[severity] += 1
        return counts

    def record(
        self,
        *,
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
    ) -> dict[str, Any]:
        extra_tags = parse_tag_string(tags)
        sanitized_raw_error = sanitize_text(raw_error, enabled=self.store.settings.enable_redaction, max_chars=8000)
        sanitized_context = sanitize_text(context, enabled=self.store.settings.enable_redaction, max_chars=8000)
        sanitized_stack_excerpt = sanitize_text(stack_excerpt, enabled=self.store.settings.enable_redaction, max_chars=4000)
        sanitized_env_json = sanitize_json_text(
            env_json,
            enabled=self.store.settings.enable_redaction,
            max_chars=self.store.settings.env_json_max_chars,
        )
        sanitized_verification_output = sanitize_text(
            verification_output,
            enabled=self.store.settings.enable_redaction,
            max_chars=self.store.settings.verification_output_max_chars,
        )
        sanitized_resolution_notes = sanitize_text(
            resolution_notes,
            enabled=self.store.settings.enable_redaction,
            max_chars=self.store.settings.note_max_chars,
        )
        profile = build_query_profile(
            error_text=raw_error,
            context=context if context else canonical_symptom,
            command=command,
            file_path=file_path,
            stack_excerpt=stack_excerpt,
            env_json=env_json,
            repo_name=repo_name,
            git_commit=git_commit,
            hint_family=error_family,
            hint_root_cause=root_cause_class,
            extra_tags=extra_tags,
            project_scope=project_scope,
            user_scope=user_scope.strip() or self.store.settings.default_user_scope,
        )

        normalized_symptom = canonical_symptom.strip() or profile.normalized_text[:400]
        merged_tags = list(dict.fromkeys(profile.tags + extra_tags))
        resolution_strategy_hints = infer_strategy_hints(
            sanitized_raw_error,
            canonical_fix,
            prevention_rule,
            verification_steps,
            sanitized_resolution_notes,
            patch_summary,
            command,
            file_path,
        )
        strategy_hints = list(dict.fromkeys(profile.strategy_hints + resolution_strategy_hints))
        strategy_key = derive_strategy_key(
            canonical_fix,
            prevention_rule,
            verification_steps,
            sanitized_resolution_notes,
            patch_summary,
            command,
            file_path,
        )
        plan = self.consolidation_service.plan(
            profile=profile,
            title=title.strip(),
            project_scope=project_scope.strip() or "global",
            canonical_symptom=normalized_symptom,
            merged_tags=merged_tags,
            command=command,
            file_path=file_path,
            stack_excerpt=sanitized_stack_excerpt,
            env_json=sanitized_env_json,
            repo_name=repo_name,
            git_commit=git_commit,
            session_id=session_id,
        )

        problem_profile = self._coerce_mapping(problem_profile_json)
        variant_profile = self._coerce_mapping(variant_profile_json)
        run_manifest = self._coerce_mapping(run_manifest_json)
        metrics_payload = self._coerce_mapping(metrics_json)
        validation_payload = self._coerce_mapping(validation_json)
        artifact_refs = self._coerce_sequence(artifact_refs_json)
        sim2real_profile = self._coerce_mapping(sim2real_profile_json)

        rl_mode_enabled = bool(
            self.store.settings.enable_rl_control
            or self.store.settings.domain_mode == "rl_control"
            or str(domain).strip() == "rl_control"
            or str(memory_kind).strip()
            or str(problem_family).strip()
            or str(theorem_claim_type).strip()
            or str(algorithm_family).strip()
            or str(runtime_stage).strip()
            or problem_profile
            or variant_profile
            or run_manifest
            or metrics_payload
            or validation_payload
            or artifact_refs
            or sim2real_profile
        )

        audit_findings: list[dict[str, Any]] = []
        promotion_summary: dict[str, Any] = {
            "requested_tier": "observed",
            "applied_tier": "observed",
            "status": "applied",
            "review_required": False,
            "review_mode": "",
            "review_reason": "",
            "reasons": [],
            "blockers": [],
            "finding_counts": {"info": 0, "warning": 0, "error": 0, "critical": 0},
        }
        resolved_memory_kind = "failure_pattern"
        resolved_problem_family = "generic"
        resolved_theorem_claim_type = "none"
        resolved_validation_tier = "observed"
        resolved_algorithm_family = ""
        resolved_runtime_stage = ""

        if rl_mode_enabled:
            family_hint = infer_problem_family(
                " ".join(
                    [
                        title,
                        raw_error,
                        canonical_fix,
                        prevention_rule,
                        canonical_symptom,
                        context,
                        patch_summary,
                    ]
                )
            )
            resolved_problem_family = normalize_problem_family(
                str(problem_family or problem_profile.get("problem_family") or family_hint or "generic"),
                default="generic",
            )
            resolved_theorem_claim_type = normalize_theorem_claim_type(
                str(theorem_claim_type or problem_profile.get("theorem_claim_type") or "none"),
                default="none",
            )
            resolved_algorithm_family = normalize_algorithm_family(
                str(algorithm_family or run_manifest.get("algorithm_family") or variant_profile.get("algorithm_family") or ""),
                default="",
            )
            resolved_runtime_stage = normalize_runtime_stage(
                str(runtime_stage or run_manifest.get("runtime_stage") or variant_profile.get("runtime_stage") or ""),
                default="",
            )
            resolved_memory_kind = normalize_memory_kind(
                str(
                    memory_kind
                    or (
                        "theory_pattern"
                        if resolved_theorem_claim_type not in {"", "none"}
                        else "experiment_pattern"
                        if run_manifest or metrics_payload
                        else "failure_pattern"
                    )
                )
            )
            sim_stage = normalize_sim2real_stage(str(sim2real_profile.get("stage", "")), default="")
            if sim_stage:
                sim2real_profile["stage"] = sim_stage
            if resolved_problem_family:
                problem_profile["problem_family"] = resolved_problem_family
            if resolved_theorem_claim_type:
                problem_profile["theorem_claim_type"] = resolved_theorem_claim_type
            if resolved_algorithm_family:
                variant_profile["algorithm_family"] = resolved_algorithm_family
                run_manifest["algorithm_family"] = resolved_algorithm_family
            if resolved_runtime_stage:
                variant_profile["runtime_stage"] = resolved_runtime_stage
                run_manifest["runtime_stage"] = resolved_runtime_stage
            if run_manifest.get("seed_count") is not None and validation_payload.get("seed_count") is None:
                validation_payload["seed_count"] = run_manifest.get("seed_count")

            is_experiment_like = resolved_memory_kind in {"experiment_pattern", "sim2real_pattern"} or bool(run_manifest or metrics_payload)
            is_theory_like = resolved_memory_kind == "theory_pattern" or resolved_theorem_claim_type not in {"", "none"}

            audit_findings.extend(finding.to_record() for finding in validate_problem_profile(problem_profile))
            if is_experiment_like or run_manifest:
                audit_findings.extend(
                    finding.to_record()
                    for finding in validate_run_manifest(
                        run_manifest,
                        required_seed_count=self.store.settings.rl_required_seed_count,
                    )
                )
            if is_experiment_like or metrics_payload:
                audit_findings.extend(finding.to_record() for finding in validate_metrics_payload(metrics_payload))
            audit_findings.extend(
                finding.to_record()
                for finding in validate_validation_payload(
                    validation_payload,
                    required_seed_count=self.store.settings.rl_required_seed_count,
                )
            )
            audit_findings.extend(
                finding.to_record()
                for finding in validate_artifact_refs(
                    artifact_refs,
                    max_refs=self.store.settings.rl_max_artifact_refs,
                )
            )
            if is_experiment_like:
                audit_findings.extend(
                    finding.to_record()
                    for finding in validate_experiment_consistency(
                        problem_family=resolved_problem_family,
                        algorithm_family=resolved_algorithm_family,
                        runtime_stage=resolved_runtime_stage,
                        run_manifest=run_manifest,
                        metrics_payload=metrics_payload,
                        validation_payload=validation_payload,
                        sim2real_profile=sim2real_profile,
                        required_seed_count=self.store.settings.rl_required_seed_count,
                    )
                )
            if is_theory_like:
                audit_findings.extend(
                    finding.to_record()
                    for finding in validate_theory_consistency(
                        problem_family=resolved_problem_family,
                        theorem_claim_type=resolved_theorem_claim_type,
                        problem_profile=problem_profile,
                        validation_payload=validation_payload,
                        algorithm_family=resolved_algorithm_family,
                        run_manifest=run_manifest,
                    )
                )

            promotion_decision = decide_promotion(
                audit_findings,
                validation_payload,
                memory_kind=resolved_memory_kind,
                theorem_claim_type=resolved_theorem_claim_type,
                requested_tier=validation_tier,
                strict=self.store.settings.rl_strict_promotion,
                required_seed_count=self.store.settings.rl_required_seed_count,
                production_min_seed_count=self.store.settings.rl_production_min_seed_count,
                candidate_warning_budget=self.store.settings.rl_candidate_warning_budget,
                review_gated=self.store.settings.rl_review_gated_promotion,
            )
            promotion_summary = promotion_decision.to_record()
            resolved_validation_tier = normalize_validation_tier(promotion_decision.applied_tier, default="observed")
            validation_payload["validation_tier"] = resolved_validation_tier
            validation_payload["promotion_requested_tier"] = promotion_decision.requested_tier
            validation_payload["promotion_review_required"] = promotion_decision.review_required
            validation_payload["promotion_status"] = promotion_decision.status
            if promotion_decision.review_reason:
                validation_payload["promotion_review_reason"] = promotion_decision.review_reason
            if promotion_decision.blockers:
                validation_payload["promotion_blockers"] = promotion_decision.blockers

        evidence_payload = {
            "validation": validation_payload,
            "finding_counts": self._count_findings_by_severity(audit_findings),
            "required_seed_count": self.store.settings.rl_required_seed_count,
            "promotion": promotion_summary,
        }

        result = self.store.record_resolution(
            matched_pattern_id=plan.matched_pattern_id,
            matched_variant_id=plan.matched_variant_id,
            pattern_payload={
                "title": title.strip(),
                "project_scope": project_scope.strip() or "global",
                "domain": domain.strip() or "generic",
                "error_family": profile.error_family,
                "root_cause_class": profile.root_cause_class,
                "canonical_symptom": normalized_symptom,
                "canonical_fix": canonical_fix.strip(),
                "prevention_rule": prevention_rule.strip(),
                "verification_steps": verification_steps.strip(),
                "tags": merged_tags,
                "signature": plan.pattern_signature,
                "confidence": 0.78,
                "memory_kind": resolved_memory_kind,
                "problem_family": resolved_problem_family,
                "theorem_claim_type": resolved_theorem_claim_type,
                "validation_tier": resolved_validation_tier,
                "problem_profile": problem_profile,
                "validation": validation_payload,
            },
            variant_payload={
                "variant_key": plan.proposed_variant_key,
                "title": title.strip(),
                "canonical_fix": canonical_fix.strip(),
                "verification_steps": verification_steps.strip(),
                "rollback_steps": "",
                "tags": merged_tags,
                "repo_fingerprint": profile.repo_fingerprint,
                "env_fingerprint": profile.env_fingerprint,
                "command_signature": profile.command_signature,
                "file_path_signature": profile.path_signature,
                "stack_signature": profile.stack_signature,
                "patch_hash": patch_hash.strip(),
                "patch_summary": patch_summary.strip(),
                "confidence": 0.78,
                "memory_strength": 0.65,
                "status": "provisional" if plan.requires_review else "active",
                "strategy_key": strategy_key,
                "strategy_hints": strategy_hints,
                "entity_slots": profile.entity_slots,
                "algorithm_family": resolved_algorithm_family,
                "runtime_stage": resolved_runtime_stage,
                "variant_profile": variant_profile,
                "sim2real_profile": sim2real_profile,
                "applicability": {
                    "project_scope": project_scope,
                    "error_family": profile.error_family,
                    "root_cause_class": profile.root_cause_class,
                    "command": command,
                    "file_path": file_path,
                    "repo_name": repo_name,
                    "problem_family": resolved_problem_family,
                },
                "negative_applicability": {},
            },
            episode_payload={
                "session_id": session_id,
                "project_scope": project_scope,
                "user_scope": profile.user_scope,
                "repo_name": repo_name,
                "repo_fingerprint": profile.repo_fingerprint,
                "git_commit": git_commit,
                "source": "manual",
                "raw_error": sanitized_raw_error,
                "normalized_error": profile.normalized_text,
                "context": sanitized_context,
                "stack_excerpt": sanitized_stack_excerpt,
                "command": command,
                "file_path": file_path,
                "exception_types": profile.exception_types,
                "query_tokens": profile.tokens,
                "entity_slots": profile.entity_slots,
                "strategy_hints": strategy_hints,
                "env_fingerprint": profile.env_fingerprint,
                "env_json": sanitized_env_json,
                "patch_hash": patch_hash.strip(),
                "patch_summary": patch_summary.strip(),
                "verification_command": verification_command.strip(),
                "verification_output": sanitized_verification_output,
                "outcome": "verified",
                "consolidation_status": "review" if plan.requires_review else "attached",
                "resolution_notes": sanitized_resolution_notes,
                "run_manifest": run_manifest,
                "metrics": metrics_payload,
                "artifact_refs": artifact_refs,
                "evidence": evidence_payload,
            },
            example_payload={
                "raw_error": sanitized_raw_error,
                "normalized_error": profile.normalized_text,
                "context": sanitized_context,
                "file_path": file_path,
                "command": command,
                "verified_fix": canonical_fix,
            },
            review_payload=(
                {
                    "project_scope": project_scope,
                    "user_scope": profile.user_scope,
                    "repo_name": repo_name,
                    "strategy_key": strategy_key,
                    "review_reason": "; ".join(
                        part
                        for part in (
                            ", ".join(plan.reasons) if plan.requires_review and plan.reasons else (plan.match_strategy if plan.requires_review else ""),
                            promotion_summary.get("review_reason", "") if promotion_summary.get("review_required") else "",
                        )
                        if part
                    )
                    or "review",
                    "entity_slots": profile.entity_slots,
                    "metadata": {
                        "matched_pattern_id": plan.matched_pattern_id,
                        "matched_variant_id": plan.matched_variant_id,
                        "proposed_pattern_key": plan.proposed_pattern_key,
                        "proposed_variant_key": plan.proposed_variant_key,
                        "score": round(plan.consolidation_score, 4),
                        "reasons": plan.reasons,
                        "match_strategy": plan.match_strategy,
                        "variant_strategy": plan.variant_strategy,
                        "memory_kind": resolved_memory_kind,
                        "problem_family": resolved_problem_family,
                        "validation_tier": resolved_validation_tier,
                        "review_mode": (
                            "mixed"
                            if plan.requires_review and promotion_summary.get("review_required")
                            else "consolidation"
                            if plan.requires_review
                            else str(promotion_summary.get("review_mode", "promotion") or "promotion")
                        ),
                        "promotion_requested_tier": promotion_summary.get("requested_tier", resolved_validation_tier),
                        "promotion_applied_tier": promotion_summary.get("applied_tier", resolved_validation_tier),
                        "promotion_status": promotion_summary.get("status", "applied"),
                        "promotion_reasons": promotion_summary.get("reasons", []),
                        "promotion_blockers": promotion_summary.get("blockers", []),
                        "finding_counts": promotion_summary.get("finding_counts", {}),
                    },
                }
                if plan.requires_review or bool(promotion_summary.get("review_required"))
                else None
            ),
            audit_findings_payload=audit_findings,
        )
        if self.store.settings.enable_dense_retrieval:
            self.dense_index.refresh_pattern(int(result["pattern_id"]))
            self.dense_index.refresh_variant(int(result["variant_id"]))

        result["match_strategy"] = plan.match_strategy
        result["variant_strategy"] = plan.variant_strategy
        result["consolidation"] = {
            "matched_pattern_id": plan.matched_pattern_id,
            "matched_variant_id": plan.matched_variant_id,
            "pattern_key": plan.pattern_signature,
            "proposed_variant_key": plan.proposed_variant_key,
            "score": round(plan.consolidation_score, 4),
            "requires_review": plan.requires_review,
            "reasons": plan.reasons,
        }
        result["query_profile"] = {
            "error_family": profile.error_family,
            "root_cause_class": profile.root_cause_class,
            "pattern_key": plan.pattern_signature,
            "variant_key": plan.proposed_variant_key,
            "strategy_key": strategy_key,
            "strategy_hints": strategy_hints,
            "entity_slots": profile.entity_slots,
            "user_scope": profile.user_scope,
        }
        result["promotion"] = promotion_summary
        result["rl_control"] = {
            "enabled": rl_mode_enabled,
            "memory_kind": resolved_memory_kind,
            "problem_family": resolved_problem_family,
            "theorem_claim_type": resolved_theorem_claim_type,
            "validation_tier": resolved_validation_tier,
            "requested_validation_tier": promotion_summary.get("requested_tier", resolved_validation_tier),
            "promotion_status": promotion_summary.get("status", "applied"),
            "algorithm_family": resolved_algorithm_family,
            "runtime_stage": resolved_runtime_stage,
            "finding_counts": self._count_findings_by_severity(audit_findings),
        }
        result["note"] = (
            "Resolution stored atomically as pattern + variant + episode. "
            "Schema v12 now preserves RL/control metadata, audit findings, artifact references, and review-gated promotion state without breaking the existing MCP surface. "
            "Use issue_get to inspect context-specific variants before reusing a fix."
        )
        return result
