# Source pacing validity and bounded received cohorts

This prospectively supersedes the unexecuted cadence-transition development
matrix. Its registration and implemented native alternative remain recorded;
no cases from that alternative have run and no outcomes informed this choice.
The simpler repair uses the reporting protocol's existing maximum interval
instead of transmitting additional schedule-transition packets. No native
simulator, report schedule, wire format, byte allowance or routing score changes.

The source algorithm can choose a period of at most 15 s at each 5 s poll.
A report's period field describes the current selection, not a binding promise
that the source will retain that selection. Therefore routing-view validity is
16 s for every paced source report, independent of whether its sampled period
field says 5 or 15 s. This reuses the existing 16 s maximum-period allowance.
It does not infer health or successful receipt from absence, and current-version
MAC failure eligibility retains its stricter 8 s rule. Installation confirmation
retains its original 8 s evidence requirement as well.

The bounded cohort and transaction-closing variants are exactly those defined
in CADENCE_REPAIR_PROTOCOL.md: only actually received same-version closed
generation counts, two consecutive buckets, at least 20 packets per source,
cohort end at most 20 s old, no pre-epoch buckets, and no closure from a cohort
that predates the pending transaction. An old cohort describes historical
service, never unobserved current service.

There are 40 development cases: sizes 10/20, layout seed 2026101501, input
seeds 2026101511/2026101512, both scenarios and five models: legacy, full_v2,
horizon, cohort, closing. All use the original native binary, identical traffic,
FIFO, source pacing, protection and budgets except legacy has the original
communication control. Horizon adds only maximum-period routing-view validity;
cohort adds the bounded latest jointly received window; closing adds eligible
poor-service closure of a pending feedback transaction. No new parameter grid.

Freeze sources before runs. At both sizes a candidate must have mean service
versus legacy at least -0.5 pp and control DATA reduction at least 20%; it must
also improve mean service over full_v2 by at least 0.5 pp overall. Choose the
first passing variant in order horizon, cohort, closing. No margin is relaxed
after results. A failed family ends method revision. A passing family still
requires newly registered unseen layouts and input streams; v2 confirmation
data are not independent validation of a repair designed after their inspection.

The host-only radio summation optimization is separately verified bitwise on
three actual native traces and preserves every within-node addition order.
It runs only after native simulation has terminated. It changes neither
network events nor numerical energy values. No runtime LLM is used.
