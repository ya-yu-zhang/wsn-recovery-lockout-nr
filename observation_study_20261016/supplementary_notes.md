# Supplementary notes

Technical detail removed from the main text for readability. Section labels match the manuscript.

## S1. Simulator revision and geometry controls (§3.1)

- Simulator: ns-3.44 at commit 43dce6710b8df69685e3479c1d33a571dda714ea.
- One fixed development layout per network size from layout seed 2026101501.
- Base management scaffold jittered within six metres; additional relay positions lie in the registered coordinate region.
- Log-distance channel with exponent three and constant-speed propagation.
- A management scaffold that is not removed in these workloads carries reports and installation messages.

## S2. Radio energy accounting (§5)

- Radio-state duration is integrated as modeled radio energy with a CC2420-like current model at 3 V (manuscript reference [21]).
- Processor, sensor, and battery effects are excluded from that model.
- Control-cost endpoint in the main text remains MAC DATA PSDU bytes of reports and installations; PHY preamble/header are excluded there.

## S3. Execution pinning and storage checks (§5)

- Registered source bytes were recovered exactly before execution.
- The pinned native source was compiled on the GitHub runner; that runner binary hash is recorded separately from any earlier host binary.
- The same runner binary was used for all forty treatments.
- Within-node addition order is preserved by post-simulation radio aggregation; gzip changes only storage encoding.
- Compressed native payloads were checked during execution against uncompressed SHA256 records.

## S4. Adverse-cell interval contributions (§6.4)

Selected cell: 10 nodes, multi_failure, input seed 2026101511.

Source 0 full-run denominator: 3375 packets. Contributions to the Full v2 versus Legacy source-0 service difference (percentage points), using the full-run denominator:

| Interval (s) | Contribution pp |
|---|---:|
| 0–65 | -0.207 |
| 65–145 | +0.059 |
| 145–225 | -0.326 |
| 225–330 | -31.733 |
| Source 0 total | -32.207 |

Worst source under Legacy is source 1; under the treatment it is source 0. The reported worst-source difference of about -27.686 points includes a +4.521-point reference correction for that identity change. Interval-wise minima are not summed.

## S5. Fig. 1 matched-cell marker reading (§6.2)

Ten-node service panel (versus Legacy, percentage points):

- Removal seed 2026101511: -27.69 on every treatment row.
- Removal seed 2026101512: -3.88 for Full v2 and Horizon; -0.72 for Cohort and Closing.
- Overload markers between about -6.26 and -1.61; Closing on overload 2026101511 reaches -1.61; the other overload input stays at -5.29 on all four rows.
- All sixteen cell markers and the four diamonds remain left of the -0.5 dotted line.

Ten-node DATA panel (reduction percent):

- Removal cells about 31.19–32.52; overload cells about 12.35–16.01, so the diamond can sit just right of 20 percent while individual overload cells do not.

Twenty-node panels:

- Service markers about +0.25 and +1.16 (removal) and +2.55 and +2.07 (overload).
- DATA markers about 35.28 and 37.12 (removal) and 33.70 and 34.97 (overload).
- All four treatments share these endpoints, so Closing is not separated from Full v2 at twenty nodes.

## S6. Diagnosis interval labels

Generation-time intervals 0–65, 65–145, 145–225, and 225–330 s follow the removal schedule. In overload workloads the same labels are reference intervals only, not injected fault periods.
