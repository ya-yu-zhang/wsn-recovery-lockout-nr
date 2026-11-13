# Second preregistration — Phase 2 V&V studies (written 2026-11-11 PT, before any phase-2 experiment)

**Status.** Written before any run counted below. Frozen results (Amp-1 0/96, Amp-2 26/48,
PostExit 26/26, competitors opened=0, sham 48/48, registration SHA256 `1f37be33…6a24`) are a
read-only reference and are never re-scored. Everything here is NEW and is labelled either
*confirmatory (C)* or *exploratory (E)*. Runtime LLM calls: 0. Nothing is pushed or sent.

**Authorization and necessity.** The corresponding author authorised the Phase-2 studies
and the additional experiments described below. [REDACTED: internal message identifiers
and laboratory-rule references.] Necessity for each study:
- (a) Docking: does the published formal model (Sec. 3.6–3.7: T, F_s, Ψ, Φ, Prop. 1, S1–S6) reproduce the
  implementation's gate outcomes on identical inputs, and does an independent DES reproduce them
  without the ns-3 PHY/MAC? This is the missing model-verification evidence that SIMPAT asks for, and no cheaper check gives it.
- (b) FlockLab: do the outcomes survive *measured* 802.15.4 link statistics (SIMPAT: "validation with
  real data")? This is not hardware validation.
- (c) DOE: where is the boundary in the induction parameters? It turns a single induced point into a
  designed sensitivity study.

**Allowed technical smoke tests** during code development: only on non-registered inputs
(`base` topology or the FlockLab probe day with generation_stop ≤ 60 s), excluded from all analyses, and logged in `CHANGELOG.md`.

---
## (a) Docking: SimPy mirror vs ns-3 (reference = frozen runs)

**Model.** `mirror/ccmirror.py` is written from the manuscript specification (constants: 5 s decision
ticks from 10 s; action stop = generation_stop − 10 s; 10 s install wait with one retry per source at
+5 s; confirmation = fresh (≤ 8 s) source report of the decision version stamped after the decision; 16 s paced source view;
F_s = fresh (≤ 8 s) current-version source report with ≥ 20 completions and ≥ 20 % failures; Ψ known only when
both sources are fresh, T is confirmed or released, route-consistent, settled 5 s buckets ending ≥ 0.2 s before t within
the last 15 s, complete closed counts ≥ 20 per source; Φ = [Ψ poor (<0.8)] ∨ [∃ F_s eligible]; Joint keeps T after
an unconfirmed exit; PostExit releases T when the exit is unconfirmed and no feedback is pending; sham logs only;
wait_extend = 20 s wait; thresh_relax_scoped = Ψ<0.95 only while T is unconfirmed). The original controller is not imported.
Two modes:
- **Mode C (conditioned).** Inputs: the recorded per-tick gateway observations, the recorded install
  decisions, and the recorded *evaluation mask* (ticks on which the implementation ran an admission check; the trigger rule —
  missing/busy/queue/failure events, pending feedback — is outside the formal model) of each frozen case. Outputs per tick: reason class, Φ, T. This checks the specification against the implementation on identical inputs.
- **Mode F (free-running SimPy DES).** It uses the same FSM plus an abstract network: 10 nodes from the case
  positions CSV, the case arrivals CSV, fixed report/install routes (s→4→5→9, 9→5→4→s), fault removals, the gateway
  install drop, per-hop frame success h(d) (logistic in distance, at most 3 MAC attempts, one application
  retry for reports), and a constant per-hop latency. **Calibration** (`mirror/calibrate.py`) uses only the jobs
  traces of `amplification2_manip_check` (4 layouts) and `amplification_pilot2/3` (excluding layout
  2026101501, the adverse layout, and every confirm layout). Parameters are hashed before any docking comparison. R = 100 replicates per case
  (seeds 20261111+i). Route choice after Φ=1 is the first pair of the 65 m simple-path catalog that avoids relays whose
  reports are > 8 s old (relay view limit); a tick is *evaluated* if it is the bootstrap tick or, with no pending feedback
  (decision + 10 s), a relay on the current paths has a view older than 8 s or Ψ is poor or some F_s is eligible. Not modelled: busy/queue evaluation triggers, queues, CSMA contention, the byte budget, relay safety evidence, and UCB learning.

**Sets.** Probe A: adverse cell (budget_10_2026101501 / multi_failure / seed 2026101511; 4 models × {joint, post_exit} = 8)
plus the Amp-2 subset layouts 2026110410–11 × 6 seeds × {joint, sham_release, post_exit} (36). Full: all 48 Amp-2 cells ×
{joint, sham_release, post_exit, wait_extend, thresh_relax_scoped} (240) + adverse (8) + prospective DOE (432, see c).

**Endpoints and pass criteria.**
- (C) C1 per-case E1 (IU-only lockout to stop) agreement ≥ 95 %. C2 per-case set of unconfirmed-exit times equal (tick resolution) ≥ 95 %.
  C3 pooled per-tick Φ agreement on evaluated ticks ≥ 0.98. C4 pooled per-tick reason-class agreement ≥ 0.95.
- (C) F1 per-case gate outcome (≥ 1 install after the first unconfirmed exit before action stop; replicate majority) agreement ≥ 95 % per arm.
  F2 first-exit time (replicate median) equal ≥ 95 %. F3 Joint E1 incidence: the ns-3 count lies inside the mirror's central 95 %
  Poisson-binomial predictive interval.
- (E) Brier score for E1; PostExit first-authorization time error; adverse-cell Mode F probabilities.
- **Probe A passes** if C1–C4 and F1–F2 pass on the probe set. If it fails: stop, diagnose, and correct only documented
  misreadings of the specification text (cited line). Log every change in `CHANGELOG.md` with a diff hash and re-run the probe once.
  Thresholds are never changed. A second failure stops (a) and is reported as a negative docking result.

## (b) FlockLab trace replay (Zenodo 10.5281/zenodo.3727526, CC-BY-4.0)
**Data.** Platform `sky` (TelosB/CC2420), channel 26, 0 dBm, 8-byte strobes. Pre-declared days (UTC): **Day A 2019-09-15**
(probe and full) and **Day B 2020-01-22** (full). All tests that day are used in time order.
**Subgraph rule.** Roles: sink 9; data relays 2, 3; control relays 4, 5; others 6, 7, 8; sources 0, 1. Required directed links,
both directions with day-PRR ≥ 0.90: 0–2, 1–2, 2–3, 3–9, 0–4, 1–4, 4–5, 5–9, 3–5, 6–4, 7–4, 8–4.
Exhaustive backtracking over injective role assignments (role order 9, 5, 4, 3, 2, 0, 1, 6, 7, 8; candidate node order shuffled
with seed 20261111; stop at 10,000 valid assignments). Draw K = 4 distinct node sets per day uniformly with seed 20261111.
Probe uses the first 2 of Day A. If fewer than K exist, use all and report.
**Injection.** New driver `wsn-closed-loop-trace` (new SHA256): a custom `ErrorModel` attached through
`LrWpanPhy::SetPostReceptionErrorModel` at every receiver. It parses the MAC header source address and, for data/command
frames, consumes the next bit of the (sender→receiver) FlockLab bitstream (R2, cyclic replay; start offset = hash(seed, link));
bit 0 ⇒ corrupt. ACK frames are not trace-dropped (declared). Positions: 4×3 grid, 6 m spacing (one collision
domain; the trace decides link loss). Secondary mode R1 = Bernoulli(day PRR), Day A only.
**Runs.** Scenarios N = multi_failure, faults [[145,3],[225,6]], no drop; M1 = frozen Amp-2 recipe, unchanged.
Arms joint, post_exit; seeds 2026111301–04. Probe: Day A, 2 subgraphs, seed …301, N+M1, 2 arms, R2 = 8 runs. Full: 2 days × 4 subgraphs × 4 seeds × 2
scenarios × 2 arms R2 = 128, plus R1 Day A (4 × 4 × 2 × 2) = 64.
**Pass (C, ingestion audit).** All runs complete. `audit_case` passes. R2: for every link the native drop count equals the number of 0-bits in the consumed window recomputed independently in
Python from the trace file, offset rule and evaluated count (exact), and for links with ≥ 100 evaluated frames |empirical drop fraction −
(1 − day PRR)| ≤ 0.03 is reported (E; bursty traces need not meet it). R1: for links with ≥ 100 evaluated frames |empirical drop fraction −
(1 − PRR)| ≤ max(0.03, 3·SE). Neutrality (E): the trace binary with traceMode=0 is run on the 2 probe-subset Amp-2 cases and its
output hashes are compared with the frozen runs (a mismatch is reported, not hidden; it would be a compiler effect). **Outcomes (E):** Joint E1 and gate-closed incidence, PostExit
installs after exit, worst-source service. **Lockout = 0 is an acceptable, archived result.** No natural-prevalence claim is made.

## (c) Fractional factorial DOE (NEW layouts budget_10_2026111101–08; seeds 2026111201–08, one per layout)
Factors (3 levels each; 3^(5−2), resolution III): A drop start {0, 120, 240} s; B drop length {20, 60, 120} s; C mask {1, 2, 3};
D fault schedule {none, [[100,3],[180,6]], [[145,3],[225,6]]} with D ≡ A+B+C (mod 3); E install wait {10, 15, 20} s with
E ≡ A+2B (mod 3). Layout is a block. Arms joint, post_exit. There are 27 × 8 × 2 = **432** runs. The induction mechanism is the frozen
`dropInstall*` CLI; there is no recipe change aimed at producing lockouts.
**Hypotheses.** H1 (C): Joint cases with ≥ 1 unconfirmed exit and no eligible F_s after the last exit have the gate closed to action
stop in ≥ 95 %. H2 (C): PostExit has IU-only E1 lockout in 0 cases. H3 (C, prospective docking): Mode-F predictions, frozen and hashed
*before* the ns-3 DOE runs, agree with ns-3 on per-case exit occurrence in ≥ 90 % and on gate outcome (F1) in ≥ 90 %.
(E) Phase diagram of Joint E1 and gate-closed incidence over A×B faceted by C; D and E main effects (logistic).

## Stopping rules (all studies)
Technical retries do not add samples. If more than 5 % of a set fails technically, stop and report. There are no design, threshold, layout or seed
changes after any outcome is seen. If a probe fails, the matching full runs are not started. Every deviation goes to `CHANGELOG.md`.
Pre-freeze amendment (before any registered run): FlockLab seeds widened to 2026111301–04 so the stated counts 128/64 hold
(the 2-seed text gave 64/32); ingestion audit rule made exact. Frozen scripts and their SHA256 are listed in `REGISTRATION_PHASE2_20261111.json`, which is committed locally (never pushed).
