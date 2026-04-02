from rl_developer_memory.utils.numeric_guards import (
    apply_gradient_clip,
    detect_exploding_update,
    detect_plateau,
    ensure_finite_metrics,
)


def test_apply_gradient_clip_limits_large_updates() -> None:
    result = apply_gradient_clip(2.5, max_norm=0.5)
    assert result.clipped_update == 0.5
    assert result.exploded is True


def test_detect_plateau_flags_flat_history() -> None:
    assert detect_plateau([1.0, 1.0, 1.0, 1.0], patience=3, min_delta=1e-4) is True


def test_ensure_finite_metrics_flags_nan_values() -> None:
    result = ensure_finite_metrics({"loss": 1.0, "critic": float("nan")})
    assert result.finite is False
    assert result.invalid_keys == ("critic",)


def test_detect_exploding_update_uses_ratio_and_thresholds() -> None:
    result = detect_exploding_update(5.0, reference_scale=0.1, ratio_threshold=10.0, absolute_threshold=100.0)
    assert result.exploded is True
