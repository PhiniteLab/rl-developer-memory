from pathlib import Path

from rl_developer_memory.theory.blueprint import build_training_blueprint_catalog
from rl_developer_memory.theory.registry import build_default_theory_registry
from rl_developer_memory.theory.sync import validate_theorem_code_sync, validate_training_blueprint_sync


def test_theory_registry_and_docs_stay_in_sync() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    registry = build_default_theory_registry()
    result = validate_theorem_code_sync(registry, doc_path=repo_root / "docs" / "theory_to_code.md")
    assert result["status"] == "ok", result["errors"]
    blueprint_result = validate_training_blueprint_sync(build_training_blueprint_catalog(registry))
    assert blueprint_result["status"] == "ok", blueprint_result["errors"]
