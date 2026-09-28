"""Bridge between CNN inference and the evidence store.

Maps to CD v1.1:
  - §6.4.11 Model management           → model_id + model_version logged
  - §6.5.1 (b) Provenance               → full inference provenance
  - §6.5.2       Key engineering event  → each inference is a key event
  - §7.3         Provenance              → every inference carries provenance
"""

from __future__ import annotations

from .schemas import EvidenceRecord, utc_now_iso
from .store import EvidenceStore


def evidence_from_inference(
    inference_result: dict,
    sensor_id: str = "AI-CAM-CONCRETE-001",
    device_id: str = "EDGE-NODE-LOCAL-01",
    operator: str = "pipeline-v1",
    phase: str = "detection",
    model_version: str = "v8.3",
) -> EvidenceRecord:
    """Wrap a CNN inference result (from src.infer.predict) into an EvidenceRecord."""
    return EvidenceRecord(
        sensor_id=sensor_id,
        device_id=device_id,
        model_id=inference_result.get("model", "unknown"),
        model_version=model_version,
        acquisition_timestamp=utc_now_iso(),
        phase=phase,
        operator=operator,
        operation_type="create",
        payload_type="ai_inference",
        payload={
            "label": inference_result["label"],
            "confidence": inference_result["confidence"],
            "probs": inference_result["probs"],
            "img_size": inference_result.get("img_size"),
            "checkpoint_accuracy": inference_result.get("checkpoint_accuracy"),
        },
    )


def store_inference(
    store: EvidenceStore,
    inference_result: dict,
    **kwargs,
) -> int:
    """Build EvidenceRecord from inference + append to store. Returns sequence number."""
    record = evidence_from_inference(inference_result, **kwargs)
    return store.append(record)


__all__ = ["evidence_from_inference", "store_inference"]
