"""Chain integrity verification.

Maps to CD v1.1 §6.5.1 (a) Data Integrity and §7.2 (Data integrity).

Two checks per record:
  1. record_hash matches SHA256(canonical_json(record))
     → catches payload tampering and metadata tampering
  2. prev_hash matches previous record's record_hash
     → catches deletion, reordering, and chain breaks
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from .schemas import EvidenceRecord
from .store import EvidenceStore, compute_record_hash
from .signatures import verify_signature


@dataclass
class VerificationResult:
    """Result of chain integrity verification."""

    total: int
    valid: int
    invalid: int
    first_invalid_sequence: int | None
    error_message: str = ""
    signature_checked: int = 0  # records that had a signature to verify

    @property
    def is_valid(self) -> bool:
        return self.invalid == 0 and self.error_message == ""


def verify_chain(
    store: EvidenceStore,
    signature_secret: bytes | None = None,
) -> VerificationResult:
    """Verify the entire chain against its recorded hashes.

    If signature_secret is provided, also verify HMAC-SHA256 signatures
    on records that carry one. v0.1 records without signatures skip the
    signature check (backward compatible).
    """
    prev_hash = "0" * 64  # genesis
    valid = 0
    invalid = 0
    first_invalid: int | None = None
    error_message = ""
    signature_checked = 0

    records = list(store.iter_all())
    for record in records:
        expected_hash = compute_record_hash(record)
        if expected_hash != record.record_hash:
            invalid += 1
            if first_invalid is None:
                first_invalid = record.sequence
                error_message = (
                    f"Sequence {record.sequence}: record_hash mismatch "
                    f"(expected {expected_hash[:16]}..., got {record.record_hash[:16]}...)"
                )
            continue

        if record.prev_hash != prev_hash:
            invalid += 1
            if first_invalid is None:
                first_invalid = record.sequence
                error_message = (
                    f"Sequence {record.sequence}: prev_hash chain break "
                    f"(expected {prev_hash[:16]}..., got {record.prev_hash[:16]}...)"
                )
            continue

        if signature_secret is not None and record.signature is not None:
            signature_checked += 1
            if not verify_signature(record, signature_secret):
                invalid += 1
                if first_invalid is None:
                    first_invalid = record.sequence
                    error_message = (
                        f"Sequence {record.sequence}: signature verification failed "
                        f"(signer_id={record.signer_id})"
                    )
                continue

        valid += 1
        prev_hash = record.record_hash

    if not records and not error_message:
        error_message = "Empty chain"

    return VerificationResult(
        total=len(records),
        valid=valid,
        invalid=invalid,
        first_invalid_sequence=first_invalid,
        error_message=error_message,
        signature_checked=signature_checked,
    )


def tamper_for_demo(store: EvidenceStore, sequence: int, field: str, new_value) -> None:
    """Bypass append() and mutate one payload field directly in SQLite.

    Used by demo_tamper.py to prove that the chain catches out-of-band edits.
    Note: tampering the payload invalidates the record_hash AND the signature
    (if any), so both will be caught by verify_chain with signature_secret.
    """
    with sqlite3.connect(store.db_path) as conn:
        row = conn.execute(
            "SELECT payload_json FROM evidence WHERE sequence = ?", (sequence,)
        ).fetchone()
        if row is None:
            raise ValueError(f"No record at sequence {sequence}")
        payload = json.loads(row[0])
        payload[field] = new_value
        conn.execute(
            "UPDATE evidence SET payload_json = ? WHERE sequence = ?",
            (json.dumps(payload, sort_keys=True), sequence),
        )
        conn.commit()


__all__ = ["VerificationResult", "verify_chain", "tamper_for_demo"]
