from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, pstdev

from rl_developer_memory.agents.base import BaseAgent
from rl_developer_memory.envs.base import Environment


@dataclass(slots=True)
class EvaluationResult:
    return_mean: float
    return_std: float
    control_effort: float
    crash_rate: float
    constraint_violation_rate: float
    episode_returns: list[float] = field(default_factory=list)


class Evaluator:
    """Roll out a small number of evaluation episodes."""

    def evaluate(self, *, agent: BaseAgent, env: Environment, episodes: int = 3) -> EvaluationResult:
        returns: list[float] = []
        actions: list[float] = []
        violations = 0
        for _ in range(max(int(episodes), 1)):
            observation = env.reset()
            total_reward = 0.0
            done = False
            while not done:
                action = agent.act(observation)
                actions.append(abs(action))
                step = env.step(action)
                if action < env.spec.action_low or action > env.spec.action_high:
                    violations += 1
                total_reward += step.reward
                observation = step.observation
                done = step.terminated or step.truncated
            returns.append(total_reward)
        return EvaluationResult(
            return_mean=mean(returns),
            return_std=pstdev(returns) if len(returns) > 1 else 0.0,
            control_effort=mean(actions) if actions else 0.0,
            crash_rate=0.0,
            constraint_violation_rate=float(violations) / float(len(actions) or 1),
            episode_returns=returns,
        )
