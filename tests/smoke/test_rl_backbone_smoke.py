from pathlib import Path

from rl_developer_memory.experiments.config import RLExperimentConfig
from rl_developer_memory.experiments.runner import ExperimentRunner


def test_rl_backbone_smoke_path_runs(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    config = RLExperimentConfig.load(repo_root / "configs" / "rl_backbone.shadow.json")
    config.checkpoint.root_dir = str(tmp_path / "artifacts")
    report = ExperimentRunner(config).run()
    assert report.evaluation_summary["return_mean"] > 0.0
    assert report.diagnostics["checkpoint_count"] >= 1
