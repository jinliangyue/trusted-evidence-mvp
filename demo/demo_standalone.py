"""Standalone demo: 不依赖 CNN 模型，演示纯存证 + 验证流程。

用法:
    python demo/demo_standalone.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evidence.schemas import EvidenceRecord
from evidence.store import EvidenceStore
from evidence.verify import verify_chain


def main():
    db_path = Path(__file__).parent.parent / "data" / "demo_evidence.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    store = EvidenceStore(db_path)

    print()
    print("=" * 70)
    print("  Trusted Evidence MVP - Standalone Demo")
    print("  Maps to ISO Form 04 CD v1.1 §6.5.1 + §7.2-7.4")
    print("=" * 70)
    print()
    print(f"Database: {db_path}")
    print()

    events = [
        ("material_acceptance", {"material": "C30 混凝土", "qty_m3": 120, "supplier": "供应商 A"}),
        ("hidden_works_inspection", {"item": "钢筋绑扎", "qty_t": 8.5, "inspector": "张三"}),
        ("structural_acceptance", {"floor": 3, "result": "pass", "cracks_found": 0}),
        ("ai_defect_detection", {"label": "Crack", "confidence": 0.943, "model": "resnet18"}),
        ("maintenance_log", {"action": "裂缝修补", "cost_rmb": 1200, "worker": "李四"}),
    ]

    print(f"[1/3] Appending {len(events)} trusted events ...")
    for i, (event_type, payload) in enumerate(events):
        record = EvidenceRecord(
            sensor_id=f"SITE-{i:03d}",
            device_id="EDGE-NODE-DEMO",
            model_id="resnet18" if "ai" in event_type else "manual",
            model_version="v8.3" if "ai" in event_type else "n/a",
            acquisition_timestamp=f"2026-10-15T08:30:0{i}.000Z",
            phase="detection" if "ai" in event_type else "storage",
            operator="demo-runner",
            operation_type="create",
            payload_type=event_type,
            payload=payload,
        )
        seq = store.append(record)
        print(f"      sequence={seq}  {event_type:<28}  hash={record.record_hash[:16]}...")

    print()
    print("[2/3] Verifying the chain ...")
    result = verify_chain(store)
    print(f"      total={result.total}  valid={result.valid}  invalid={result.invalid}")
    print(f"      -> {'PASS' if result.is_valid else 'FAIL'}")

    print()
    print("[3/3] Reading back the AI defect detection record ...")
    ai_record = store.get_by_sequence(3)
    assert ai_record is not None
    print(f"      sensor_id:           {ai_record.sensor_id}")
    print(f"      model_id:            {ai_record.model_id}")
    print(f"      acquisition_ts:      {ai_record.acquisition_timestamp}")
    print(f"      payload.label:       {ai_record.payload['label']}")
    print(f"      payload.confidence:  {ai_record.payload['confidence']}")

    print()
    print("Next step: run demo_tamper.py to see tamper detection.")
    print()


if __name__ == "__main__":
    main()
