# Phase-2 results (2026-11-11 PT) — probes run; full sets stopped by rule

**Registration.** `REGISTRATION_PHASE2_20261111.json`, SHA256 `caf07cc98efd5e2d6b4fa60d5d5c3bf6cdb622d8f9ea9d70caac3ea6ca84ab4f`,
committed locally as `e788c7d` (nothing pushed). Prereg `PREREG_PHASE2_20261111.md`. Frozen reference (registration `1f37be33…6a24`,
Amp-1 0/96, Amp-2 26/48, PostExit 26/26, competitors 0, sham 48/48) was not touched or re-scored. The manuscript was not edited.

## Step 0: freeze and rebuild
- SIMPAT v0 frozen as `submission_package_20261028/simpat_v0_20261111/`; manifest SHA `a781fe53…d346`.
- ns-3.44 libraries rebuilt with conda GCC 14.4 (`REBUILD_NOTE.md`). Spot-check on 48 random Amp-2 cases: **48/48 match** (480 files).
  The match uses comparator v2. v1 had flagged only `hashes.controller`, which is the SHA of a file that contains wall-clock fields. That is a comparator deviation, logged.

## Probe A: docking (SimPy mirror vs ns-3; 36 Amp-2 subset + 8 adverse cases)
| Mode | Endpoint | Result | Threshold |
|---|---|---|---|
| C (conditioned on recorded inputs) | C1 E1 / C2 exit times / C3 Φ per tick / C4 reason per tick | **1.000 / 1.000 / 1.000 / 1.000** (2,948 ticks, 1,750 evaluated) | 0.95/0.95/0.98/0.95 |
| F (free-running DES) | F1 gate outcome: joint / sham / post_exit | 1.00 / 1.00 / **0.00** | ≥ 0.95 |
| F | F2 first exit (Amp-2) | 1.00 all arms | ≥ 0.95 |
| F | adverse cell (8): F1 / F2 | 6/8 / **0/8** (mirror exits at 80–110 s, ns-3 at 245 s) | — |
| F (E, probe only) | Joint E1: ns-3 7/12; mirror 95 % interval [1, 7], mean 3.35 | edge | — |

**Verdict: probe A FAILED** (Mode F). Mode C shows that the written specification reproduces the implementation's gate exactly on identical inputs, including all 8 adverse-cell model×arm outcomes.
Mode F fails because the abstract network never re-opens the gate after a PostExit release. In ns-3, source reports switch to 5 s on local
queue/contention state changes (manuscript l.156; 1,332 of 2,355 emitted source reports in the probe cases). That re-phases them onto
the relay-report ticks, so Ψ becomes known while the relay views are still ≤ 8 s. The mirror models no queue or CSMA state (declared), so its Ψ-known
ticks fall on stale relay views and no candidate pair is admissible. Joint/sham F1 agreement is therefore uninformative: the mirror never re-opens in any arm.
This is not a text misreading that can be fixed under the registered rule, so per the registration there is no re-run and the Mode-F claim is reported as a **negative
docking result**. An honest description: the gate logic is verified; the network-level reproduction needs a contention/state submodel.

## Probe B: FlockLab replay (Day A 2019-09-15, subgraphs A0, A1, seed 2026111301, R2)
- Traces: Day A 12 tests, 27 nodes, 552 links (5,616 unrecorded rows treated as missing). Day B 4 tests, 702 links.
  The registered rule gave 10,000 valid assignments (A: 212 distinct node sets; B: 393). K = 4 drawn per day.
- New binary `flocklab/wsn-closed-loop-trace`, SHA256 `ddc624a2…c00a` (source `1f296e33…0150`, header `9c4d8894…2d72`).
- **PASS**: 8/8 runs complete, `audit_case` 8/8, R2 ingestion recomputed exactly for every link in 8/8 runs.
  Neutrality (E): with traceMode=0 the output is byte-identical to the frozen Amp-2 runs (2/2 cases, 4 hashes each).
- Outcomes (E, n = 2 per cell): M1 Joint E1 2/2 (gate closed, exit at 20 s, no F_s after exit); M1 PostExit E1 0/2 (6–8 installs after exit).
  N (no drop), both arms: no unconfirmed exit, lockout 0/4 (an acceptable archived result).

## Not run (stopped by rule)
Full docking (C full, F full), prospective DOE predictions plus the 432-run DOE, and full FlockLab (128 R2 + 64 R1) were not started.
The parent's instruction says "if a probe fails, stop and report", and the registration says "a probe failure stops the matching full runs". No phase diagram exists.

## Deviations (all in CHANGELOG.md)
1. Spot-check comparator v1 → v2 (wall-clock hash field).
2. Pre-freeze prereg amendments (evaluation mask; Mode-F evaluation rule; FlockLab seeds 01–04 so that 128/64 holds; exact ingestion audit; median_low).
3. Post-freeze `prepare_traces.py` crash fix (empty rcv_stream = missing, not loss), made before any outcome.
4. Post-freeze `trace_wrapper.sh` fix: empty `--traceFile=` rejected, which affected the neutrality runs only.

## Files
`results/dock_C_probe.json`, `results/dock_F_probe.json`, `flocklab/results_probe/{runs,summary,link_audit}.json`,
`flocklab/results_neutral/summary.json`, `figures/fig_docking_probe_table.png`, `figures/docking_probe_table.md`,
`figures/fig_flocklab_probe_outcomes.png`, `mirror/calibration.json`. Raw ns-3 output: `raw_on_request/scratch_phase2/`.
