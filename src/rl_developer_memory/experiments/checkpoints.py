from __future__ import annotations

import fcntl
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rl_developer_memory.utils.serialization import atomic_write_json, load_json_file


@dataclass(slots=True)
class CheckpointRecord:
    step: int
    state_path: Path
    meta_path: Path
    stable: bool = False


class CheckpointManager:
    """Generic JSON checkpoint manager for the dependency-free RL backbone."""

    def __init__(self, root_dir: Path | str, *, keep_last: int = 3) -> None:
        self.root_dir = Path(root_dir)
        self.keep_last = max(int(keep_last), 1)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root_dir / "manifest.json"

    def save(self, *, step: int, state: dict[str, Any], metadata: dict[str, Any], stable: bool = False) -> CheckpointRecord:
        state_path = self.root_dir / f"checkpoint-step-{int(step):04d}.state.json"
        meta_path = self.root_dir / f"checkpoint-step-{int(step):04d}.meta.json"
        atomic_write_json(state_path, state)
        atomic_write_json(meta_path, {**metadata, "stable": bool(stable)})
        entry = {"step": int(step), "state_path": str(state_path), "meta_path": str(meta_path), "stable": bool(stable)}
        keep = self.keep_last

        def _append(manifest: list[dict[str, Any]]) -> tuple[None, list[dict[str, Any]]]:
            manifest.append(entry)
            return None, manifest[-keep:]

        self._locked_manifest_update(_append)
        return CheckpointRecord(step=int(step), state_path=state_path, meta_path=meta_path, stable=bool(stable))

    def latest(self) -> CheckpointRecord | None:
        manifest = self._load_manifest()
        if not manifest:
            return None
        item = manifest[-1]
        return CheckpointRecord(
            step=int(item["step"]),
            state_path=Path(item["state_path"]),
            meta_path=Path(item["meta_path"]),
            stable=bool(item.get("stable", False)),
        )

    def load_latest(self) -> tuple[dict[str, Any], dict[str, Any]] | None:
        latest = self.latest()
        if latest is None:
            return None
        return load_json_file(latest.state_path), load_json_file(latest.meta_path)

    def load_record(self, record: CheckpointRecord | None) -> tuple[dict[str, Any], dict[str, Any], CheckpointRecord] | None:
        if record is None:
            return None
        return load_json_file(record.state_path), load_json_file(record.meta_path), record

    def load_path(self, path: str | Path) -> tuple[dict[str, Any], dict[str, Any], CheckpointRecord] | None:
        state_path = Path(path)
        if not state_path.exists():
            return None
        meta_path = state_path.with_suffix(".meta.json")
        if not meta_path.exists():
            meta_path = self.root_dir / state_path.name.replace(".state.json", ".meta.json")
        metadata = load_json_file(meta_path) if meta_path.exists() else {}
        step = int(metadata.get("step", 0))
        return load_json_file(state_path), metadata, CheckpointRecord(step=step, state_path=state_path, meta_path=meta_path, stable=bool(metadata.get("stable", False)))

    def mark_stable(self, step: int) -> CheckpointRecord | None:
        target_step = int(step)
        result_holder: list[CheckpointRecord | None] = [None]

        def _mark(manifest: list[dict[str, Any]]) -> tuple[None, list[dict[str, Any]]]:
            updated: list[dict[str, Any]] = []
            for item in manifest:
                stable = bool(item.get("stable", False)) or int(item["step"]) == target_step
                next_item = {**item, "stable": stable}
                updated.append(next_item)
                if int(item["step"]) == target_step:
                    rec = CheckpointRecord(step=int(item["step"]), state_path=Path(item["state_path"]), meta_path=Path(item["meta_path"]), stable=stable)
                    meta = load_json_file(rec.meta_path)
                    atomic_write_json(rec.meta_path, {**meta, "stable": stable})
                    result_holder[0] = rec
            return None, updated

        self._locked_manifest_update(_mark)
        return result_holder[0]

    def latest_stable(self) -> CheckpointRecord | None:
        stable = [item for item in self._load_manifest() if bool(item.get("stable", False))]
        if not stable:
            return None
        item = stable[-1]
        return CheckpointRecord(step=int(item["step"]), state_path=Path(item["state_path"]), meta_path=Path(item["meta_path"]), stable=True)

    def rollback(self) -> CheckpointRecord | None:
        result_holder: list[CheckpointRecord | None] = [None]

        def _rollback(manifest: list[dict[str, Any]]) -> tuple[None, list[dict[str, Any]] | None]:
            if len(manifest) < 2:
                return None, None
            manifest = manifest[:-1]
            item = manifest[-1]
            result_holder[0] = CheckpointRecord(
                step=int(item["step"]),
                state_path=Path(item["state_path"]),
                meta_path=Path(item["meta_path"]),
                stable=bool(item.get("stable", False)),
            )
            return None, manifest

        self._locked_manifest_update(_rollback)
        return result_holder[0]

    def rollback_to_last_stable(self) -> CheckpointRecord | None:
        latest_stable = self.latest_stable()
        if latest_stable is None:
            return None
        cutoff = latest_stable.step

        def _rollback_stable(manifest: list[dict[str, Any]]) -> tuple[None, list[dict[str, Any]]]:
            return None, [item for item in manifest if int(item["step"]) <= cutoff]

        self._locked_manifest_update(_rollback_stable)
        return latest_stable

    def _locked_manifest_update(self, updater: Any) -> Any:
        """Read-modify-write manifest under an exclusive file lock."""
        lock_path = self.manifest_path.with_suffix(".lock")
        lock_path.touch(exist_ok=True)
        with open(lock_path) as lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            try:
                manifest = self._load_manifest_unlocked()
                result, new_manifest = updater(manifest)
                if new_manifest is not None:
                    atomic_write_json(self.manifest_path, new_manifest)
                return result
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)

    def _load_manifest_unlocked(self) -> list[dict[str, Any]]:
        if not self.manifest_path.exists():
            return []
        return list(load_json_file(self.manifest_path))

    def _load_manifest(self) -> list[dict[str, Any]]:
        lock_path = self.manifest_path.with_suffix(".lock")
        lock_path.touch(exist_ok=True)
        with open(lock_path) as lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_SH)
            try:
                return self._load_manifest_unlocked()
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
