# Amplification-2 confirmation report: gateway timed install drop plus downstream-relay co-intervention

English public version. The Chinese working report is also kept in this folder
as `AMPLIFICATION2_CONFIRM_REPORT_20261104.zh.md`. Numbers are those of the
frozen JSON `AMPLIFICATION2_CONFIRM_RESULTS_20261104.json`.

- Generated: 2026-11-04 (America/Los_Angeles)
- Pre-registration: `AMPLIFICATION2_PREREG_20261104.md` (including Appendix A disclosure addendum; **E1 remains IU-only**)
- Registration: `amplification2_confirm_registration.json`
  - **Frozen before scoring:** yes
  - mtime (America/Los_Angeles): 2026-11-04 06:13:57 PST
  - SHA256: `1f37be33c2ebd65766da85defb33bbacf5acb21c6544c1c52645f50a184f6a24`
  - n_configs: **384**
- Analysis: `analyze_amplification2_confirm.py` (frozen with the registration; S1–S3 criteria unchanged)
- Machine-readable results: `AMPLIFICATION2_CONFIRM_RESULTS_20261104.json`
- Per-cell summary: in the raw run tree (`raw_on_request/control_budget_study_20261015/results/amplification2_confirm_summary.json`), available on request

## Verdict in one sentence

**A-tier evidence thresholds: met.** S1 = true, S2 = true, S3 = true.

A-tier holds only under this **controlled induction**, never as a natural-prevalence estimate. PostExit is an ablation, not a recommended protocol.

## Co-intervention disclosure (methods)

Primary recipe `M1_drop_both_0_200_dn36` applies a **gateway install drop** (`dropInstallStartSec=0, End=200, Mask=3`) **jointly** with faults `[[145,3],[225,6]]`. The S1/S2/S3 results below are estimated under that joint condition and must **not** be interpreted as the marginal effect of “dropping installs alone.” The drop remains the direct mechanism of confirmation loss; the downstream 3/6 removals are the preregistered service-impairment background. Induction is a controlled gateway manipulation; extrapolation to natural wireless loss must remain cautious.

## Side-by-side with Attempt 1 (multiplicity)

| Attempt | Pre-registration | Induction | Joint E1 | S1 | S2 | S3 |
|---|---|---|---|---|---|---|
| 1 | AMPLIFICATION_PREREG_20261103 | S1_overload_R0 + d(4,0) stratification | **0/96** | no | no | no |
| 2 (this report) | AMPLIFICATION2_PREREG_20261104 | M1_drop_both_0_200_dn36 (drop + downstream 3/6) | **26/48** | yes | yes | yes |

## Run integrity

| Item | Result |
|---|---|
| Closed-loop runs | **384/384** completed, failures **0** (`amplification2_confirm_failures.json` empty) |
| Cells | 48 (8 layouts × 6 inputs) |
| Native audit | all passed |
| sham_release bit-identical to Joint | 48/48 yes |
| Runtime LLM | 0 |

## The three criteria (IU-only E1, frozen)

| Criterion | Pre-registered requirement | Result | Truth value |
|---|---|---|---|
| S1 | Joint E1 ≥ 3 cells and ≥ 2 layouts | **26/48**; 8 layouts (every layout has at least one lockout cell) | **yes** |
| S2 | post_exit opened in ≥ 2 lockout cells | **26** / 26 lockout cells | **yes** |
| S3 | on every S2-successful cell, at least one competitor (`wait_extend` / `thresh_relax_scoped`) does not open; sham bit-identical to Joint on all cells | wait_extend opened: **0**; thresh_relax_scoped: **0** (both 0 on every S2 cell); sham identical: yes | **yes** |

### Lockout-cell list (Joint E1)

The per-cell table (topology, seed, first_exit_s, blocked_unconfirmed) is identical to that in the Chinese original and in `AMPLIFICATION2_CONFIRM_RESULTS_20261104.json`. All 26 cells have first_exit_s = 20.0; blocked_unconfirmed counts range from 44 to 48. The 26 S2 post_exit-opened cells are exactly this list.

## Exploratory: MFS-dilution diagnosis (**does not** change E1 / S1)

E1 still requires that every evaluated admission after the exit has settled reason **exactly** `installation_unconfirmed`. The table only describes how many Joint cells lost strict E1 because `missing_fresh_source` was mixed in (the gate still closed, no later install).

| Diagnostic item | Count |
|---|---|
| Joint cells | 48 |
| Had an unconfirmed exit | 48 |
| Strict E1 (IU-only) | 26 |
| Cells with MFS after the exit | 22 |
| Gate stayed closed and reasons were only IU∨MFS, but strict E1 was lost because of MFS | 22 |
| Exploratory “IU∨MFS and no authorised install” soft-closed cells (not a criterion) | 48 |

Per-cell IU/MFS counts are in the JSON field `exploratory_MFS.per_cell`.

## Relative to A-tier

By the pre-registration, A ⇔ S1 ∧ S2 ∧ S3 = **met**. The claim must still obey S4 (a conditional boundary; controlled drop; reported beside Attempt-1 0/96; co-intervention disclosed). Exploratory: fs_relax_scoped/global also opened on some S2 cells (consistency of the second conjunct) and are not counted as S3 competitor failures.

## What was not done

- E1 / S1–S3 / the recipe / the cell list / mask / window / faults were not changed; no cells were added in light of results.
