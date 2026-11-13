# Amplification-1 confirmation report: induced condition C plus competitor / sham ablation

English public version of the confirmation report. The original Chinese working
note contained internal process commentary and is not deposited. All numbers
below are taken from the frozen machine-readable file
`AMPLIFICATION_CONFIRM_RESULTS_20261104.json`.

- Generated: early 2026-11-04 (America/Los_Angeles)
- Pre-registration: `AMPLIFICATION_PREREG_20261103.md` (registered 2026-11-03 23:30 PST, before confirmation runs)
- Registration: `results/amplification_confirm_registration.json` (n_configs=768)
- Analysis: `analyze_amplification_confirm.py` (frozen, **unmodified**; SHA256 of the 11 frozen sources rechecked after the run, all consistent)
- Machine-readable results: `AMPLIFICATION_CONFIRM_RESULTS_20261104.json`. The full per-cell table lives in the raw run tree (`raw_on_request/control_budget_study_20261015/results/amplification_confirm_summary.json`), available on request.

## Verdict in one sentence

**A-tier evidence thresholds: not met.** S1 = false, S2 = false, S3 = false.

Under pre-registered stopping rule 5: S1 not met → report “not met,” add no cells or inputs inside this registration; any later amplification requires a new registration file, labelled as a second attempt (multiplicity must be disclosed).

## Run integrity

| Item | Result |
|---|---|
| Closed-loop runs | 768/768 completed, 0 failures (`amplification_confirm_failures.json` empty; no `FAILED_ATTEMPT.txt`) |
| Cells | 96 (weak last-hop stratum 12 layouts × 6 inputs = 72; contrast 4 × 6 = 24) |
| Native audit | all passed |
| sham_release bit-identical to Joint | 96/96 yes (sanity check passed; campaign valid) |
| Process | not killed; analysis began only after natural completion |

## The three criteria

| Criterion | Pre-registered requirement | Result | Truth value |
|---|---|---|---|
| S1 | Joint E1 lockout to the deadline ≥ 3 cells, covering ≥ 2 layouts | **0/96** (Wilson 95% CI 0–3.85%); weak last-hop stratum 0/72, contrast 0/24 | **no** |
| S2 | post_exit opened in ≥ 2 lockout cells | no lockout cells, 0 | **no** |
| S3 | on every S2-successful cell, at least one competitor (`wait_extend` / `thresh_relax_scoped`) does not open, and sham 96/96 bit-identical to Joint | antecedent empty → frozen code judges false; the sham sub-condition itself is true | **no** |

Lockout-cell list: **empty**. H2 (incidence in the weak last-hop stratum > contrast): 0/72 vs 0/24, one-sided Fisher *p* = 1.0, not supported.

## Descriptive / exploratory results (do not affect the decision)

- **Unconfirmed exits were common, but none formed a strict lockout.** In 81/96 cells Joint had at least one unconfirmed exit; in 35/96 there was ≥ 1 `installation_unconfirmed` rejection; but after the last unconfirmed exit the gate was reopened before the deadline (eligible *F_s*, a later confirmation, or re-authorisation), so E1 never held.
- **Closest cell to lockout:** `budget_10_2026110310 / 2026110504` (weak last-hop stratum). Joint had 31 `installation_unconfirmed` rejections and worst-source service 24.21%, but still had authorisations and 4 installs, so E1 is not met. On that cell: post_exit +15.36 pp, fs_relax_scoped/global +15.36 pp, **wait_extend +27.19 pp** (and that arm had no unconfirmed exit at all), thresh_relax_scoped 0. Thus “wait longer,” a competing explanation, had a larger effect than relaxing *T* — contrary to the pre-registered mechanism prediction (wait_extend should not act), and unfavourable to a “*T*-specific” narrative.
- Next closest: `budget_10_2026110320 / 2026110504` (contrast) 14 rejections, post_exit +7.98 pp, wait_extend +5.80 pp, thresh_relax_global +8.36 pp, fs_relax_global +12.27 pp.
- **“opened” counts of each arm on all 96 cells** (on non-lockout cells, opened only means “authorisation + install after an exit and service ≥ +1 pp,” not “an already locked gate was opened”): post_exit 10, wait_extend 12, fs_relax_scoped 2, fs_relax_global 27, thresh_relax_global 17, thresh_relax_scoped 0, sham 0. In 7 of post_exit's 10 opened cells, Joint had no `installation_unconfirmed` rejection at all, so those cells cannot be read as a mechanism reproduction.
- **Side effects on non-lockout cells (all 96 cells are non-lockout):** post_exit changed 21 cells (up 12 / down 9, mean +0.41 pp, control +0.18%); wait_extend changed 59 (27/32, +0.14 pp, −0.44%); fs_relax_global 69 (39/30, +0.63 pp); thresh_relax_global 35 (23/12, +0.63 pp); fs_relax_scoped 7 (2/5, −0.05 pp); thresh_relax_scoped and sham 0 cells.
- **Development versus confirmation gap.** The same S1_overload_R0 recipe produced lockouts on development layouts (pilot2 3/48, pilot3 1/48) and **0/96** on 16 new layouts. Recipe selection overfit the development set; the geometric hypothesis “weak last control hop d(4,0) ≥ 54 m” (H2) was not supported.

## What remains relative to A-tier

1. **Fundamentally, condition C was not elicited on independent new layouts.** A-tier requires ≥ 3 independent lockout cells; this campaign has 0. The only existing strict lockout evidence remains the original registered adverse cell (and a few development-layout cells, none of which can serve as confirmation).
2. S2/S3 therefore could not be tested; the causal specificity of “changing only *T* opens the gate” was not reproduced in a second setting.
3. On the cell closest to lockout, wait_extend had a larger effect than post_exit, so the competing explanation (the confirmation wait is too short) was not ruled out and received some exploratory support.
4. For the manuscript: persistent lockout under this natural-pressure recipe should be treated as a rare pathological boundary, and this preregistered negative confirmation (0/96) must be reported beside any later attempt. A second, separately registered attempt later used a different induction mechanism (gateway timed install drop); see the Amplification-2 report.

## What was not done

- The pre-registration, arm definitions, thresholds, and analysis scripts were not changed; no case was rerun; the process was not killed.
