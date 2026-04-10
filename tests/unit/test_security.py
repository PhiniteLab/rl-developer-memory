"""Unit tests for rl_developer_memory.security redaction module."""

from __future__ import annotations

import json

import pytest

from rl_developer_memory.security import (
    _looks_secret_key,
    _looks_secret_value,
    _redact_text,
    sanitize_json_text,
    sanitize_mapping,
    sanitize_text,
)


# ---------------------------------------------------------------------------
# _looks_secret_key
# ---------------------------------------------------------------------------
class TestLooksSecretKey:
    @pytest.mark.parametrize(
        "key",
        [
            "password",
            "my_password",
            "API_KEY",
            "api-key",
            "client_secret",
            "auth_token",
            "private_key",
            "secret",
            "MY_SECRET",
            "authorization",
            "credential",
            "token",
        ],
    )
    def test_detects_secret_keys(self, key: str) -> None:
        assert _looks_secret_key(key), f"Expected '{key}' to be detected as secret"

    @pytest.mark.parametrize(
        "key",
        [
            "username",
            "hostname",
            "port",
            "debug",
            "count",
            "description",
            "project_scope",
        ],
    )
    def test_safe_keys_pass(self, key: str) -> None:
        assert not _looks_secret_key(key), f"'{key}' should NOT be secret"


# ---------------------------------------------------------------------------
# _looks_secret_value
# ---------------------------------------------------------------------------
class TestLooksSecretValue:
    @pytest.mark.parametrize(
        "value",
        [
            "sk-abc12345678",
            "ghp_abcdefghijklmn",
            "xoxb-123456789-abcde",
            "AKIAIOSFODNN7EXAMPLE",
            "AIzaSyB4_QxCkE11__abcdefghijk",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig",
        ],
    )
    def test_detects_known_secret_patterns(self, value: str) -> None:
        assert _looks_secret_value(value), f"Expected '{value}' to be detected"

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "hello-world",
            "12345",
            "short",
        ],
    )
    def test_safe_values_pass(self, value: str) -> None:
        assert not _looks_secret_value(value), f"'{value}' should NOT be secret"

    def test_long_alphanumeric_detected(self) -> None:
        long_token = "A" * 30
        assert _looks_secret_value(long_token)


# ---------------------------------------------------------------------------
# _redact_text
# ---------------------------------------------------------------------------
class TestRedactText:
    def test_redact_bearer_token(self) -> None:
        text = "Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.payload.sig"
        result = _redact_text(text)
        assert "eyJhbGciOiJSUzI1NiJ9" not in result
        assert "[REDACTED]" in result

    def test_redact_private_key(self) -> None:
        pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIBogIB...\n-----END RSA PRIVATE KEY-----"
        result = _redact_text(pem)
        assert "MIIBogIB" not in result
        assert "[REDACTED_PRIVATE_KEY]" in result

    def test_redact_api_key_assignment(self) -> None:
        text = "api_key=sk-secret12345"
        result = _redact_text(text)
        assert "sk-secret12345" not in result

    def test_preserves_normal_text(self) -> None:
        text = "This is a normal log line with no secrets."
        result = _redact_text(text)
        assert result == text


# ---------------------------------------------------------------------------
# sanitize_text
# ---------------------------------------------------------------------------
class TestSanitizeText:
    def test_redacts_when_enabled(self) -> None:
        text = "token: Bearer abc123xyz"
        result = sanitize_text(text, enabled=True)
        assert "abc123xyz" not in result

    def test_passthrough_when_disabled(self) -> None:
        text = "secret=mysecret123"
        result = sanitize_text(text, enabled=False)
        assert result == text

    def test_truncation(self) -> None:
        text = "x" * 200
        result = sanitize_text(text, max_chars=50)
        assert len(result) <= 50
        assert "truncated" in result

    def test_none_input(self) -> None:
        result = sanitize_text(None, enabled=True)  # type: ignore[arg-type]
        assert result == ""


# ---------------------------------------------------------------------------
# sanitize_json_text
# ---------------------------------------------------------------------------
class TestSanitizeJsonText:
    def test_redacts_keys_in_json(self) -> None:
        payload = json.dumps({"password": "hunter2", "name": "test"})
        result = sanitize_json_text(payload, enabled=True)
        parsed = json.loads(result)
        assert parsed["password"] == "[REDACTED]"
        assert parsed["name"] == "test"

    def test_redacts_nested_secrets(self) -> None:
        payload = json.dumps({"config": {"api_key": "sk-12345678abc"}})
        result = sanitize_json_text(payload, enabled=True)
        parsed = json.loads(result)
        assert parsed["config"]["api_key"] == "[REDACTED]"

    def test_passthrough_when_disabled(self) -> None:
        payload = json.dumps({"password": "hunter2"})
        result = sanitize_json_text(payload, enabled=False)
        assert "hunter2" in result

    def test_non_json_falls_back_to_text(self) -> None:
        text = "not json but has secret=abc123"
        result = sanitize_json_text(text, enabled=True)
        assert "abc123" not in result

    def test_empty_string(self) -> None:
        assert sanitize_json_text("", enabled=True) == ""


# ---------------------------------------------------------------------------
# sanitize_mapping
# ---------------------------------------------------------------------------
class TestSanitizeMapping:
    def test_redacts_secret_keys(self) -> None:
        data = {"password": "hunter2", "host": "localhost"}
        result = sanitize_mapping(data, enabled=True)
        assert result["password"] == "[REDACTED]"
        assert result["host"] == "localhost"

    def test_redacts_secret_values_in_safe_keys(self) -> None:
        data = {"env_var": "ghp_abcdefghijklmn"}
        result = sanitize_mapping(data, enabled=True)
        assert result["env_var"] == "[REDACTED]"

    def test_passthrough_when_disabled(self) -> None:
        data = {"password": "hunter2"}
        result = sanitize_mapping(data, enabled=False)
        assert result["password"] == "hunter2"

    def test_nested_mapping_redaction(self) -> None:
        data = {"outer": {"client_secret": "abc"}}
        result = sanitize_mapping(data, enabled=True)
        assert result["outer"]["client_secret"] == "[REDACTED]"
