from __future__ import annotations

from dataclasses import dataclass

from rl_developer_memory.agents.base import BaseAgent
from rl_developer_memory.experiments.checkpoints import CheckpointManager


@dataclass(slots=True, frozen=True)
class RecoveryResult:
    action: str
    restored: bool
    checkpoint: str
    step: int


class RecoveryManager:
    """Resume and rollback orchestration around the generic checkpoint manager."""

    def __init__(self, checkpoint_manager: CheckpointManager) -> None:
        self.checkpoint_manager = checkpoint_manager

    def resume(self, *, agent: BaseAgent, resume_from: str = "") -> RecoveryResult:
        if resume_from:
            record = self.checkpoint_manager.load_path(resume_from)
        else:
            latest = self.checkpoint_manager.latest()
            record = self.checkpoint_manager.load_record(latest) if latest is not None else None
        if record is None:
            return RecoveryResult(action="resume", restored=False, checkpoint="", step=0)
        state, _meta, checkpoint = record
        agent.load_state_dict(state)
        return RecoveryResult(action="resume", restored=True, checkpoint=str(checkpoint.state_path), step=checkpoint.step)

    def rollback_to_last_stable(self, *, agent: BaseAgent) -> RecoveryResult:
        checkpoint = self.checkpoint_manager.rollback_to_last_stable()
        if checkpoint is None:
            return RecoveryResult(action="rollback", restored=False, checkpoint="", step=0)
        loaded = self.checkpoint_manager.load_record(checkpoint)
        if loaded is None:
            return RecoveryResult(action="rollback", restored=False, checkpoint="", step=0)
        state, _meta, record = loaded
        agent.load_state_dict(state)
        return RecoveryResult(action="rollback", restored=True, checkpoint=str(record.state_path), step=record.step)
