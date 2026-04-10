from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True, frozen=True)
class NetworkSpec:
    """Network description used by algorithm specs and config."""

    name: str
    role: str
    hidden_sizes: tuple[int, ...] = ()
    activation: str = "identity"
    output_activation: str = "identity"
    metadata: dict[str, str] = field(default_factory=dict)


class PolicyNetwork(Protocol):
    def __call__(self, observation: float) -> float:
        ...

    def state_dict(self) -> dict[str, float]:
        ...

    def load_state_dict(self, state: dict[str, float]) -> None:
        ...


class ValueNetwork(Protocol):
    def __call__(self, observation: float) -> float:
        ...

    def state_dict(self) -> dict[str, float]:
        ...

    def load_state_dict(self, state: dict[str, float]) -> None:
        ...


class _ScalarLinearModel:
    """Small scalar model used to keep the RL backbone executable without torch."""

    def __init__(self, *, weight: float = 0.0, bias: float = 0.0) -> None:
        self.weight = float(weight)
        self.bias = float(bias)

    def __call__(self, observation: float) -> float:
        return self.weight * float(observation) + self.bias

    def state_dict(self) -> dict[str, float]:
        return {"weight": self.weight, "bias": self.bias}

    def load_state_dict(self, state: dict[str, float]) -> None:
        self.weight = float(state["weight"])
        self.bias = float(state["bias"])


class ScalarPolicyNetwork(_ScalarLinearModel):
    """Deterministic scalar policy network for tests and smoke runs."""


class ScalarValueNetwork(_ScalarLinearModel):
    """Deterministic scalar value network for tests and smoke runs."""


# ---------------------------------------------------------------------------
# Activation functions
# ---------------------------------------------------------------------------

_ACTIVATIONS: dict[str, type[object]] = {}


def _relu(x: float) -> float:
    return max(0.0, x)


def _tanh(x: float) -> float:
    return math.tanh(x)


def _sigmoid(x: float) -> float:
    clamped = max(-500.0, min(500.0, x))
    return 1.0 / (1.0 + math.exp(-clamped))


def _identity(x: float) -> float:
    return x


_ACTIVATION_FNS: dict[str, type[object] | None] = {
    "relu": None,
    "tanh": None,
    "sigmoid": None,
    "identity": None,
}


def get_activation(name: str) -> type[object] | None:
    """Return activation callable by name."""
    mapping = {"relu": _relu, "tanh": _tanh, "sigmoid": _sigmoid, "identity": _identity}
    return mapping.get(name)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Multi-Layer Perceptron (MLP)
# ---------------------------------------------------------------------------


class _Layer:
    """Single dense layer: y = activation(w @ x + b) (scalar-only for dependency-free usage)."""

    __slots__ = ("activation_fn", "biases", "weights")

    def __init__(self, *, input_size: int, output_size: int, activation: str = "identity") -> None:
        scale = 1.0 / max(input_size, 1) ** 0.5
        self.weights: list[list[float]] = [
            [scale * (((i * 7 + j * 13) % 97) / 97.0 - 0.5) for j in range(input_size)]
            for i in range(output_size)
        ]
        self.biases: list[float] = [0.0] * output_size
        fn = get_activation(activation)
        self.activation_fn = fn if fn is not None else _identity

    def forward(self, inputs: list[float]) -> list[float]:
        outputs: list[float] = []
        for _i, (row, bias) in enumerate(zip(self.weights, self.biases, strict=False)):
            total = bias
            for w, x in zip(row, inputs, strict=True):
                total += w * x
            outputs.append(self.activation_fn(total))  # type: ignore[operator]
        return outputs

    def state_dict(self) -> dict[str, list[list[float]] | list[float]]:
        return {"weights": [list(row) for row in self.weights], "biases": list(self.biases)}

    def load_state_dict(self, state: dict[str, list[list[float]] | list[float]]) -> None:
        self.weights = [list(row) for row in state["weights"]]  # type: ignore[union-attr]
        self.biases = list(state["biases"])  # type: ignore[arg-type]


class ScalarMLP:
    """Dependency-free multi-layer perceptron for scalar input/output.

    Uses configurable hidden sizes and activation functions.
    Designed to exercise the NetworkSpec fields (hidden_sizes, activation)
    that were previously unused.
    """

    def __init__(self, *, hidden_sizes: tuple[int, ...] = (8,), activation: str = "tanh", output_activation: str = "identity") -> None:
        self.hidden_sizes = hidden_sizes
        self.activation = activation
        self.output_activation = output_activation
        self._layers: list[_Layer] = []
        prev_size = 1  # scalar input
        for size in hidden_sizes:
            self._layers.append(_Layer(input_size=prev_size, output_size=size, activation=activation))
            prev_size = size
        self._layers.append(_Layer(input_size=prev_size, output_size=1, activation=output_activation))

    def __call__(self, observation: float) -> float:
        x = [float(observation)]
        for layer in self._layers:
            x = layer.forward(x)
        return x[0]

    def state_dict(self) -> dict[str, list[dict[str, list[list[float]] | list[float]]]]:
        return {"layers": [layer.state_dict() for layer in self._layers]}

    def load_state_dict(self, state: dict[str, list[dict[str, list[list[float]] | list[float]]]]) -> None:
        for layer, layer_state in zip(self._layers, state["layers"], strict=True):
            layer.load_state_dict(layer_state)

    @property
    def parameters(self) -> list[float]:
        """Flatten all parameters for gradient/norm computation."""
        params: list[float] = []
        for layer in self._layers:
            for row in layer.weights:
                params.extend(row)
            params.extend(layer.biases)
        return params


class MLPPolicyNetwork(ScalarMLP):
    """Multi-layer policy network for scalar control."""


class MLPValueNetwork(ScalarMLP):
    """Multi-layer value network for scalar control."""


def build_network_from_spec(spec: NetworkSpec, *, role: str = "value") -> ScalarMLP | _ScalarLinearModel:
    """Factory: build a network from a NetworkSpec.

    Falls back to the simple linear model when hidden_sizes is empty.
    """
    if not spec.hidden_sizes:
        return ScalarValueNetwork() if role == "value" else ScalarPolicyNetwork()
    cls = MLPValueNetwork if role == "value" else MLPPolicyNetwork
    return cls(
        hidden_sizes=spec.hidden_sizes,
        activation=spec.activation,
        output_activation=spec.output_activation,
    )
