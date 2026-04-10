"""Training pipeline and stabilization policy for the additive RL backbone."""

from .pipeline import StabilizationPolicy, TrainerPipeline
from .schedules import (
    ConstantLR,
    CosineAnnealingLR,
    ExponentialDecayLR,
    ExponentialEpsilonDecay,
    LinearDecayLR,
    LinearEpsilonDecay,
    LRSchedule,
    WarmupLR,
)
from .stability import (
    EarlyStoppingController,
    EntropyTemperatureController,
    HardTargetUpdatePolicy,
    ObservationNormalizer,
    PlateauDetector,
    RewardNormalizer,
    SoftTargetUpdatePolicy,
    UpdateController,
)

__all__ = [
    "ConstantLR",
    "CosineAnnealingLR",
    "EarlyStoppingController",
    "EntropyTemperatureController",
    "ExponentialDecayLR",
    "ExponentialEpsilonDecay",
    "HardTargetUpdatePolicy",
    "LRSchedule",
    "LinearDecayLR",
    "LinearEpsilonDecay",
    "ObservationNormalizer",
    "PlateauDetector",
    "RewardNormalizer",
    "SoftTargetUpdatePolicy",
    "StabilizationPolicy",
    "TrainerPipeline",
    "UpdateController",
    "WarmupLR",
]
