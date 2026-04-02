#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from rl_developer_memory.experiments.config import RLExperimentConfig
from rl_developer_memory.experiments.runner import ExperimentRunner


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = RLExperimentConfig.load(repo_root / "configs" / "rl_backbone.shadow.json")
    report = ExperimentRunner(config).run()
    print(json.dumps({
        "status": "ok",
        "experiment_name": report.config["experiment_name"],
        "algorithm": report.algorithm["spec"]["name"],
        "return_mean": report.evaluation_summary["return_mean"],
        "checkpoint": report.checkpoint,
    }, indent=2))


if __name__ == "__main__":
    main()
