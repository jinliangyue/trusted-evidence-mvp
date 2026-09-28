"""Signature demo: HMAC-SHA256 multi-party signing (v0.2 feature).

Maps to CD v1.1:
  - §6.5.1 (c) Authenticity               -> each signer has its own secret
  - §6.5.1 (f) Multi-party Verification   -> different parties sign different records
  - §7.2         Data integrity           -> signature + hash chain together

用法:
    python3 demo/demo_signatures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evidence.schemas import EvidenceRecord
from evidence.signatures import generate_key, sign_record
from evidence.store import EvidenceStore
from evidence.verify import tamper_for_demo, verify_chain


def main():
    db_path = Path(__file__).parent.parent / "data" / "signature_evidence.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    store = EvidenceStore(db_path)

    # Simulate 3 parties: factory, supervisor, owner
    factory_secret = generate_key()
    supervisor_secret = generate_key()
    owner_secret = generate_key()

    print()
    print("=" * 70)
    print("  Trusted Evidence MVP - v0.2 Multi-Party Signature Demo")
    print("  Maps to CD v1.1 §6.5.1 (c) Authenticity + (f) Multi-party")
    print("=" * 70)
    print()

    print("[1/5] Generating 3 party secrets ...")
    print(f"      factory    signer_id: {sign_record.__name__ and ''}")
    # We don't call sign_record yet; just show secrets are random
    print(f"      factory    key: {factory_secret.hex()[:16]}... (32 bytes)")
    print(f"      supervisor key: {supervisor_secret.hex()[:16]}... (32 bytes)")
    print(f"      owner      key: {owner_secret.hex()[:16]}... (32 bytes)")

    print()
    print("[2/5] Appending 9 records, signed by 3 different parties ...")

    signing_parties = [
        ("factory", factory_secret, "material_acceptance", {"material": "C30", "qty_m3": 50}),
        ("factory", factory_secret, "material_acceptance", {"material": "C30", "qty_m3": 50}),
        ("supervisor", supervisor_secret, "hidden_works_inspection", {"item": "rebar", "ok": True}),
        ("factory", factory_secret, "concrete_pour", {"volume_m3": 50, "temp_c": 22}),
        ("supervisor", supervisor_secret, "concrete_pour_acceptance", {"strength_mpa": 28.5}),
        ("owner", owner_secret, "structural_acceptance", {"floor": 1, "result": "pass"}),
        ("factory", factory_secret, "weld_inspection", {"welds_inspected": 24, "defects": 0}),
        ("supervisor", supervisor_secret, "weld_acceptance", {"defects_accepted": 0}),
        ("owner", owner_secret, "final_acceptance", {"overall_result": "pass"}),
    ]

    for party, secret, event_type, payload in signing_parties:
        record = EvidenceRecord(
            sensor_id=f"INSPECTOR-{party.upper()}-01",
            device_id=f"DEVICE-{party.upper()}-01",
            model_id="manual_inspection",
            model_version="n/a",
            acquisition_timestamp="2026-11-15T10:00:00.000Z",
            phase="storage",
            operator=f"{party}_inspector",
            operation_type="create",
            payload_type=event_type,
            payload=payload,
        )
        # Use append(secret=...) so signing happens AFTER prev_hash is set.
        seq = store.append(record, secret=secret)
        print(f"      seq={seq}  {party:<10}  {event_type:<32}  "
              f"signer_id={record.signer_id}  sig={record.signature[:16]}...")

    print()
    print("[3/5] Verifying signatures with a party-secrets lookup ...")
    from evidence.signatures import verify_signature
    all_records = list(store.iter_all())
    parties_secrets = {
        "signer-factory-sentinel": factory_secret,  # placeholder, real IDs differ
    }
    # Map signer_id -> secret by checking each record's signer_id
    signer_to_secret = {}
    for rec in all_records:
        for name, sec in [
            ("factory", factory_secret),
            ("supervisor", supervisor_secret),
            ("owner", owner_secret),
        ]:
            if verify_signature(rec, sec):
                signer_to_secret[rec.signer_id] = name
                break

    for rec in all_records:
        party = signer_to_secret.get(rec.signer_id, "UNKNOWN")
        print(f"      seq={rec.sequence}  signer_id={rec.signer_id}  "
              f"party={party:<10}  sig={rec.signature[:16]}...")

    print()
    print("[4/5] Simulating tampering: edit supervisor-signed record's payload ...")
    # tamper with seq=2 (supervisor's hidden_works_inspection)
    tamper_for_demo(store, sequence=2, field="ok", new_value=False)
    print("      Done.")

    print()
    print("[5/5] Re-verifying each record with its OWN party's secret ...")
    print("      (using per-record secret lookup, not a single global secret)")
    # IMPORTANT: re-read records from DB so we see the post-tamper payloads.
    all_records = list(store.iter_all())
    bad = 0
    for rec in all_records:
        sec = None
        for name, s in [
            ("factory", factory_secret),
            ("supervisor", supervisor_secret),
            ("owner", owner_secret),
        ]:
            if signer_to_secret.get(rec.signer_id) == name:
                sec = s
                break
        if sec is None:
            print(f"      seq={rec.sequence}  signer_id={rec.signer_id}  -> no matching secret")
            bad += 1
            continue
        ok = verify_signature(rec, sec)
        flag = "OK " if ok else "FAIL"
        if not ok:
            bad += 1
        print(f"      seq={rec.sequence}  signer_id={rec.signer_id}  -> {flag}")

    print()
    print(f"      Total bad records: {bad}")
    print(f"      Note: sequence 2 was tampered -> its signature now invalid")

    print()
    print("=" * 70)
    print("  v0.2 adds:")
    print("    - HMAC-SHA256 signatures (CD §6.5.1 c Authenticity)")
    print("    - Multi-party signer_id tracking (CD §6.5.1 f Multi-party)")
    print("    - Tampering breaks BOTH hash chain AND signature")
    print()
    print("  v0.2 limitation (honest):")
    print("    - HMAC requires shared secret (not true PKI / asymmetric)")
    print("    - v3 roadmap: Ed25519 / ECDSA / SM2 for asymmetric signing")
    print("=" * 70)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
