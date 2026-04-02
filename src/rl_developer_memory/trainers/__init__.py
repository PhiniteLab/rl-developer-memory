"""Training pipeline and stabilization policy for the additive RL backbone."""

from .pipeline import StabilizationPolicy, TrainerPipeline
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
    "EarlyStoppingController",
    "EntropyTemperatureController",
    "HardTargetUpdatePolicy",
    "ObservationNormalizer",
    "PlateauDetector",
    "RewardNormalizer",
    "SoftTargetUpdatePolicy",
    "StabilizationPolicy",
    "TrainerPipeline",
    "UpdateController",
]
