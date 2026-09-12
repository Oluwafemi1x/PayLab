from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from paylab.models import HistoryEvent, ProviderName, TriggerRequest, TriggerResponse


class HistoryStore(Protocol):
    """Storage contract shared by SQLite and PostgreSQL history backends."""

    def record(self, request: TriggerRequest, response: TriggerResponse) -> None: ...

    def list_events(
        self, *, limit: int = 50, provider: ProviderName | None = None
    ) -> list[HistoryEvent]: ...

    def get_event(self, event_id: str) -> HistoryEvent | None: ...


class EventHistory:
    """Small SQLite event store for local PayLab runs.

    Secrets and raw webhook bodies are deliberately not persisted.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            configured = os.getenv("PAYLAB_DB_PATH")
            db_path = configured or (Path.home() / ".paylab" / "paylab.db")
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    event TEXT NOT NULL,
                    target_url TEXT NOT NULL,
                    duplicate INTEGER NOT NULL,
                    invalid_signature INTEGER NOT NULL,
                    retry_count INTEGER NOT NULL,
                    fault TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    deliveries_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_provider ON events(provider)"
            )

    def record(self, request: TriggerRequest, response: TriggerResponse) -> None:
        created_at = datetime.now(UTC).isoformat()
        deliveries = [item.model_dump(mode="json") for item in response.deliveries]
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO events (
                    event_id, provider, event, target_url, duplicate, invalid_signature,
                    retry_count, fault, created_at, metadata_json, deliveries_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    response.event_id,
                    response.provider,
                    response.event,
                    response.target_url,
                    response.duplicate,
                    int(response.invalid_signature),
                    response.retry_count,
                    response.fault,
                    created_at,
                    json.dumps(request.model_dump(mode="json")["metadata"], separators=(",", ":")),
                    json.dumps(deliveries, separators=(",", ":")),
                ),
            )

    def list_events(
        self, *, limit: int = 50, provider: ProviderName | None = None
    ) -> list[HistoryEvent]:
        limit = max(1, min(limit, 200))
        query = "SELECT * FROM events"
        params: list[Any] = []
        if provider:
            query += " WHERE provider = ?"
            params.append(provider)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_event(self, event_id: str) -> HistoryEvent | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM events WHERE event_id = ?", (event_id,)
            ).fetchone()
        return self._row_to_event(row) if row else None

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> HistoryEvent:
        return HistoryEvent(
            event_id=row["event_id"],
            provider=row["provider"],
            event=row["event"],
            target_url=row["target_url"],
            duplicate=row["duplicate"],
            invalid_signature=bool(row["invalid_signature"]),
            retry_count=row["retry_count"],
            fault=row["fault"],
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata_json"]),
            deliveries=json.loads(row["deliveries_json"]),
        )


_history_store: HistoryStore | None = None


def _build_history_store() -> HistoryStore:
    database_url = os.getenv("PAYLAB_DATABASE_URL", "").strip()
    if not database_url:
        return EventHistory()

    if database_url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
        try:
            from paylab.postgres_history import PostgresEventHistory
        except ModuleNotFoundError as exc:
            if exc.name == "psycopg":
                raise RuntimeError(
                    "PostgreSQL history requires the optional dependency: "
                    'pip install "paylab-dev[postgres]"'
                ) from exc
            raise
        return PostgresEventHistory(database_url)

    raise ValueError(
        "PAYLAB_DATABASE_URL currently supports PostgreSQL URLs only "
        "(postgresql://, postgres://, or postgresql+psycopg://)."
    )


def get_history_store() -> HistoryStore:
    global _history_store
    if _history_store is None:
        _history_store = _build_history_store()
    return _history_store


def _reset_history_store_for_tests() -> None:
    global _history_store
    _history_store = None
