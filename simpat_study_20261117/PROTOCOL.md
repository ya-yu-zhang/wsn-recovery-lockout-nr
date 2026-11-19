# SIMPAT simulation study — registration (frozen 2026-11-17, before any stage outcome)

Purpose: turn the forty-case negative-result diagnosis into a simulation-modelling study that meets the
Simulation Modelling Practice and Theory (SIMPAT) requirements for model development, implementation,
verification/validation, scalability and sensitivity analysis. The user authorised additional
experiments on 2026-11-17 ("论文质量最重要"). Each stage below still states its scientific question, the
evidence it adds, why the existing material does not supply it, and the cheaper alternative considered
(EXPERIMENT_PRINCIPLES.md).

Unchanged and not reopened: the forty-case screen, its frozen margins, its failure of all three
observation repairs and the stop rule of HORIZON_REPAIR_PROTOCOL.md. No stage below selects, tunes or
claims a new routing method. PostExit is a one-premise *intervention* used to test a causal claim, not a
proposed protocol. Runtime LLM calls: zero.

## Execution
GitHub-hosted runners (ubuntu-24.04), ns-3.44 at commit 43dce6710b8df69685e3479c1d33a571dda714ea, engine
recreated exactly as in control_budget_study_20261015/RECREATE.md. Compact per-case records are committed
to `simpat_study_20261117/results/`; raw native traces are uploaded as workflow artifacts only (no
duplicate raw traces in git). Technical re-runs of a failed shard do not add samples.

## Arms
* `joint` — implemented controller: an installation transaction that closed as `abandoned_unconfirmed`
  keeps all admission predicates in the unconfirmed state (premise T of Proposition 1).
* `post_exit` — identical except that such a transaction is released once its bounded wait has ended and
  no feedback transaction is pending; the controller then reasons from the per-source observed
  configuration that `base_controller.view` already rebuilds from received report versions
  (`contract_controllers.py`). Nothing else changes.
* `legacy` — the original controller (reference for service and control bytes).
Coupled controllers: `full_v2`, `horizon`, `cohort`, `closing` as in the forty-case screen.

## Registered lockout descriptors (`lockout.py`)
Unconfirmed exit; evaluated / rejected admission check; post-exit window; broad lockout L_broad (a
post-exit window reaches the action stop, 320 s, with no route decision, no confirmation and at least one
rejected check); strict lockout L_strict (L_broad and every evaluated check in the window rejected with
settled-service reason `installation_unconfirmed`, at least three checks). Endpoints per case: worst-source
timely service (200 ms) and control MAC DATA PSDU bytes, exactly as in the screen.

## E0 smoke (`--stage smoke`, 6 runs) — execution check only
Adverse cell (10 nodes, layout 2026101501, removal workload, input 2026101511): legacy, full_v2 and
horizon under both contracts, plus one 40-node run for timing. Acceptance: joint arms reproduce the
archived service 0.5928888… and 67 812 control bytes exactly; legacy reproduces 0.8697490…/98 550.
Not analysed scientifically.

## E1 model verification by docking (`docking/`, 125 + 125 runs)
Question: does the ns-3.44 lr-wpan MAC, which produced the decisive CHANNEL_ACCESS_FAILURE, behave as the
IEEE 802.15.4 unslotted CSMA-CA procedure prescribes? Missing evidence: the paper relied on the simulator
without any check of the access mechanism. Cheaper alternative considered: citing simulator
documentation — rejected because no published validation of the ns-3.44 lr-wpan access statistics was
located. Design: single-hop star, N ∈ {2,4,8,12,16} stations at 5 m, aggregate offered DATA airtime
G ∈ {0.05,0.15,0.30,0.45,0.60}, 64-byte MSDU with ACK, macMaxFrameRetries = 2, 120 s (5 s warm-up),
5 replications per cell in each simulator; an independently written reference model
(`csma_reference.py`) implements the standard procedure. Endpoints per request: P(success),
P(CHANNEL_ACCESS_FAILURE), P(NO_ACK), CCA busy fraction, mean MAC service time. Agreement criterion
(frozen): for each (N,G) cell, |Δ| ≤ 0.02 for the three probabilities and the busy fraction, and relative
service-time difference ≤ 10 %; the model is declared docked when ≥ 90 % of cell×endpoint comparisons
agree. Disagreements are reported, not tuned away; any later correction of a reference-model *defect*
(as opposed to a parameter fit) will be documented with its diff.

## E2 causal intervention on the original matrix (`--stage contract`, 64 runs)
Question: is premise T (joint confirmation contract) a necessary cause of the documented lockout?
Missing evidence: the paper's mechanism claim rests on an observational trace and a logical
proposition; no intervention was executed under the pinned environment. Design: the 8 original matched
cells × {full_v2, horizon, cohort, closing} × {joint, post_exit}. Joint arms must equal the archived
screen records exactly (reproducibility check). Prediction (registered): in the adverse cell all
post_exit arms leave the lockout and authorise a recovery decision after the exit; in cells without an
unconfirmed exit the two contracts are identical bit for bit.

## E3 prevalence and scalability (`--stage scale`, 600 runs)
Question: how often do unconfirmed exits and lockouts occur across layouts, sizes and workloads, and what
is the paired effect of releasing premise T? Missing evidence: one layout per size cannot speak to
scalability or frequency. Design: sizes {10, 20, 40} × ten fresh layout seeds 2026111701–2026111710 ×
fresh inputs {2026111711, 2026111712} × {removal, overload} = 120 cells; arms legacy, full_v2/joint,
full_v2/post_exit, horizon/joint, horizon/post_exit. Analysis: proportions of cells with an unconfirmed
exit, L_broad, L_strict per size and arm (Wilson 95 % intervals; cells sharing a layout are dependent, so
intervals are also given with layout as the resampling unit); paired post_exit − joint differences in
service and control bytes with layout-cluster bootstrap 95 % intervals (10 000 resamples, seed 20261117);
coupled-controller service and byte change against legacy per size. No significance-driven selection.

## E4 sensitivity (`--stage sensitivity`, 400 runs)
Question: does the lockout depend on the bounded installation wait and on the control-byte refill rate
(the two parameters that set how long a transaction may stay open and how scarce control capacity is)?
Design: 10-node E3 cells (40), horizon controller, both contracts; one-factor-at-a-time around the
baseline (wait 10 s, rate 305 B/s, taken from E3): wait ∈ {5, 15, 20} s and rate ∈ {152, 610} B/s.
Endpoints: L_broad / L_strict incidence, unconfirmed exits, service, control bytes, post_exit − joint
service difference. Cheaper alternative considered: analytical argument only — rejected because the
exit time interacts with the closed loop.

## Stop rules
Every stage runs once to completion. A technical failure (runner, build, out-of-disk) is retried without
change of configuration. No stage is extended, re-seeded or re-parameterised after its outcome is seen.
If E0 fails its exact-reproduction acceptance, the cause is diagnosed before any other stage runs.

## Amendment 1 (2026-11-18, after E1–E4 completed; before E5 is run)

**E1 outcome under the frozen criterion.** ns-3.44 and the registered reference agree on 82/125
cell×endpoint comparisons (65.6 %), below the 90 % docking criterion. This registered verdict stands and is
reported as "not docked".

**E1 diagnosis (exploratory, post hoc).** Frame timing matched exactly (identical 4.736 ms median MAC
service time at low load) and offered load matched, so the gap lies in sensing and collision handling.
Reading the ns-3.44 source identified two properties: (i) reception is decided by an SINR-based error model,
so frames can survive overlaps (capture), whereas the registered reference destroys every overlapped frame;
(ii) `LrWpanPhy::PlmeCcaRequest` resets the CCA energy peak to zero and `EndRx` removes a signal without
updating that peak, so a frame already on the air that ends inside the 8-symbol window is not sensed — a
deviation from the standard's energy detection over the window. Adding both properties to the reference
(`capture=True, cca_window='peak_reset'`) gives 119/125 agreement (95.2 %); the residual misses are at
G = 0.60, where ns-3's capture is partial rather than complete. `docking/diagnose_docking.py` reproduces all
variants. Both properties make ns-3 *optimistic* about channel-access failure relative to a
standard-conformant, collision-destructive medium.

**E5 robustness to the CCA deviation (`--stage cca_patch`, 360 runs + 125 docking runs).**
Question: do the lockout incidence and the post-exit effect depend on property (ii)? Design: ns-3.44 with a
one-line patch that initialises the CCA peak with the power present when the CCA starts (all else pinned);
docking grid rerun on the patched simulator (expected: agreement with the `capture` reference variant rises
and the `peak_reset` signature disappears); and all 120 E3 cells with legacy, horizon/joint and
horizon/post_exit. Endpoints and analysis as E3, plus paired patched − unpatched differences for each arm.
No outcome of E5 is used to change E1–E4 or their registered verdicts.
