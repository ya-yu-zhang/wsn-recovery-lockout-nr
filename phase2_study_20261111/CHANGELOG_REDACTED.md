# Phase-2 CHANGELOG (all times PT, 2026-11-11)

## Before freeze
- Step 0. SIMPAT v0 frozen as `submission_package_20261028/simpat_v0_20261111/` (SHA256_MANIFEST.txt; manifest SHA a781fe53…d346).
- Step 0. ns-3.44 libraries rebuilt with conda GCC 14.4 (REBUILD_NOTE.md). Spot-check of 48 random Amp-2 cases:
  v1 comparator reported 0/48 because `record.json` → `hashes.controller` is the SHA256 of controller.json, which embeds
  wall-clock fields (`constraint_wall_ns` etc.). **Deviation (comparator only):** v2 accepts that field only when it equals the SHA of
  its own controller.json and the two controller.json files agree after removing wall-clock keys. v2: MATCH 48/48 (480 files).
  No frozen file was changed.
- Smoke tests (excluded from all analyses): `mirror/smoke_test.py` on the `base` topology, generation_stop 60 s, placeholder
  calibration. Found one mirror bug (Mode-F policy refused every install while T was unconfirmed, even with eligible F_s);
  fixed before freeze to follow Prop. 1 (Φ via F_s).
- Trace driver `flocklab/wsn-closed-loop-trace.cc` = frozen driver + 3 CLI options + error-model attach + per-link counter dump.
  Built with conda GCC 14.4 (`build_trace_binary.sh`); compiled, not yet run.
- Pre-freeze prereg amendments: (i) Mode C uses the recorded evaluation mask; (ii) Mode-F evaluation rule stated;
  (iii) FlockLab seeds 2026111301–04 so the stated 128/64 counts hold (2 seeds gave 64/32); (iv) ingestion audit made exact
  (R2 recomputation) plus trace-binary neutrality check (E); (v) Mode-F replicate first-exit = median_low, None when p_exit < 0.5.

## After freeze
(entries appended below with time and diff hash)
17:49 freeze: REGISTRATION sha caf07cc98efd…ab4f, commit e788c7d
- 17:50 post-freeze bug fix (before any outcome): prepare_traces.py crashed on FlockLab rows with empty rcv_stream (unrecorded). Fix: such rows and absent tests are treated as missing observations (excluded), not as losses; link stream = observed tests in time order. diff sha256 606e1c988856…; new file sha256 994b9d580cbc…
- 17:54 post-freeze harness fix: neutrality runs failed at CLI parse (empty --traceFile= rejected by ns-3 CommandLine; ns-3 printed help). trace_wrapper.sh now omits trace options when traceMode=0. Trace-mode runs unaffected (identical argv). diff sha256 df4832bef609…, new sha256 17ec598f7904…. Failed attempts kept in raw_on_request/scratch_phase2/flocklab_neutral/*/FAILED_ATTEMPT.txt (renamed .first).
- 17:55 calibrate.py run (pre-docking): calibration.json sha256 20b11804…2e84 (logit_k 0.0274, d0 126.9 m, 394 cases, success 0.897).
- 17:55 Probe A Mode C: PASS (C1=C2=C3=C4=1.000, n=44). Probe A Mode F: FAIL (F1 post_exit 0/12; adverse F2 0/8).
  Diagnosis: ns-3 source reports switch to 5 s on local queue/contention *state changes* (manuscript l.156; 1332 of 2355 emitted
  source reports in the 36 probe cases), which re-phases them onto the relay-report ticks; the mirror has no queue/CSMA state
  (declared not modelled), so its Ψ-known ticks fall when relay views are > 8 s old and no candidate pair is admissible.
  No *text misreading* exists that can be corrected under the registered abstraction (a faithful state-change clause is a no-op
  without a contention model, and inventing one would be tuning toward the answer). Per registration: no re-run; full Mode-F
  docking, prospective DOE predictions (H3) not started. Per parent instruction ("if a probe fails, stop and report"): full
  docking, DOE (432) and full FlockLab (128+64) NOT started.
- 17:55 Probe B: PASS (8/8 complete, audit_case 8/8, R2 exact ingestion recomputation 8/8). Neutrality (E): trace binary,
  traceMode=0, byte-identical (.csv/.jobs/.protocol/.radio) to frozen Amp-2 runs on 2 cases.
- 17:57 ADDENDUM_PHASE2_20261111b.md ([REDACTED: internal author authorization] releases the stop; H3 void). analyze_doe.py edited only to skip H3 when predictions are void; doe/predictions_FDOE.json = void marker. sha addendum fc637ae54afaae64…, analyze_doe c30363337545abee…
- 17:59 Mode C FULL (registered, n=248): C1=C2=C3=C4=1.000 → PASS.
- 17:59 dock.py ns3_outcome: KeyError when a frozen case has no unconfirmed exit (post_exit() omits installs_after_exit);
  fixed with .get(…, 0). Registered probe/full sets unaffected (every case there has an exit). sha eadeadaa3524337e…
- 17:59 Exploratory (E) dock_extended.py over all 9 frozen sets with supported arms (1,653 cases; 465 skipped: fs_relax_*,
  thresh_relax_global, legacy). C1, Φ, reason: 100 % everywhere. C2 strict 1,384/1,653: all 269 misses are wait exits later rescued
  by a late confirmation, which the frozen post_exit() counts as exits but the mirror's registered endpoint excludes (definition
  difference, not logic). With the frozen convention (PH2_EXITS_INCL_LATE=1) C2 = 1,653/1,653.
- 17:59 FlockLab full attempt 1: BrokenProcessPool for all 192 at start (worker pool killed when the launching shell exited; no case started/finished, no outcome seen). Relaunched detached with setsid; attempt-1 log kept as results_full/runs_attempt1_brokenpool.json.
- 18:01 FlockLab full attempt 2: OOM kill (dmesg: python3 worker 2.3 GB RSS; trace runs emit large protocol logs; 6 workers > 16 GB). Technical, no outcome seen. One case (B0 seed01 N joint) completed in a foreground diagnostic and is reused from cache. Relaunched with 4 workers.
- 18:01 DOE design.json sha256 3a9fbfdccce2d85b… (432 cases); DOE launched (3 workers) concurrently with FlockLab (4 workers).
- 18:06 Phase-2b registration frozen: REGISTRATION_PHASE2B_20261111.json sha 9afb4dc3180c0436…; smoke tests (mirror2b/smoke_cq.py, base topology) run before freeze, excluded.
- 18:4x FlockLab FULL (attempt 3, 4 workers): 192/192 complete, 0 technical failures, audit_case 192/192. Ingestion audit (registered,
  strict): R2 exact recomputation 11,199/11,199 link-runs PASS; R1 tolerance rule 3,409/3,413 link-runs — 4 exceed max(0.03, 3·SE)
  → registered ingestion audit = FAIL. (E) exact-binomial expectation of exceedances under a correct Bernoulli stream = 2.69
  (results_full/audit_diagnostic_E.json): consistent with chance; the per-link rule had no multiplicity allowance. Not re-scored.
- 18:4x DOE: 432/432 complete, 0 technical failures, audit 432/432. H1 PASS (95/96 = 0.990). H2 FAIL as registered (1/216 PostExit
  E1: budget_10_2026111103, point 25, exit at 260 s; the only evaluated tick at/after the exit is the exit tick itself, release
  applies at the next tick, and no admission check was triggered before stop) — reported as a registered failure; the mechanism
  is an endpoint-definition edge case, not a T lock (E). H1 single exception (Joint, point 16): reopened after a first exit
  via late confirmation, locked after the last exit. H3 VOID (Addendum 1).
- 18:4x Phase-2b probe (P, 44): FAIL — F1 joint 0.667, sham 0.667, post_exit 1.000; F2 1.000 all arms. Joint E1 ns-3 7/12 vs mirror
  interval [0, 4]. (E) diagnosis (results/dock2b_probe_diagnostic_E.json): every mirror Joint reopening is via an eligible F_s;
  aggregate contention matches ns-3 a priori (CCA busy 0.353 vs 0.363; NO_ACK jobs/run 3,654 vs 3,579; CAF/run 716 vs 457).
  Holdout (H, 108) run as registered regardless (both sets required).
- 18:47 Harness: holdout run (no checkpoint, 4 min in, no output) stopped and relaunched via mirror2b/dock2b_ckpt.py (per-case checkpoint files; same mode_f, seeds, scorer; summary pass via thread pool). sha 03e2c38e5fc89b5c…
- 19:25 Phase-2b holdout (H, 108): FAIL — F1 joint 0.917, sham 0.917, post_exit 1.000; F2 1.000 all arms. Secondary F3
  over 48 Joint cells: ns-3 26/48 (= frozen Amp-2 count) vs mirror 95 % interval [3, 13] (expected 7.6) → outside → FAIL; Brier 0.401.
  Phase 2b registered verdict: FAIL. No re-runs, no model changes.
