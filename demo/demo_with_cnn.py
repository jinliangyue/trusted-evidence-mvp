"""CNN integration demo: calls jinliangyue/concrete-crack-detection infer.predict()
and stores each result into the trusted evidence chain.

用法:
    python demo/demo_with_cnn.py [image_path]

依赖:
    需要 CNN 项目的 checkpoint 存在 (models/crack_resnet18_best.pt)。
    如果不在，自动回退到 mock 数据演示。

退出码:
    0 = 演示完成（无论真实推理还是 mock）
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evidence.bridge import store_inference
from evidence.store import EvidenceStore
from evidence.verify import verify_chain

CNN_PROJECT = Path(__file__).parent.parent.parent / "项目作品" / "CNN裂缝检测项目"


def try_real_inference(image_path: Path) -> dict | None:
    """Try calling CNN project's infer.predict(). Returns None on failure."""
    if not CNN_PROJECT.exists():
        return None
    ckpt = CNN_PROJECT / "models" / "crack_resnet18_best.pt"
    if not ckpt.exists():
        return None
    try:
        sys.path.insert(0, str(CNN_PROJECT))
        from src.infer import predict
        return predict(image_path, model_name="resnet18")
    except Exception as e:
        print(f"WARNING: CNN inference failed: {e}")
        return None


def mock_inference(label: str, confidence: float) -> dict:
    """Mock inference result for when CNN checkpoint is unavailable."""
    return {
        "label": label,
        "confidence": confidence,
        "probs": {
            "NoCrack": 1 - confidence if label == "Crack" else confidence,
            "Crack": confidence if label == "Crack" else 1 - confidence,
        },
        "model": "resnet18",
        "img_size": 160,
        "checkpoint_accuracy": 0.8792,
    }


def main():
    db_path = Path(__file__).parent.parent / "data" / "cnn_evidence.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    store = EvidenceStore(db_path)

    print()
    print("=" * 70)
    print("  CNN Integration Demo - Real AI Inference + Trusted Storage")
    print("  Bridges jinliangyue/concrete-crack-detection -> evidence chain")
    print("=" * 70)
    print()

    image_arg = sys.argv[1] if len(sys.argv) > 1 else None
    real_inference = None
    if image_arg:
        real_inference = try_real_inference(Path(image_arg))

    samples = []
    if real_inference:
        samples.append(("REAL", real_inference))
        for _ in range(4):
            samples.append(("MOCK", mock_inference(
                "Crack" if _ % 2 == 0 else "NoCrack",
                0.85 + _ * 0.03,
            )))
    else:
        samples.extend([
            ("MOCK", mock_inference("Crack", 0.95)),
            ("MOCK", mock_inference("NoCrack", 0.92)),
            ("MOCK", mock_inference("Crack", 0.87)),
            ("MOCK", mock_inference("NoCrack", 0.98)),
            ("MOCK", mock_inference("Crack", 0.91)),
        ])

    print(f"[1/3] Storing {len(samples)} inference results ...")
    for tag, result in samples:
        seq = store_inference(store, result, sensor_id="AI-CAM-FIELD-01")
        fetched = store.get_by_sequence(seq)
        assert fetched is not None
        print(
            f"      [{tag}] sequence={seq}  {result['label']:<8}  "
            f"confidence={result['confidence']:.4f}  "
            f"hash={fetched.record_hash[:16]}..."
        )

    print()
    print("[2/3] Verifying the chain ...")
    result = verify_chain(store)
    print(f"      total={result.total}  valid={result.valid}  invalid={result.invalid}")
    print(f"      -> {'PASS' if result.is_valid else 'FAIL'}")

    print()
    print("[3/3] Proving the bridge maps to CD v1.1 §6.5.1 ...")
    record = store.get_by_sequence(0)
    assert record is not None
    print(f"      (a) Data Integrity        - record_hash + prev_hash chain")
    print(f"      (b) Provenance            - sensor_id={record.sensor_id}, "
          f"model_id={record.model_id}, model_version={record.model_version}")
    print(f"      (c) Authenticity          - device_id={record.device_id}")
    print(f"      (d) Timestamp Verify      - acq={record.acquisition_timestamp}")
    print(f"      (e) Auditability          - operator={record.operator}, "
          f"op={record.operation_type}")
    print(f"      (g) Lifecycle Trace       - phase={record.phase}")

    print()
    if not real_inference:
        print("TIP: pass an image path to trigger real CNN inference:")
        print(f"     python {Path(__file__).name} path/to/concrete_image.jpg")
        print(f"     Requires checkpoint: {CNN_PROJECT}/models/crack_resnet18_best.pt")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
