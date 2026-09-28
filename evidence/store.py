"""SQLite-backed append-only evidence store with SHA-256 hash chain.

Maps to CD v1.1:
  - §6.5.1 (a) Data Integrity         → SHA-256 hash chain per row
  - §6.5.2       Key event cert.      → append-only schema
  - §7.2         Data integrity       → hash-based verification
  - §7.3         Provenance           → full metadata in row
  - §7.4         Auditability         → operation_type + operator logged
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Iterator

from .schemas import EvidenceRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence (
    sequence             INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id            TEXT NOT NULL UNIQUE,
    sensor_id            TEXT NOT NULL,
    device_id            TEXT NOT NULL,
    model_id             TEXT NOT NULL,
    model_version        TEXT NOT NULL,
    acquisition_timestamp TEXT NOT NULL,
    record_timestamp     TEXT NOT NULL,
    phase                TEXT NOT NULL,
    operator             TEXT NOT NULL,
    operation_type       TEXT NOT NULL,
    payload_type         TEXT NOT NULL,
    payload_json         TEXT NOT NULL,
    prev_hash            TEXT NOT NULL,
    record_hash          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_record_id ON evidence(record_id);
CREATE INDEX IF NOT EXISTS idx_record_timestamp ON evidence(record_timestamp);
CREATE INDEX IF NOT EXISTS idx_sensor_id ON evidence(sensor_id);
"""


def compute_record_hash(record: EvidenceRecord) -> str:
    """SHA-256 of canonical JSON (excluding record_hash itself)."""
    canonical = record.canonical_json().encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class EvidenceStore:
    """Append-only evidence store with hash chain integrity."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _last_record(self, conn: sqlite3.Connection) -> tuple[int, str] | None:
        """Return (sequence, record_hash) of last record, or None if empty."""
        row = conn.execute(
            "SELECT sequence, record_hash FROM evidence ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        return (row["sequence"], row["record_hash"]) if row else None

    def append(self, record: EvidenceRecord) -> int:
        """Append a record to the chain. Returns the sequence number.

        Hash chain invariant:
            record.record_hash = SHA256(canonical_json(record))
        where canonical_json includes prev_hash = previous record's record_hash.
        """
        with self._connect() as conn:
            last = self._last_record(conn)
            if last is not None:
                last_seq, last_hash = last
                record.sequence = last_seq + 1
                record.prev_hash = last_hash

            record.record_hash = compute_record_hash(record)

            conn.execute(
                """
                INSERT INTO evidence (
                    sequence, record_id, sensor_id, device_id,
                    model_id, model_version,
                    acquisition_timestamp, record_timestamp,
                    phase, operator, operation_type,
                    payload_type, payload_json,
                    prev_hash, record_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.sequence,
                    record.record_id,
                    record.sensor_id,
                    record.device_id,
                    record.model_id,
                    record.model_version,
                    record.acquisition_timestamp,
                    record.record_timestamp,
                    record.phase,
                    record.operator,
                    record.operation_type,
                    record.payload_type,
                    json.dumps(record.payload, sort_keys=True),
                    record.prev_hash,
                    record.record_hash,
                ),
            )
            conn.commit()
            return record.sequence

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM evidence").fetchone()
            return row["n"]

    def get_by_sequence(self, sequence: int) -> EvidenceRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM evidence WHERE sequence = ?", (sequence,)
            ).fetchone()
            return self._row_to_record(row) if row else None

    def iter_all(self) -> Iterator[EvidenceRecord]:
        with self._connect() as conn:
            for row in conn.execute(
                "SELECT * FROM evidence ORDER BY sequence ASC"
            ).fetchall():
                yield self._row_to_record(row)

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> EvidenceRecord:
        return EvidenceRecord(
            sequence=row["sequence"],
            record_id=row["record_id"],
            sensor_id=row["sensor_id"],
            device_id=row["device_id"],
            model_id=row["model_id"],
            model_version=row["model_version"],
            acquisition_timestamp=row["acquisition_timestamp"],
            record_timestamp=row["record_timestamp"],
            phase=row["phase"],
            operator=row["operator"],
            operation_type=row["operation_type"],
            payload_type=row["payload_type"],
            payload=json.loads(row["payload_json"]),
            prev_hash=row["prev_hash"],
            record_hash=row["record_hash"],
        )


__all__ = ["EvidenceStore", "compute_record_hash", "SCHEMA"]
