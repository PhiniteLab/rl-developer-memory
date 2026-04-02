#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from rl_developer_memory.theory.blueprint import build_training_blueprint_catalog
from rl_developer_memory.theory.registry import build_default_theory_registry
from rl_developer_memory.theory.sync import validate_theorem_code_sync, validate_training_blueprint_sync


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    registry = build_default_theory_registry()
    result = validate_theorem_code_sync(
        registry,
        doc_path=repo_root / "docs" / "theory_to_code.md",
    )
    blueprint_result = validate_training_blueprint_sync(build_training_blueprint_catalog(registry))
    combined = {
        "status": "ok" if result["status"] == "ok" and blueprint_result["status"] == "ok" else "fail",
        "theorem_code": result,
        "training_blueprint": blueprint_result,
    }
    print(json.dumps(combined, indent=2))
    raise SystemExit(0 if combined["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
