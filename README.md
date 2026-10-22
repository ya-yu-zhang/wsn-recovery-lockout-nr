# Recovery lockout after partial route installation in a sparse-feedback WSN controller

Public materials for the IEEE Access Negative Result manuscript in `observation_study_20261016/manuscript.md`.

## Contents
- `control_budget_study_20261015/`: observation-controller sources, the pre-specified repair protocol, and the registration, manifest, admission-audit, analysis, and per-case metric records of the forty-case screen.
- `observation_study_20261016/`: the manuscript source, analysis and diagnosis scripts, numerical summaries (`results/`), and the two figures (`figures/`).

## Reproducing the screen decisions
```
cd observation_study_20261016
python analyze.py          # recomputes the paired effects and screen gates from the records
python make_figures.py     # redraws Fig. 1 and Fig. 2 (requires matplotlib)
```
Python 3.11 or later is assumed.

## Not included
The native packet-level archive (about 676 MB) and the pinned ns-3 simulation driver are not included. `diagnose_traces.py` and `diagnose_partial_installation.py` read that archive and are provided for inspection. The archive is identified by SHA256 `fdf083436532c88613103363ea548f243cae0b5b525ab1cbc656ffa7d865674d` and is available from the corresponding author on reasonable request.

## Integrity
Hashes recorded in `results/*.json` are computed over the exact bytes of the record files (LF line endings for JSON, CRLF for the CSV); `.gitattributes` preserves those bytes on checkout.

## License
Code is released under the MIT License (`LICENSE`). Data records, numerical summaries, and figures are released under CC BY 4.0.
