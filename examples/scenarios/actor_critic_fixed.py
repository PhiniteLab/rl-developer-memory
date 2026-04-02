from __future__ import annotations


def actor_loss(*, log_probs: list[float], returns: list[float], values: list[float]) -> float:
    advantages = [ret - value for ret, value in zip(returns, values, strict=True)]
    return -sum(log_prob * advantage for log_prob, advantage in zip(log_probs, advantages, strict=True))


def expected_actor_loss(*, log_probs: list[float], returns: list[float], values: list[float]) -> float:
    advantages = [ret - value for ret, value in zip(returns, values, strict=True)]
    return -sum(log_prob * advantage for log_prob, advantage in zip(log_probs, advantages, strict=True))


def validate_advantage_routing() -> None:
    log_probs = [0.2, -0.4, 0.1]
    returns = [3.0, 1.0, 2.5]
    values = [2.5, 0.5, 2.0]
    got = actor_loss(log_probs=log_probs, returns=returns, values=values)
    expected = expected_actor_loss(log_probs=log_probs, returns=returns, values=values)
    if abs(got - expected) > 1e-9:
        raise AssertionError("Fixed actor-critic loss should use advantages, not raw returns.")


if __name__ == "__main__":
    validate_advantage_routing()
