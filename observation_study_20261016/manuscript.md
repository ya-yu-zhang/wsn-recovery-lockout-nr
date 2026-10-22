# Recovery Lockout after Partial Route Installation under Sparse Feedback in Wireless Sensor Networks

## Authors

Shu-Chuan Chu, Ya-Yu Zhang, Zhenyu Meng, Zhao Jia, and Jeng-Shyang Pan

Shu-Chuan Chu and Jeng-Shyang Pan are with the School of Computer Science and the School of Artificial Intelligence/School of Future Technology, Nanjing University of Information Science and Technology, Nanjing 210044, China. Ya-Yu Zhang is with the School of Computer Science, Nanjing University of Information Science and Technology, Nanjing 210044, China. Zhenyu Meng is with the School of Computer Science and Software, Zhaoqing University, Zhaoqing 526061, China. Zhao Jia is with the School of Information Engineering, Jiangxi University of Water Resources and Electric Power, Nanchang 330099, China.

Corresponding author: Jeng-Shyang Pan (e-mail: 100112@nuist.edu.cn).

## Abstract

On a shared low-power medium, an improved control-byte account does not imply that evidence-qualified routing recovery remains usable. A wireless sensor network controller is examined in which sparse source reports, per-hop control-byte reservation, and positive received evidence gate recovery. Forty registered cases cover two network sizes, two workloads, and two shared input seeds. Under the coupled Full v2 mechanism relative to Legacy, control-frame bytes fall by 23.02 percent at ten nodes while worst-source timely service falls by 10.78 percentage points; at twenty nodes, service rises by 1.51 points and control-frame bytes fall by 35.27 percent. None of the three observation repairs meets the frozen joint criterion, so this repair family is stopped without expanding the matrix and without further trials on the same ineffective observation changes. In an exploratory diagnosis of the largest adverse cell selected after the screen, the recorded sequence separates byte-budget admission, channel-access failure before any data frame, ended installation waiting, a global confirmation condition that still blocks recovery despite available candidates, and historical service deficits that can be reconstructed offline from received records. Fifteen later checks remain rejected; eleven source-, version-, and epoch-indexed deficit windows match the native logs. A conditional argument states when a longer routing view or feedback-transaction closure leaves the block in place, and when escape is possible. The deliverable is a recheckable confirmation-contract failure chain. Prevalence is not estimated, and no benefit is assigned to an unexecuted replacement.

Keywords: control traffic; partial observation; reproducible simulation; routing recovery; service cohorts; wireless sensor networks

## 1 Introduction

Application packets, and the measurements by which their routes are managed, are carried by a wireless sensor network over the same medium. Capacity can be released when reports are suppressed. The same suppression can delay installation confirmation and can remove the observations by which recovery is authorized. When the reporting policy is changed, the information supplied to the controller is changed with it. The coupling matters once application data and multihop control messages contend for one finite request queue.

Ways of reducing communication are already available in adaptive dissemination and in traffic metering. Transmission intervals are adjusted by Trickle from local consistency [1]. Rate and burst allowances are expressed by token-based metering [2]. Feedback and shared-medium load are also related by reliable sensor-network transport [3]. A narrower question is raised by these mechanisms. When routing recovery depends on received evidence, is the service of the application that supplies that evidence preserved by a verified reduction in control DATA, meaning the bytes carried in medium-access-control data frames? Judging recoverability from control-byte savings, or from qualified snapshots alone, can therefore mislead.

An implementation with two application sources and a gateway controller is studied. Complete control-request reservation at every hop is combined with protected admission for selected evidence and with source report pacing. After bootstrap, recovery is required to rest on positive received evidence of poor service, or of current-version transmission failures. A missing relay report is not treated as proof of failure. Unqualified reconfiguration is avoided by that choice. A physically damaged route can also be left without enough evidence for a change.

The reported experiment was a prospectively registered development screen of three observation changes. Interpretation of that screen as a negative-result mechanism study is exploratory. No successful method was selected. The original service and byte-saving criteria were retained. The existing traces were then diagnosed, so that a lack of received measurements could be separated from a policy that refuses to interpret them.

Recovery lockout after partial route installation is traced at packet and transaction level. Byte-budget admission, channel access, the end of waiting, and permission for a later decision are kept apart. The control-contract conditions under which a timeout leaves the service gate closed are stated, together with the later observations by which the gate can be opened. Historical service is identified from received epoch certificates and from closed generation counts. It is not required that both sources hold the latest desired version. Every reconstructed count in the diagnosed case is checked against native packet records. The service and control-traffic setting is supplied by the forty-case screen, and every failed repair selection is kept. The rate-and-burst relation is used only as an accounting check. No gain is claimed for a routing optimizer, or for contextual learning. The contribution claimed here is a locatable confirmation-contract failure and a documented stop on further repairs in this family, not a superior routing method.

The question lies in the communication, networking, and control range of IEEE Access. Application data and the reports used to manage routes share one IEEE 802.15.4 queue. The Negative Result form is used because the registered repairs miss their own service and byte criteria. The blocking condition remains explicit and can be matched again to the native traces.

The working hypothesis is that a bounded installation wait, together with broader received observations, is sufficient for positive-evidence recovery to remain usable after a partial update. The registered observation repairs do not support that hypothesis: they miss the frozen service and byte criteria. Three properties that are easy to treat as one event are separated by the recorded case. Waiting has stopped. Past service can be calculated. Another action is authorized. The conclusion applies to the confirmation contract that was implemented. Sparse reporting, or conservative admission, is not thereby shown to block recovery in general.

## 2 Related work

Redundant dissemination is reduced by Trickle through consistency and interval adaptation [1]. A five-second local poll is used by the sources studied here. A report period of five or fifteen seconds is chosen from installation state, medium access control (MAC) completion, and local contention. The sampled period can be changed at the next poll. An interpretation problem is created for the gateway: the period in the last received report is not a commitment about the next transmission. A full Trickle stack is not implemented, and that name is not assigned by the present comparison to a timer proxy.

Admitted volume is bounded by traffic metering with a replenished allowance [2]. Where the charge is taken determines the bound obtained here. Forwarding and repeated application-level attempts are omitted if only reports generated by a source are counted. A conservative bound over those requests is obtained when a maximum transmission cost is reserved at each control-request admission. Sensor transport is addressed by Rate-Controlled Reliable Transport (RCRT) [3]. The endpoint considered here is timely application service, while the same medium is consumed by routing control.

Transmission-interval overlap and suppression bottlenecks in low-power dissemination are identified by A2-Trickle, with evaluation in simulation and on a device testbed [4]. Propagation under Trickle is its subject. Contending unicast management is examined here, and the diagnosed restriction is the gateway's interpretation of partially installed source versions. The pacing rule is not treated as Trickle. No measured comparison with A2-Trickle is claimed.

Persistent failures in a dense electronic shelf-labeling deployment were used to guide gateway changes [5]; that single-hop scheduled setting differs from the present multihop simulation, but shares the narrower point that a concrete failure should be located along the communication and management path before it is attributed to an optimizer. Event-triggered concurrent-transmission control [6] and network-update abstractions that separate desired from installed configurations [7] likewise motivate examining sparse reports and partial source versions. Per-packet consistency for distributed updates is not claimed, and a successful replacement policy is left unresolved.

## 3 Network and observed evidence

### 3.1 Native model and workloads

ns-3.44 is used [8]. Sources are nodes 0 and 1; the gateway remains node 9 at both sizes. Additional nodes are forwarding and reporting relays, so twenty-node layouts add candidate relays and reporting load without adding application flows. One fixed development layout per size, from layout seed 2026101501, is used. Geometry controls and the pinned simulator revision are archived with the replication package (see supplementary_notes.md).

IEEE 802.15.4 carrier assessment, contention, acknowledgments, and up to two retries after an initial MAC attempt are modeled. Application packets and control requests share a FIFO of capacity sixteen. Positions remain fixed until a scheduled relay removal. The main fixed settings are listed in Table 1; channel and scaffold details are archived with the replication package.

| Setting | Value |
|---|---|
| Network sizes | 10 and 20 nodes including two sources and one gateway |
| Generation horizon and tail | 330 s and 20 s |
| Application payload and timely deadline | 64 bytes and 200 ms |
| FIFO capacity and maximum DATA attempts | 16 requests and 3 attempts per request |
| Controller clock and scored route-pair limit | 5 s and 64 evaluations per decision |
| Source report periods | 5 s or 15 s |
| Byte refill rate, capacity, protected reserve | 305 bytes/s, 4572 bytes, 1524 bytes |
| Per-request reservation | 381 bytes |
| Received source MAC failure age | At most 8 s |
| Alternative routing-view validity | 16 s for paced source reports |
| Alternative historical service cohort | Two consecutive 5 s buckets, end at most 20 s old |

A frozen exponential interarrival stream is used by each source. In the relay-removal workload, the rate is cycled through 5, 20, and 5 packets/s in consecutive thirty-second phases throughout generation. Relays 2, 3, and 6 are removed at 65, 145, and 225 s. In the overload workload, the rates are 10, 40, and 10 packets/s. No removals are injected. Inputs with seeds 2026101511 and 2026101512 are shared across all treatments within each size and workload. The two workload outcomes that use one input seed are not additional independent seeds.

### 3.2 Controller information and common route search

Reports already delivered to the gateway, its own control counters, and application packets it has received are the observations available to it. Future removals, the simulator's physical-liveness flags, and fields of lost reports are not available. An installed route version, current-version MAC completion counts, and generation counts for closed five-second buckets are carried by source reports. The first complete bucket following local installation is identified by a received epoch certificate. Offered load known to the offline evaluator is not substituted for an unknown online denominator.

While installation packets are in flight, the installed version can differ between the two sources. Installation must be confirmed by each source through an actual received report. One bounded installation retry per source, exit after ten seconds without confirmation, and reconciliation of late confirmations are included in the common transaction mechanism. A pending feedback transaction is an accounting and waiting state. No learning update uses its outcome in these experiments.

The service predicate that was implemented is more restrictive than a record of those source versions. Unknown is returned if the most recent installation transaction has not been closed as confirmed. Each received source version is also required to map to the controller's desired current route for that source. Individually reported versions can therefore be left, by a closed unconfirmed transaction, without an admissible joint service calculation. These implementation conditions are part of the mechanism under examination.

The same initial routes, geometric candidate construction, received-report feasibility rules, and resource scorer are used by all treatments. The original exhaustive construction is used by the ten-node catalog. At most thirty-two paths per source, at most seven nodes per path, and at most 100000 construction expansions are retained by the twenty-node catalog. At most sixty-four route pairs are scored at each decision. Catalog construction and feasibility checks are excluded from that limit. Search duration is modeled as twenty microseconds per scored evaluation. It is not a measured deployment latency.

A resource proxy, weighted by 0.85, is combined by the scorer with 0.15 times the mean of the two source congestion proxies. Normalized hops, path length, and shared relays are weighted in the resource proxy by 0.60, 0.25, and 0.15. Queue occupancy, the busy-to-carrier-assessment ratio, and MAC service time are weighted in the congestion proxy by 0.45, 0.35, and 0.20. Received network state is described. A counterfactual outcome oracle is not. With this scorer held fixed, the observation changes can be read on their own. No second optimizer is added.

## 4 Communication and observation mechanisms

### 4.1 Complete per-hop control reservation

Byte credit B is held by every node at the start and is replenished at rate r, with a cap at B. Before a control request enters an available FIFO slot, q bytes are reserved by the node. With a maximum 127-byte DATA frame and three possible attempts, q equals 381 bytes. A separate admission is created by forwarding, at the forwarding node. Application-level report and installation retries are also charged. Unused credit is not refunded after a successful first attempt.

The settings are B = 4572 bytes and r = 305 bytes/s. Ordinary control requests need q plus a protected reserve R = 1524 bytes. Protected requests need q. Both consume q from the same credit pool. Protection is applied to source reports, to installation packets, and to reports from relays that hold a local application-forwarding lease. Observed forwarding activity is used by the lease. Report priority is conveyed by a spare encoding bit, without an increase in payload size. Rounding drift is avoided by integer byte-nanosecond credit.

Let $A_i(t)$ denote cumulative reserved bytes and $C_i(t)$ the actual control DATA bytes transmitted by node i through time t. Nonnegative credit with a full initial bucket gives the following classical bound.

$$ C_i(t) <= A_i(t) <= B + r t $$

Every actual control DATA attempt belongs to a reserved request, and the maximum attempts and frame size of that request are covered by the reservation. Which requests can use credit is changed by protection. The bound is not enlarged. The reasoning applies to transmitted MAC DATA protocol service data units (PSDUs). No bound is made on acknowledgments, receive time, service, or energy.

### 4.2 Source pacing and evidence-qualified recovery

A poll is made by a source every five seconds. A five-second period is chosen during the fifteen seconds after local installation, when at least ten current-version MAC completions show more than twenty percent failure, or when the local queue and contention state changes. Otherwise a fifteen-second period is chosen. A report is emitted only if the selected interval has elapsed. Deterministic input-dependent phases are identical across treatments.

After bootstrap, a known service cohort with worst-source timely delivery below 0.8 is required by the coupled controller, or a received source report no older than eight seconds with at least twenty current-version MAC completions and at least twenty percent failures. Complete received denominators, and at least twenty offered packets per source, are required by the service cohort. This admission predicate differs from the source's local pacing trigger. Recovery is not authorized by unknown service, by an absent relay report, or by congestion alone. A useful action can therefore be postponed by the rule when a source cannot report its own impairment.

### 4.3 Three bounded observation changes

In Full v2, routing-view validity follows the sampled report period: sixteen seconds after a fifteen-second advertisement, and eight after a five-second one. Because a source may lengthen its period at the next poll without transmitting a schedule change, the gateway can expire a view while an allowed schedule is still followed. An expanded routing view remains an old observation. It is not proof of current health.

Horizon applies sixteen-second validity to every paced source report and retains the eight-second rules for transmission-failure evidence and installation confirmation. Cohort additionally uses the latest two consecutive closed generation buckets actually received for both sources when recent denominators are incomplete, under the epoch, count, maturation, and age bounds in Table 1; historical buckets are never relabeled as unobserved current service. Closing may interrupt a pending feedback transaction when a qualified cohort that begins after that transaction establishes poor service. A reward is not created. An update is not created. Table 2 orders the treatments. Identical native reporting, budgets, wire formats, and path scores are used; closed-loop traces may still diverge.

| Treatment | Byte budget and pacing | Positive-evidence admission | Source routing view | Additional received cohort | Qualified transaction closure |
|---|---|---|---|---|---|
| Legacy | Original | Original admission | Original rules | No | No |
| Full v2 | Enabled | Enabled | 8 or 16 s by sampled period | No | No |
| Horizon | Enabled | Enabled | 16 s | No | No |
| Cohort | Enabled | Enabled | 16 s | Two bounded closed buckets | No |
| Closing | Enabled | Enabled | 16 s | Two bounded closed buckets | Yes |

### 4.4 Received-only historical service audit

After the failed screen had been inspected, an offline audit was applied to the existing traces. Whether the gateway had received enough information for a historical service calculation after partial installation was the question. No controller action is changed by the audit. No network transmission is changed. The existing sixteen-second source-view limit, two consecutive five-second buckets, twenty-second maximum cohort-end age, 200 ms delivery maturation, and twenty offered packets per source are retained. Counts are indexed by source, reported version, and generation bucket. Only closed buckets at or after the received version-epoch certificate are contributed by a report. Each reported version must also occur in an installation command already known to the controller, or in its known initial configuration.

The latest pair of consecutive buckets available for both reported source versions is selected by the audit. Their start is no earlier than either source's certified epoch. Their end precedes the decision by at least the timely-delivery deadline and is at most twenty seconds old. Source numerators are taken from timely arrivals already observed by the gateway for those generation buckets. Different reported versions may be held by the two sources. A desired version is never substituted by the audit for a reported one.

Under monotonically increasing installation versions and correct received epoch certificates, the historical cohort is identified by these conditions. Confirmation of the latest joint update is not required. Packets generated after a version's installation epoch and before the report timestamp are described by a closed count reported under that version. An intervening later version, followed by a return to the reported version, is prevented by monotonic versions. The denominator of each source is identified when the argument is applied independently. Timely numerators are fixed before the decision by the shared maturation condition. Past packets are identified. Current route health is not established, and neither is the outcome of a subsequent installation. Each reconstructed count is checked against native packet-generation versions, separately from the received-only calculation.

### 4.5 Conditional recovery eligibility

A post-bootstrap decision time, after installation waiting has ended, is considered. Confirmation means that the latest joint installation is marked confirmed. Route consistency means that each reported source version maps to its desired current route. The implemented historical-service predicate is known only if both conditions hold and its received-count conditions are satisfied. Recovery is admitted only if known service is poor, or if an eligible source-local MAC-failure report is present.

If the joint installation remains unconfirmed, and if no source-local failure report meets the age, version, and completion-count conditions, the historical-service predicate is unknown. Both branches of recovery admission are then false. Candidates and byte credit alone cannot authorize a recovery action. While those two premises hold, the implication is left unchanged by ending the installation wait, by extending a source-view lifetime, or by making additional closed buckets available. The implication follows by substitution of the unknown service predicate and the ineligible failure report into the two recovery branches. The argument is conditional and is tied to this implementation. A general impossibility theorem is not obtained.

The block can be ended if later confirmations satisfy the joint contract, or if the second branch is activated by an eligible failure report. A controller bound by a different contract could leave this condition. The outcome of that change would require a separate execution. If confirmation becomes available while reported paths still disagree with the desired route pair, route consistency remains a further condition. Deletion of the global confirmation test alone does not reconcile the observed and desired configurations. The premises are checked in Section 6.4 against the finite recorded trajectory. That no escape can ever occur is not inferred.

## 5 Experimental questions and analysis

Two bounded questions are answered by the screen. Does the combined communication and admission mechanism satisfy its intended service and control-byte tradeoff in the selected development settings? Do successively broader uses of received observations recover that tradeoff? The combined intervention is estimated by Legacy versus Full v2. Byte budgeting cannot be isolated from pacing or from admission by that contrast. The specified observation changes inside the combined mechanism are examined by Horizon versus Full v2, by Cohort versus Horizon, and by Closing versus Cohort.

Forty native cases are contained in the matrix: two sizes, two workloads, two input seeds, and five treatments. Eight matched size/workload/input cells are represented by those forty configurations, with two input seeds and one layout-generation seed. Forty independent repetitions are not constituted. The screen is small and developmental, so paired values and descriptive means are reported. Population confidence intervals and significance tests are not. The limited replication would not be repaired if packets or controller ticks were pooled as independent samples.

For each source, full-run service is unique packets delivered within 200 ms, divided by all generated packets during 330 s. The primary endpoint is the smaller of the two source rates. Bootstrap, waiting, failed recovery, and missing-feedback periods are included. Actual report and installation MAC DATA PSDU bytes, at every hop and attempt, are summed as the control cost. The physical layer (PHY) preamble and header are excluded. Acknowledgments, application DATA, and modeled radio energy are accounted separately; the radio current model and related constants are archived with the replication package [9].

Each candidate was required, by the prospective screen, to maintain mean service within minus 0.5 percentage points of Legacy and to reduce mean control DATA by at least twenty percent at both sizes. An overall mean service increase of at least 0.5 points over Full v2 was also required. The selection order was Horizon, then Cohort, then Closing. Failure of all three ends this method-revision family. These are development selection criteria. They are not statistical noninferiority tests. The criteria were not relaxed after the outcomes had been observed. No independent confirmation was started for an unselected candidate.

Existing records only are used by the subsequent diagnosis. Arrival and coordinate hashes are verified across all five treatments in each matched cell. Legacy and Full v2 are read, at packet level, in all eight cells. The three repair records are read in the largest adverse cell. Nineteen protocol traces are obtained. Generation-time intervals follow the existing removal schedule; in overload they are reference intervals only. The largest adverse cell was selected after the outcomes. Prevalence of the mechanism is not estimated by that diagnosis. Interval contribution formulas and the worst-source identity correction are archived with the replication package.

Native traces, offered arrivals, coordinates, controller transcripts, and configuration/source hashes are preserved for each case. Native and received-evidence audits reconstruct service and DATA counts, reservations, attempt limits, received report fields, and post-bootstrap admission predicates. Screen decisions are recomputed from the committed manifest, metrics, registration, and admission audit. Execution used one pinned runner binary for all forty treatments; payload hashing and storage encoding checks are archived with the replication package. Preparation assistance is disclosed in the Acknowledgment. No language model is invoked by the experimental controller or by the simulator.

## 6 Results

### 6.1 Accounting and execution

All forty cases were completed, and the native and received-evidence audits were passed. The per-node transmitted control-DATA bound was satisfied by the thirty-two budget-enabled cases. Offered packet counts agree across all five treatments in each matched cell. All recorded learning-update vectors are zero. Faithful accounting and execution of the specified experiment are established by these checks. Effectiveness of the recovery policy is not.

Admission checks, including rejected requests, are counted by the existing audit field named budget_admissions. The original records are retained. Admitted requests are obtained by subtraction of the rejections. At ten nodes, 2623 checks with 28 rejections are made by Full v2 across four cases. At twenty nodes, 4350 checks with 644 rejections are made. These are repeated request counts. They are not independent outcomes. More control-request denials against the configured allowance are indicated at twenty nodes. Channel contention is not measured, and the cause of each application loss is not identified.

### 6.2 Joint service and communication outcome

Both sizes and all four candidates are kept in Table 3 and Fig. 1. At ten nodes the mean service changes are minus 10.78, minus 10.31, minus 9.52, and minus 8.83 points, all left of the frozen minus-0.5 line, while mean control-DATA reductions are 23.02, 22.80, 22.61, and 22.14 percent, just right of 20 percent. At twenty nodes the four treatments share one pair of full-run endpoints: plus 1.51 service points and a 35.27 percent DATA reduction. None of the three repairs passes the complete screen.

| Nodes | Treatment | Service versus Legacy pp | Control DATA reduction percent | Service versus Full v2 pp |
|---|---|---:|---:|---:|
| 10 | Full v2 | -10.78 | 23.02 | 0.00 |
| 10 | Horizon | -10.31 | 22.80 | +0.47 |
| 10 | Cohort | -9.52 | 22.61 | +1.26 |
| 10 | Closing | -8.83 | 22.14 | +1.95 |
| 20 | Full v2 | +1.51 | 35.27 | 0.00 |
| 20 | Horizon | +1.51 | 35.27 | 0.00 |
| 20 | Cohort | +1.51 | 35.27 | 0.00 |
| 20 | Closing | +1.51 | 35.27 | 0.00 |

The strongest single adverse cell is the ten-node removal workload with input seed 2026101511. Legacy worst-source service is 86.97 percent; Full v2 and every repair reach 59.29 percent, a 27.69-point loss unchanged by the repair sequence. Localized gains elsewhere—Cohort by 3.15 points over Full v2 on the second removal input, and Closing by 4.65 points on one overload input—raise some repair averages without meeting the joint criterion. Matched-cell markers and the removal-versus-overload split behind the ten-node DATA means are noted in the Fig. 1 caption; full paired values are archived with the replication package.

![Fig. 1 Paired service and control-DATA effects relative to Legacy for four matched cells per size (teal: removal; brown: overload), with diamonds as means and dotted lines as frozen development criteria, not confidence limits. At ten nodes one removal cell lies at minus 27.69 service points on every treatment row; DATA reductions straddle 20 percent by workload. At twenty nodes all four treatments share the plotted endpoints](figures/Fig1.png)

### 6.3 Historical evidence and recovery decisions

Controller snapshots with a qualified service calculation, and post-bootstrap decisions admitted by the positive-evidence predicate, are counted in Table 4. At ten nodes, 75 qualified snapshots are recorded for Full v2 across four cases, against 172 for Legacy. The count is raised by Cohort and Closing to 173 and 175. At twenty nodes the count is raised from 72 under Full v2 to 240 under either cohort-based variant. Availability of the specified historical calculation is shown by the larger counts. Accuracy about unobserved current service is not.

| Nodes | Treatment | Qualified service snapshots | Post-bootstrap gated decisions |
|---|---|---:|---:|
| 10 | Legacy | 172 | Not applicable |
| 10 | Full v2 | 75 | 15 |
| 10 | Horizon | 71 | 16 |
| 10 | Cohort | 173 | 16 |
| 10 | Closing | 175 | 16 |
| 20 | Legacy | 226 | Not applicable |
| 20 | Full v2 | 72 | 0 |
| 20 | Horizon | 72 | 0 |
| 20 | Cohort | 240 | 0 |
| 20 | Closing | 240 | 0 |

Qualified historical snapshots are more numerous at twenty nodes. No post-bootstrap gated decision is made by any budget-enabled variant, and the service and byte endpoints remain identical. At ten nodes, the total number of qualified service snapshots is not increased by extending routing-view validity alone. The closed-loop trajectory and the version epochs can change. The original recent-cohort requirements remain strict. Observation availability, decision eligibility, and realized service are distinct quantities in these runs.

Mean modeled total radio energy is slightly greater than Legacy for each budget-enabled treatment at each size. A small decrease is present in some individual pairs. Listening and application traffic remain inside the radio model. An energy saving is not established by the control-byte reductions. No network-lifetime claim is made.

### 6.4 Partial installation and recovery eligibility

The largest loss is localized by the selected adverse cell. After relay 6 is removed at 225 s, source 0 under Full v2 generates 1166 version-2 packets on route 0–8–6–9, and none arrives on time. Legacy had already installed route 0–4–5–9 at approximately 215 s and delivers 1071 of the same 1166 packets on time; its advantage is therefore not faster detection and recovery after that removal.

An updated route pair is issued at 235 s and retried at 240 s. Both source-0 requests pass byte-credit admission, yet their gateway MAC jobs end with CHANNEL_ACCESS_FAILURE (status 225) and zero DATA attempts [8]. Source 1 installs version 3 at approximately 240.036 s. At 245 s the transaction closes as abandoned and unconfirmed while source 0 still reports version 2. Insufficient byte credit does not explain those source-0 failures.

From 245 through 315 s, fifteen decision checks by each of Horizon, Cohort, and Closing find candidate routes available, but the service predicate returns installation_unconfirmed and no eligible source-local MAC-failure report is present, so recovery remains rejected after waiting has ended. Full v2 likewise rejects all fifteen checks, five with installation unconfirmed and ten with missing-source service. Fig. 2 summarizes this confirmation-contract lockout. Release could still follow a later eligible failure report, or a later confirmation.

A received-only audit separates that eligibility block from an absence of useful counts. At 265 s, received versions 2 and 3 with buckets 50 and 51 yield offered counts [36, 60] and timely counts [0, 59] under valid epoch certificates. Eleven of the fifteen post-exit checks support such a historical deficit; every reconstructed count matches native generation and delivery records. These eleven checks are repeated historical observations, not independent replications. The audit executes no route change, so no repaired-policy service benefit is estimated. Interval-wise source contributions and the worst-source identity correction are archived with the replication package.

![Fig. 2 Recovery sequence in the selected ten-node adverse cell: removal at 225 s, admitted yet channel-failed installation attempts at 235–240 s, unconfirmed exit at 245 s, and fifteen blocked checks with candidates present. The received-only window at 265 s is an offline calculation with no executed recovery](figures/Fig2.png)

## 7 Discussion

A checkable bound for one defined traffic class is supplied by the reservation rule. The measured drop in control bytes is consistent with that accounting aim. A passed byte audit is not, by itself, evidence of service-preserving recovery. That is what the failed joint criterion shows. Whether the remaining transmissions still carry usable feedback is left open by a bound on one transmitted class. The gap is made concrete by the ten-node DATA panel. Removal circles lie to the right of the 20 percent line. Overload circles lie to the left of it. The diamond, which is the quantity tested by the screen, sits just to the right of the line. The gap remains after every protocol audit has been passed. For a communication and control study, that separation is the usable result. A byte account can be rechecked. A service gate can stay shut after waiting has ended. Both are present in the same traces.

A more specific account of the largest adverse input is given by the targeted diagnosis. The source 0 installation requests are admitted by byte credit. Transmission is prevented by channel access. A global confirmation condition is left unsatisfied by the closed partial transaction. With the longer source view, the later block persists. Candidates are available, and received counts sufficient for a bounded historical calculation are also available. The recovery threshold is not met by the recorded source-local failures, even while end-to-end delivery is zero. An end-to-end service certificate is not replaced, in this case, by source-local transmission success.

That condition is not addressed by the received-cohort variants. Their additional historical windows are considered only after the earlier installation and route-consistency checks. Observed source states would still have to be reconciled, by a controller that kept them as a vector, with its desired route pair. That reconciliation is not implemented by deletion of the global confirmation check alone. A past deficit can be identified from received records. That much is established by the shadow audit. Whether use of the deficit produces a successful and affordable installation would have to be determined by a separate closed-loop intervention. The failed repair selection is retained. No such performance claim is made.

A universal scaling law cannot be established by the comparison between sizes. One different layout is used at each size, and the catalog construction also differs between ten and twenty nodes. A higher reporting population therefore occurs together with additional forwarding alternatives and with a different geometry. A population-level recommendation to add relays is not validated by the positive twenty-node result. Average deployment damage is not estimated by the negative ten-node result.

The screen is small, and it is developmental, by design. Multiple configurations are spanned by the same two input identifiers, and bucket observations overlap in time. Those dependencies are kept visible. Packet counts, snapshots, and configuration counts are not used as a nominal sample size. The documented adverse behavior, and the failure of these three repairs on the specified inputs, are supported. General noninferiority is not established. Effective alternatives are not ruled out. Behavior across unseen deployment families is not quantified.

For the policy that was implemented, the separation between a byte bound and a service requirement is what is retained. Evidence age and installation epochs have to be represented explicitly by a controller that consumes intentionally sparse feedback. Broader historical evidence is to be evaluated through complete application outcomes. Practical recovery value can be overstated if only the count of usable windows is increased. This repair sequence is stopped by the registered failure. Repeated parameter changes on the same inputs are not motivated.

The design implication follows from the conditional argument in Section 4.5. An explicit post-exit interpretation is needed, by a bounded transaction, of the source states that were actually observed. Otherwise eligibility can continue to be controlled by an unconfirmed joint target after the wait to which it belonged has ended. A control contract is what is implicated. How often the problem occurs is not estimated. Identifiable history is distinguished by the source/version audit from unknown history, under the stated certificates. Reconfiguration on every historical deficit is not a tested recommendation.

## 8 Conclusion

In forty native development simulations, the targeted traffic of complete control-DATA reservation is reduced, while service outcomes differ between the two fixed layouts. The frozen joint criterion is met by none of the three observation repairs. A specific failure chain is identified by the existing traces. Installation of one source is prevented by channel access. The bounded transaction exits partially confirmed. Later recovery is suppressed by a global evidence predicate. Why the gate need not be reopened by the end of waiting, or by added observations, is explained by the conditional eligibility argument. Eleven historical deficit windows are reconstructed by a source/version-indexed audit from information already received, and are matched independently to native packets. A limitation of the implemented confirmation contract is identified by the negative result, together with the explicit conditions under which the observed block persists. General inferiority of sparse reporting is not established. Failure prevalence is not established. The service benefit of a replacement control policy is not established.

## Acknowledgment

OpenAI Codex [10] was used only for language polishing of the manuscript text. The authors reviewed all polished text and accept full responsibility for the content of the paper.

## Funding

No specific funding was received for this work.

## Author contributions

Contribution to the paper is confirmed as follows. Conceptualization was carried out by Ya-Yu Zhang, Shu-Chuan Chu, and Jeng-Shyang Pan. Methodology was carried out by Ya-Yu Zhang, Shu-Chuan Chu, and Zhenyu Meng. Software was carried out by Ya-Yu Zhang. Validation was carried out by Ya-Yu Zhang, Zhenyu Meng, and Zhao Jia. Formal analysis was carried out by Ya-Yu Zhang and Zhenyu Meng. Investigation was carried out by Ya-Yu Zhang and Zhao Jia. Resources were provided by Jeng-Shyang Pan. Data curation was carried out by Ya-Yu Zhang. Visualization was carried out by Ya-Yu Zhang and Zhao Jia. The original draft was prepared by Ya-Yu Zhang. Review and editing were carried out by Ya-Yu Zhang, Shu-Chuan Chu, Zhenyu Meng, Zhao Jia, and Jeng-Shyang Pan. Supervision was provided by Shu-Chuan Chu and Jeng-Shyang Pan. Project administration was carried out by Shu-Chuan Chu. The results were reviewed by all authors, and the final version of the manuscript was approved by all authors.

## Conflicts of interest

The authors declare that they have no conflicts of interest.

## Data availability

The analysis scripts, observation-controller sources, registration and screen records for the forty cases, numerical summaries, and figures supporting the findings are publicly available at https://github.com/ya-yu-zhang/wsn-recovery-lockout-nr. Running the included analysis script on these records reproduces the reported screen decisions. The native packet-level archive (about 676 MB), from which the reported counts were taken, and the pinned simulation driver are available from the corresponding author upon reasonable request; the archive is identified by SHA256 fdf083436532c88613103363ea548f243cae0b5b525ab1cbc656ffa7d865674d.

## References

[1] P. Levis, T. Clausen, J. Hui, O. Gnawali, and J. Ko, "The Trickle Algorithm," RFC 6206, Mar. 2011, doi: 10.17487/RFC6206.

[2] J. Heinanen and R. Guerin, "A Single Rate Three Color Marker," RFC 2697, Sep. 1999, doi: 10.17487/RFC2697.

[3] J. Paek and R. Govindan, "RCRT: Rate-controlled reliable transport for wireless sensor networks," in Proc. ACM SenSys, 2007, pp. 305–319, doi: 10.1145/1322263.1322293.

[4] G. Jeong, M. Park, and J. Paek, "A2-Trickle: Adaptive & Aligned Trickle for Rapid and Reliable Dissemination in Low-Power Wireless Networks," IEEE Access, vol. 8, pp. 214374–214382, 2020, doi: 10.1109/ACCESS.2020.3040160.

[5] J. Ock, H. Kim, H.-S. Kim, J. Paek, and S. Bahk, "Low-Power Wireless With Denseness: The Case of an Electronic Shelf Labeling System—Design and Experience," IEEE Access, vol. 7, pp. 163887–163897, 2019, doi: 10.1109/ACCESS.2019.2950886.

[6] M. Trobinger, G. de Albuquerque Gleizer, T. Istomin, M. Mazo Jr., A. L. Murphy, and G. P. Picco, "The Wireless Control Bus: Enabling Efficient Multi-Hop Event-Triggered Control with Concurrent Transmissions," ACM Trans. Cyber-Phys. Syst., vol. 6, no. 1, Art. no. 4, 2022, doi: 10.1145/3485467.

[7] M. Reitblatt, N. Foster, J. Rexford, C. Schlesinger, and D. Walker, "Abstractions for network update," in Proc. ACM SIGCOMM, 2012, pp. 323–334, doi: 10.1145/2342356.2342427.

[8] ns-3 Project, "ns-3.44 model library and source release," 2025. Accessed: Oct. 16, 2026. [Online]. Available: https://www.nsnam.org/releases/ns-3-44/

[9] Texas Instruments, "CC2420 2.4 GHz IEEE 802.15.4 / ZigBee-ready RF Transceiver," SWRS041C, 2013. [Online]. Available: https://www.ti.com/lit/ds/symlink/cc2420.pdf

[10] OpenAI, "Codex." Accessed: Oct. 20, 2026. [Online]. Available: https://openai.com/codex

## Biographies

Shu-Chuan Chu received the Ph.D. degree in 2004 from the School of Computer Science, Engineering, and Mathematics, Flinders University of South Australia. She joined Flinders University in December 2009 after nine years at Cheng Shiu University, Taiwan. She has been a Research Fellow and Associate Professor in the College of Science and Engineering, Flinders University, Australia, since December 2009. From September 1, 2019, to August 31, 2024, she was Professor and Doctoral Supervisor in the School of Computer Science and Engineering, Shandong University of Science and Technology. Since September 1, 2024, she has been Professor and Doctoral Supervisor in the School of Artificial Intelligence/School of Future Technology, Nanjing University of Information Science and Technology. Her research interests include swarm intelligence, intelligent computing, and wireless sensor networks.

Ya-Yu Zhang has been a master's student in the School of Computer Science, Nanjing University of Information Science and Technology, Nanjing, China, since September 2024. Biography to be completed by the author.

Zhenyu Meng is with the School of Computer Science and Software, Zhaoqing University, Zhaoqing 526061, China. Biography to be completed by the author.

Zhao Jia received the Ph.D. degree from Hohai University, Nanjing, China. His research interests include evolutionary computation, pattern recognition, and big data analysis. Biography to be completed by the author.

Jeng-Shyang Pan was affiliated with the Department of Electrical Engineering, University of Edinburgh, from October 1993 to June 1996. The public ORCID record lists research interests in computational intelligence, information hiding, image signal processing, and wireless sensor networks. Biography to be completed by the author.
