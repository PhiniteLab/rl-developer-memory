"""Theory-to-code contracts and registry helpers."""

from .blueprint import (
    AblationHookSpec,
    AlgorithmTrainingBlueprint,
    ArtifactExpectationSpec,
    AuditHookSpec,
    BlueprintStepSpec,
    FailureModeSpec,
    LossDecompositionSpec,
    ReportingFieldSpec,
    UpdateEquationSpec,
    build_training_blueprint_catalog,
)
from .registry import (
    AssumptionSpec,
    NotationSpec,
    ObjectiveTerm,
    RiskMetricBinding,
    TheoremMapping,
    build_default_theory_registry,
    validate_assumption_bindings,
)
from .sync import load_doc_mappings, resolve_anchor, validate_theorem_code_sync, validate_training_blueprint_sync
from .validators import (
    audit_seed_variance,
    validate_blueprint_registry_alignment,
    validate_experiment_assumptions,
    validate_result_artifacts,
)

__all__ = [
    "AblationHookSpec",
    "AlgorithmTrainingBlueprint",
    "ArtifactExpectationSpec",
    "AssumptionSpec",
    "AuditHookSpec",
    "BlueprintStepSpec",
    "FailureModeSpec",
    "LossDecompositionSpec",
    "NotationSpec",
    "ObjectiveTerm",
    "ReportingFieldSpec",
    "RiskMetricBinding",
    "TheoremMapping",
    "UpdateEquationSpec",
    "audit_seed_variance",
    "build_default_theory_registry",
    "build_training_blueprint_catalog",
    "load_doc_mappings",
    "resolve_anchor",
    "validate_assumption_bindings",
    "validate_blueprint_registry_alignment",
    "validate_experiment_assumptions",
    "validate_result_artifacts",
    "validate_theorem_code_sync",
    "validate_training_blueprint_sync",
]
