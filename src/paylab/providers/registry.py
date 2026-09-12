from __future__ import annotations

import re
import warnings
from importlib import metadata as importlib_metadata

from paylab.providers.base import ProviderAdapter
from paylab.providers.flutterwave import FlutterwaveAdapter
from paylab.providers.monnify import MonnifyAdapter
from paylab.providers.paystack import PaystackAdapter
from paylab.providers.stripe import StripeAdapter

ENTRY_POINT_GROUP = "paylab.providers"
_PROVIDER_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

BUILTIN_PROVIDERS: dict[str, ProviderAdapter] = {
    "paystack": PaystackAdapter(),
    "stripe": StripeAdapter(),
    "flutterwave": FlutterwaveAdapter(),
    "monnify": MonnifyAdapter(),
}

PROVIDERS: dict[str, ProviderAdapter] = dict(BUILTIN_PROVIDERS)
_discovered = False


def normalize_provider_name(name: str) -> str:
    normalized = name.strip().lower()
    if not _PROVIDER_NAME_RE.fullmatch(normalized):
        raise ValueError(
            "Provider names must start with a letter or digit and contain only "
            "lowercase letters, digits, '.', '_' or '-'."
        )
    return normalized


def _coerce_adapter(entry_point_name: str, loaded: object) -> ProviderAdapter:
    candidate = loaded() if isinstance(loaded, type) and issubclass(loaded, ProviderAdapter) else loaded
    if not isinstance(candidate, ProviderAdapter):
        raise TypeError("provider entry point must resolve to a ProviderAdapter instance or subclass")

    adapter_name = normalize_provider_name(candidate.name)
    if adapter_name != entry_point_name:
        raise ValueError(
            f"entry point name '{entry_point_name}' does not match adapter.name '{adapter_name}'"
        )
    return candidate


def register_provider(
    adapter: ProviderAdapter,
    *,
    name: str | None = None,
    replace: bool = False,
) -> ProviderAdapter:
    provider_name = normalize_provider_name(name or adapter.name)
    if provider_name in PROVIDERS and not replace:
        raise ValueError(f"Provider '{provider_name}' is already registered")
    PROVIDERS[provider_name] = adapter
    return adapter


def load_entry_point_providers(*, force: bool = False) -> dict[str, ProviderAdapter]:
    global _discovered
    if _discovered and not force:
        return PROVIDERS

    if force:
        PROVIDERS.clear()
        PROVIDERS.update(BUILTIN_PROVIDERS)

    for entry_point in importlib_metadata.entry_points(group=ENTRY_POINT_GROUP):
        try:
            provider_name = normalize_provider_name(entry_point.name)
            if provider_name in PROVIDERS:
                warnings.warn(
                    f"Ignoring PayLab provider plugin '{provider_name}' because that name is already registered.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            register_provider(_coerce_adapter(provider_name, entry_point.load()), name=provider_name)
        except Exception as exc:  # noqa: BLE001 - third-party plugin boundary
            warnings.warn(
                f"Ignoring invalid PayLab provider plugin '{entry_point.name}': {exc}",
                RuntimeWarning,
                stacklevel=2,
            )

    _discovered = True
    return PROVIDERS


def get_provider(name: str) -> ProviderAdapter:
    load_entry_point_providers()
    provider_name = normalize_provider_name(name)
    try:
        return PROVIDERS[provider_name]
    except KeyError as exc:
        available = ", ".join(sorted(PROVIDERS))
        raise ValueError(
            f"Unsupported provider '{provider_name}'. Available providers: {available}"
        ) from exc


def provider_names() -> list[str]:
    load_entry_point_providers()
    return sorted(PROVIDERS)


def _reset_provider_registry_for_tests() -> None:
    global _discovered
    PROVIDERS.clear()
    PROVIDERS.update(BUILTIN_PROVIDERS)
    _discovered = False
