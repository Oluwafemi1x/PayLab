from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from paylab.models import HistoryEvent, ProviderName, TriggerRequest, TriggerResponse


def _normalize_database_url(database_url: str) -> str:
    value = database_url.strip()
    if value.startswith("postgresql+psycopg://"):
        return "postgresql://" + value.removeprefix("postgresql+psycopg://")
    if value.startswith("postgres://"):
        return "postgresql://" + value.removeprefix("postgres://")
    if value.startswith("postgresql://"):
        return value
    raise ValueError("PostgresEventHistory requires a PostgreSQL database URL.")


class PostgresEventHistory:
    """PostgreSQL-backed PayLab event history.

    Signing secrets and raw signed webhook bodies are never persisted.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = _normalize_database_url(database_url)
        self._initialize()

    def _connect(self):
        return psycopg.connect(
            self.database_url,
            row_factory=dict_row,
            connect_timeout=5,
        )

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
                    invalid_signature BOOLEAN NOT NULL,
                    retry_count INTEGER NOT NULL,
                    fault TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    metadata_json JSONB NOT NULL,
                    deliveries_json JSONB NOT NULL
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
        metadata = request.model_dump(mode="json")["metadata"]
        deliveries = [item.model_dump(mode="json") for item in response.deliveries]
        created_at = datetime.now(UTC)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO events (
                    event_id, provider, event, target_url, duplicate, invalid_signature,
                    retry_count, fault, created_at, metadata_json, deliveries_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO UPDATE SET
                    provider = EXCLUDED.provider,
                    event = EXCLUDED.event,
                    target_url = EXCLUDED.target_url,
                    duplicate = EXCLUDED.duplicate,
                    invalid_signature = EXCLUDED.invalid_signature,
                    retry_count = EXCLUDED.retry_count,
                    fault = EXCLUDED.fault,
                    created_at = EXCLUDED.created_at,
                    metadata_json = EXCLUDED.metadata_json,
                    deliveries_json = EXCLUDED.deliveries_json
                """,
                (
                    response.event_id,
                    response.provider,
                    response.event,
                    response.target_url,
                    response.duplicate,
                    response.invalid_signature,
                    response.retry_count,
                    response.fault,
                    created_at,
                    Jsonb(metadata),
                    Jsonb(deliveries),
                ),
            )

    def list_events(
        self, *, limit: int = 50, provider: ProviderName | None = None
    ) -> list[HistoryEvent]:
        limit = max(1, min(limit, 200))
        with self._connect() as connection:
            if provider is None:
                rows = connection.execute(
                    "SELECT * FROM events ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM events
                    WHERE provider = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (provider, limit),
                ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_event(self, event_id: str) -> HistoryEvent | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM events WHERE event_id = %s",
                (event_id,),
            ).fetchone()
        return self._row_to_event(row) if row else None

    @staticmethod
    def _row_to_event(row: Mapping[str, Any]) -> HistoryEvent:
        return HistoryEvent(
            event_id=row["event_id"],
            provider=row["provider"],
            event=row["event"],
            target_url=row["target_url"],
            duplicate=row["duplicate"],
            invalid_signature=row["invalid_signature"],
            retry_count=row["retry_count"],
            fault=row["fault"],
            created_at=row["created_at"],
            metadata=row["metadata_json"],
            deliveries=row["deliveries_json"],
        )
