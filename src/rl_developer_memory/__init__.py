"""rl_developer_memory package."""
# pyright: reportUnsupportedDunderAll=false

from importlib import import_module
from types import ModuleType

__version__ = "0.1.0"

_MODULE_EXPORTS = {
    "agents",
    "algorithms",
    "backup",
    "buffers",
    "callbacks",
    "evaluation",
    "experiments",
    "learning",
    "matching",
    "migrations",
    "models",
    "networks",
    "normalization",
    "quality_checks",
    "release_readiness",
    "retrieval",
    "services",
    "settings",
    "skill_bundle_sync",
    "storage",
    "theory",
    "trainers",
    "utils",
}

__all__ = [
    "__version__",
    "agents",
    "algorithms",
    "backup",
    "buffers",
    "callbacks",
    "evaluation",
    "experiments",
    "learning",
    "matching",
    "migrations",
    "models",
    "networks",
    "normalization",
    "quality_checks",
    "release_readiness",
    "retrieval",
    "services",
    "settings",
    "skill_bundle_sync",
    "storage",
    "theory",
    "trainers",
    "utils",
]


def __getattr__(name: str) -> ModuleType:
    if name not in _MODULE_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module
