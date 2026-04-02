from __future__ import annotations

DISCOUNT = 0.95


def q_learning_target(*, reward: float, next_q_values: list[float], done: bool) -> float:
    return reward + DISCOUNT * max(next_q_values)


def validate_terminal_transition() -> None:
    reward = 1.0
    next_q_values = [7.0, 3.5]
    got = q_learning_target(reward=reward, next_q_values=next_q_values, done=True)
    if abs(got - reward) > 1e-9:
        raise AssertionError("Q-learning target bootstraps through terminal state; expected reward-only target when done=True.")


if __name__ == "__main__":
    validate_terminal_transition()
