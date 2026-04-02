"""Framework-agnostic network contracts for the RL backbone."""

from .base import NetworkSpec, ScalarPolicyNetwork, ScalarValueNetwork

__all__ = ["NetworkSpec", "ScalarPolicyNetwork", "ScalarValueNetwork"]
