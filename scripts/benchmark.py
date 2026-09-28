"""Performance benchmark for trusted_evidence MVP.

Measures append + verify throughput at various chain lengths and signature modes.
Provides baseline numbers for CD v1.1 §6.5.3 (Implementation-specific performance reporting).

用法:
    python3 scripts/benchmark.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evidence.schemas import EvidenceRecord
from evidence.signatures import generate_key, sign_record
from evidence.store import EvidenceStore
from evidence.verify import verify_chain


def benchmark(N: int, with_signatures: bool = False) -> dict:
    """Append N records, measure time, verify, measure time. Return metrics."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    store = EvidenceStore(db_path)

    secret = None
    if with_signatures:
        secret = generate_key()

    # --- Append phase ---
    start = time.perf_counter()
    for i in range(N):
        record = EvidenceRecord(
            sensor_id=f"SENSOR-{i:06d}",
            device_id="BENCH-NODE-01",
            model_id="resnet18",
            model_version="v8.3",
            acquisition_timestamp=f"2026-10-15T08:30:{i % 60:02d}.000Z",
            payload={
                "i": i,
                "label": "Crack" if i % 2 == 0 else "NoCrack",
                "confidence": 0.9 + (i % 10) * 0.01,
            },
        )
        if with_signatures:
            sign_record(record, secret)
        store.append(record)
    append_elapsed = time.perf_counter() - start

    # --- Verify phase ---
    start = time.perf_counter()
    result = verify_chain(store, signature_secret=secret)
    verify_elapsed = time.perf_counter() - start

    # Cleanup
    db_path.unlink(missing_ok=True)

    return {
        "N": N,
        "with_signatures": with_signatures,
        "append_total_s": append_elapsed,
        "append_avg_ms": append_elapsed / N * 1000,
        "append_throughput_rps": N / append_elapsed,
        "verify_total_s": verify_elapsed,
        "verify_avg_ms": verify_elapsed / N * 1000,
        "verify_throughput_rps": N / verify_elapsed,
        "valid": result.valid,
        "invalid": result.invalid,
        "signature_checked": result.signature_checked,
        "is_valid": result.is_valid,
    }


def format_row(r: dict) -> str:
    sig_tag = "with-HMAC" if r["with_signatures"] else "no-sig   "
    return (
        f"  N={r['N']:>5}  {sig_tag}  "
        f"append: {r['append_total_s']:>6.3f}s ({r['append_avg_ms']:>6.2f}ms/r, "
        f"{r['append_throughput_rps']:>7.1f}/s)  "
        f"verify: {r['verify_total_s']:>6.3f}s ({r['verify_avg_ms']:>6.2f}ms/r, "
        f"{r['verify_throughput_rps']:>7.1f}/s)  "
        f"valid={r['valid']}/{r['N']}"
    )


def main():
    print()
    print("=" * 100)
    print("  Trusted Evidence MVP - Performance Benchmark")
    print("  Maps to CD v1.1 §6.5.3 (Implementation-specific performance reporting)")
    print("=" * 100)
    print()
    print("  Hardware: this machine (single-threaded SQLite + WAL)")
    print("  Workload: synthetic AI inference records")
    print()

    sizes = [100, 500, 1000]
    results = []
    for N in sizes:
        for sig in [False, True]:
            r = benchmark(N, with_signatures=sig)
            results.append(r)
            print(format_row(r))

    print()
    print("  Observations:")
    no_sig_1000 = next(r for r in results if r["N"] == 1000 and not r["with_signatures"])
    sig_1000 = next(r for r in results if r["N"] == 1000 and r["with_signatures"])
    overhead_pct = (sig_1000["append_avg_ms"] - no_sig_1000["append_avg_ms"]) / no_sig_1000["append_avg_ms"] * 100
    print(f"    - Signing overhead (HMAC-SHA256): +{overhead_pct:.1f}% per record")
    print(f"    - At 1000 records, verify throughput: {sig_1000['verify_throughput_rps']:.0f}/s")
    print(f"    - At 1000 records, append throughput (with sig): {sig_1000['append_throughput_rps']:.0f}/s")
    print()
    print("  CD v1.1 §6.5.3 requires:")
    print("    - data throughput (peak and average) under specified business load")
    print("    - trusted submission timeliness")
    print("    - multi-party participation model")
    print("    - error rate and recovery time")
    print()
    print("  This benchmark provides the v0.2 baseline. For project-level")
    print("  targets, refer to CD v1.1 §6.5.3 Type C acceptance (project-specific).")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
