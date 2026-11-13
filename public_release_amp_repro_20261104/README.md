# Amplification and ablation package

Lightweight public-release bundle for the confirmation-premise ablation and the
two preregistered induction attempts (Amplification-1 and Amplification-2)
reported in

*"Multi-Level Verification and Validation of a Packet-Level Wireless Sensor Network Simulation: Preregistered Docking and Trace-Driven Replay of Confirmation-Contract Lockout"*

Canonical repository: https://github.com/ya-yu-zhang/wsn-recovery-lockout-nr

Correspondence: jspan@ieee.org

This package lives in this dated subdirectory of the public repository.

## What this is (and is not)

| Is | Is not |
|----|--------|
| A **preregistered diagnostic protocol** for a conditional recovery boundary under sparse confirmation feedback | A claim of a better routing protocol |
| Multiplicity table: Attempt-1 **0/96** ∥ Attempt-2 **26/48** (controlled induction) | Evidence that lockout is common in natural sparse-feedback deployments |
| PostExit = **T-only ablation arm** (diagnostic) | A recommended deployment policy |

A-tier evidence holds only under controlled induction, never as natural prevalence.

## Zero-friction reproduction (no ns-3, no pip extras)

Requires only **Python 3** (stdlib). From this package root:

```bash
python3 scripts/print_paper_endpoints.py
python3 scripts/verify_registration_sha.py
```

Expected console endpoints (must match the manuscript):

- Attempt-1 Joint E1 = **0/96**
- Attempt-2 Joint E1 = **26/48**, layouts **8/8**
- S2 post_exit opened = **26/26**
- S3: `wait_extend` opened = **0**, `thresh_relax_scoped` opened = **0**, sham **48/48** identical to Joint
- `A_tier = true` (controlled induction + co-intervention)
- Registration SHA256 = `1f37be33c2ebd65766da85defb33bbacf5acb21c6544c1c52645f50a184f6a24`
- Exploratory MFS dilution = **22/48** (IU-only E1 unchanged)

There is **no** `requirements.txt` for this path.

## Theory–code digital twin

See [`THEORY_CODE_MAP.md`](THEORY_CODE_MAP.md) (20 mapped rows): Prop. 1 / T / IU / F_s / PostExit / Amp-2 M1 `dropInstall*` / S1–S3 / A_tier ↔ named Python and ns-3 symbols under `theory_code_refs/`.

## Package layout

```
amplification1_20261103/     # Attempt-1 prereg + confirm report/JSON (0/96)
amplification2_20261104/     # Attempt-2 prereg (locked Chinese + unofficial EN), registration, confirm report/JSON (26/48)
ablation_study_20261103/     # Contract ablation (English public report) + mixin code + case summaries
theory_code_refs/            # Frozen analysis/controller/ns-3 sources for the twin map
scripts/                     # Zero-friction printers
THEORY_CODE_MAP.md
README.md
```

Chinese working reports that are **not** hash-locked are provided as English
public versions in this package. The hash-locked Amplification-2 preregistration
is kept byte-identical; an unofficial English translation sits beside it
(`AMPLIFICATION2_PREREG_20261104.EN_unofficial_translation.md`); the Chinese
original is authoritative. Absolute paths inside that locked file are from the
authors' machine.

## Claim bounds (read before citing)

1. Attempt-2 success uses **gateway timed install drop** (`dropInstall*` mask=3, `[0,200)`) plus pre-registered **downstream relay faults** `[[145,3],[225,6]]`. S1–S3 are estimated under that **joint** condition — not a pure-drop marginal effect, and not natural packet loss.
2. Attempt-1 **0/96** under geometric / natural-pressure recipes remains valid and must be reported beside Attempt-2.
3. E1 is **IU-only**; MFS dilution is exploratory and did not redefine the endpoint.
4. PostExit is an ablation, not a recommended protocol.

## Full simulation re-run (optional, not required for review)

Replaying 384 Amplification-2 confirm cells needs the ns-3 native engine and the
raw run tree, which are not in this lightweight bundle. SHA256 of the frozen
native binary / source used for Attempt-2 are recorded in
`AMPLIFICATION2_CONFIRM_RESULTS_20261104.json` (`native_sha256`,
`native_source_sha256`). Contact the corresponding author for the full runner
tree (on the order of 2.8 GB for Attempt-2; 9.6 GB for Attempt-1).

## License / citation

See the repository root `README.md`, `LICENSE`, `LICENSE-DATA`, and `CITATION.cff`.
