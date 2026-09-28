"""Tests for HMAC-SHA256 digital signatures (v0.2)."""

import copy
from pathlib import Path

import pytest

from evidence.schemas import EvidenceRecord
from evidence.signatures import (
    generate_key,
    sign_record,
    signer_id_from_secret,
    verify_signature,
)
from evidence.store import EvidenceStore
from evidence.verify import verify_chain


@pytest.fixture
def secret() -> bytes:
    return generate_key()


def _make_record(**overrides) -> EvidenceRecord:
    defaults = dict(
        sensor_id="AI-CAM-01",
        device_id="EDGE-01",
        model_id="resnet18",
        model_version="v8.3",
        acquisition_timestamp="2026-10-15T08:30:15.123Z",
        payload={"label": "Crack", "confidence": 0.95},
    )
    defaults.update(overrides)
    return EvidenceRecord(**defaults)


def test_generate_key_returns_32_bytes():
    key = generate_key()
    assert isinstance(key, bytes)
    assert len(key) == 32


def test_generate_key_is_random():
    assert generate_key() != generate_key()


def test_signer_id_is_deterministic_and_16_hex(secret):
    sid1 = signer_id_from_secret(secret)
    sid2 = signer_id_from_secret(secret)
    assert sid1 == sid2
    assert sid1.startswith("signer-")
    assert len(sid1) == len("signer-") + 16


def test_signer_id_differs_per_secret():
    sid1 = signer_id_from_secret(generate_key())
    sid2 = signer_id_from_secret(generate_key())
    assert sid1 != sid2


def test_sign_record_sets_signature_and_signer_id(secret):
    record = _make_record()
    assert record.signature is None
    assert record.signer_id is None
    sig = sign_record(record, secret)
    assert record.signature == sig
    assert record.signature is not None
    assert len(record.signature) == 64  # SHA-256 hex
    assert record.signer_id is not None
    assert record.signer_id.startswith("signer-")


def test_sign_then_verify_roundtrip(secret):
    record = _make_record()
    sign_record(record, secret)
    assert verify_signature(record, secret) is True


def test_verify_signature_fails_with_wrong_secret(secret):
    record = _make_record()
    sign_record(record, secret)
    other_secret = generate_key()
    assert verify_signature(record, other_secret) is False


def test_verify_signature_returns_true_for_unsigned_record(secret):
    record = _make_record()
    assert record.signature is None
    assert verify_signature(record, secret) is True  # backward compat


def test_verify_signature_returns_false_if_secret_empty_for_signed_record(secret):
    record = _make_record()
    sign_record(record, secret)
    assert verify_signature(record, b"") is False


def test_sign_record_rejects_empty_secret():
    record = _make_record()
    with pytest.raises(ValueError, match="non-empty"):
        sign_record(record, b"")


def test_signature_does_not_include_record_hash_field():
    """The canonical_json excludes signature AND record_hash, so signing
    a record must be deterministic regardless of record_hash value."""
    record_a = _make_record(record_id="x", record_timestamp="2026-01-01T00:00:00.000Z")
    record_b = _make_record(record_id="x", record_timestamp="2026-01-01T00:00:00.000Z")
    secret = generate_key()
    sig_a = sign_record(record_a, secret)
    sig_b = sign_record(record_b, secret)
    # Both records have record_hash="" before signing, and signatures
    # should be identical because canonical_json is identical.
    assert sig_a == sig_b


def test_chain_with_signatures_verifies(tmp_path: Path, secret):
    db = tmp_path / "sig.db"
    s = EvidenceStore(db)
    for i in range(3):
        rec = _make_record(payload={"i": i})
        # Use append(secret=...) so signing happens AFTER prev_hash is set.
        s.append(rec, secret=secret)
    result = verify_chain(s, signature_secret=secret)
    assert result.is_valid
    assert result.signature_checked == 3


def test_chain_with_wrong_secret_signature_fails(tmp_path: Path, secret):
    db = tmp_path / "sig.db"
    s = EvidenceStore(db)
    for i in range(2):
        rec = _make_record(payload={"i": i})
        s.append(rec, secret=secret)
    wrong = generate_key()
    result = verify_chain(s, signature_secret=wrong)
    assert not result.is_valid
    assert result.first_invalid_sequence == 0
    assert "signature verification failed" in result.error_message


def test_chain_backward_compat_without_signing(tmp_path: Path, secret):
    """v0.1 records (no signature) still verify when signature_secret provided."""
    db = tmp_path / "sig.db"
    s = EvidenceStore(db)
    for i in range(2):
        rec = _make_record(payload={"i": i})  # no signing
        s.append(rec)
    result = verify_chain(s, signature_secret=secret)
    assert result.is_valid
    assert result.signature_checked == 0  # no records had signatures to check
