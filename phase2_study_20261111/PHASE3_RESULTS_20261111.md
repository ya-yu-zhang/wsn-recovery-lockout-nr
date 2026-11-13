# Phase-3 results (Phase-2 full sets + Phase 2b), 2026-11-11 PT

Authority: the corresponding author authorised continuation of the registered studies. Registrations: Phase 2 `REGISTRATION_PHASE2_20261111.json` (SHA256 `caf07cc9…ab4f`); Addendum 1
`ADDENDUM_PHASE2_20261111b.md` (`fc637ae5…6dec`, committed `c69f023` before any run below); Phase 2b
`REGISTRATION_PHASE2B_20261111.json` (`9afb4dc3…5a23`, committed `c70a441` before any 2b run). Frozen results (`1f37be33…6a24`)
untouched. Nothing pushed or sent. Manuscript not edited. Deviations: `CHANGELOG.md`.

## (1) Mode C docking (conditioned mirror vs ns-3)
| Set | n | C1 E1 | C2 exit times | C3 Φ/tick | C4 reason/tick | Verdict |
|---|---|---|---|---|---|---|
| Registered full (48 cells × 5 arms + 8 adverse) | 248 | 1.000 | 1.000 | 1.000 | 1.000 | **PASS** |
| (E) all 9 frozen sets, supported arms | 1,653 | 1.000 | 0.837 | 1.000 (46,598) | 1.000 (110,751) | — |
| (E) same, frozen exit convention | 1,653 | 1.000 | 1.000 | 1.000 | 1.000 | — |
The strict-C2 misses (269) are exits that a late confirmation later rescued. The frozen `post_exit()` counts them as exits; the mirror's registered endpoint does not. The difference is in the definition, not in the gate logic. 465 cases with arms the mirror does not implement were skipped.

## (2) FlockLab trace replay (192 registered runs)
192/192 complete, `audit_case` 192/192. **Ingestion audit (registered): FAIL**:
- R2 exact recomputation passed for all 11,199/11,199 link-runs.
- R1 tolerance failed for 4/3,413 link-runs. The exact-binomial expectation of such exceedances under a correct stream is 2.69 (E), so this is consistent with chance; the per-link rule had no multiplicity allowance.

| Day | Mode | Scenario | Arm | n | ≥1 unconf. exit | E1 lockout (Wilson 95 % CI) | install after exit | median worst service |
|---|---|---|---|---|---|---|---|---|
| A | R2 | M1 | Joint | 16 | 16 | 9 (0.33–0.77) | 0 | 0.400 |
| A | R2 | M1 | PostExit | 16 | 16 | 0 (0.00–0.19) | 16 | 0.631 |
| B | R2 | M1 | Joint | 16 | 16 | 9 (0.33–0.77) | 0 | 0.399 |
| B | R2 | M1 | PostExit | 16 | 16 | 0 (0.00–0.19) | 16 | 0.475 |
| A | R1 | M1 | Joint | 16 | 16 | 6 (0.18–0.61) | 0 | 0.401 |
| A | R1 | M1 | PostExit | 16 | 16 | 0 (0.00–0.19) | 16 | 0.683 |
| A/B | R2/R1 | N | both | 96 | 1–3 per cell | 0 in all cells (each 0.00–0.19) | 1–3 | 0.16–0.78 |
Under measured link statistics the outcomes match the simulation contrast. With the induced drop (M1), Joint never reopened in 48/48 runs and locked to stop in 24/48. PostExit reopened in 48/48. Without the drop (N), lockout was 0/96: no natural-prevalence claim.

## (3) DOE 3^(5−2), 8 new layouts, 432 runs (H3 void)
432/432 complete, 0 technical failures, audit 432/432.
- **H1 PASS**: 95/96 = 0.990 ≥ 0.95. The one exception reopened after its first exit through a late confirmation and was locked after its last exit.
- **H2 FAIL as registered**: PostExit E1 = 1/216 (point 25: drop 240–360 s, mask 2, wait 10 s). Mechanism (E): the only evaluated tick at or after the exit is the exit tick itself. Release applies at the next tick, and no admission check was triggered before stop. This is an endpoint-definition edge case, not a T lock, but it is reported as a failure.
- **H3 VOID.**
- **Phase diagram (E)**, Joint E1 by factor level:
  - drop start 0/120/240 s → 0.60/0.25/0.07
  - length 20/60/120 s → 0.24/0.28/0.40
  - mask 1/2/3 → 0.29/0.24/0.39
  - faults none/early/late → 0.24/0.29/0.39
  - wait 10/15/20 s → 0.29/0.28/0.35
  Lockout needs an install attempt inside the drop window. When the window starts at 240 s, exits mostly do not occur (0–2/8 per point).

## (4) Phase 2b: Mode F′ with an a-priori contention/queue submodel
| Set | Arm | n | F1 | F2 | mean P(gate open) |
|---|---|---|---|---|---|
| Probe P | Joint / sham / PostExit | 12 each | 0.667 / 0.667 / 1.000 | 1.000 | 0.39 / 0.39 / 1.00 |
| Holdout H | Joint / sham / PostExit | 36 each | 0.917 / 0.917 / 1.000 | 1.000 | 0.31 / 0.31 / 1.00 |
F3 over 48 Joint cells: ns-3 26/48, mirror interval [3, 13] → outside. Brier 0.401. **Phase 2b verdict: FAIL.**
- The contention submodel fixed the PostExit mismatch (0 → 1.000).
- Joint/sham are now over-opened: every Joint reopening in the mirror happens through an eligible F_s.
- Aggregate contention matches ns-3 without fitting (CCA busy 0.353 vs 0.363; NO_ACK jobs/run 3,654 vs 3,579). The remaining gap is therefore in how per-window source-failure evidence is distributed.
The defensible claim is that the gate logic is verified exactly (Mode C). Network-level free-running reproduction remains a negative docking result.

## Figures (PDF+PNG, `figures/final/`)
`Fig_P2_docking_table`, `Fig_P2_flocklab_outcomes`, `Fig_P2_doe_phase_diagram`, `Fig_P2_doe_main_effects`; tables `TABLES_PHASE2.md`.
