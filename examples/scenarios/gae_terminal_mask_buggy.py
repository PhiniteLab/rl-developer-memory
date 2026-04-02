from __future__ import annotations

DISCOUNT = 0.99
LAMBDA = 0.95


def gae_step(*, reward: float, value: float, next_value: float, next_advantage: float) -> float:
    delta = reward + DISCOUNT * next_value - value
    return delta + DISCOUNT * LAMBDA * next_advantage


def validate_terminal_advantage_cutoff() -> None:
    got = gae_step(reward=1.0, value=0.3, next_value=4.0, next_advantage=6.0)
    expected = 1.0 - 0.3
    if abs(got - expected) > 1e-9:
        raise AssertionError("GAE recursion propagates advantage across terminal boundary because done mask is ignored.")


if __name__ == "__main__":
    validate_terminal_advantage_cutoff()
