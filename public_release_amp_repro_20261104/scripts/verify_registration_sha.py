#!/usr/bin/env python3
"""Recompute SHA256 of amplification2_confirm_registration.json and compare
to the frozen value reported in AMPLIFICATION2_CONFIRM_RESULTS / RECEIPT.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "amplification2_20261104" / "amplification2_confirm_registration.json"
RESULTS = ROOT / "amplification2_20261104" / "AMPLIFICATION2_CONFIRM_RESULTS_20261104.json"
RECEIPT = (
    ROOT
    / "amplification2_20261104"
    / "AMPLIFICATION2_CONFIRM_REGISTRATION_RECEIPT_20261104.json"
)
EXPECTED = "1f37be33c2ebd65766da85defb33bbacf5acb21c6544c1c52645f50a184f6a24"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if not REG.is_file():
        print("ERROR: missing", REG, file=sys.stderr)
        sys.exit(1)
    got = sha256_file(REG)
    reported = json.loads(RESULTS.read_text())["registration_sha256"]
    receipt = json.loads(RECEIPT.read_text())["registration_sha256"]
    print("file     :", got)
    print("results  :", reported)
    print("receipt  :", receipt)
    print("expected :", EXPECTED)
    ok = got == reported == receipt == EXPECTED
    print("MATCH" if ok else "MISMATCH")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
