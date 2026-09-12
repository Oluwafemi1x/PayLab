from pathlib import Path

import pytest

import paylab.history as history_module
from paylab.history import EventHistory


def test_history_factory_uses_sqlite_without_database_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PAYLAB_DATABASE_URL", raising=False)
    monkeypatch.setenv("PAYLAB_DB_PATH", str(tmp_path / "factory.db"))
    history_module._reset_history_store_for_tests()

    store = history_module.get_history_store()

    assert isinstance(store, EventHistory)
    history_module._reset_history_store_for_tests()


def test_history_factory_rejects_unsupported_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAYLAB_DATABASE_URL", "mysql://localhost/paylab")
    history_module._reset_history_store_for_tests()

    with pytest.raises(ValueError, match="supports PostgreSQL"):
        history_module.get_history_store()

    history_module._reset_history_store_for_tests()
