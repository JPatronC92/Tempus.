import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict

def _to_iso_utc(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    raise TypeError("Unsupported date type for canonicalization")

def canonicalize_payload(
    *,
    urn_global: str,
    vigencia_desde: datetime | str,
    vigencia_hasta: datetime | str | None,
    esquema_id: str,
    logica_json: Dict[str, Any],
) -> bytes:
    payload = {
        "urn_global": urn_global,
        "vigencia_desde": _to_iso_utc(vigencia_desde),
        "vigencia_hasta": _to_iso_utc(vigencia_hasta),
        "esquema_id": str(esquema_id),
        "logica_json": logica_json,
    }

    canonical_str = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return canonical_str.encode("utf-8")

def generate_hmac(canonical_bytes: bytes, secret_key: bytes | None = None) -> str:
    """Generates an HMAC-SHA256 hash for the given bytes using the provided or default secret key."""
    import hmac
    
    if secret_key is None:
        from src.core.config import get_settings
        # encode settings.SECRET_KEY to bytes
        secret_key = get_settings().SECRET_KEY.encode('utf-8')

    return hmac.new(
        secret_key,
        canonical_bytes,
        hashlib.sha256
    ).hexdigest()

def verify_hmac(canonical_bytes: bytes, received_hash: str, secret_key: bytes | None = None) -> bool:
    """Verifies that the provided hash matches the HMAC-SHA256 of the canonical bytes."""
    import hmac
    expected_hash = generate_hmac(canonical_bytes, secret_key)
    return hmac.compare_digest(received_hash, expected_hash)
