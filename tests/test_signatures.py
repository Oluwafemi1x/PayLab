import base64
import hashlib
import hmac

from paylab.providers.flutterwave import FlutterwaveAdapter
from paylab.providers.paystack import PaystackAdapter
from paylab.providers.stripe import StripeAdapter


def test_paystack_signature_matches_body() -> None:
    secret = "sk_test_paylab"
    event = PaystackAdapter().build_event("charge.success", secret, {})
    expected = hmac.new(secret.encode(), event.body, hashlib.sha512).hexdigest()
    assert event.headers["x-paystack-signature"] == expected


def test_stripe_signature_matches_body() -> None:
    secret = "whsec_paylab"
    event = StripeAdapter().build_event("payment_intent.succeeded", secret, {})
    header = event.headers["Stripe-Signature"]
    timestamp = header.split(",")[0].split("=")[1]
    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + event.body, hashlib.sha256
    ).hexdigest()
    assert f"v1={expected}" in header


def test_flutterwave_signature_matches_body() -> None:
    secret = "flw_paylab"
    event = FlutterwaveAdapter().build_event("charge.completed", secret, {})
    digest = hmac.new(secret.encode(), event.body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    assert event.headers["flutterwave-signature"] == expected


def test_invalid_signature_is_actually_invalid() -> None:
    secret = "correct-secret"
    event = PaystackAdapter().build_event("charge.success", secret, {}, invalid_signature=True)
    correct = hmac.new(secret.encode(), event.body, hashlib.sha512).hexdigest()
    assert event.headers["x-paystack-signature"] != correct
