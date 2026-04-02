from __future__ import annotations

ACTION_LIMIT = 1.0


def smoothed_target_action(*, policy_action: float, noise: float) -> float:
    return policy_action + noise


def validate_action_clipping() -> None:
    got = smoothed_target_action(policy_action=0.95, noise=0.2)
    if got > ACTION_LIMIT:
        raise AssertionError("TD3 target policy smoothing misses action clipping and exceeds action bounds.")


if __name__ == "__main__":
    validate_action_clipping()
