"""HMAC-SHA256 digital signatures for evidence records (v0.2).

Maps to CD v1.1:
  - §6.5.1 (c) Authenticity               -> signer_id field
  - §6.5.1 (f) Multi-party Verification   -> per-party HMAC secret
  - §7.2         Data integrity           -> signature chained with hash chain

v0.2 design choices:
  - HMAC-SHA256 instead of full PKI for student-MVP scope.
  - Each record optionally carries (signer_id, signature).
  - v0.1 records without signatures still verify (backward compatible).
  - signer_id is derived from secret so different parties can be tracked
    without exposing the secret.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from .schemas import EvidenceRecord


def generate_key() -> bytes:
    """Generate a cryptographically random 32-byte HMAC key."""
    return secrets.token_bytes(32)


def signer_id_from_secret(secret: bytes, prefix: str = "signer") -> str:
    """Derive a stable 16-hex-char signer_id from the secret.

    Tracking which party signed which record without exposing the secret.
    """
    digest = hashlib.sha256(secret).hexdigest()[:16]
    return f"{prefix}-{digest}"


def sign_record(record: EvidenceRecord, secret: bytes) -> str:
    """Compute HMAC-SHA256 over the record's canonical JSON.

    Mutates record.signature and record.signer_id in place.
    Returns the hex signature.
    """
    if not secret:
        raise ValueError("secret must be non-empty bytes")
    # Set signer_id BEFORE canonical_json so it's included in the signed msg.
    # Otherwise sign and verify would compute different msgs (signer_id transitions
    # from None to a derived string), and verification would always fail.
    if record.signer_id is None:
        record.signer_id = signer_id_from_secret(secret)
    msg = record.canonical_json().encode("utf-8")
    sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    record.signature = sig
    return sig


def verify_signature(record: EvidenceRecord, secret: bytes) -> bool:
    """Verify HMAC-SHA256 signature. Constant-time comparison.

    Records without signature return True (backward compat with v0.1).
    """
    if record.signature is None:
        return True
    if not secret:
        return False
    msg = record.canonical_json().encode("utf-8")
    expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, record.signature)


__all__ = [
    "generate_key",
    "signer_id_from_secret",
    "sign_record",
    "verify_signature",
]
