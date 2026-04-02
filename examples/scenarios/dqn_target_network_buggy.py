from __future__ import annotations

DISCOUNT = 0.99


def dqn_target(*, reward: float, online_next_q: list[float], target_next_q: list[float]) -> float:
    greedy_action = max(range(len(online_next_q)), key=online_next_q.__getitem__)
    return reward + DISCOUNT * online_next_q[greedy_action]


def validate_target_network_usage() -> None:
    reward = 0.5
    online_next_q = [9.0, 1.0]
    target_next_q = [2.5, 1.0]
    got = dqn_target(reward=reward, online_next_q=online_next_q, target_next_q=target_next_q)
    expected = reward + DISCOUNT * target_next_q[0]
    if abs(got - expected) > 1e-9:
        raise AssertionError("DQN target uses online-network bootstrap value instead of detached target-network value.")


if __name__ == "__main__":
    validate_target_network_usage()
