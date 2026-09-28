"""Evidence record schema.

Maps to CD v1.1 §6.5.1 seven trusted data functions:

  a) Data Integrity              → hash_chain (prev_hash + record_hash)
  b) Provenance                  → sensor_id / device_id / model_id / model_version
  c) Authenticity                → device_id (forgery requires private key — v2)
  d) Timestamp Verifiability     → acquisition_timestamp + record_timestamp
  e) Auditability                → operation_type + operator
  f) Multi-party Verification    → (v1: placeholder fields; v2: signature)
  g) Lifecycle Traceability      → phase (detection/evaluation/storage)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal


def utc_now_iso() -> str:
    """ISO 8601 UTC timestamp with millisecond precision (per CD §6.1.2)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


Phase = Literal["detection", "evaluation", "storage"]
OperationType = Literal["create", "read", "verify"]


@dataclass
class EvidenceRecord:
    """One trusted evidence record in the append-only hash chain."""

    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sequence: int = 0  # 0-indexed position in the chain (set by store)

    # --- CD §6.5.1 (b) Provenance + (c) Authenticity ---
    sensor_id: str = ""
    device_id: str = ""
    model_id: str = ""
    model_version: str = ""

    # --- CD §6.5.1 (d) Timestamp Verifiability ---
    acquisition_timestamp: str = ""
    record_timestamp: str = field(default_factory=utc_now_iso)

    # --- CD §6.5.1 (g) Lifecycle Traceability ---
    phase: Phase = "detection"

    # --- CD §6.5.1 (e) Auditability ---
    operator: str = "system"
    operation_type: OperationType = "create"

    # --- The actual payload ---
    payload_type: str = "ai_inference"
    payload: dict = field(default_factory=dict)

    # --- Hash chain (filled by store) ---
    prev_hash: str = "0" * 64
    record_hash: str = ""

    def to_canonical_dict(self) -> dict:
        """Canonical dict for hashing (excludes record_hash itself)."""
        d = asdict(self)
        d.pop("record_hash")
        return d

    def canonical_json(self) -> str:
        """Deterministic JSON for hashing (sorted keys, no whitespace)."""
        return json.dumps(self.to_canonical_dict(), sort_keys=True, separators=(",", ":"))


__all__ = ["EvidenceRecord", "Phase", "OperationType", "utc_now_iso"]
