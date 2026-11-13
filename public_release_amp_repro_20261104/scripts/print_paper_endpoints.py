#!/usr/bin/env python3
"""Zero-friction paper-endpoint printer (stdlib only; no ns-3 re-run).

Reads frozen Amplification-1 / Amplification-2 confirm JSON and prints the
same primary numbers the manuscript reports (Attempt-1 0/96 ∥ Attempt-2
26/48, S1–S3, A_tier, registration SHA, co-intervention, IU-only, MFS).

Usage (from package root):
  python3 scripts/print_paper_endpoints.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AMP1 = ROOT / "amplification1_20261103" / "AMPLIFICATION_CONFIRM_RESULTS_20261104.json"
AMP2 = ROOT / "amplification2_20261104" / "AMPLIFICATION2_CONFIRM_RESULTS_20261104.json"
REG = ROOT / "amplification2_20261104" / "amplification2_confirm_registration.json"
EXPECTED_REG_SHA = (
    "1f37be33c2ebd65766da85defb33bbacf5acb21c6544c1c52645f50a184f6a24"
)


def fail(msg: str) -> None:
    print("ERROR:", msg, file=sys.stderr)
    sys.exit(1)


def load(path: Path) -> dict:
    if not path.is_file():
        fail(f"missing frozen artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    a1 = load(AMP1)
    a2 = load(AMP2)

    # --- Attempt 1 ---
    a1_lock, a1_n = a1["incidence"]["overall"]
    a1_e1 = f"{a1_lock}/{a1_n}"
    if a1_e1 != "0/96":
        fail(f"Attempt-1 Joint E1 expected 0/96, got {a1_e1}")
    if a1.get("prior_attempt1_joint_E1") not in (None, "0/96") and a1_e1 != a1.get(
        "prior_attempt1_joint_E1"
    ):
        pass  # amp1 file has no prior field; ignore

    # --- Attempt 2 ---
    joint_cells = a2["joint_cells"]
    e1_n = a2["joint_E1_lockout"]
    a2_e1 = f"{e1_n}/{joint_cells}"
    if a2_e1 != "26/48":
        fail(f"Attempt-2 Joint E1 expected 26/48, got {a2_e1}")
    if a2.get("prior_attempt1_joint_E1") != "0/96":
        fail("Attempt-2 JSON prior_attempt1_joint_E1 must be 0/96")

    s1 = a2["thresholds"]["S1"]
    s2 = a2["thresholds"]["S2"]
    s3 = a2["thresholds"]["S3"]
    layouts = s1["layouts"]
    pe = s2["post_exit_opened"]
    arms = s3["replicating_cells_by_arm"]
    a_tier = bool(a2["thresholds"]["A_tier"]) and bool(a2.get("A_tier"))

    if len(layouts) != 8:
        fail(f"S1 layouts expected 8, got {len(layouts)}")
    if len(pe) != 26:
        fail(f"S2 post_exit opened expected 26, got {len(pe)}")
    for name in ("wait_extend", "thresh_relax_scoped"):
        if len(arms.get(name, ["?"])) != 0:
            fail(f"S3 {name} opened expected 0, got {len(arms[name])}")
    if not a2.get("sham_identical_to_joint_all_cells"):
        fail("sham_identical_to_joint_all_cells must be true")
    if not a_tier:
        fail("A_tier must be true")

    reg_sha_json = a2["registration_sha256"]
    if reg_sha_json != EXPECTED_REG_SHA:
        fail(f"registration_sha256 in JSON mismatch: {reg_sha_json}")
    if not REG.is_file():
        fail(f"missing registration file: {REG}")
    reg_sha_file = sha256_file(REG)
    if reg_sha_file != EXPECTED_REG_SHA:
        fail(
            f"registration file SHA mismatch:\n"
            f"  expected {EXPECTED_REG_SHA}\n"
            f"  got      {reg_sha_file}"
        )

    mfs = a2.get("exploratory_MFS") or {}
    mfs_dilution = mfs.get(
        "joint_cells_lost_E1_solely_from_MFS_mix_while_gate_stayed_closed"
    )
    if mfs_dilution != 22:
        fail(f"exploratory MFS dilution expected 22, got {mfs_dilution}")

    # --- Console verdict (paper-aligned) ---
    print("=" * 72)
    print("WSN confirmation-contract endpoints (frozen JSON; no ns-3 re-run)")
    print("=" * 72)
    print()
    print("Paper title:")
    print(
        "  Multi-Level Verification and Validation of a Packet-Level"
    )
    print(
        "  Wireless Sensor Network Simulation: Preregistered Docking and"
    )
    print(
        "  Trace-Driven Replay of Confirmation-Contract Lockout"
    )
    print()
    print("--- Multiplicity table (must report both attempts) ---")
    print(f"  Attempt-1 Joint E1 (IU-only lockout to stop):  {a1_e1}")
    print(
        f"  Attempt-1 verdict: S1={a1['verdict']['S1']} S2={a1['verdict']['S2']} "
        f"S3={a1['verdict']['S3']} A_tier={a1['verdict']['A_tier']}"
    )
    print(f"  Attempt-2 Joint E1 (IU-only lockout to stop):  {a2_e1}")
    print(f"  Attempt-2 S1 layouts with ≥1 lockout cell:     {len(layouts)}/8")
    print(f"  Attempt-2 S2 post_exit opened (aligned exit):  {len(pe)}/26")
    print(
        "  Attempt-2 S3 wait_extend opened on S2 cells:   "
        f"{len(arms['wait_extend'])}"
    )
    print(
        "  Attempt-2 S3 thresh_relax_scoped opened:       "
        f"{len(arms['thresh_relax_scoped'])}"
    )
    print(
        "  Attempt-2 sham identical to Joint (all cells): "
        f"{a2['sham_identical_to_joint_all_cells']}  (48/48)"
    )
    print(f"  Attempt-2 A_tier:                              {a_tier}")
    print()
    print("--- Registration integrity ---")
    print(f"  amplification2_confirm_registration.json SHA256:")
    print(f"    {reg_sha_file}")
    print(
        f"  frozen_before_scoring: {a2.get('registration_frozen_before_scoring')}"
    )
    print(
        f"  registration mtime (America/Los_Angeles): "
        f"{a2.get('registration_mtime_America_Los_Angeles')}"
    )
    print()
    print("--- Claim bounds (not natural prevalence) ---")
    print(f"  E1 definition: IU-only (reason == installation_unconfirmed)")
    print(f"  Co-intervention: {a2.get('co_intervention')}")
    print(
        f"  Exploratory MFS dilution (gate closed, lost strict E1): "
        f"{mfs_dilution}/48"
    )
    print(
        "  Note: gateway timedrop = controlled induction; first attempt "
        "0/96 remains the natural-pressure negative."
    )
    print()
    print("--- Compact verdicts (reviewer one-glance) ---")
    print(f"  Attempt1_Joint_E1 = {a1_e1}")
    print(f"  Attempt2_Joint_E1 = {a2_e1}")
    print(f"  Attempt2_S1_layouts = {len(layouts)}/8")
    print(f"  Attempt2_S2_post_exit_opened = {len(pe)}/26")
    print("  Attempt2_S3_wait_extend_opened = 0")
    print("  Attempt2_S3_thresh_relax_scoped_opened = 0")
    print("  Attempt2_sham = 48/48 identical to Joint")
    print(f"  A_tier = {str(a_tier).lower()}")
    print(f"  registration_sha256 = {reg_sha_file}")
    print("=" * 72)
    print("OK: frozen endpoints match the manuscript numbers.")


if __name__ == "__main__":
    main()
