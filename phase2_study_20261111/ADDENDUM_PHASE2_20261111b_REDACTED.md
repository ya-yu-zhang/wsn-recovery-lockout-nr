# Addendum 1 to the Phase-2 registration (written 2026-11-11 PT, before any run below)

[REDACTED: internal author authorization to continue the registered studies after the probe-A stop.]
This releases the stop imposed after the probe-A failure (parent rule "if a probe fails, stop"). It does not change any
registered threshold, design, layout or seed, and frozen results remain read-only.

Order and status of the studies:
1. (a, Mode C full) Registered full set (48 Amp-2 cells × {joint, sham_release, post_exit, wait_extend, thresh_relax_scoped} + 8 adverse),
   C1–C4 as registered. It is conditioned rescoring of frozen data, with no new simulation. Exploratory extension (E): `amplification2_manip_check` (16).
2. (b) FlockLab full: 128 R2 + 64 R1 = 192 runs as registered. Probe B passed. Reported with Wilson 95 % CIs (E).
3. (c) DOE, 432 runs, as registered. **H3 is VOID**: Mode F failed probe A (F1 post_exit 0/12), so no prospective Mode-F prediction is
   claimed. H1 and H2 are tested as registered. `run_doe.py` requires a predictions file; it is replaced by a file stating that H3 is void
   (`doe/predictions_FDOE.json` = {"void": true, ...}), so `analyze_doe.py` skips H3. The phase diagram stays exploratory (E).
4. (d) Mode-F rework: a NEW registration (Phase 2b) is written and frozen before any 2b code runs on registered inputs.
The Mode-F probe-A failure stands as the registered Phase-2 outcome whatever Phase 2b shows.
