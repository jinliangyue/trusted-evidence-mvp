"""Tests for the evidence store."""

from pathlib import Path

import pytest

from evidence.schemas import EvidenceRecord
from evidence.store import EvidenceStore, compute_record_hash


@pytest.fixture
def store(tmp_path: Path) -> EvidenceStore:
    return EvidenceStore(tmp_path / "test_evidence.db")


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


def test_store_init_creates_empty_table(store: EvidenceStore):
    assert store.count() == 0


def test_append_single_record_assigns_sequence_0(store: EvidenceStore):
    record = _make_record()
    seq = store.append(record)
    assert seq == 0
    assert store.count() == 1


def test_two_appends_form_a_hash_chain(store: EvidenceStore):
    r1 = _make_record(payload={"label": "Crack", "confidence": 0.95})
    r2 = _make_record(payload={"label": "NoCrack", "confidence": 0.87})
    seq1 = store.append(r1)
    seq2 = store.append(r2)
    assert seq1 == 0
    assert seq2 == 1

    fetched = store.get_by_sequence(seq2)
    assert fetched is not None
    assert fetched.prev_hash == r1.record_hash
    assert fetched.record_hash != ""
    assert fetched.prev_hash != "0" * 64


def test_record_hash_is_deterministic_and_64_hex(store: EvidenceStore):
    record = _make_record(payload={"a": 1, "b": 2})
    h1 = compute_record_hash(record)
    h2 = compute_record_hash(record)
    assert h1 == h2
    assert len(h1) == 64


def test_canonical_json_is_key_order_independent():
    # record_id and record_timestamp differ by default; pin them for this test
    r1 = _make_record(record_id="fixed-id", record_timestamp="2026-01-01T00:00:00.000Z",
                      payload={"a": 1, "b": 2})
    r2 = _make_record(record_id="fixed-id", record_timestamp="2026-01-01T00:00:00.000Z",
                      payload={"b": 2, "a": 1})
    assert r1.canonical_json() == r2.canonical_json()


def test_payload_change_changes_hash():
    r1 = _make_record(payload={"label": "Crack", "confidence": 0.95})
    r2 = _make_record(payload={"label": "Crack", "confidence": 0.96})
    assert compute_record_hash(r1) != compute_record_hash(r2)


def test_get_by_sequence_returns_none_for_missing(store: EvidenceStore):
    assert store.get_by_sequence(999) is None


def test_iter_all_returns_records_in_order(store: EvidenceStore):
    for i in range(5):
        store.append(_make_record(payload={"i": i}))
    sequences = [r.sequence for r in store.iter_all()]
    assert sequences == [0, 1, 2, 3, 4]
