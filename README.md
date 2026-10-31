# Recovery lockout after partial route installation in a sparse-feedback WSN controller

Public materials for the IEEE Access Negative Result manuscript
*"Discovery and Analysis of Recovery Lockout in Sparse-Feedback Wireless Sensor Networks: A Negative Result Study on Observation Repairs"*
(Shu-Chuan Chu, Ya-Yu Zhang, Chih-Cheng Chen, Zhenyu Meng, Jeng-Shyang Pan).

Repository: https://github.com/ya-yu-zhang/wsn-recovery-lockout-nr
Corresponding author: Jeng-Shyang Pan, 100112@nuist.edu.cn

## What is included

| Folder | Contents |
|---|---|
| `observation_study_20261016/` | Manuscript source (`manuscript.md`), Supplementary Notes S1–S6, analysis script (`analyze.py`), figure script (`make_figures.py`), two packet-level diagnosis scripts, numerical summaries (`results/`), and Figs. 1–2 (`figures/`, PNG and EPS). |
| `control_budget_study_20261015/` | Observation-controller sources (`budget_controller.py`, `cadence_controller.py`, `horizon_controller.py`), the pre-specified protocols (`PROTOCOL.md`, `CADENCE_REPAIR_PROTOCOL.md`, `HORIZON_REPAIR_PROTOCOL.md`), and the registration, manifest, admission-audit, analysis, and per-case metric records of the forty-case screen (`results/`). |
| `control_budget_study_20261015/engine/` | Source of the simulation engine used for all forty cases: the Python controller package `wsn/`, the ns-3 closed-loop driver `ns3/wsn-closed-loop.cc` with its headers, the run/audit modules, and unit tests. |
| `control_budget_study_20261015/*.py`, `test_mechanism.cc`, `RECREATE.md`, `environment.json` | Study driver (`run_horizon_development.py`, `run_study.py`, `fast_native_run.py`, `audit_case.py`, `build_environment.py`, `prepare_engine.py`), and the recorded execution environment (ns-3.44, commit `43dce6710b8df69685e3479c1d33a571dda714ea`). |

**How the two folders relate.** `control_budget_study_20261015/` holds the executed screen and its raw records. `observation_study_20261016/analyze.py` reads `../control_budget_study_20261015/results/` directly, so both folders are current and both are needed. Neither folder is superseded.

## What is not included (available on reasonable request)

- The native packet-level archive (about 676 MB), SHA256 `fdf083436532c88613103363ea548f243cae0b5b525ab1cbc656ffa7d865674d`. All reported packet-level counts were taken from this archive.
- The compiled, pinned ns-3.44 build and native binary. The driver *source* is in `engine/ns3/`. `environment.json` records the binary hash.

To obtain either item, contact the corresponding author.

## Reproducing Tables III–IV and Figs. 1–2

Requires Python 3.11 or later. `analyze.py` uses only the standard library.

```
cd observation_study_20261016
pip install -r requirements.txt   # matplotlib, only needed for the figures
python analyze.py                 # recomputes paired effects, screen gates, and Tables III and IV from the committed records
python make_figures.py            # redraws Fig. 1 and Fig. 2 from the committed summaries
```

`diagnose_traces.py` and `diagnose_partial_installation.py` read the native archive. They are provided for inspection and do not run without it.

## Re-running the simulations (optional)

The engine under `control_budget_study_20261015/engine/` is the prepared engine exactly as executed. `prepare_engine.py` is already applied and must **not** be run again. Every `.py`, `.cc`, and `.h` file there, together with the study-level sources, matches the `source_sha256` values in `results/horizon_development_registration.json`. Three registered files are left out on purpose, and none is imported by the screen: a scratch compiler-test file (`tmprokgqxpj/test.cc`) and two report-packaging helpers (`tools/build_observable_report.py`, `tools/build_observable_delivery.py`).

Running the screen requires ns-3.44 at the commit above (see `RECREATE.md`, `build_environment.py`), g++ with C++20, numpy (`control_budget_study_20261015/requirements.txt`). Run from `control_budget_study_20261015/`:

```
python run_horizon_development.py --register-only   # after building the driver: checks the frozen registration against the source and binary hashes
python run_horizon_development.py --workers 3
```

Bit-level identity of new runs with the archived ones has only been checked in the pinned environment.

## Results-file glossary

| File | Meaning |
|---|---|
| `control_budget_study_20261015/results/horizon_development_registration.json` | Frozen 40-case configuration list, with source and native-binary SHA256 values recorded before execution. |
| `.../horizon_development_manifest.json` | Per-case index: configuration, audit outcome, radio-energy estimate, and controller updates. |
| `.../horizon_development_case_metrics.csv` | Per-case service and control-DATA metrics (CRLF line endings preserved). |
| `.../horizon_development_admission_audit.json` | Post-bootstrap admission-predicate audit. |
| `.../horizon_development_analysis.json` | Screen-gate evaluation as executed. |
| `.../fast_host_equivalence.json` | Check that the faster host-side energy aggregation matches the original bit for bit. |
| `observation_study_20261016/results/reanalysis.json` | Recomputed screen decisions and Table III/IV summaries. |
| `.../paired_effects.csv` | Matched-cell paired effects against Legacy and Full v2. |
| `.../target_recovery_summary.json`, `partial_installation_summary.json`, `recovery_mechanism_findings.json` | Exploratory diagnosis summaries for the adverse cell (Table IV, Fig. 2, Supplementary Notes). |

## Integrity

Hashes recorded in `results/*.json` are computed over the exact bytes of the record files: LF line endings for JSON and source files, CRLF for the CSV. `.gitattributes` keeps those bytes on checkout.

## Scope and limitations

- This is a **negative-result** study. None of the three observation repairs passes the pre-specified screen, and no positive method claim is made.
- The study has one fixed evaluation layout per size (layout seed 2026101501) and a 2 × 2 × 2 matched matrix (two network sizes, two workloads, two input seeds) for each of five treatments, giving forty cases. It is not a sample of network architectures.
- The screen criteria are algorithmic gates, not statistical non-inferiority tests. No independent confirmation was run.
- The lockout diagnosis is exploratory. It uses existing records from the selected adverse cell and does not estimate how common the mechanism is.

## Citation

Please cite the paper once it is published. Until then, cite this repository using `CITATION.cff` (GitHub's "Cite this repository" button):

> S.-C. Chu, Y.-Y. Zhang, C.-C. Chen, Z. Meng, and J.-S. Pan, "Discovery and Analysis of Recovery Lockout in Sparse-Feedback Wireless Sensor Networks: A Negative Result Study on Observation Repairs," public materials, v1.0-submission, 2026. https://github.com/ya-yu-zhang/wsn-recovery-lockout-nr

## License

- Code (all `.py`, `.cc`, and `.h` files) is released under the MIT License: [`LICENSE`](LICENSE).
- Data records, numerical summaries, figures, protocols, and the manuscript text are released under Creative Commons Attribution 4.0 International: [`LICENSE-DATA`](LICENSE-DATA).
