# Version evidence under a complete control DATA budget

This new mechanism study follows failed learning diagnostics. It withdraws contextual learning superiority as a primary claim. No LLM participates in any experiment. The historical diagnostic draft is not reused as new evidence and missing historical raw files are not described as archived.

## Proposed mechanism

Every node reserves three times the maximum 127-byte PSDU before admitting any control MAC request, including ordinary reports, forwarded reports, application report retries and route installations. Three is the configured maximum MAC DATA attempt count. Credit starts at 4572 bytes and refills at 305 bytes/s. Ordinary reports cannot consume the final 1524 bytes; source version/generation evidence, locally leased active-relay reports and installations may use that protected credit. Priority is conveyed in a spare report-depth bit without increasing the frame size. Local data-forwarding leases, not simulator liveness or future routes, identify active relays. A budget rejection is an actual control-packet loss and stays in service outcomes.

Source reports use a five-second clock for fifteen seconds after local installation, during measured current-version source failures above 20 percent with at least ten completions, or after a local queue/CCA state change. Otherwise they use fifteen seconds. State is based only on local measurements. Received source reports advertising a fifteen-second period have a sixteen-second view-validity limit; five-second reports keep eight seconds. Installation and feedback qualification retain their stricter eight-second received-evidence rule. This does not guarantee reception or feedback availability.

The deterministic accounting invariant is per-node transmitted control DATA at most B+r*t, using conservative reservations and no refunds. ACK, application DATA and radio energy are measured separately. This bound does not imply a service, delay or network-lifetime guarantee. Unused reservations remain charged.

## Development matrix

Fix one twenty-node layout seed 2026101501 and input seeds 2026101511 and 2026101512. Use 330-second multi-failure and overload workloads and resource routing. Compare legacy reporting/partial retry budget, pacing only, unified protected budget only, and the full mechanism: sixteen matched cases. Fault times and nodes are 65:2,145:3,225:6 in the multi-failure scenario; overload has no injected removals. Report phases are deterministically shuffled using the input seed and are identical in matched treatments, preventing fixed low node IDs from receiving an early token advantage. Both sources, candidate pool, native PHY/MAC, packet sizes, deadlines, installation rules and maximum64 evaluations are shared. Failed runs are retained; outcome-based replacement is forbidden.

Proceed only if the full mechanism has mean worst-source timely-delivery change at least minus0.5 percentage points against legacy and mean paired control DATA reduction at least20 percent across all four inputs. Report every cell, censoring, installation exits, full-run service, exact control bytes, search evaluations and radio energy. If it fails, allow one mechanism revision only when a recorded diagnostic identifies an implementation or admission failure. Publish the amendment before new runs, retaining the failed matrix.

## Confirmation and scale

After the method is frozen, use10,20,40 nodes, three unseen layout seeds2026101521–2026101523, two scenarios, and ten unique input seeds per layout and scale. Compare legacy and full communication mechanisms under resource, route-stability and common-pool hop reference routing:1080 cases. The geometry uses a protected management scaffold and newly sampled extra relays; it is not a sample of all network architectures. Gateway ID remains9 at every scale. Other nodes are relays and two application sources remain0 and1. Use a deterministic bounded geometry-only catalog for scales above10, shared by all controls, and retain at most64 charged route evaluations. The hop reference is not RPL, MRHOF or ETX.

Main paired uncertainty is conditional on the nine fixed layouts. Reused scenario streams form blocks; the independent input-seed identifier is unique for every scale/layout/repetition. Bootstrap paired seed blocks within each layout and preserve both scenarios inside a block. Report per-scale and per-scenario results and layout ranges. Do not represent layouts as independent repetitions or report universal topology generalization. Do not tune on confirmation results or add repetitions until significance appears.

Submit a mechanism paper only if confirmed full-run service and communication evidence support its stated scope. Novelty and acceptance cannot be guaranteed by implementation or formatting. Author metadata and declarations are required separately. Preserve the original negative learning findings in the research history.
