"""Tests for chain integrity verification."""

import sqlite3
from pathlib import Path

import pytest

from evidence.schemas import EvidenceRecord
from evidence.store import EvidenceStore
from evidence.verify import tamper_for_demo, verify_chain


@pytest.fixture
def store_with_5_records(tmp_path: Path) -> EvidenceStore:
    db = tmp_path / "test_evidence.db"
    s = EvidenceStore(db)
    for i in range(5):
        s.append(
            EvidenceRecord(
                sensor_id="AI-CAM-01",
                device_id="EDGE-01",
                model_id="resnet18",
                model_version="v8.3",
                acquisition_timestamp=f"2026-10-15T08:30:0{i}.000Z",
                payload={"i": i, "label": "Crack", "confidence": 0.9 + i * 0.01},
            )
        )
    return s


def test_valid_chain_verifies(store_with_5_records: EvidenceStore):
    result = verify_chain(store_with_5_records)
    assert result.is_valid
    assert result.total == 5
    assert result.valid == 5
    assert result.invalid == 0
    assert result.first_invalid_sequence is None


def test_tampered_payload_detected(store_with_5_records: EvidenceStore):
    tamper_for_demo(
        store_with_5_records, sequence=2, field="confidence", new_value=0.01
    )
    result = verify_chain(store_with_5_records)
    assert not result.is_valid
    # Tampering at sequence 2 cascades: 3 and 4's prev_hash also break.
    assert result.invalid >= 1
    assert result.first_invalid_sequence == 2
    assert "record_hash mismatch" in result.error_message


def test_tampered_metadata_detected(store_with_5_records: EvidenceStore):
    tamper_for_demo(
        store_with_5_records, sequence=3, field="label", new_value="NoCrack"
    )
    result = verify_chain(store_with_5_records)
    assert not result.is_valid
    assert result.first_invalid_sequence == 3


def test_deleted_middle_record_detected_as_chain_break(
    store_with_5_records: EvidenceStore,
):
    with sqlite3.connect(store_with_5_records.db_path) as conn:
        conn.execute("DELETE FROM evidence WHERE sequence = 2")
        conn.commit()
    result = verify_chain(store_with_5_records)
    assert not result.is_valid
    assert result.first_invalid_sequence == 3


def test_empty_chain_returns_error(tmp_path: Path):
    store = EvidenceStore(tmp_path / "empty.db")
    result = verify_chain(store)
    assert result.total == 0
    assert not result.is_valid
    assert result.error_message == "Empty chain"
