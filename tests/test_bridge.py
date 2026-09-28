"""Tests for the CNN-inference bridge."""

from pathlib import Path

import pytest

from evidence.bridge import evidence_from_inference, store_inference
from evidence.schemas import EvidenceRecord
from evidence.store import EvidenceStore
from evidence.verify import verify_chain


@pytest.fixture
def store(tmp_path: Path) -> EvidenceStore:
    return EvidenceStore(tmp_path / "bridge_evidence.db")


def _mock_inference(label: str = "Crack", confidence: float = 0.95) -> dict:
    return {
        "label": label,
        "confidence": confidence,
        "probs": {"NoCrack": 1 - confidence, "Crack": confidence},
        "model": "resnet18",
        "img_size": 160,
        "checkpoint_accuracy": 0.8792,
    }


def test_evidence_from_inference_maps_all_fields():
    record = evidence_from_inference(
        _mock_inference(label="NoCrack", confidence=0.87),
        sensor_id="AI-CAM-FIELD-07",
        device_id="EDGE-NODE-DEMO",
    )
    assert record.sensor_id == "AI-CAM-FIELD-07"
    assert record.device_id == "EDGE-NODE-DEMO"
    assert record.model_id == "resnet18"
    assert record.model_version == "v8.3"
    assert record.payload_type == "ai_inference"
    assert record.payload["label"] == "NoCrack"
    assert record.payload["confidence"] == 0.87
    assert record.payload["img_size"] == 160


def test_store_inference_appends_and_chain_holds(store: EvidenceStore):
    seq_a = store_inference(store, _mock_inference(label="Crack", confidence=0.95))
    seq_b = store_inference(store, _mock_inference(label="NoCrack", confidence=0.92))
    seq_c = store_inference(store, _mock_inference(label="Crack", confidence=0.88))

    assert [seq_a, seq_b, seq_c] == [0, 1, 2]
    result = verify_chain(store)
    assert result.is_valid
    assert result.total == 3


def test_store_inference_records_are_chronological(store: EvidenceStore):
    store_inference(store, _mock_inference())
    record = store.get_by_sequence(0)
    assert record is not None
    assert record.acquisition_timestamp.endswith("Z")
    assert "T" in record.acquisition_timestamp
