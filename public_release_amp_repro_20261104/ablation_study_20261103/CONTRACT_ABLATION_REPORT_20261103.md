# Confirmation-contract ablation (first campaign) — 2026-11-03

English public report. The original Chinese working note contained a local
machine hostname and private operating-system recovery instructions and is
**not** deposited. All numbers below are taken from
`CONTRACT_ABLATION_RESULTS_20261103.json`.

These results come from a genuine ns-3.44 closed-loop rerun (one controller
change; the native driver source was not changed). Mixin code, registration
files, and case summaries are in this folder. Raw case trees are not in this
lightweight bundle; they are available on request.

## 0. Environment and reproducibility

- Execution environment: Linux (Debian 13), g++ 14.2.0, ns-3.44 commit `43dce6710b8df69685e3479c1d33a571dda714ea`, built following `RECREATE.md` / `build_environment.py`, lr-wpan module, release configuration.
- The newly compiled driver has SHA256 `c02726c6…ecd86`, which differs from the archived driver `9b2d4ad7…6673` because the compiler differed. **Behavioural reproduction:** the joint (original contract) arm matches the archived forty-case results **bit for bit** on worst-source service and control DATA bytes for 18/18 configurations, including the adverse cell 0.592889 / 67812 B.
- Every new run passed the native audit and the control-byte bound check. Runtime LLM calls: 0.

## 1. Ablation definition (registered before the run)

Only premise *T* of Proposition 1 is changed. Thresholds, *F_s* eligibility, packet formats, the byte budget, the reporting cadence, and the native code are unchanged.

- **Joint (baseline):** the implemented global confirmation contract — after an install wait exits unconfirmed, the transaction remains “unconfirmed” for every admission predicate.
- **PostExit (relaxation):** when the install wait has ended unconfirmed and no feedback transaction is pending, release that transaction; the controller then reasons from the observation state already rebuilt per source from received report versions (`base_controller.view`).
- Implementation: `contract_ablation.py` (a short mixin). Registrations: `registrations/contract_ablation_{adverse,matrix}_registration.json`, `registrations/contract_generalization_registration.json`.

PostExit is an ablation arm, not a recommended deployment protocol.

## 2. Primary result: the most adverse cell (10 nodes, repeated relay removals, input 2026101511)

| Model | Joint worst-source service | PostExit | Δ service | Joint control DATA | PostExit | Δ control |
|---|---|---|---|---|---|---|
| Full v2 / Horizon / Cohort / Closing | 59.29% | **79.97%** | **+20.68 pp** | 67,812 B | 69,811 B | +2.95% |

(Legacy reference 86.97%.)

Horizon trajectory:

- Joint: unconfirmed exit at 245 s; 245–315 s, **15/15** checks rejected, service predicate = `installation_unconfirmed`, a candidate exists, no eligible failure report, and no later install — **the paper's lockout is fully reproduced**.
- PostExit: release at 250 s; 250–260 s service still unknown (no settled same-version buckets / sparse evidence); at **265 s** service is known, worst-source on-time rate 0.00 → authorise and issue an install (decision 4); confirmation at 270 s; afterwards known service 1.00/1.00/0.93. The lockout disappears and a recovery path is reachable again.
- Conclusion: relaxing the confirmation premise → the lockout disappears, post-exit authorisation appears, and worst-source service rises +20.68 pp, at +2.95% more control bytes. The direction of the effect is clear; the endpoint definitions were not changed.

## 3. Original layout, 8 cells × {Full v2, Horizon} (16 pairs)

PostExit changes the result only in the adverse cell above; the other 7 cells × 2 models are **bit-identical** to Joint (Δ = 0). The intervention acts only when premise *T* holds (minimality).

## 4. Generalization (new layouts 2026110301–04 × new inputs 2026110311/12 × 10/20 nodes × 2 workloads = 32 cells, registered before the run)

- Under Joint, **15/32** cells had an unconfirmed exit, but **0/32** locked out to the action deadline (E1): the gate was usually reopened by a later confirmation or by evidence.
- PostExit changed only **2/32** cells: 10-node overload L1/s12 **+5.70 pp** (control +3.80%); 20-node overload L1/s12 **−3.33 pp** (control +0.10%); the other 30 cells were bit-identical.
- Mean Δ service: 10 nodes +0.36 pp, 20 nodes −0.21 pp. Joint versus Legacy: control DATA −22.15% (10) / −31.73% (20), service −0.59 / −4.05 pp.

## 5. How this should be written

- The falsifiable claim receives **closed-loop causal support** on the adverse cell: changing only *T* removes the lockout and raises service.
- But persistent lockout did **not** reappear on the new layouts (0/32), and relaxing the contract is **not uniformly beneficial** (one rise, one fall). The main text must therefore state a **conditional boundary**: lockout requires a late unconfirmed exit (after the last fault, near the action deadline) together with no eligible failure report and no later confirmation. It must not be written as a prevalence, or as “relaxing the contract is generally better.”
