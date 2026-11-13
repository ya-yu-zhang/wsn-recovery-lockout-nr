# REBUILD NOTE — ns-3.44 library rebuild on the box (2026-11-11, America/Los_Angeles)

## Why
When phase 1 started (2026-11-11, about 17:15 PT), the box had the ns-3.44 source tree
(`/workspace/wsn_ablation/repo/ns3_vendor/ns-allinone-3.44/ns-3.44`, git commit
`43dce6710b8df69685e3479c1d33a571dda714ea`), but `build/lib` was missing, and the system had no
`g++`/`cmake`. The registered driver binary
`control_budget_study_20261015/engine/ns3/wsn-closed-loop` (SHA256
`5e77691695f30ce36d5de37f1426fda0a2deb266be2b5fb3e889279af96da6be`, the hash recorded in the
Amp-2 confirm registration/results) therefore could not load `libns3.44-*.so`. apt returned HTTP
500 from the box proxy.

## What was done
* Toolchain: conda-forge `gxx_linux-64=14` (GCC **14.4.0**) installed with micromamba into
  `/workspace/wsn_ablation/tc_env` (log `/workspace/wsn_ablation/mamba_20261111.log`).
  The original build used the system `/usr/bin/c++` (GCC 14.2 per environment.json).
* Libraries only: cmake/ninja from the repository's `build_tools`, with the same flags as
  `build_environment.py` (`NS3_ENABLED_MODULES=lr-wpan`, release, no examples/tests/python/PCH/ccache, `-pipe`), but into a NEW cache directory
  `ns-3.44/cmake-cache-rebuild-20261111` (the original `cmake-cache` was left untouched).
  There were 281 targets and the build took 1 min 09 s (log `/workspace/wsn_ablation/rebuild_20261111.log`). Output: `ns-3.44/build/lib/libns3.44-*.so`.
* The registered driver binary was **not** recompiled; its SHA256 is unchanged (`5e776916…a6be`).
* No ns-3 source, engine source, frozen result, or registration was modified.

## Reproducibility check (48 Amp-2 confirm cases)
`rebuild_check/spotcheck48.py` reran 48 frozen Amp-2 confirm cases (random sample, seed 20261111;
8 arms and 8 layouts covered) into `/workspace/scratch_phase2/repro48` and compared all
10 output files per case (480 files).
* Byte-identical, all 48 cases: `.csv`, `.jobs.csv`, `.protocol.jsonl`, `.radio.csv` (decompressed),
  summary `.json`, `stderr.log`, `_arrivals.csv`, `_positions.csv`.
* `controller.json`: identical after removing wall-clock fields (`compute_wall_ns`,
  `constraint_wall_ns`, `wall_seconds`) and paths.
* `record.json`: identical after removing wall-clock fields/paths **and** `hashes.controller`.
  **Logged deviation from the first comparison script (v1 → v2):** v1 reported 0/48 because
  `hashes.controller` differs. That field is SHA256 of `controller.json`, which embeds wall-clock
  values, so it necessarily changes on every rerun. v2 (`spotcheck48_compare_v2.py`, no new simulation)
  accepts the difference only if each side equals SHA256 of its own `controller.json` bytes and the
  two `controller.json` files agree after wall-clock removal. Result: **48/48 match**
  (`spotcheck48_result_v2.json`). The v1 output (`spotcheck48_result.json`) is retained.
* Earlier phase-1 check: 16/16 cases matched in the same way.

Conclusion: the rebuilt libraries reproduce the frozen Amp-2 traces exactly (wall-clock fields excepted).
Every new phase-2 ns-3 run uses these libraries. FlockLab replay additionally uses a new driver binary
built by the same conda GCC 14.4; its hash is recorded separately.
