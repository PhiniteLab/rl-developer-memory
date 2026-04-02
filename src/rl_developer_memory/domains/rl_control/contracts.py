from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, TypedDict


class ArtifactRef(TypedDict, total=False):
    kind: str
    uri: str
    description: str
    checksum: str
    bytes: int


class ProblemProfile(TypedDict, total=False):
    problem_family: str
    system_name: str
    task_name: str
    dynamics_class: str
    state_dimension: int
    action_dimension: int
    observation_space: str
    action_space: str
    assumptions: list[str]
    disturbance_model: str
    sampling_time: float
    theorem_claim_type: str
    lyapunov_candidate: str


class RunManifest(TypedDict, total=False):
    algorithm_family: str
    runtime_stage: str
    seed_count: int
    train_env_id: str
    eval_env_id: str
    baseline_names: list[str]
    device: str
    simulator: str
    action_bounds: list[float]
    normalization: dict[str, Any]


class MetricsPayload(TypedDict, total=False):
    return_mean: float
    return_std: float
    tracking_rmse: float
    control_effort: float
    constraint_violation_rate: float
    crash_rate: float
    confidence_interval: list[float]


class ValidationPayload(TypedDict, total=False):
    seed_count: int
    theory_reviewed: bool
    baseline_comparison: bool
    hardware_validated: bool
    production_verified: bool
    reviewed_by: str
    notes: str
    validation_tier: str


@dataclass(slots=True)
class RLAuditFinding:
    audit_type: str
    severity: str
    status: str = "open"
    summary: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def coerce_json_value(raw: Any, *, fallback: Any) -> Any:
    if raw in (None, "", b""):
        return fallback
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
