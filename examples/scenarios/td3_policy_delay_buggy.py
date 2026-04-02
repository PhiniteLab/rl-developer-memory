from __future__ import annotations


def should_update_actor(*, step: int, policy_delay: int) -> bool:
    return step % 1 == 0


def validate_policy_delay() -> None:
    if should_update_actor(step=1, policy_delay=2):
        raise AssertionError("TD3 actor update ignores policy_delay and runs on every critic step.")


if __name__ == "__main__":
    validate_policy_delay()
