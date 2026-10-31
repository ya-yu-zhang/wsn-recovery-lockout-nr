# Bounded diagnostic repair after failed small-network confirmation

The complete registered ten-node stratum contains 240 cases and 60 paired
input/scenario cells. Full v2 minus common control has mean service -4.1271
percentage points; full v2 minus admission-only has -3.6089 points. The
predeclared all-scale service condition therefore fails. No v2 positive
confirmation claim is retained and no threshold or input is silently changed.

In 4020 full-v2 observation ticks, 1605 report missing fresh source evidence;
1573 of these contain a received source report advertising 5 s with an age
between 8 and 16 s. Code inspection shows that the source can change to a
15 s schedule without emitting the changed schedule. The routing view's
16 s allowance applies only after receipt of a report advertising 15 s.
Additionally, insisting on the latest closed buckets makes service unknown
between quiet source reports, even when earlier same-version counts were
actually received. These are diagnostic observations, not executed repair
benefits or a causal proof of each service loss.

One repair family is permitted, with no parameter sweep. All rate, burst,
reserve, traffic, geometry, route score, byte charging and installation retry
parameters remain fixed. Old v2 source files and running cases are untouched.

1. A source emits a schedule-transition report when its selected period
   differs from its last emitted period. Subsequent emissions obey the newly
   advertised period. Polls remain 5 s apart, so this cannot exceed one source
   report per poll. The wire payload is unchanged. A lost transition report
   is still lost; no free controller observation is introduced.
2. A cohort variant uses the latest pair of consecutive complete, actually
   received, same-version source buckets when the original latest-window
   rule lacks counts. Its end must be no more than 20 s old, both sources
   must have at least 20 packets, and its start must follow the received
   installation epoch. Twenty seconds follows the existing three closed
   five-second counter slots plus one reporting clock step; it is not tuned.
3. A closing variant additionally allows an already known poor-service
   cohort to close a pending non-learning feedback transaction, provided the
   cohort starts after that transaction. Confirmation and actual packet
   costs remain enforced. This closes the control loop without inventing a
   reward or inferring health from an unknown state.

The development matrix has sizes 10 and 20, old development layout seed
2026101501, input seeds 2026101511/2026101512 and two scenarios. Five controls
are common control, unchanged full v2, cadence-only repair, cadence plus
bounded cohort, and the closing variant: 40 actual native cases. These
inputs are development inputs, not independent confirmation repetitions.

Before running, freeze all source and native binary hashes. A candidate can
proceed only if, at both sizes, mean service versus common control is at
least -0.5 points and control DATA reduction is at least 20 percent; it must
also improve mean service over full v2 by at least 0.5 points overall.
If multiple candidates pass, select the first in the fixed order cadence,
cohort, closing, favoring the smaller change. Do not relax a failed margin.
If none passes, stop method revision and report the failed mechanism and
scope limitations. No claim of sufficient publication novelty is automatic.

A passing repair requires a newly registered independent input/layout
confirmation. The old v2 confirmation outcomes cannot serve as independent
validation of the repair. No runtime LLM or learned policy is introduced.
