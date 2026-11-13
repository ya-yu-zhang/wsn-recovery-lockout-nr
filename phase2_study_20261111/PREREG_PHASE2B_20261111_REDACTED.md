# Phase-2b registration: Mode F' (contention/queue submodel), written 2026-11-11 PT before any 2b run on registered inputs

**Status and authority.** [REDACTED: internal author authorization to continue.] The Phase-2 Mode-F probe-A failure (F1 post_exit
0/12) is final and is never overwritten. Phase 2b is a NEW, separately registered test of the diagnosis written in CHANGELOG
(source reports re-phase on queue/contention state changes). Frozen results are read-only. Runtime LLM calls: 0.

**Model.** `mirror2b/ccmirror_cq.py` (NetworkCQ) replaces only the abstract Network of Phase-2 Mode F. The gate FSM, decision
policy, endpoints and scorer are unchanged (`mirror/ccmirror.py`, `mirror/dock.py`, whose SHA256 are as in the Phase-2 registration
except dock.py's logged KeyError fix). Every constant is taken a priori from the ns-3 driver source or the ns-3.44 LrWpan defaults,
with line references in the module docstring: FIFO queue 16, unslotted CSMA/CA (minBE 3, maxBE 5, maxBackoffs 4, unit 20 sym,
CCA 8 sym), 3 MAC attempts, CCA radius from the driver formula (46.1 m), PSDU sizes, the unified control budget
(305 B/s, 4572 B, reserve 1524 B, 381 B per frame), the report retry rule, the local state bins, the relay lease of 12 s, the source 5/15 s rule
(install < 15 s, failure, or state change) and the relay 10/15 s rule. Link quality is the FROZEN Phase-2 calibration h(d)
(sha256 20b11804…2e84), converted to a per-attempt q = 1 − (1 − h)^(1/3). **No parameter is fitted to any gate outcome.**
Smoke tests (base topology, synthetic arrivals, 60 s) were run before this registration and are excluded.

**Sets.** P = the same 44 probe cases as Phase-2 probe A (36 Amp-2 subset layouts 2026110410–11 × 6 seeds × {joint, sham_release,
post_exit} + 8 adverse). H = fresh holdout: Amp-2 layouts 2026110412–17 × 6 seeds × the same 3 arms = 108 frozen ns-3 cases, never
used for calibration, mirror development or Phase-2 probing. R = 100 replicates (seeds 20261111+i).

**Endpoints (confirmatory).** As in Phase 2: F1 per-case gate outcome (replicate majority) and F2 replicate-median first exit, per arm.
- **Pass 2b** if F1 ≥ 0.95 and F2 ≥ 0.95 for every arm on BOTH P (Amp-2 part) and H.
- Secondary (C): F3 = ns-3 Joint E1 count over the 48 Joint cells (P ∪ H Joint, Amp-2) inside the mirror's central 95 %
  Poisson-binomial interval.
- (E): adverse-cell agreement, mean post-exit gate-open probability, Brier score for E1.
**Rules.** One run per set, no re-runs after outcomes are seen, and no code changes after freeze except crash fixes, each logged with a diff hash. A
fail is reported as a fail. Technical failures > 5 % stop the set.
