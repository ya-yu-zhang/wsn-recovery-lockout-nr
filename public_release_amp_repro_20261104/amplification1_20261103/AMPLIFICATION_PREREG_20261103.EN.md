# English version — Amplification-1 pre-registration

This is an English public version of `AMPLIFICATION_PREREG_20261103.md`.
That file is not hash-locked in the manuscript; the Chinese text (with
machine paths rewritten to `raw_on_request/`) remains in this folder as
the working original.

---

# Amplification pre-registration: induced condition C plus competitor / sham ablation

- Registration time: 2026-11-03 23:30 PST (America/Los_Angeles), **before any confirmation-stage run**.
- Code location on the authors' machine is recorded in the Chinese original as a path now written `raw_on_request/control_budget_study_20261015/`.
- Freeze method: `python3 run_amplification.py --stage confirm --register-only` writes `results/amplification_confirm_registration.json` with all 768 configurations and SHA256 of `amplification_arms.py, amplification_stages.py, run_amplification.py, analyze_amplification.py, analyze_amplification_confirm.py, analyze_contract_ablation.py, audit_case.py, contract_ablation.py, horizon_controller.py, budget_controller.py, fast_native_run.py` and of the native driver. A formal run aborts if any file or configuration has drifted.
- Runtime LLM calls: 0. No fabrication; no substitution of cells, arms, or thresholds in light of results.

## 0. Developmental (pilot) work — disclosed as such

Before confirmation, only the Joint arm was run on **development layouts** already used in earlier studies (2026101501, 2026101521–23, 2026110301–04), solely to choose a pressure recipe (only Joint lockout incidence was inspected; no relaxation-arm effects were inspected):

| Stage | Content | Joint lockout to the deadline (E1) |
|---|---|---|
| pilot | 7 fault timings × 5 layouts × {10,20} nodes × 2 inputs, multi_failure | 1/140 (the original adverse cell only, R0) |
| pilot2 | 5 recipes (including control-route relays 4/5 faulted) × 8 layouts × {10,20} × 3 inputs × {multi_failure, overload} | R0+overload 3/48; R7 five-fault multi 2/48; others 0 |
| pilot3 | 4 overload recipes × 8 layouts × 10 nodes × 6 inputs | R0+overload 1/48; others 0 |

There was also an implementation-equivalence check: all 8 arms on the original adverse cell, confirming that this module's `post_exit` arm bit-reproduces the existing ablation (0.5929→0.7997, 67812→69811 B). On that same cell, `fs_relax_global` (0.7902) and `thresh_relax_global` (0.7964) also raised service, while the `*_scoped` versions, `wait_extend`, and `sham_release` were bit-identical to Joint. **This was known before confirmation**, so the primary “does not copy in the same cell” criterion was placed on the scoped competitors and on `wait_extend`, and the global arms were treated as exploratory secondary results (Section 4).

Developmental observations (used to form the mechanism hypothesis, not as confirmation evidence):

1. Install packets follow the fixed control route 9→5→4→source (native driver, line 415), independent of the data path. Lockout cells all showed “a source install is lost → that source still reports with the old version (both sources fresh) → the old path is broken downstream of the source's first hop, so source-side failure counts *F_s* do not see the loss.”
2. Under light-load multi_failure, unconfirmed exits almost never occur; overload produces many unconfirmed exits, but most are reopened by eligible *F_s* or a later confirmation; only *F_s*-blind cells form a strict lockout.
3. Killing control relays 4/5 also disconnects source reports (reason becomes `missing_fresh_source`); the gate closes but *T* is not an identifiable binding cause — those cases are correctly excluded from strict E1.
4. Lockout layouts had d(4,0) ≥ 54 m (a weaker last control hop); development layouts with d(4,0) < 54 m had 0 lockouts (weak evidence, hence only secondary hypothesis H2).

## 1. Stress recipe (frozen)

- **S1_overload_R0:** overload workload (`arrivals` rates 10/40/10 /s, existing scenario definition unchanged) **plus** the already registered permanent three-relay removal schedule `[[65,2],[145,3],[225,6]]`. In the original forty-case study, overload never carried faults and multi_failure never carried overload; this recipe combines the two for the first time, as “load + late data-relay faults.”
- Everything else is unchanged: 10 nodes, generation_stop 330 s, action deadline 320 s, local15_event reporting, unified control budget, evidence protection, version cadence, FIFO, epoch certificates, report retry, thresholds, *F_s* rules, packet formats, native driver.

## 2. Cells (all new layouts / new inputs, never previously run)

- **Weak last control-hop stratum (stress, 12 layouts):** layout seeds scanned in order from 2026110305, taking the first 12 with d(4,0) ≥ 54 m **by geometry alone**: 2026110306, 309, 310, 319, 324, 327, 328, 331, 334, 336, 338, 340.
- **Contrast stratum (4 layouts):** the first 4 in the same scan with d(4,0) < 50 m: 2026110307, 311, 318, 320.
- Input seeds: 2026110501–2026110506 (6).
- Cells: 16 layouts × 6 inputs = **96 cells**; 8 arms per cell → **768** closed-loop runs.

## 3. Arm definitions (all based on HorizonController; each changes only one rule relative to Joint)

| Arm | Role | Rule |
|---|---|---|
| joint | Baseline | The implemented global confirmation contract (premise *T* holds) |
| post_exit | Treatment | Relax only *T*: release the transaction when the install wait ends unconfirmed and no feedback transaction is pending (same as the existing `contract_ablation.PostExitMixin`) |
| sham_release | Placebo (sanity check) | Compute the same release condition and log it, but do not release; must be bit-identical to Joint, or the whole campaign is invalid |
| wait_extend | Competing hypothesis (“the wait is too short”) | Install-confirmation wait 10 s → 20 s; *T* unchanged |
| thresh_relax_scoped | Competing relaxation (service predicate) | Only inside a *T*-blocking window (current install already exited unconfirmed), worst-source on-time threshold 0.80 → 0.95 |
| fs_relax_scoped | Mechanism-consistency arm (second conjunct) | Only inside a *T*-blocking window, *F_s* eligibility n ≥ 20 and failure ratio ≥ 0.20 → n ≥ 5 and ≥ 0.10 |
| fs_relax_global | Exploratory | Same as above but in force throughout |
| thresh_relax_global | Exploratory | Same as above but in force throughout |

Pre-stated mechanism predictions (Proposition 1: *T* ∧ no eligible *F_s* ⇒ gate closed):

- post_exit: on lockout cells, should re-authorise and issue an install, and worst-source service should rise.
- sham_release, wait_extend, thresh_relax_scoped: on lockout cells should **not** open the gate (during a *T* block, service is unknown, so the threshold cannot act; lost confirmation messages are not recovered by waiting longer).
- fs_relax_scoped: attacks the second conjunct; **if** the relaxed *F_s* fires, the gate may open — this is not a placebo, it is a consistency check that “lockout = the conjunction,” and it is not counted in pass/fail.
- Global arms may change the pre-exit trajectory and may raise service by “avoiding C” rather than “opening C”; reported exploratorily only.

## 4. Endpoints and criteria (`analyze_amplification_confirm.py`, frozen)

- **E1 lockout to the deadline** (identical to paper I3 / `analyze_contract_ablation.post_exit`): after the last unconfirmed exit, every evaluated admission check before the action deadline has service reason `installation_unconfirmed`, and no further install is issued.
- **Gate reachable again with a same-direction effect (opened):** after the first unconfirmed exit, an arm has at least one authorised admission and at least one issued install, and worst-source service is ≥ +1.0 pp versus Joint in the same cell. For post_exit, the first-exit time must also match Joint (pre-release trajectory identical).

**A-tier evidence thresholds (as given, and pre-registered as such):**

- **S1:** Joint E1 lockout cells ≥ 3, covering ≥ 2 layouts.
- **S2:** Among those lockout cells, post_exit opened in ≥ 2 cells.
- **S3:** On every S2-successful cell, at least one competitor (`wait_extend` or `thresh_relax_scoped`) does **not** open; and sham_release is bit-identical to Joint on all 96 cells.
- **S4:** The claim remains a conditional boundary (not written as a better protocol) — a writing constraint, not a data test.
- A-tier ⇔ S1 ∧ S2 ∧ S3 (S4 is enforced when writing).

Secondary / exploratory (do not affect the A-tier decision):

- H2: lockout incidence in the weak last-hop stratum > contrast stratum (one-sided Fisher exact test); overall incidence + Wilson 95% CI.
- Side effects on non-lockout cells: number of cells changed, up/down, mean Δ service (pp), mean Δ control bytes (%).
- Behaviour of fs_relax_scoped and of the global arms on lockout cells.

## 5. Stopping rules

- All 768 runs are completed in one campaign; no early stop, no added cells or inputs, no reruns (except a process crash; keep `FAILED_ATTEMPT.txt` and rerun the same configuration, recorded in the report).
- Any run that fails the native audit is retained and reported; cells that contain a failed run are excluded from the S1–S3 numerators.
- If S1 is not met: report “not met” and add no cells inside this registration; any later amplification requires a new registration file, labelled as a second attempt (multiplicity risk stated in the report).
- If S1 is met but S2 or S3 is not: report “condition C can be elicited, but the causal specificity of *T* was not reproduced on independent cells.”
