from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from .blueprint import AlgorithmTrainingBlueprint
from .registry import TheoryRegistry


def _resolve_anchor(anchor: str) -> Any:
    parts = anchor.split(".")
    for index in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:index])
        attribute_parts = parts[index:]
        try:
            target: Any = importlib.import_module(module_name)
        except ImportError:
            continue
        for attribute in attribute_parts:
            target = getattr(target, attribute)
        return target
    raise ImportError(f"Unable to resolve anchor: {anchor}")


def resolve_anchor(anchor: str) -> Any:
    return _resolve_anchor(anchor)


def load_doc_mappings(path: Path) -> dict[str, dict[str, str]]:
    """Parse the machine-readable mapping table from docs/THEORY_TO_CODE.md."""

    mapping_rows: dict[str, dict[str, str]] = {}
    in_mapping_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped.removeprefix("## ").strip().lower()
            in_mapping_table = "mapping table" in heading
            continue
        if not in_mapping_table:
            continue
        if not stripped.startswith("|"):
            continue
        columns = [part.strip() for part in stripped.strip("|").split("|")]
        if len(columns) < 7 or columns[0] in {"mapping_id", "---"}:
            continue
        mapping_rows[columns[0]] = {
            "equation_family": columns[1],
            "code_anchor": columns[2],
            "assumption_ids": columns[3],
            "validator_anchor": columns[4],
            "metric_keys": columns[5],
            "risk_description": columns[6],
        }
    return mapping_rows


def validate_theorem_code_sync(registry: TheoryRegistry, *, doc_path: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    for objective in registry.objectives:
        try:
            _resolve_anchor(objective.code_anchor)
        except Exception as exc:  # pragma: no cover - exercised in tests
            errors.append(f"missing-objective-anchor:{objective.term_id}:{exc}")
    for mapping in registry.mappings:
        try:
            _resolve_anchor(mapping.code_anchor)
        except Exception as exc:  # pragma: no cover - exercised in tests
            errors.append(f"missing-code-anchor:{mapping.mapping_id}:{exc}")
        try:
            _resolve_anchor(mapping.validator_anchor)
        except Exception as exc:  # pragma: no cover - exercised in tests
            errors.append(f"missing-validator-anchor:{mapping.mapping_id}:{exc}")
    docs_ok = True
    if doc_path is not None:
        doc_mappings = load_doc_mappings(doc_path)
        registry_ids = {mapping.mapping_id for mapping in registry.mappings}
        doc_ids = set(doc_mappings)
        missing_in_docs = sorted(registry_ids - doc_ids)
        missing_in_registry = sorted(doc_ids - registry_ids)
        if missing_in_docs:
            docs_ok = False
            errors.extend(f"missing-doc-row:{item}" for item in missing_in_docs)
        if missing_in_registry:
            docs_ok = False
            errors.extend(f"orphan-doc-row:{item}" for item in missing_in_registry)
        for mapping in registry.mappings:
            doc_row = doc_mappings.get(mapping.mapping_id)
            if doc_row is None:
                continue
            if doc_row["code_anchor"] != mapping.code_anchor:
                docs_ok = False
                errors.append(f"doc-anchor-mismatch:{mapping.mapping_id}")
            if doc_row["validator_anchor"] != mapping.validator_anchor:
                docs_ok = False
                errors.append(f"doc-validator-mismatch:{mapping.mapping_id}")
    return {"status": "ok" if not errors else "fail", "errors": errors, "docs_ok": docs_ok}


def validate_training_blueprint_sync(blueprints: dict[str, AlgorithmTrainingBlueprint]) -> dict[str, Any]:
    errors: list[str] = []
    for algorithm_key, blueprint in blueprints.items():
        anchor_groups = (
            (f"step:{item.step_id}", item.code_anchor) for item in blueprint.steps
        )
        extra_anchors = [
            (f"loss:{item.component_id}", item.code_anchor) for item in blueprint.loss_decomposition
        ] + [
            (f"update:{item.update_id}", item.code_anchor) for item in blueprint.update_equations
        ] + [
            (f"audit:{item.hook_id}", item.code_anchor) for item in blueprint.audit_hooks
        ] + [
            (f"audit-validator:{item.hook_id}", item.validator_anchor) for item in blueprint.audit_hooks
        ] + [
            (f"ablation:{item.ablation_id}", item.code_anchor) for item in blueprint.ablation_hooks
        ] + [
            (f"report:{item.section}.{item.field_name}", item.source_anchor) for item in blueprint.reporting_template
        ] + [
            (f"artifact-producer:{item.artifact_id}", item.producer_anchor)
            for item in blueprint.artifact_expectations
            if item.producer_anchor.startswith("rl_developer_memory.")
        ] + [
            (f"artifact-validator:{item.artifact_id}", item.validator_anchor)
            for item in blueprint.artifact_expectations
            if item.validator_anchor.startswith("rl_developer_memory.")
        ]
        for anchor_id, anchor in [*list(anchor_groups), *extra_anchors]:
            try:
                _resolve_anchor(anchor)
            except Exception as exc:  # pragma: no cover - exercised in tests
                errors.append(f"missing-blueprint-anchor:{algorithm_key}:{anchor_id}:{exc}")
    return {"status": "ok" if not errors else "fail", "errors": errors}
