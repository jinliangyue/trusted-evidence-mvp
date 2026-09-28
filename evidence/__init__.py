"""Trusted evidence package — minimal hash-chain evidence store.

Maps to ISO Form 04 CD v1.1 §6.5.1 (Trusted Data Functions)
and §7.2 / §7.3 / §7.4 (Data Integrity / Provenance / Auditability).
"""

from .schemas import EvidenceRecord, utc_now_iso
from .store import EvidenceStore, compute_record_hash
from .verify import VerificationResult, verify_chain, tamper_for_demo
from .bridge import evidence_from_inference, store_inference
from .signatures import (
    generate_key,
    sign_record,
    signer_id_from_secret,
    verify_signature,
)

__all__ = [
    "EvidenceRecord",
    "utc_now_iso",
    "EvidenceStore",
    "compute_record_hash",
    "VerificationResult",
    "verify_chain",
    "tamper_for_demo",
    "evidence_from_inference",
    "store_inference",
    "generate_key",
    "sign_record",
    "signer_id_from_secret",
    "verify_signature",
]
