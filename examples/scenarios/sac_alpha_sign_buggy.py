from __future__ import annotations


def alpha_residual(*, observed_entropy: float, target_entropy: float) -> float:
    return observed_entropy - target_entropy


def validate_temperature_update_direction() -> None:
    got = alpha_residual(observed_entropy=0.2, target_entropy=0.8)
    if abs(got - 0.6) > 1e-9:
        raise AssertionError("SAC temperature update uses the wrong sign; expected target_entropy - observed_entropy.")


if __name__ == "__main__":
    validate_temperature_update_direction()
