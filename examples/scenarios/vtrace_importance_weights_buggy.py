from __future__ import annotations


def corrected_actor_term(*, rho_clipped: float, td_error: float) -> float:
    return td_error


def validate_importance_weighting() -> None:
    got = corrected_actor_term(rho_clipped=0.3, td_error=2.0)
    if abs(got - 0.6) > 1e-9:
        raise AssertionError("Off-policy correction omits clipped importance weights in the actor update.")


if __name__ == "__main__":
    validate_importance_weighting()
