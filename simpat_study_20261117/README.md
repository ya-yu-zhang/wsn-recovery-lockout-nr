# Substrate-docking layer and scale stage (added 18 November 2026)

This folder adds two layers to the study whose earlier materials are at the repository root. Both
were registered in [`PROTOCOL.md`](PROTOCOL.md) before their runs (stages E0–E4 on 17 November
2026; E5 in Amendment 1, before it ran). Nothing in the folders deposited earlier was changed.

| Manuscript element | Stage | Records |
|---|---|---|
| V&V layer (v), substrate docking of the ns-3.44 CSMA-CA, and its diagnosis | E1, E5 docking | `results/docking/` (`ns3.jsonl`, `reference.jsonl`, `reference_variants.jsonl`, `ns3_cca_patched.jsonl`, `diagnosis.json`) |
| Natural incidence and scaling over 120 new cells at 10, 20 and 40 nodes | E3 | `results/scale/` |
| Robustness on ns-3.44 with the one-line CCA patch | E5 | `results/cca_patch/` |

Other stages run under the same registration are also deposited, so that no registered result is
withheld:

- E0, an exact-reproduction smoke check: `results/smoke/`.
- E2, a PostExit replication on the original eight cells: `results/contract/`, with controller transcripts.
- E4, one-factor sensitivity of installation wait and byte refill: `results/sensitivity/`.

## Reproducing the numbers and figures (Python 3.11+, standard library plus matplotlib)

```
cd simpat_study_20261117
python analyze_simpat.py               # results/analysis.json: incidences, paired effects, vs. Legacy
python a_endpoint.py                   # results/a_endpoint_E1.json: IU-only E1, defined as in analyze_contract_ablation.post_exit
python docking/diagnose_docking.py     # results/docking/diagnosis.json: registered verdict and diagnostic variants
python merge_figures/make_merge_figures.py   # Fig4 (five lanes), FigD, FigE
```

`diagnose_docking.py` reruns the independent reference model, which is pure Python, in about a minute.

## Re-running the simulations

- `run_simpat.py --stage {smoke,contract,scale,sensitivity,cca_patch} --shard i --shards n` drives the
  prepared engine in `../control_budget_study_20261015/engine/`.
- `docking/run_docking.py` builds `docking/csma_docking.cc` against ns-3.44 at commit
  `43dce6710b8df69685e3479c1d33a571dda714ea`.
- `ci/wsn-simpat-study.yml` is the GitHub Actions workflow that executed every stage. The `cca_patch`
  variant applies one change to `src/lr-wpan/model/lr-wpan-phy.cc`: in `PlmeCcaRequest`, the CCA peak
  is initialised with the current signal power instead of zero.

Raw native traces of these stages, about 1,800 runs, are available on request.

## Endpoints

- *Unconfirmed exit*, *broad* and *strict lockout*: as defined in `lockout.py`.
- *IU-only E1*: computed by `a_endpoint.py` exactly as `analyze_contract_ablation.post_exit` in
  `public_release_amp_repro_20261104/theory_code_refs/`.
- *Worst-source timely service* and *control MAC DATA PSDU bytes*: as in the forty-case screen.

PostExit releases only premise *T*. It is a diagnostic ablation, not a recommended protocol.
Runtime LLM calls: 0.
