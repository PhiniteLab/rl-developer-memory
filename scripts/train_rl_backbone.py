#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rl_developer_memory.experiments.config import RLExperimentConfig
from rl_developer_memory.experiments.runner import ExperimentRunner


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run config-driven RL backbone training + evaluation.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rl_backbone.shadow.json"),
        help="Path to experiment config (.json or .toml).",
    )
    parser.add_argument(
        "--checkpoint-root",
        type=Path,
        default=None,
        help="Optional override for checkpoint.root_dir.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    config = RLExperimentConfig.load(args.config)
    if args.checkpoint_root is not None:
        config.checkpoint.root_dir = str(args.checkpoint_root)
    report = ExperimentRunner(config).run()
    payload = {
        "mode": "train",
        "experiment_name": report.config["experiment_name"],
        "algorithm": report.algorithm["spec"]["name"],
        "training_summary": report.training_summary,
        "evaluation_summary": report.evaluation_summary,
        "checkpoint": report.checkpoint,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
