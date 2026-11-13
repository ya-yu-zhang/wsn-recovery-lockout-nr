# Multi-level V&V package (Phase 2 / 2b)

Curated package supporting the docking, FlockLab trace-replay, and factorial
layers reported in

*"Multi-Level Verification and Validation of a Packet-Level Wireless Sensor Network Simulation: Preregistered Docking and Trace-Driven Replay of Confirmation-Contract Lockout"*

Correspondence: jspan@ieee.org

## Public registrations (route b)

This folder does **not** contain the unredacted Phase-2 / Phase-2b registration
files. Use:

- `REGISTRATION_PHASE2_20261111_REDACTED.json`
- `PREREG_PHASE2_20261111_REDACTED.md`
- `ADDENDUM_PHASE2_20261111b_REDACTED.md`
- `PREREG_PHASE2B_20261111_REDACTED.md`
- `REGISTRATION_PHASE2B_20261111_REDACTED.json`
- `CHANGELOG_REDACTED.md`
- `REDACTION_LOG.md`

The SHA256 values printed in the manuscript are those of the unredacted
originals (see the log). Those originals are available to the editor and
reviewers on request. A modified file is never presented under the original
hash.

Other hash-locked scripts, `doe/design.json`, the trace-driver source and the
pinned binary `flocklab/wsn-closed-loop-trace` (SHA256 `ddc624a2…c00a`) are
deposited byte-identical. Absolute paths inside locked files are from the
authors' machine.

## What is not in this folder

- A vendored copy of SimPy. Use **SimPy 4.1.1**. (Some locked registration
  texts still say “vendored”; that copy is not deposited.)
- Raw DOE and FlockLab run directories (`raw_on_request/scratch_phase2/doe`,
  about 3.56 GB; `raw_on_request/scratch_phase2/flocklab_full`, about 1.25 GB).
  Unlocked result JSON `dir` fields have been rewritten to that prefix.
  Identified raw trees are available from the corresponding author on request.

## Numbers cross-check

```
python3 checks/check_phase23_numbers.py
```

Figure redraws for the manuscript version live in `../figures_v2/`.
