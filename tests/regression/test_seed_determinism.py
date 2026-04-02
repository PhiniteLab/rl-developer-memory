from pathlib import Path

from rl_developer_memory.experiments.config import RLExperimentConfig
from rl_developer_memory.experiments.runner import ExperimentRunner


def test_same_seed_produces_same_training_summary(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    base = RLExperimentConfig.load(repo_root / "configs" / "rl_backbone.shadow.json")
    base.checkpoint.root_dir = str(tmp_path / "run_a")
    report_a = ExperimentRunner(base).run()

    replay = RLExperimentConfig.load(repo_root / "configs" / "rl_backbone.shadow.json")
    replay.checkpoint.root_dir = str(tmp_path / "run_b")
    report_b = ExperimentRunner(replay).run()

    assert report_a.training_summary == report_b.training_summary
    assert report_a.evaluation_summary == report_b.evaluation_summary
