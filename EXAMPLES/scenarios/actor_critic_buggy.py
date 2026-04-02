from __future__ import annotations


def actor_loss(*, log_probs: list[float], returns: list[float], values: list[float]) -> float:
    return -sum(log_prob * ret for log_prob, ret in zip(log_probs, returns, strict=True))


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
        raise AssertionError("Actor-critic policy loss is using returns instead of advantages; subtract critic values before policy update.")


if __name__ == "__main__":
    validate_advantage_routing()
