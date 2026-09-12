from paylab.providers.base import ProviderAdapter
from paylab.providers.flutterwave import FlutterwaveAdapter
from paylab.providers.paystack import PaystackAdapter
from paylab.providers.stripe import StripeAdapter

PROVIDERS: dict[str, ProviderAdapter] = {
    "paystack": PaystackAdapter(),
    "stripe": StripeAdapter(),
    "flutterwave": FlutterwaveAdapter(),
}

__all__ = ["PROVIDERS", "ProviderAdapter"]
