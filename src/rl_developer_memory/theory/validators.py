from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from rl_developer_memory.domains.rl_control.contracts import RLAuditFinding

from .blueprint import AlgorithmTrainingBlueprint
from .registry import TheoryRegistry
from .sync import resolve_anchor


def _finding(audit_type: str, severity: str, summary: str, **payload: Any) -> RLAuditFinding:
    return RLAuditFinding(audit_type=audit_type, severity=severity, summary=summary, payload=payload)


_STABILITY_THEOREMS = {"stability", "asymptotic_stability", "exponential_stability", "iss", "iiss", "uub", "practical_stability"}


def validate_blueprint_registry_alignment(
    blueprint: AlgorithmTrainingBlueprint,
    *,
    registry: TheoryRegistry,
) -> list[RLAuditFinding]:
    findings: list[RLAuditFinding] = []
    mapping_ids = {item.mapping_id for item in registry.mappings}
    objective_ids = {item.term_id for item in registry.objectives}
    for mapping_id in blueprint.theorem_mapping_ids:
        if mapping_id not in mapping_ids:
            findings.append(_finding("theory", "error", "Blueprint references an unknown theorem mapping.", mapping_id=mapping_id))
    for component in blueprint.loss_decomposition:
        if component.component_id not in objective_ids:
            findings.append(_finding("theory", "error", "Blueprint references an unknown loss component.", component_id=component.component_id))
        try:
            resolve_anchor(component.code_anchor)
        except Exception as exc:  # pragma: no cover - exercised in tests
            findings.append(_finding("theory", "error", "Blueprint loss component anchor cannot be resolved.", component_id=component.component_id, error=str(exc)))
    for step in blueprint.steps:
        try:
            resolve_anchor(step.code_anchor)
        except Exception as exc:  # pragma: no cover - exercised in tests
            findings.append(_finding("theory", "error", "Blueprint step anchor cannot be resolved.", step_id=step.step_id, error=str(exc)))
    if len(blueprint.steps) != 10:
        findings.append(_finding("theory", "error", "Training blueprint must expose the canonical 10-step flow.", step_count=len(blueprint.steps)))
    if not blueprint.reporting_template:
        findings.append(_finding("review", "error", "Training blueprint is missing a reporting template."))
    return findings


def validate_experiment_assumptions(
    *,
    blueprint: AlgorithmTrainingBlueprint,
    registry: TheoryRegistry,
    documented_assumptions: Sequence[str],
    documented_hidden_assumptions: Sequence[str],
    theorem_claim_type: str,
    lyapunov_candidate: str,
    audit_hooks: Sequence[str],
) -> list[RLAuditFinding]:
    findings: list[RLAuditFinding] = []
    mapping_index = {item.mapping_id: item for item in registry.mappings}
    required_assumptions: set[str] = set()
    for mapping_id in blueprint.theorem_mapping_ids:
        mapping = mapping_index.get(mapping_id)
        if mapping is not None:
            required_assumptions.update(mapping.assumption_ids)
    documented = {str(item).strip() for item in documented_assumptions if str(item).strip()}
    hidden_documented = {str(item).strip() for item in documented_hidden_assumptions if str(item).strip()}
    missing_required = sorted(required_assumptions - documented)
    if missing_required:
        findings.append(
            _finding(
                "theory",
                "warning",
                "Required theorem assumptions are not fully documented by the experiment config.",
                missing_assumptions=missing_required,
            )
        )
    hidden_gaps = sorted(set(blueprint.hidden_assumptions) - hidden_documented)
    if hidden_gaps:
        findings.append(
            _finding(
                "theory",
                "warning",
                "Hidden assumptions for the training blueprint are not explicitly documented.",
                hidden_assumption_gaps=hidden_gaps,
            )
        )
    normalized_theorem = str(theorem_claim_type or "").strip().lower()
    configured_hooks = {str(item).strip() for item in audit_hooks if str(item).strip()}
    if normalized_theorem == "hjb_optimality" and "hjb_hook" not in configured_hooks:
        findings.append(_finding("theory", "warning", "HJB theorem claim is present but hjb_hook is not enabled."))
    if normalized_theorem in _STABILITY_THEOREMS and "lyapunov_hook" not in configured_hooks:
        findings.append(_finding("theory", "warning", "Stability theorem claim is present but lyapunov_hook is not enabled."))
    if normalized_theorem in _STABILITY_THEOREMS and not str(lyapunov_candidate).strip():
        findings.append(_finding("theory", "warning", "Stability theorem claim is present but lyapunov_candidate is missing."))
    return findings


def audit_seed_variance(
    *,
    seed_count: int,
    required_seed_count: int,
    production_min_seed_count: int,
    return_std: float | None,
    confidence_interval: Sequence[float] | None,
    variance_budget: float,
) -> list[RLAuditFinding]:
    findings: list[RLAuditFinding] = []
    if seed_count < required_seed_count:
        findings.append(
            _finding(
                "experiment",
                "warning",
                "Seed count is below the configured evaluation threshold.",
                seed_count=seed_count,
                required_seed_count=required_seed_count,
            )
        )
    if seed_count >= production_min_seed_count and return_std is None and not confidence_interval:
        findings.append(_finding("experiment", "warning", "High-seed evaluation is missing return_std or confidence_interval evidence."))
    if return_std is not None and return_std > variance_budget:
        findings.append(
            _finding(
                "experiment",
                "warning",
                "Observed return variance exceeds the configured variance budget.",
                return_std=return_std,
                variance_budget=variance_budget,
            )
        )
    if confidence_interval and len(confidence_interval) == 2:
        try:
            width = float(confidence_interval[1]) - float(confidence_interval[0])
        except (TypeError, ValueError):
            findings.append(_finding("experiment", "error", "confidence_interval bounds must be numeric for variance audit."))
        else:
            if width > 2 * variance_budget:
                findings.append(
                    _finding(
                        "experiment",
                        "warning",
                        "Confidence interval width exceeds twice the configured variance budget.",
                        confidence_interval_width=width,
                        variance_budget=variance_budget,
                    )
                )
    return findings


def validate_result_artifacts(
    artifact_refs: Sequence[Mapping[str, Any]] | None,
    *,
    blueprint: AlgorithmTrainingBlueprint,
    expected_artifacts: Sequence[str] = (),
) -> list[RLAuditFinding]:
    findings: list[RLAuditFinding] = []
    artifact_refs = artifact_refs or []
    available_kinds = {
        str(item.get("kind", "")).strip()
        for item in artifact_refs
        if isinstance(item, Mapping) and str(item.get("kind", "")).strip()
    }
    required_kinds = {item.kind for item in blueprint.artifact_expectations if item.required}
    required_kinds.update(str(item).strip() for item in expected_artifacts if str(item).strip())
    missing = sorted(kind for kind in required_kinds if kind not in available_kinds)
    if missing:
        findings.append(
            _finding(
                "runtime",
                "warning",
                "Result artifacts are missing required blueprint evidence.",
                missing_artifact_kinds=missing,
            )
        )
    return findings
