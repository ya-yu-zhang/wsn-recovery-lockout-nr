# Discovery and Analysis of Recovery Lockout in Sparse-Feedback Wireless Sensor Networks: A Negative Result Study on Observation Repairs

## Authors

Shu-Chuan Chu^1,2^, Ya-Yu Zhang^1^, Chih-Cheng Chen^3^, Zhenyu Meng^4^, and Jeng-Shyang Pan^1,2,5,6^

^1^School of Computer Science, Nanjing University of Information Science and Technology, Nanjing 210044, China

^2^School of Artificial Intelligence/School of Future Technology, Nanjing University of Information Science and Technology, Nanjing 210044, China

^3^Department of Automatic Control Engineering, Feng Chia University, Taichung City 407102, Taiwan

^4^School of Computer Science and Software, Zhaoqing University, Zhaoqing 526061, China

^5^Department of Information Management, Chaoyang University of Technology, Taichung 413310, Taiwan

^6^Faculty of Electrical Engineering and Computer Science, VSB-Technical University of Ostrava, 708 00 Ostrava, Czech Republic

Corresponding author: Jeng-Shyang Pan (e-mail: 100112@nuist.edu.cn).

## Abstract

On a shared low-power wireless medium, minimizing control-traffic overhead is typically expected to enhance performance. However, this paper demonstrates a counterintuitive phenomenon in wireless sensor networks: reducing control-byte overhead does not guarantee that evidence-qualified routing recovery remains functional, and it can induce a severe recovery lockout. We examine a wireless sensor network gateway controller that couples sparse source reporting, per-hop control-byte reservation, and positive received evidence to gate routing recovery. In a prospectively registered evaluation of forty matched cases spanning two network sizes, two workloads, and two shared input seeds, we compare the coupled mechanism (Full v2) with the original controller (Legacy). Full v2 reduces control-frame bytes by a mean of 35.27% at twenty nodes, but at ten nodes it lowers mean worst-source timely service by 10.78 percentage points. Three pre-specified observation repairs--extending routing-view lifetimes, introducing historical service cohorts, and implementing qualified transaction closures--all fail the frozen joint criteria. Guided by this negative result, we conduct an exploratory packet-level diagnosis of the worst cell traces to trace the failure chain. The analysis disentangles byte-budget admission from channel-access failures and shows how a global confirmation contract can hold the recovery gate in an "unknown" state after a bounded installation wait ends, despite available candidate routes and identifiable historical deficits. The primary contribution is isolating and verifiably documenting this confirmation-contract lockout, supported by a public repository of analysis scripts and records that marks an empirical boundary for sparse-feedback wireless sensor network controller designs.

Keywords: wireless sensor networks, routing recovery, control traffic, negative results, reproducible simulation, confirmation contract

## 1 Introduction

Application packets, and the measurements by which their routes are managed, are carried by a wireless sensor network (WSN) over the same medium. Capacity can be released when reports are suppressed. The same suppression can delay installation confirmation and can remove the observations by which recovery is authorized. When the reporting policy is changed, the information supplied to the controller is changed with it. The coupling matters once application data and multihop control messages contend for one finite request queue.

Ways of reducing communication are already available in adaptive dissemination and in traffic metering. Transmission intervals are adjusted by Trickle from local consistency [1]. Rate and burst allowances are expressed by token-based metering [2]. Feedback and shared-medium load are also related by reliable sensor-network transport [3]. A narrower question is raised by these mechanisms. When routing recovery depends on received evidence, is the service of the application that supplies that evidence preserved by a verified reduction in control DATA, meaning the bytes carried in medium-access-control data frames? Judging recoverability from control-byte savings, or from qualified snapshots alone, can mislead.

An implementation with two application sources and a gateway controller is studied. Complete control-request reservation at every hop is combined with protected admission for selected evidence and with source report pacing. After bootstrap, recovery is required to rest on positive received evidence of poor service, or of current-version transmission failures. A missing relay report is not treated as proof of failure. Unqualified reconfiguration is avoided by that choice. A physically damaged route can also be left without enough evidence for a change.

Reducing control-plane traffic is a common way to release capacity on a shared low-power medium [1], [2]. In the controller studied here, that reduction exposes a tension that we call the Sparse-Feedback Paradox: restricting source reporting yields verifiable control-byte savings, but it also thins the stream of received positive evidence that the gateway uses to authorize and validate routing recovery. The gateway can then be left unable either to confirm a current failure or to justify a reconfiguration. The term labels this implementation-level coupling; it is not proposed as a general law. The paper therefore concentrates on a traceable diagnosis of why the registered observation repairs did not remove the block, rather than on further parameter tuning.

The reported experiment was a prospectively registered evaluation of three observation changes. Interpretation of that evaluation as a negative-result mechanism study is exploratory. No successful method was selected. The original service and byte-saving criteria were retained. The existing traces were then diagnosed, so that a lack of received measurements could be separated from a policy that refuses to interpret them.

Recovery lockout after partial route installation is traced at packet and transaction level. Byte-budget admission, channel access, the end of waiting, and permission for a later decision are kept apart. The control-contract conditions under which a timeout leaves the service gate closed are stated, together with the later observations by which the gate can be opened. Historical service is identified from received epoch certificates and from closed generation counts. It is not required that both sources hold the latest desired version. Every reconstructed count in the diagnosed case is checked against native packet records. The service and control-traffic setting is supplied by the forty-case evaluation, and every failed repair selection is kept. The rate-and-burst relation is used only as an accounting check. No gain is claimed for a routing optimizer, or for contextual learning.

The working hypothesis is that a bounded installation wait, together with broader received observations, is sufficient for positive-evidence recovery to remain usable after a partial update. The registered observation repairs do not support that hypothesis: they miss the frozen service and byte criteria. Three properties that are easy to treat as one event are separated by the recorded case. Waiting has stopped. Past service can be calculated. Another action is authorized. The conclusion applies to the confirmation contract that was implemented. Sparse reporting, or conservative admission, is not thereby shown to block recovery in general.

Contributions of This Work.

This paper does not present a new performance optimizer. It documents an empirical and conditional analytical boundary for control-plane reduction in one implemented WSN controller. The contributions are threefold:

1. **Sparse-Feedback Paradox.** We identify and name a trade-off observed in a shared-medium WSN controller: control-traffic suppression that passes its byte audit can starve the gateway of the positive received evidence that its recovery rule requires.

2. **Confirmation-contract lockout.** We state the implemented recovery-admission rule as a conditional proposition (Proposition 1): while the latest joint installation transaction is unconfirmed and no source presents an eligible failure report, observation repairs that leave these two premises unchanged cannot authorize recovery.

3. **Recheckable negative-result record.** We release the forty-case evaluation matrix, together with analysis scripts, registration records, numerical summaries, and figures, in a public repository. The native packet-level archive (about 676 MB) and the pinned simulation driver remain available from the corresponding author upon reasonable request (see Data Availability). The traced confirmation-contract failure chain gives later controller designs a concrete case against which repairs can be rechecked.

## 2 Related work

Redundant dissemination is reduced by Trickle through consistency and interval adaptation [1]. A five-second local poll is used by the sources studied here. A report period of five or fifteen seconds is chosen from installation state, medium access control (MAC) completion, and local contention. The sampled period can be changed at the next poll. An interpretation problem is created for the gateway: the period in the last received report is not a commitment about the next transmission. A full Trickle stack is not implemented, and that name is not assigned by the present comparison to a timer proxy.

Admitted volume is bounded by traffic metering with a replenished allowance [2]. Where the charge is taken determines the bound obtained here. Forwarding and repeated application-level attempts are omitted if only reports generated by a source are counted. A conservative bound over those requests is obtained when a maximum transmission cost is reserved at each control-request admission. Sensor transport is addressed by Rate-Controlled Reliable Transport (RCRT) [3]. The endpoint considered here is timely application service, while the same medium is consumed by routing control.

Transmission-interval overlap and suppression bottlenecks in low-power dissemination are identified by A²-Trickle, with evaluation in simulation and on a device testbed [4]. Propagation under Trickle is its subject. Contending unicast management is examined here, and the diagnosed restriction is the gateway's interpretation of partially installed source versions. The pacing rule is not treated as Trickle. No measured comparison with A²-Trickle is claimed.

Persistent failures in a dense electronic shelf-labeling deployment were used to guide gateway changes [5]; that single-hop scheduled setting differs from the present multihop simulation, but shares the narrower point that a concrete failure should be located along the communication and management path before it is attributed to an optimizer. Event-triggered concurrent-transmission control [6] and network-update abstractions that separate desired from installed configurations [7] likewise motivate examining sparse reports and partial source versions. Per-packet consistency for distributed updates is not claimed, and a successful replacement policy is left unresolved.

Collection-tree and IPv6 routing for low-power networks provide complementary baselines for multihop delivery under lossy links [8], [9]. Those stacks emphasize distributed path selection and trickle-style consistency; they do not examine a centralized confirmation contract that gates recovery on jointly confirmed installations after sparse reports. IEEE 802.15.4 remains the shared medium model used here [10]. Contiki/uIP-class stacks and early low-power OS designs similarly treat control and data on one radio path [11], [12]. Classical surveys of WSN routing and deployment constraints likewise emphasize energy and topology limits without analyzing confirmation-gated recovery after partial installation [13], [14]. Time-slotted and industrial low-power variants further reduce contention by scheduling [15]; the standardization path toward these low-power routing and scheduling stacks is reviewed in [16]. Scheduled access is outside the unscheduled first-in, first-out (FIFO) contention model studied here. Software-defined sensor-network control likewise motivates separating desired from installed state, but does not isolate the present confirmation-contract lockout [17].

Prior work from the authors' group has applied evolutionary search to WSN localization and fault detection [18], [19]. Those studies target optimization, deployment accuracy, or anomaly classification. The present negative-result study is complementary: it does not propose a superior optimizer. It documents how a sparse-feedback confirmation contract can freeze recovery after a partial installation, even when candidate routes and historical deficits are identifiable offline.

Recent advanced controllers in WSNs have explored adaptive mechanisms that balance control overhead against topology reconfiguration or routing efficiency [20], [21], yet they typically assume continuous or regularly synchronized feedback rather than evidence-qualified recovery after a partial installation under sparse source reporting.

## 3 Network and observed evidence

### 3.1 Native model and workloads

ns-3.44 is used [22]. Sources are nodes 0 and 1; the gateway remains node 9 at both sizes. Additional nodes are forwarding and reporting relays, so twenty-node layouts add candidate relays and reporting load without adding application flows. One fixed evaluation layout per size, from layout seed 2026101501, is used. Geometry controls and the pinned simulator revision are available in the public repository (Supplementary Notes S1; see Data Availability).

IEEE 802.15.4 carrier assessment, contention, acknowledgments, and up to two retries after an initial MAC attempt are modeled. Application packets and control requests share a FIFO of capacity sixteen. Positions remain fixed until a scheduled relay removal. The main fixed settings are listed in Table I; channel and scaffold details are available in the public repository (Supplementary Notes S1; see Data Availability).

Table 1. Fixed Network and Observation Settings.

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

Let $A_i(t)$ denote cumulative reserved bytes and $C_i(t)$ the actual control DATA bytes transmitted by node i through time t. Nonnegative credit with a full initial bucket gives the classical bound (1).

$$ C_i(t) \le A_i(t) \le B + r t $$

Bound (1) holds because every actual control DATA attempt belongs to a reserved request, and the maximum attempts and frame size of that request are covered by the reservation. Which requests can use credit is changed by protection. The bound is not enlarged. The reasoning applies to transmitted MAC DATA protocol service data units (PSDUs). No bound is made on acknowledgments, receive time, service, or energy.

### 4.2 Source pacing and evidence-qualified recovery

A poll is made by a source every five seconds. A five-second period is chosen during the fifteen seconds after local installation, when at least ten current-version MAC completions show more than twenty percent failure, or when the local queue and contention state changes. Otherwise a fifteen-second period is chosen. A report is emitted only if the selected interval has elapsed. Deterministic input-dependent phases are identical across treatments.

After bootstrap, a known service cohort with worst-source timely delivery below 0.8 is required by the coupled controller, or a received source report no older than eight seconds with at least twenty current-version MAC completions and at least twenty percent failures. Complete received denominators, and at least twenty offered packets per source, are required by the service cohort. This admission predicate differs from the source's local pacing trigger. Recovery is not authorized by unknown service, by an absent relay report, or by congestion alone. A useful action can therefore be postponed by the rule when a source cannot report its own impairment.

### 4.3 Three bounded observation changes

In Full v2, routing-view validity follows the sampled report period: sixteen seconds after a fifteen-second advertisement, and eight after a five-second one. Because a source may lengthen its period at the next poll without transmitting a schedule change, the gateway can expire a view while an allowed schedule is still followed. An expanded routing view remains an old observation. It is not proof of current health.

Horizon applies sixteen-second validity to every paced source report and retains the eight-second rules for transmission-failure evidence and installation confirmation. Cohort additionally uses the latest two consecutive closed generation buckets actually received for both sources when recent denominators are incomplete, under the epoch, count, maturation, and age bounds in Table I; historical buckets are never relabeled as unobserved current service. Closing may interrupt a pending feedback transaction when a qualified cohort that begins after that transaction establishes poor service. A reward is not created. An update is not created. Table II orders the treatments. Identical native reporting, budgets, wire formats, and path scores are used; closed-loop traces may still diverge.

Table 2. Matched Communication and Observation Treatments.

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

### 4.5 Formalization of Recovery Eligibility and Lockout

A post-bootstrap decision time after installation waiting has ended is considered. Let T ∈ {Confirmed, Unconfirmed} denote the state of the latest joint installation transaction, and let F_s ∈ {Eligible, Ineligible} denote whether source s presents an eligible local MAC-failure report under the age, version, and completion-count conditions. Let Ψ(T, {F_s}) be the global service predicate implemented by the controller. Route consistency further requires that each reported source version maps to its desired current route; the historical-service calculation is known only when T = Confirmed, route consistency holds, and the received-count conditions are satisfied.

**Proposition 1 (Confirmation-Contract Lockout Boundary).** *If T = Unconfirmed and F_s = Ineligible for every source s, then Ψ(T, {F_s}) = Unknown. Define the recovery authorization indicator Φ(Ψ, {F_s}) ∈ {0, 1} by the implemented two-branch rule: Φ = 1 only if known service is poor, or if at least one source presents an eligible failure report. Under these premises, Φ(Unknown, {Ineligible}_s) = 0.*

**Proof.** Recovery admission is the disjunction of two branches. Branch B1 is true only when Ψ = Poor. Branch B2 is true only when there exists a source s with F_s = Eligible. Under T = Unconfirmed, the implemented predicate returns Ψ = Unknown, so B1 is false. Under F_s = Ineligible for all s, B2 is false. Therefore Φ = B1 ∨ B2 = 0. ∎

The implication is left unchanged by ending the installation wait, by extending a source-view lifetime, or by making additional closed buckets available, while those two premises hold: such observation repairs do not rewrite T or F_s. Candidates and byte credit alone cannot authorize a recovery action. The block can be ended if later confirmations satisfy the joint contract, or if B2 is activated by an eligible failure report. A controller bound by a different contract could leave this absorbing state; the outcome of that change would require a separate execution. If confirmation becomes available while reported paths still disagree with the desired route pair, route consistency remains a further condition. Deletion of the global confirmation test alone does not reconcile the observed and desired configurations. The premises are checked in Section 6.4 against the finite recorded trajectory. That no escape can ever occur is not inferred. The argument is conditional and is tied to this implementation; a general impossibility theorem is not obtained.

## 5 Experimental questions and analysis

Two bounded questions are answered by the evaluation. Does the combined communication and admission mechanism satisfy its intended service and control-byte tradeoff in the selected evaluation settings? Do successively broader uses of received observations recover that tradeoff? The combined intervention is estimated by Legacy versus Full v2. Byte budgeting cannot be isolated from pacing or from admission by that contrast. The specified observation changes inside the combined mechanism are examined by Horizon versus Full v2, by Cohort versus Horizon, and by Closing versus Cohort.

Forty native cases are contained in the matrix: two sizes, two workloads, two input seeds, and five treatments. Eight matched size/workload/input cells are represented by those forty configurations, with two input seeds and one layout-generation seed. Forty independent repetitions are not constituted. The evaluation matrix is small and limited-scale, so paired values and descriptive means are reported. Population confidence intervals and significance tests are not. The limited replication would not be repaired if packets or controller ticks were pooled as independent samples.

For each source, full-run service is unique packets delivered within 200 ms, divided by all generated packets during 330 s. The primary endpoint is the smaller of the two source rates. Bootstrap, waiting, failed recovery, and missing-feedback periods are included. Actual report and installation MAC DATA PSDU bytes, at every hop and attempt, are summed as the control cost. The physical layer (PHY) preamble and header are excluded. Acknowledgments, application DATA, and modeled radio energy are accounted separately; the radio current model and related constants are available in the public repository (Supplementary Notes S2; see Data Availability) [23].

Each candidate was required, by the prospective evaluation, to maintain mean service within minus 0.5 percentage points of Legacy and to reduce mean control DATA by at least twenty percent at both sizes. An overall mean service increase of at least 0.5 points over Full v2 was also required. The selection order was Horizon, then Cohort, then Closing. Failure of all three ends this method-revision family. These are algorithmic screening criteria. They are not statistical noninferiority tests. The criteria were not relaxed after the outcomes had been observed. No independent confirmation was started for an unselected candidate.

Existing records only are used by the subsequent diagnosis. Arrival and coordinate hashes are verified across all five treatments in each matched cell. Legacy and Full v2 are read, at packet level, in all eight cells. The three repair records are read in the largest adverse cell. Nineteen protocol traces are obtained. Generation-time intervals follow the existing removal schedule; in overload they are reference intervals only. The largest adverse cell was selected after the outcomes. Prevalence of the mechanism is not estimated by that diagnosis. Interval contribution formulas and the worst-source identity correction are available in the public repository (Supplementary Notes S4; see Data Availability).

Native traces, offered arrivals, coordinates, controller transcripts, and configuration/source hashes are preserved for each case. Native and received-evidence audits reconstruct service and DATA counts, reservations, attempt limits, received report fields, and post-bootstrap admission predicates. Screen decisions are recomputed from the committed manifest, metrics, registration, and admission audit. Execution used one pinned deterministic simulation execution environment for all forty treatments; payload hashing and storage encoding checks are available in the public repository (Supplementary Notes S3; see Data Availability). Preparation assistance is disclosed in the Acknowledgment. No language model is invoked by the experimental controller or by the simulator.

## 6 Results

### 6.1 Accounting and execution

All forty cases were completed, and the native and received-evidence audits were passed. The per-node transmitted control-DATA bound was satisfied by the thirty-two budget-enabled cases. Offered packet counts agree across all five treatments in each matched cell. All recorded learning-update vectors are zero. Faithful accounting and execution of the specified experiment are established by these checks. Effectiveness of the recovery policy is not.

![Fig. 1 Paired service and control-DATA effects relative to Legacy for four matched cells per size. Circles denote relay-removal workloads and squares denote overload; filled versus open markers distinguish the two shared input seeds; open diamonds are four-cell means. Pink Lockout Zone shading marks service change ≤ −0.5 percentage points (the frozen service criterion); gray shading marks control-DATA reduction < 20%. Dotted lines are the frozen evaluation criteria, not confidence limits. Panels: (a)/(b) ten nodes; (c)/(d) twenty nodes. At ten nodes one removal cell lies at −27.69 service points on every treatment row; DATA reductions straddle 20% by workload. At twenty nodes all four treatments share the plotted endpoints.](figures/Fig1.png)

Admission checks, including rejected requests, are counted by the existing audit field named budget_admissions. The original records are retained. Admitted requests are obtained by subtraction of the rejections. At ten nodes, 2623 checks with 28 rejections are made by Full v2 across four cases. At twenty nodes, 4350 checks with 644 rejections are made. These are repeated request counts. They are not independent outcomes. More control-request denials against the configured allowance are indicated at twenty nodes. Channel contention is not measured, and the cause of each application loss is not identified.

### 6.2 Joint service and communication outcome

Both sizes and all four candidates are kept in Table III and Fig. 1. At ten nodes the mean service changes are minus 10.78, minus 10.31, minus 9.52, and minus 8.83 points, all left of the frozen minus-0.5 line, while mean control-DATA reductions are 23.02, 22.80, 22.61, and 22.14 percent, just right of 20 percent. At twenty nodes the four treatments share one pair of full-run endpoints: plus 1.51 service points and a 35.27 percent DATA reduction. None of the three repairs passes the complete evaluation criteria.

Table 3. Descriptive Means Over Four Matched Workload-Input Cells per Size.

| Nodes | Treatment | Service vs. Legacy (pp) | Control DATA reduction vs. Legacy (%) | Service vs. Full v2 (pp) |
|---|---|---:|---:|---:|
| 10 | Full v2 | -10.78 | 23.02 | 0.00 |
| 10 | Horizon | -10.31 | 22.80 | +0.47 |
| 10 | Cohort | -9.52 | 22.61 | +1.26 |
| 10 | Closing | -8.83 | 22.14 | +1.95 |
| 20 | Full v2 | +1.51 | 35.27 | 0.00 |
| 20 | Horizon | +1.51 | 35.27 | 0.00 |
| 20 | Cohort | +1.51 | 35.27 | 0.00 |
| 20 | Closing | +1.51 | 35.27 | 0.00 |

The strongest single adverse cell is the ten-node removal workload with input seed 2026101511. Legacy worst-source service is 86.97 percent; Full v2 and every repair reach 59.29 percent, a 27.69-point loss unchanged by the repair sequence. Localized gains elsewhere--Cohort by 3.15 points over Full v2 on the second removal input, and Closing by 4.65 points on one overload input--raise some repair averages without meeting the joint criterion. Matched-cell markers and the removal-versus-overload split behind the ten-node DATA means are noted in the Fig. 1 caption; full paired values are available in the public repository (Supplementary Notes S5; see Data Availability).

### 6.3 Historical evidence and recovery decisions

Controller snapshots with a qualified service calculation, and post-bootstrap decisions admitted by the positive-evidence predicate, are counted in Table IV. At ten nodes, 75 qualified snapshots are recorded for Full v2 across four cases, against 172 for Legacy. The count is raised by Cohort and Closing to 173 and 175. At twenty nodes the count is raised from 72 under Full v2 to 240 under either cohort-based variant. Availability of the specified historical calculation is shown by the larger counts. Accuracy about unobserved current service is not.

Table 4. Qualified Service Snapshots and Gated Decisions (Four Cases per Size).

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

The largest loss is localized by the selected adverse cell. After relay 6 is removed at 225 s, source 0 under Full v2 generates 1166 version-2 packets on route 0-8-6-9, and none arrives on time. Legacy had already installed route 0-4-5-9 at approximately 215 s and delivers 1071 of the same 1166 packets on time; its advantage is therefore not faster detection and recovery after that removal.

An updated route pair is issued at 235 s and retried at 240 s. Both source-0 requests pass byte-credit admission, yet their gateway MAC jobs end with CHANNEL_ACCESS_FAILURE (status 225) and zero DATA attempts [22]. Source 1 installs version 3 at approximately 240.036 s. At 245 s the transaction closes as abandoned and unconfirmed while source 0 still reports version 2. Insufficient byte credit does not explain those source-0 failures.

From 245 through 315 s, fifteen decision checks by each of Horizon, Cohort, and Closing find candidate routes available, but the service predicate returns installation_unconfirmed and no eligible source-local MAC-failure report is present, so recovery remains rejected after waiting has ended. Full v2 likewise rejects all fifteen checks, five with installation unconfirmed and ten with missing-source service, and finds candidate routes at only five of them. Fig. 2 summarizes this confirmation-contract lockout. Release could still follow a later eligible failure report, or a later confirmation.

A received-only audit separates that eligibility block from an absence of useful counts. At 265 s, received versions 2 and 3 with buckets 50 and 51 yield offered counts [36, 60] and timely counts [0, 59] under valid epoch certificates. Eleven of the fifteen post-exit checks support such a historical deficit; every reconstructed count matches native generation and delivery records. These eleven checks are repeated historical observations, not independent replications. The audit executes no route change, so no repaired-policy service benefit is estimated. Interval-wise source contributions and the worst-source identity correction are available in the public repository (Supplementary Notes S4; see Data Availability).

![Fig. 2 Confirmation-contract lockout in the selected ten-node adverse cell. (a) Schematic topology after relay 6 is removed at 225 s (not physical coordinates): source 0 remains on broken route 0-8-6-9 (v2), while source 1 holds intact route 1-4-5-9 (v3) toward gateway 9. (b) Timeline: admitted yet channel-failed installation attempts at 235-240 s, unconfirmed exit at 245 s, and a 245-315 s lockout with fifteen blocked checks--candidates available at 15/15 checks under Horizon/Cohort/Closing but only 5/15 under Full v2. The dashed 265 s window is an offline received-only audit (offered [36, 60], timely [0, 59]; deficit at 11/15) with no executed recovery.](figures/Fig2.png)

## 7 Discussion

A checkable bound for one defined traffic class is supplied by the reservation rule. The measured drop in control bytes is consistent with that accounting aim. A passed byte audit is not, by itself, evidence of service-preserving recovery. That is what the failed joint criterion shows. Whether the remaining transmissions still carry usable feedback is left open by a bound on one transmitted class. The gap is made concrete by the ten-node DATA panel. Removal markers (circles) lie to the right of the 20 percent line. Overload markers (squares) lie to the left of it. The diamond, which is the quantity tested by the evaluation, sits just to the right of the line. The gap remains after every protocol audit has been passed. For a communication and control study, that separation is the usable result. A byte account can be rechecked. A service gate can stay shut after waiting has ended. Both are present in the same traces.

A more specific account of the largest adverse input is given by the targeted diagnosis. The source 0 installation requests are admitted by byte credit. Transmission is prevented by channel access. A global confirmation condition is left unsatisfied by the closed partial transaction. With the longer source view, the later block persists. Candidates are available, and received counts sufficient for a bounded historical calculation are also available. The recovery threshold is not met by the recorded source-local failures, even while end-to-end delivery is zero. An end-to-end service certificate is not replaced, in this case, by source-local transmission success.

That condition is not addressed by the received-cohort variants. Their additional historical windows are considered only after the earlier installation and route-consistency checks. Observed source states would still have to be reconciled, by a controller that kept them as a vector, with its desired route pair. That reconciliation is not implemented by deletion of the global confirmation check alone. A past deficit can be identified from received records. That much is established by the shadow audit. Whether use of the deficit produces a successful and affordable installation would have to be determined by a separate closed-loop intervention. The failed repair selection is retained. No such performance claim is made.

A universal scaling law cannot be established by the comparison between sizes. One different layout is used at each size, and the catalog construction also differs between ten and twenty nodes. A higher reporting population therefore occurs together with additional forwarding alternatives and with a different geometry. A population-level recommendation to add relays is not validated by the positive twenty-node result. Average deployment damage is not estimated by the negative ten-node result.

The evaluation is small, and it is intentionally limited in scale, by design. Multiple configurations are spanned by the same two input identifiers, and bucket observations overlap in time. Those dependencies are kept visible. Packet counts, snapshots, and configuration counts are not used as a nominal sample size. The documented adverse behavior, and the failure of these three repairs on the specified inputs, are supported. General noninferiority is not established. Effective alternatives are not ruled out. Behavior across unseen deployment families is not quantified.

For the policy that was implemented, the separation between a byte bound and a service requirement is what is retained. Evidence age and installation epochs have to be represented explicitly by a controller that consumes intentionally sparse feedback. Broader historical evidence is to be evaluated through complete application outcomes. Practical recovery value can be overstated if only the count of usable windows is increased. This repair sequence is stopped by the registered failure. Repeated parameter changes on the same inputs are not motivated.

The design implication follows from the conditional argument in Section 4.5. An explicit post-exit interpretation is needed, by a bounded transaction, of the source states that were actually observed. Otherwise eligibility can continue to be controlled by an unconfirmed joint target after the wait to which it belonged has ended. A control contract is what is implicated. How often the problem occurs is not estimated. Identifiable history is distinguished by the source/version audit from unknown history, under the stated certificates. Reconfiguration on every historical deficit is not a tested recommendation.

## 8 Conclusion

Using a deterministic simulation matrix of forty evaluation cases, this paper has isolated and analyzed a recovery lockout in a wireless sensor network controller operated under reduced control overhead. The implemented control-DATA reservation bounds the audited control traffic and reduces mean control-DATA bytes by 22.14-23.02% at ten nodes and by 35.27% at twenty nodes across the four budget-enabled treatments, yet none of the three prospectively registered observation repairs satisfies the frozen joint screening criteria. In the most adverse cell, the exploratory diagnosis and the conditional analysis trace the failure to the Sparse-Feedback Paradox as it arises in this implementation: reduced reporting leaves the centralized controller without the positive evidence it needs to authorize an alternative route configuration.

Proposition 1 shows that, while the latest joint transaction is unconfirmed and no source presents an eligible failure report, the implemented global confirmation contract keeps the recovery gate closed after the bounded installation wait ends, so observation repairs that do not change those premises cannot reopen it. The recorded trajectory stays in that state for all fifteen post-exit checks; release through a later confirmation or an eligible failure report is not excluded. The offline received-only audit identifies a historical deficit at eleven of those fifteen checks using only received records, but the implemented policy cannot act on it. This negative result does not imply that sparse-reporting designs fail in general. It marks a verifiable boundary for this controller and indicates that sparse-feedback WSN controllers need an explicit post-exit interpretation of partially installed source states that reconciles observed and desired configurations.
## Acknowledgment

OpenAI Codex [24] was used only for language polishing of the manuscript text. The authors reviewed all polished text and accept full responsibility for the content of the paper.

## Funding

No specific funding was received for this work.

## Author contributions

Contribution to the paper is confirmed as follows. Conceptualization was carried out by Ya-Yu Zhang, Shu-Chuan Chu, and Jeng-Shyang Pan. Methodology was carried out by Ya-Yu Zhang, Shu-Chuan Chu, and Zhenyu Meng. Software was carried out by Ya-Yu Zhang. Validation was carried out by Ya-Yu Zhang, Zhenyu Meng, and Chih-Cheng Chen. Formal analysis was carried out by Ya-Yu Zhang and Zhenyu Meng. Investigation was carried out by Ya-Yu Zhang and Chih-Cheng Chen. Resources were provided by Jeng-Shyang Pan. Data curation was carried out by Ya-Yu Zhang. Visualization was carried out by Ya-Yu Zhang and Chih-Cheng Chen. The original draft was prepared by Ya-Yu Zhang. Review and editing were carried out by Ya-Yu Zhang, Shu-Chuan Chu, Zhenyu Meng, Chih-Cheng Chen, and Jeng-Shyang Pan. Supervision was provided by Shu-Chuan Chu and Jeng-Shyang Pan. Project administration was carried out by Shu-Chuan Chu. The results were reviewed by all authors, and the final version of the manuscript was approved by all authors.

## Conflicts of interest

The authors declare that they have no conflicts of interest.

## Data availability

The analysis scripts, observation-controller sources, registration and screen records for the forty cases, numerical summaries, and figures supporting the findings are publicly available at https://github.com/ya-yu-zhang/wsn-recovery-lockout-nr. Running the included analysis script on these records reproduces the reported screen decisions and Tables III and IV; the included figure script redraws Figs. 1 and 2 from the committed summaries. The two packet-level diagnosis scripts are included for inspection, but they require the native archive. The native packet-level archive (about 676 MB), from which the reported counts were taken, and the pinned simulation driver are available from the corresponding author upon reasonable request; the archive is identified by SHA256 fdf083436532c88613103363ea548f243cae0b5b525ab1cbc656ffa7d865674d.

## References

[1] P. Levis, T. Clausen, J. Hui, O. Gnawali, and J. Ko, “The Trickle Algorithm,” RFC 6206, Mar. 2011, doi: 10.17487/RFC6206.

[2] J. Heinanen and R. Guerin, “A Single Rate Three Color Marker,” RFC 2697, Sep. 1999, doi: 10.17487/RFC2697.

[3] J. Paek and R. Govindan, “RCRT: Rate-controlled reliable transport for wireless sensor networks,” in *Proc. ACM SenSys*, 2007, pp. 305-319, doi: 10.1145/1322263.1322293.

[4] G. Jeong, M. Park, and J. Paek, “A²-Trickle: Adaptive & Aligned Trickle for Rapid and Reliable Dissemination in Low-Power Wireless Networks,” *IEEE Access*, vol. 8, pp. 214374-214382, 2020, doi: 10.1109/ACCESS.2020.3040160.

[5] J. Ock, H. Kim, H.-S. Kim, J. Paek, and S. Bahk, “Low-Power Wireless With Denseness: The Case of an Electronic Shelf Labeling System--Design and Experience,” *IEEE Access*, vol. 7, pp. 163887-163897, 2019, doi: 10.1109/ACCESS.2019.2950886.

[6] M. Trobinger, G. de Albuquerque Gleizer, T. Istomin, M. Mazo Jr., A. L. Murphy, and G. P. Picco, “The Wireless Control Bus: Enabling Efficient Multi-Hop Event-Triggered Control with Concurrent Transmissions,” *ACM Trans. Cyber-Phys. Syst.*, vol. 6, no. 1, Art. no. 4, Nov. 2021, doi: 10.1145/3485467.

[7] M. Reitblatt, N. Foster, J. Rexford, C. Schlesinger, and D. Walker, “Abstractions for network update,” in *Proc. ACM SIGCOMM*, 2012, pp. 323-334, doi: 10.1145/2342356.2342427.

[8] T. Winter, Ed., P. Thubert, Ed., A. Brandt, J. Hui, R. Kelsey, P. Levis, K. Pister, R. Struik, J. P. Vasseur, and R. Alexander, “RPL: IPv6 Routing Protocol for Low-Power and Lossy Networks,” RFC 6550, Mar. 2012, doi: 10.17487/RFC6550.

[9] O. Gnawali, R. Fonseca, K. Jamieson, D. Moss, and P. Levis, “Collection Tree Protocol,” in *Proc. ACM SenSys*, 2009, pp. 1-14, doi: 10.1145/1644038.1644040.

[10] IEEE Standard for Low-Rate Wireless Networks, IEEE Std 802.15.4-2020, 2020, doi: 10.1109/IEEESTD.2020.9144691.

[11] A. Dunkels, B. Grönvall, and T. Voigt, “Contiki--a lightweight and flexible operating system for tiny networked sensors,” in *Proc. IEEE LCN*, 2004, pp. 455-462, doi: 10.1109/LCN.2004.38.

[12] J. Hill, R. Szewczyk, A. Woo, S. Hollar, D. Culler, and K. Pister, “System architecture directions for networked sensors,” in *Proc. ASPLOS*, 2000, pp. 93-104, doi: 10.1145/378993.379006.

[13] J. N. Al-Karaki and A. E. Kamal, “Routing techniques in wireless sensor networks: a survey,” *IEEE Wireless Commun.*, vol. 11, no. 6, pp. 6-28, Dec. 2004, doi: 10.1109/MWC.2004.1368893.

[14] J. Yick, B. Mukherjee, and D. Ghosal, “Wireless sensor network survey,” *Comput. Netw.*, vol. 52, no. 12, pp. 2292-2330, 2008, doi: 10.1016/j.comnet.2008.04.002.

[15] D. Dujovne, T. Watteyne, X. Vilajosana, and P. Thubert, “6TiSCH: deterministic IP-enabled industrial internet (of things),” *IEEE Commun. Mag.*, vol. 52, no. 12, pp. 36-41, Dec. 2014, doi: 10.1109/MCOM.2014.6979984.

[16] T. Watteyne, A. Molinaro, M. G. Richichi, and M. Dohler, “From MANET to IETF ROLL standardization: A paradigm shift in WSN routing protocols,” *IEEE Commun. Surveys Tuts.*, vol. 13, no. 4, pp. 688-707, 2011, doi: 10.1109/SURV.2011.082710.00092.

[17] L. Galluccio, S. Milardo, G. Morabito, and S. Palazzo, “SDN-WISE: Design, prototyping and experimentation of a stateful SDN solution for WIreless SEnsor networks,” in *Proc. IEEE INFOCOM*, 2015, pp. 513-521, doi: 10.1109/INFOCOM.2015.7218418.

[18] Z.-G. Du, J.-S. Pan, S.-C. Chu, H.-J. Luo, and P. Hu, “Quasi-Affine Transformation Evolutionary Algorithm With Communication Schemes for Application of RSSI in Wireless Sensor Networks,” *IEEE Access*, vol. 8, pp. 8583-8594, 2020, doi: 10.1109/ACCESS.2020.2964783.

[19] J.-S. Pan, R.-Y. Wang, S.-C. Chu, K.-K. Tseng, and F. Fan, “A Quasi-Affine Transformation Evolutionary Algorithm Enhanced by Hybrid Taguchi Strategy and Its Application in Fault Detection of Wireless Sensor Network,” *Symmetry*, vol. 15, no. 4, Art. no. 795, 2023, doi: 10.3390/sym15040795.

[20] T.-M. Hoang, T.-L. Tran, P. Nagaradjane, I. Ioannou, T.-T. Phan, H.-L. Tran, and A.-T. Pham, "Control Signaling Constrained Topology Reconfiguration for Clustered Wireless Sensor Networks," *IEEE Access*, vol. 14, pp. 117182-117192, 2026, doi: 10.1109/ACCESS.2026.3717923.

[21] J. Yang, W. Li, C. Li, L. Zhang, and L. Liu, "An Energy-Efficient and Transmission-Efficient Adaptive Routing Algorithm Using Deep Reinforcement Learning for Wireless Sensor Networks," *IEEE Internet Things J.*, vol. 12, no. 23, pp. 50414-50426, Dec. 2025, doi: 10.1109/JIOT.2025.3609624.

[22] ns-3 Project, “ns-3.44 model library and source release,” 2025. Accessed: Oct. 16, 2026. [Online]. Available: https://www.nsnam.org/releases/ns-3-44/

[23] Texas Instruments, “CC2420 2.4 GHz IEEE 802.15.4 / ZigBee-ready RF Transceiver,” SWRS041C, Mar. 2013. Accessed: Oct. 16, 2026. [Online]. Available: https://www.ti.com/lit/ds/symlink/cc2420.pdf

[24] OpenAI, “Codex.” Accessed: Oct. 20, 2026. [Online]. Available: https://openai.com/codex/

## Biographies

**Shu-Chuan Chu** received the B.S. degree from National Taiwan University of Science and Technology, Taipei, Taiwan, in 1988, and the Ph.D. degree from the School of Computer Science, Engineering, and Mathematics, Flinders University, Adelaide, South Australia, in 2004.
She spent nine years at Cheng Shiu University, Kaohsiung, Taiwan, before joining Flinders University, Australia, in Dec. 2009, where she served as a Research Fellow and Associate Professor in the College of Science and Engineering. From Sept. 2019 to Aug. 2024, she was a Professor and Doctoral Supervisor with the School of Computer Science and Engineering, Shandong University of Science and Technology, Qingdao, China. Since Sept. 2024, she has been a Professor and Doctoral Supervisor with the School of Artificial Intelligence/School of Future Technology, Nanjing University of Information Science and Technology, Nanjing, China. Her research interests include swarm intelligence, evolutionary computation, and wireless sensor networks.

**Ya-Yu Zhang** has been a master's student in the School of Computer Science, Nanjing University of Information Science and Technology, Nanjing, China, since September 2024. Biography to be completed by the author.

**Chih-Cheng Chen** has been a Professor at Feng Chia University, Taiwan, since 2019. He became a Member of IEEE in 2011, and a Senior Member in 2016. He earned his M.S. degree in 2005. In 2011, he received his Ph.D. degree from the Department of Mechatronics Engineering, National Changhua University of Education. He has been researching the RFID application system in various applications such as patrol systems and long-term care of the elderly. His research mainly focuses on artificial intelligence of things (AIoT) technology and AI applications.

**Zhenyu Meng** is with the School of Computer Science and Software, Zhaoqing University, Zhaoqing 526061, China. Biography to be completed by the author.

**Jeng-Shyang Pan** (Senior Member, IEEE) received the B.S. degree in electronic engineering from the National Taiwan University of Science and Technology, Taipei, Taiwan, in 1986, the M.S. degree in communication engineering from National Chiao Tung University, Hsinchu, Taiwan, in 1988, and the Ph.D. degree in electrical engineering from the University of Edinburgh, Edinburgh, U.K., in 1996. Prof. Pan is an IET Fellow. He has served as Vice Chair of the IEEE Tainan Section and Chair of the Tainan Chapter of the IEEE Signal Processing Society. He is currently a Professor at the Faculty of Electrical Engineering and Computer Science, VSB-Technical University of Ostrava, Czech Republic, and also serves as a Professor at the Department of Information Management, Chaoyang University, Taichung, Taiwan. His current research interests include artificial intelligence, wireless sensor networks, and computational intelligence.
