from __future__ import annotations

import os
import random
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SeedReport:
    seed: int
    deterministic: bool
    numpy_seeded: bool


@dataclass(slots=True)
class DeterministicSeedDiscipline:
    """Central seed coordinator shared by trainers and experiments."""

    seed: int
    deterministic: bool = True
    last_report: SeedReport | None = None

    def apply(self) -> SeedReport:
        self.last_report = seed_everything(self.seed, deterministic=self.deterministic)
        return self.last_report

    def derive(self, offset: int) -> int:
        return int(self.seed) + int(offset)

    def state_dict(self) -> dict[str, int | bool]:
        return {"seed": int(self.seed), "deterministic": bool(self.deterministic)}


def seed_everything(seed: int, *, deterministic: bool = True) -> SeedReport:
    """Seed stdlib random and NumPy when available."""

    normalized_seed = int(seed)
    random.seed(normalized_seed)
    os.environ["PYTHONHASHSEED"] = str(normalized_seed)
    numpy_seeded = False
    try:
        import numpy as np  # type: ignore
    except Exception:
        numpy_seeded = False
    else:  # pragma: no cover - exercised only when numpy is installed
        np.random.seed(normalized_seed)
        numpy_seeded = True
    return SeedReport(seed=normalized_seed, deterministic=deterministic, numpy_seeded=numpy_seeded)
