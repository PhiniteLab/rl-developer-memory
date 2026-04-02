#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rl_developer_memory.experiments.config import RLExperimentConfig
from rl_developer_memory.experiments.runner import ExperimentRunner


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run config-driven RL backbone evaluation.")
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
    parser.add_argument(
        "--episodes",
        type=int,
        default=None,
        help="Optional evaluation episode override.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    config = RLExperimentConfig.load(args.config)
    if args.checkpoint_root is not None:
        config.checkpoint.root_dir = str(args.checkpoint_root)
    report = ExperimentRunner(config).evaluate_only(episodes=args.episodes)
    payload = {"mode": "eval", **report}
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
