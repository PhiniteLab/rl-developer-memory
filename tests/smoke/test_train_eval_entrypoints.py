import json
import subprocess
import sys
from pathlib import Path


def test_train_and_eval_entrypoints_run_with_config(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    checkpoint_root = tmp_path / "artifacts"
    config_path = repo_root / "configs" / "rl_backbone.shadow.toml"

    train_proc = subprocess.run(
        [
            sys.executable,
            "scripts/train_rl_backbone.py",
            "--config",
            str(config_path),
            "--checkpoint-root",
            str(checkpoint_root),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert train_proc.returncode == 0, train_proc.stdout + train_proc.stderr
    train_payload = json.loads(train_proc.stdout)
    assert train_payload["mode"] == "train"
    assert train_payload["checkpoint"]["latest_step"] > 0

    eval_proc = subprocess.run(
        [
            sys.executable,
            "scripts/eval_rl_backbone.py",
            "--config",
            str(config_path),
            "--checkpoint-root",
            str(checkpoint_root),
            "--episodes",
            "2",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert eval_proc.returncode == 0, eval_proc.stdout + eval_proc.stderr
    eval_payload = json.loads(eval_proc.stdout)
    assert eval_payload["mode"] == "eval"
    assert eval_payload["checkpoint_loaded"] is True
