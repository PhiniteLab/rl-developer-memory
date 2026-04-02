from __future__ import annotations

from dataclasses import dataclass

from rl_developer_memory.agents.base import ActorCriticAgent, AgentContext
from rl_developer_memory.callbacks.base import CallbackManager
from rl_developer_memory.envs.base import EnvSpec, StepResult
from rl_developer_memory.experiments.checkpoints import CheckpointManager
from rl_developer_memory.experiments.recovery import RecoveryManager
from rl_developer_memory.trainers.pipeline import StabilizationPolicy, TrainerPipeline


@dataclass
class NaNRewardEnv:
    spec: EnvSpec = EnvSpec(
        env_id="nan-reward-v0",
        observation_shape=(1,),
        action_shape=(1,),
        action_low=-1.0,
        action_high=1.0,
        reward_scale=1.0,
        max_episode_steps=3,
    )
    step_count: int = 0

    def reset(self) -> float:
        self.step_count = 0
        return 1.0

    def step(self, action: float) -> StepResult:
        self.step_count += 1
        reward = 1.0 if self.step_count == 1 else float("nan")
        return StepResult(
            observation=1.0,
            reward=reward,
            terminated=self.step_count >= 2,
            truncated=False,
            info={"action": action},
        )


def test_trainer_rolls_back_to_last_stable_checkpoint_on_nan(tmp_path) -> None:
    pipeline = TrainerPipeline(
        stabilization=StabilizationPolicy(
            deterministic_seed=7,
            reward_scale=1.0,
            advantage_scale=1.0,
            target_update_tau=0.5,
            entropy_temperature=0.1,
            gradient_clip=0.5,
            plateau_patience=4,
            early_stop_min_delta=1e-3,
        )
    )
    agent = ActorCriticAgent(
        context=AgentContext(
            discount=0.95,
            learning_rate=0.1,
            entropy_temperature=0.1,
            target_update_tau=0.5,
        )
    )
    manager = CheckpointManager(tmp_path, keep_last=3)
    recovery = RecoveryManager(manager)

    def save_checkpoint(step: int, metrics: dict[str, float], stable: bool = False):
        record = manager.save(step=step, state=agent.state_dict(), metadata={"step": step, "metrics": metrics}, stable=stable)
        if stable:
            manager.mark_stable(step)
        return record

    result = pipeline.train(
        agent=agent,
        env=NaNRewardEnv(),
        max_steps=4,
        callbacks=CallbackManager(),
        recovery_manager=recovery,
        checkpoint_saver=save_checkpoint,
    )

    diagnostics = result["diagnostics"]
    assert diagnostics["anomaly_count"] >= 1
    assert diagnostics["rollback_count"] >= 1
    latest = manager.latest()
    assert latest is not None
    assert latest.step == 1
