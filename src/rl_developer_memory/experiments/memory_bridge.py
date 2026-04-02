from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rl_developer_memory.domains.rl_control.validators import (
    validate_artifact_refs,
    validate_experiment_consistency,
    validate_metrics_payload,
    validate_problem_profile,
    validate_run_manifest,
    validate_theory_consistency,
    validate_validation_payload,
)


@dataclass(slots=True)
class RLMemoryBridge:
    """Convert experiment reports into payloads consumable by the MCP memory surface."""

    def build_payloads(self, report: Any) -> dict[str, Any]:
        payload = {
            "problem_profile_json": report.problem_profile,
            "run_manifest_json": report.run_manifest,
            "metrics_json": report.metrics_payload,
            "validation_json": report.validation_payload,
            "audit_findings": self.audit_report(report),
        }
        if getattr(report, "artifact_refs", None) is not None:
            payload["artifact_refs_json"] = report.artifact_refs
        if getattr(report, "training_blueprint", None) is not None:
            payload["training_blueprint_json"] = report.training_blueprint
        return payload

    def audit_report(self, report: Any) -> list[dict[str, Any]]:
        findings = []
        findings.extend(item.to_record() for item in validate_problem_profile(report.problem_profile))
        findings.extend(item.to_record() for item in validate_run_manifest(report.run_manifest, required_seed_count=int(report.validation_payload.get("seed_count", 3) or 3)))
        findings.extend(item.to_record() for item in validate_metrics_payload(report.metrics_payload))
        findings.extend(item.to_record() for item in validate_validation_payload(report.validation_payload, required_seed_count=int(report.validation_payload.get("seed_count", 3) or 3)))
        findings.extend(
            item.to_record()
            for item in validate_experiment_consistency(
                problem_family=str(report.problem_profile.get("problem_family", "")),
                algorithm_family=str(report.run_manifest.get("algorithm_family", "")),
                runtime_stage=str(report.run_manifest.get("runtime_stage", "")),
                run_manifest=report.run_manifest,
                metrics_payload=report.metrics_payload,
                validation_payload=report.validation_payload,
                required_seed_count=int(report.validation_payload.get("seed_count", 3) or 3),
            )
        )
        findings.extend(
            item.to_record()
            for item in validate_theory_consistency(
                problem_family=str(report.problem_profile.get("problem_family", "")),
                theorem_claim_type=str(report.problem_profile.get("theorem_claim_type", "")),
                problem_profile=report.problem_profile,
                validation_payload=report.validation_payload,
                algorithm_family=str(report.run_manifest.get("algorithm_family", "")),
                run_manifest=report.run_manifest,
            )
        )
        findings.extend(item.to_record() for item in validate_artifact_refs(getattr(report, "artifact_refs", None)))
        findings.extend(list(report.theory_sync.get("audit_findings", [])))
        return findings
