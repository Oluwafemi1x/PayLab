from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BuiltEvent:
    event_id: str
    body: bytes
    headers: dict[str, str]


class ProviderAdapter(ABC):
    name: str

    @abstractmethod
    def build_event(
        self,
        event_type: str,
        secret: str,
        metadata: dict[str, Any],
        *,
        invalid_signature: bool = False,
    ) -> BuiltEvent:
        raise NotImplementedError
