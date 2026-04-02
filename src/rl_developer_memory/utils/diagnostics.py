from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha1
from typing import Any, Mapping


@dataclass(slots=True, frozen=True)
class FailureSignature:
    family: str
    signature: str
    step: int
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class AnomalyEvent:
    step: int
    category: str
    message: str
    values: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FailureSignatureCapture:
    """Create stable, redacted failure signatures for runtime anomalies."""

    def capture(self, *, family: str, step: int, details: Mapping[str, Any]) -> FailureSignature:
        normalized = "|".join(f"{key}={details[key]!r}" for key in sorted(details))
        digest = sha1(f"{family}|{normalized}".encode("utf-8")).hexdigest()[:12]
        return FailureSignature(family=family, signature=f"{family}:{digest}", step=int(step), details=dict(details))


@dataclass(slots=True)
class TrainingDiagnosticsCollector:
    """Collect structured runtime diagnostics across the training pipeline."""

    seed: int | None = None
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    resumes: list[dict[str, Any]] = field(default_factory=list)
    rollbacks: list[dict[str, Any]] = field(default_factory=list)
    anomalies: list[AnomalyEvent] = field(default_factory=list)
    failure_signatures: list[FailureSignature] = field(default_factory=list)
    temperature_history: list[float] = field(default_factory=list)
    target_updates: list[dict[str, float]] = field(default_factory=list)
    normalizers: dict[str, dict[str, Any]] = field(default_factory=dict)
    guards: list[dict[str, Any]] = field(default_factory=list)
    stop_reasons: list[str] = field(default_factory=list)

    def record_seed(self, seed: int) -> None:
        self.seed = int(seed)

    def record_checkpoint(self, *, step: int, path: str, stable: bool) -> None:
        self.checkpoints.append({"step": int(step), "path": path, "stable": bool(stable)})

    def record_resume(self, *, source: str, loaded: bool) -> None:
        self.resumes.append({"source": source, "loaded": bool(loaded)})

    def record_rollback(self, *, step: int, restored_path: str) -> None:
        self.rollbacks.append({"step": int(step), "restored_path": restored_path})

    def record_anomaly(self, *, step: int, category: str, message: str, values: Mapping[str, Any]) -> None:
        self.anomalies.append(AnomalyEvent(step=int(step), category=category, message=message, values=dict(values)))

    def record_failure_signature(self, signature: FailureSignature) -> None:
        self.failure_signatures.append(signature)

    def record_temperature(self, value: float) -> None:
        self.temperature_history.append(float(value))

    def record_target_update(self, payload: Mapping[str, float]) -> None:
        self.target_updates.append({str(key): float(value) for key, value in payload.items()})

    def record_normalizer(self, name: str, state: Mapping[str, Any]) -> None:
        self.normalizers[str(name)] = dict(state)

    def record_guard(self, *, step: int, name: str, payload: Mapping[str, Any]) -> None:
        item = {"step": int(step), "name": str(name)}
        item.update({str(key): value for key, value in payload.items()})
        self.guards.append(item)

    def record_stop_reason(self, reason: str) -> None:
        self.stop_reasons.append(str(reason))

    def summary(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "checkpoint_count": len(self.checkpoints),
            "resume_count": len(self.resumes),
            "rollback_count": len(self.rollbacks),
            "anomaly_count": len(self.anomalies),
            "failure_signature_count": len(self.failure_signatures),
            "latest_temperature": self.temperature_history[-1] if self.temperature_history else None,
            "last_stop_reason": self.stop_reasons[-1] if self.stop_reasons else "",
            "normalizers": self.normalizers,
            "checkpoints": list(self.checkpoints),
            "resumes": list(self.resumes),
            "rollbacks": list(self.rollbacks),
            "anomalies": [item.to_dict() for item in self.anomalies],
            "failure_signatures": [item.to_dict() for item in self.failure_signatures],
            "guards": list(self.guards),
        }
