from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def safe_json_dumps(payload: Any) -> str:
    """Serialize payloads with stable ordering and UTF-8 friendly settings."""

    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(safe_json_dumps(payload), encoding="utf-8")
    temp_path.replace(path)


def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
