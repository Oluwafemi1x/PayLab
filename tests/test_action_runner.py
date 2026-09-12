from pathlib import Path

import pytest

from paylab.action_runner import _as_bool, load_action_config


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYLAB_PROVIDER", "paystack")
    monkeypatch.setenv("PAYLAB_EVENT", "charge.success")
    monkeypatch.setenv("PAYLAB_TARGET_URL", "http://127.0.0.1:9000/webhooks/paystack")
    monkeypatch.setenv("PAYLAB_SECRET", "super-secret-value")


def test_action_config_reads_inputs_without_echoing_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("PAYLAB_MIN_SCORE", "90")
    monkeypatch.setenv("PAYLAB_DEEP", "true")
    monkeypatch.setenv("PAYLAB_JSON_REPORT", str(tmp_path / "gate.json"))
    monkeypatch.setenv("PAYLAB_HTML_REPORT", str(tmp_path / "gate.html"))

    config = load_action_config()

    assert config.request.provider == "paystack"
    assert config.request.secret == "super-secret-value"
    assert config.request.enable_fault_injection is True
    assert config.min_score == 90


def test_action_config_rejects_invalid_min_score(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("PAYLAB_MIN_SCORE", "101")

    with pytest.raises(ValueError):
        load_action_config()


def test_action_boolean_parser_is_strict() -> None:
    assert _as_bool("true") is True
    assert _as_bool("OFF") is False
    with pytest.raises(ValueError):
        _as_bool("sometimes")
