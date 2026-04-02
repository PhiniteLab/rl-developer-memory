from rl_developer_memory.algorithms.catalog import build_algorithm_catalog


def test_algorithm_catalog_contains_requested_families() -> None:
    catalog = build_algorithm_catalog()
    for name in ("dqn", "ppo", "a2c", "ddpg", "td3", "sac"):
        assert name in catalog
        assert catalog[name].spec.training_flow[0] == "problem/env definition"
