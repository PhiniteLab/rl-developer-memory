"""Unit tests for ScalarMLP, MLP networks, and build_network_from_spec factory."""

from __future__ import annotations

from rl_developer_memory.networks.base import (
    MLPPolicyNetwork,
    MLPValueNetwork,
    NetworkSpec,
    ScalarMLP,
    ScalarPolicyNetwork,
    ScalarValueNetwork,
    _Layer,
    _relu,
    _sigmoid,
    _tanh,
    build_network_from_spec,
)


class TestActivationFunctions:
    def test_relu_positive(self) -> None:
        assert _relu(5.0) == 5.0

    def test_relu_negative(self) -> None:
        assert _relu(-3.0) == 0.0

    def test_relu_zero(self) -> None:
        assert _relu(0.0) == 0.0

    def test_tanh_range(self) -> None:
        assert -1.0 <= _tanh(10.0) <= 1.0
        assert -1.0 <= _tanh(-10.0) <= 1.0

    def test_sigmoid_range(self) -> None:
        assert 0.0 < _sigmoid(0.0) < 1.0
        assert abs(_sigmoid(0.0) - 0.5) < 1e-9

    def test_sigmoid_extreme(self) -> None:
        assert _sigmoid(1000.0) > 0.99
        assert _sigmoid(-1000.0) < 0.01


class TestLayer:
    def test_forward_shape(self) -> None:
        layer = _Layer(input_size=3, output_size=2, activation="relu")
        output = layer.forward([1.0, 2.0, 3.0])
        assert len(output) == 2

    def test_state_dict_roundtrip(self) -> None:
        layer = _Layer(input_size=2, output_size=2, activation="tanh")
        state = layer.state_dict()
        layer2 = _Layer(input_size=2, output_size=2, activation="tanh")
        layer2.load_state_dict(state)
        assert layer2.weights == layer.weights
        assert layer2.biases == layer.biases


class TestScalarMLP:
    def test_call_returns_float(self) -> None:
        mlp = ScalarMLP(hidden_sizes=(4, 4), activation="tanh")
        result = mlp(1.0)
        assert isinstance(result, float)

    def test_different_inputs_different_outputs(self) -> None:
        mlp = ScalarMLP(hidden_sizes=(8,), activation="relu")
        out1 = mlp(0.0)
        out2 = mlp(5.0)
        assert out1 != out2

    def test_state_dict_roundtrip(self) -> None:
        mlp = ScalarMLP(hidden_sizes=(4, 4), activation="tanh")
        original_output = mlp(1.0)
        state = mlp.state_dict()
        mlp2 = ScalarMLP(hidden_sizes=(4, 4), activation="tanh")
        mlp2.load_state_dict(state)
        assert mlp2(1.0) == original_output

    def test_parameters_count(self) -> None:
        mlp = ScalarMLP(hidden_sizes=(3,), activation="relu")
        # Layer 1: 3 weights + 3 biases = 6
        # Layer 2: 3 weights + 1 bias = 4
        params = mlp.parameters
        assert len(params) == 10

    def test_single_hidden_layer(self) -> None:
        mlp = ScalarMLP(hidden_sizes=(8,), activation="tanh", output_activation="identity")
        assert len(mlp._layers) == 2  # hidden + output

    def test_multiple_hidden_layers(self) -> None:
        mlp = ScalarMLP(hidden_sizes=(8, 4, 2), activation="relu")
        assert len(mlp._layers) == 4  # 3 hidden + 1 output


class TestMLPNetworkClasses:
    def test_policy_network(self) -> None:
        net = MLPPolicyNetwork(hidden_sizes=(4,), activation="tanh")
        result = net(0.5)
        assert isinstance(result, float)

    def test_value_network(self) -> None:
        net = MLPValueNetwork(hidden_sizes=(4,), activation="relu")
        result = net(0.5)
        assert isinstance(result, float)


class TestBuildNetworkFromSpec:
    def test_empty_hidden_returns_linear(self) -> None:
        spec = NetworkSpec(name="test", role="value", hidden_sizes=())
        net = build_network_from_spec(spec, role="value")
        assert isinstance(net, ScalarValueNetwork)

    def test_empty_hidden_policy_returns_linear(self) -> None:
        spec = NetworkSpec(name="test", role="policy", hidden_sizes=())
        net = build_network_from_spec(spec, role="policy")
        assert isinstance(net, ScalarPolicyNetwork)

    def test_with_hidden_returns_mlp(self) -> None:
        spec = NetworkSpec(
            name="test", role="value", hidden_sizes=(8, 4), activation="tanh"
        )
        net = build_network_from_spec(spec, role="value")
        assert isinstance(net, MLPValueNetwork)

    def test_policy_mlp(self) -> None:
        spec = NetworkSpec(
            name="test", role="policy", hidden_sizes=(8,), activation="relu"
        )
        net = build_network_from_spec(spec, role="policy")
        assert isinstance(net, MLPPolicyNetwork)
