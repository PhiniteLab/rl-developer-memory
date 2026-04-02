from __future__ import annotations


def ppo_surrogate(*, ratio: float, advantage: float, clip_epsilon: float) -> float:
    unclipped = ratio * advantage
    clipped_ratio = max(min(ratio, 1.0 + clip_epsilon), 1.0 - clip_epsilon)
    clipped = clipped_ratio * advantage
    return max(unclipped, clipped)


def validate_clipped_objective() -> None:
    got = ppo_surrogate(ratio=1.4, advantage=1.0, clip_epsilon=0.2)
    if abs(got - 1.2) > 1e-9:
        raise AssertionError("PPO clipped objective uses max instead of min for positive advantages.")


if __name__ == "__main__":
    validate_clipped_objective()
