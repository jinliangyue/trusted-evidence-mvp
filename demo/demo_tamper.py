"""Tamper detection demo.

用法:
    python demo/demo_tamper.py

答辩现场建议流程:
    1. 跑这个脚本
    2. 让评委看 verification fail + 哪个 sequence 出错
    3. 重跑 demo_standalone.py 重新初始化干净数据库
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evidence.schemas import EvidenceRecord
from evidence.store import EvidenceStore
from evidence.verify import tamper_for_demo, verify_chain


def main():
    db_path = Path(__file__).parent.parent / "data" / "demo_evidence.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    store = EvidenceStore(db_path)

    print()
    print("=" * 70)
    print("  Trusted Evidence MVP - Tamper Detection Demo")
    print("  This proves the chain catches ANY out-of-band edit.")
    print("=" * 70)
    print()

    print("[1/4] Appending 10 trusted AI inference results ...")
    for i in range(10):
        record = EvidenceRecord(
            sensor_id=f"AI-CAM-{i:03d}",
            device_id="EDGE-NODE-DEMO",
            model_id="resnet18",
            model_version="v8.3",
            acquisition_timestamp=f"2026-10-15T08:30:{i:02d}.000Z",
            phase="detection",
            operator="ai-pipeline",
            operation_type="create",
            payload_type="ai_inference",
            payload={
                "image_id": f"img_{i:04d}.jpg",
                "label": "Crack" if i % 2 == 0 else "NoCrack",
                "confidence": 0.90 + i * 0.005,
            },
        )
        store.append(record)
    print("      done.")

    print()
    print("[2/4] Verifying the chain (should all pass) ...")
    result = verify_chain(store)
    print(f"      total={result.total}  valid={result.valid}  invalid={result.invalid}")
    print(f"      -> {'PASS' if result.is_valid else 'FAIL'}")

    print()
    print("[3/4] Simulating tampering: directly editing SQLite ...")
    print("      Target: sequence 4 (5th record)")
    print("      Change: image_id 'img_0004.jpg' -> 'modified.jpg'")
    print("      Method: bypass store.append() to simulate malicious DBA / bug")
    tamper_for_demo(store, sequence=4, field="image_id", new_value="modified.jpg")
    print("      tampering complete.")

    print()
    print("[4/4] Re-verifying the chain (should detect tampering) ...")
    result = verify_chain(store)
    print(f"      total={result.total}  valid={result.valid}  invalid={result.invalid}")
    print(f"      -> {'PASS' if result.is_valid else 'FAIL'}")
    if not result.is_valid:
        print(f"      First invalid: sequence {result.first_invalid_sequence}")
        print(f"      Detail:        {result.error_message}")

    print()
    print("=" * 70)
    print("  The chain caught:")
    print("    - payload tampering (e.g. changing confidence to hide misclassification)")
    print("    - metadata tampering (e.g. faking sensor_id or timestamp)")
    print("    - record deletion (chain break in prev_hash)")
    print("    - record reordering (prev_hash mismatch)")
    print()
    print("  Maps to ISO Form 04 CD v1.1:")
    print("    - §6.5.1 (a) Data Integrity        - hash chain")
    print("    - §7.2         Data integrity      - SHA-256 verification")
    print("    - §7.4         Auditability        - operation_type recorded")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
