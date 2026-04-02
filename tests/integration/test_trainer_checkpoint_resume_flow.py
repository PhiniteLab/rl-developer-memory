from pathlib import Path

from rl_developer_memory.experiments.config import RLExperimentConfig
from rl_developer_memory.experiments.runner import ExperimentRunner


def test_checkpoint_resume_flow_produces_latest_checkpoint(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    config = RLExperimentConfig.load(repo_root / "configs" / "rl_backbone.shadow.json")
    config.checkpoint.root_dir = str(tmp_path / "artifacts")
    report = ExperimentRunner(config).run()
    assert report.checkpoint["latest_step"] >= 1

    resumed = ExperimentRunner(config).resume_from_checkpoint()
    assert resumed.checkpoint["root_dir"] == report.checkpoint["root_dir"]
    assert resumed.checkpoint["resumed_from"] != ""
    assert resumed.diagnostics["resume_count"] >= 1
