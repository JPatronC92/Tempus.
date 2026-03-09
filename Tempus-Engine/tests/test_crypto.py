from datetime import datetime, timezone
from src.domain.services.crypto import canonicalize_payload, generate_hmac, verify_hmac

def test_canonicalize_payload_order_independence():
    """Test that two JSON dicts with different key orders generate the same hash"""
    json1 = {"b": 2, "a": 1, "c": {"z": 100, "x": 50}}
    json2 = {"a": 1, "c": {"x": 50, "z": 100}, "b": 2}

    payload1 = canonicalize_payload(
        urn_global="urn:test",
        vigencia_desde=datetime(2023, 1, 1, tzinfo=timezone.utc),
        vigencia_hasta=None,
        esquema_id="schema123",
        logica_json=json1
    )

    payload2 = canonicalize_payload(
        urn_global="urn:test",
        vigencia_desde=datetime(2023, 1, 1, tzinfo=timezone.utc),
        vigencia_hasta=None,
        esquema_id="schema123",
        logica_json=json2
    )

    assert payload1 == payload2
    assert generate_hmac(payload1, b"test_secret") == generate_hmac(payload2, b"test_secret")

def test_canonicalize_payload_change_modifies_hash():
    """Test that modifying a single field changes the generated hash"""
    json_base = {"a": 1}

    payload_base = canonicalize_payload(
        urn_global="urn:test",
        vigencia_desde=datetime(2023, 1, 1, tzinfo=timezone.utc),
        vigencia_hasta=None,
        esquema_id="schema123",
        logica_json=json_base
    )

    payload_modified = canonicalize_payload(
        urn_global="urn:test",
        vigencia_desde=datetime(2023, 1, 2, tzinfo=timezone.utc), # Modified date
        vigencia_hasta=None,
        esquema_id="schema123",
        logica_json=json_base
    )

    assert generate_hmac(payload_base, b"test_secret") != generate_hmac(payload_modified, b"test_secret")

def test_verify_hmac():
    payload = b"dummy_payload"
    secret = b"my_super_secret"
    h = generate_hmac(payload, secret)
    
    assert verify_hmac(payload, h, secret) is True
    assert verify_hmac(payload, h, b"wrong_secret") is False
    assert verify_hmac(b"tampered", h, secret) is False
