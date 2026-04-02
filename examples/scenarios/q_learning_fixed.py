from __future__ import annotations

DISCOUNT = 0.95


def q_learning_target(*, reward: float, next_q_values: list[float], done: bool) -> float:
    bootstrap = 0.0 if done else DISCOUNT * max(next_q_values)
    return reward + bootstrap


def validate_terminal_transition() -> None:
    reward = 1.0
    next_q_values = [7.0, 3.5]
    got = q_learning_target(reward=reward, next_q_values=next_q_values, done=True)
    if abs(got - reward) > 1e-9:
        raise AssertionError("Fixed Q-learning target should equal reward on terminal transitions.")


if __name__ == "__main__":
    validate_terminal_transition()
