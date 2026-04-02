from __future__ import annotations

DISCOUNT = 0.9


def n_step_return(*, rewards: list[float], bootstrap_value: float) -> float:
    total = 0.0
    for index, reward in enumerate(rewards):
        total += (DISCOUNT ** index) * reward
    total += (DISCOUNT ** len(rewards)) * bootstrap_value
    return total


def validate_terminal_masking() -> None:
    rewards = [1.0, 0.5]
    got = n_step_return(rewards=rewards, bootstrap_value=10.0)
    expected = rewards[0] + DISCOUNT * rewards[1]
    if abs(got - expected) > 1e-9:
        raise AssertionError("N-step return bootstraps past a terminal transition; expected terminal mask to stop recursion.")


if __name__ == "__main__":
    validate_terminal_masking()
