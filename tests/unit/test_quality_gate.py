from __future__ import annotations

from pathlib import Path

from rl_developer_memory.quality_gate import evaluate_memory_hygiene, evaluate_repository_structure

ROOT = Path(__file__).resolve().parents[2]


def test_repository_structure_check_passes_for_current_repo() -> None:
    report = evaluate_repository_structure(ROOT)
    assert report["status"] == "passed"


def test_memory_hygiene_contract_is_present() -> None:
    report = evaluate_memory_hygiene(ROOT)
    assert report["status"] == "passed"
