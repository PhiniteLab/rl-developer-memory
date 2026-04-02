import subprocess
import sys
from pathlib import Path


def test_theory_sync_script_passes() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "scripts/validate_theory_code_sync.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
