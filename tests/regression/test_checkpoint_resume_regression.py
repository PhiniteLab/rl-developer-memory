
from rl_developer_memory.experiments.checkpoints import CheckpointManager


def test_checkpoint_manager_rollback_preserves_previous_checkpoint(tmp_path) -> None:
    manager = CheckpointManager(tmp_path, keep_last=3)
    manager.save(step=1, state={"x": 1}, metadata={"step": 1}, stable=True)
    manager.save(step=2, state={"x": 2}, metadata={"step": 2}, stable=False)
    rolled = manager.rollback()
    assert rolled is not None
    assert rolled.step == 1


def test_checkpoint_manager_loads_latest_stable_checkpoint(tmp_path) -> None:
    manager = CheckpointManager(tmp_path, keep_last=3)
    first = manager.save(step=1, state={"x": 1}, metadata={"step": 1}, stable=True)
    manager.save(step=2, state={"x": 2}, metadata={"step": 2}, stable=False)
    latest_stable = manager.latest_stable()
    assert latest_stable is not None
    assert latest_stable.step == first.step
    loaded = manager.load_record(latest_stable)
    assert loaded is not None
    state, meta, record = loaded
    assert state["x"] == 1
    assert meta["stable"] is True
    assert record.stable is True
