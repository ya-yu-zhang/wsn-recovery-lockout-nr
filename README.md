# Public materials for a packet-level WSN simulation V&V study

Public materials for the manuscript

*"Multi-Level Verification and Validation of a Packet-Level Wireless Sensor Network Simulation: Preregistered Docking and Trace-Driven Replay of Confirmation-Contract Lockout"*

(Shu-Chuan Chu, Ya-Yu Zhang, Chih-Cheng Chen, Zhenyu Meng, Jeng-Shyang Pan).

Repository: https://github.com/ya-yu-zhang/wsn-recovery-lockout-nr

Corresponding author: Jeng-Shyang Pan, jspan@ieee.org

**Staging notice.** This tree is a *local snapshot* of the intended public repository. It has **not** been pushed, and no pull request, Zenodo/OSF record, or manuscript Data Availability change to “deposited” has been made. After an authorised push, replace this notice with the resulting commit hash.

## One-command reviewer path (no ns-3, no extra Python packages)

Requires only Python 3 (standard library). From the Amplification / ablation package root:

```
cd public_release_amp_repro_20261104
python3 scripts/print_paper_endpoints.py
python3 scripts/verify_registration_sha.py
```

Expected frozen endpoints (must match the manuscript):

- Attempt-1 Joint E1 = **0/96**
- Attempt-2 Joint E1 = **26/48**, layouts **8/8**
- S2 post_exit opened = **26/26**
- S3: `wait_extend` opened = **0**, `thresh_relax_scoped` opened = **0**, sham **48/48** identical to Joint
- `A_tier = true` under **controlled induction** only (not a natural-prevalence estimate)
- Registration SHA256 = `1f37be33c2ebd65766da85defb33bbacf5acb21c6544c1c52645f50a184f6a24`
- Exploratory MFS dilution = **22/48** (IU-only E1 unchanged)

PostExit is a **T-only ablation arm**, not a recommended deployment protocol.

## What is included

| Folder | Contents |
|---|---|
| `control_budget_study_20261015/` | Observation-controller sources, pre-specified repair protocols, and the registration, manifest, admission-audit, analysis, and per-case metric records of the **forty-case screen**. Engine source (`engine/wsn/`, `engine/ns3/wsn-closed-loop.cc` and headers), study drivers, and unit tests. |
| `observation_study_20261016/` | Analysis and figure scripts, numerical summaries, original Figs. 1–2 (PNG/EPS), and Repository Notes R1–R6 (named Supplementary Notes S1–S6 in this folder). These recompute Table 3 and Supplementary Table S2 and draw the original versions of Figs. 2–3. |
| `public_release_amp_repro_20261104/` | Lightweight Amplification-1 / Amplification-2 and confirmation-premise **ablation** package (preregistrations, frozen Amplification-2 registration, confirmation reports and JSON summaries, case summaries, theory–code map, zero-dependency endpoint scripts). |
| `phase2_study_20261111/` | Curated multi-level **V&V** package: redacted Phase-2/2b registrations and preregistrations with a redaction log, deviation log (redacted), SimPy mirror and scorers, FlockLab trace-driver source and pinned binary, factorial design and result summaries, figure scripts, and a numbers cross-check script. |
| `figures_v2/` | Scripts and vector figures that redraw every figure of the present manuscript version from frozen result files (Liberation Sans, 140 mm, Okabe–Ito / cividis). |

`observation_study_20261016/analyze.py` reads `../control_budget_study_20261015/results/` directly, so both forty-case folders are required. Neither is superseded.

## Registrations and hash-locked files

Printed SHA256 values in the manuscript (§7.1 and Supplementary Table S11) are those of the **unredacted originals**.

- The Amplification-2 confirmation registration `public_release_amp_repro_20261104/amplification2_20261104/amplification2_confirm_registration.json` is deposited **byte-identical**. SHA256 `1f37be33c2ebd65766da85defb33bbacf5acb21c6544c1c52645f50a184f6a24`.
- Five Phase-2 / Phase-2b registration files contain internal correspondence. This repository holds only redacted copies `*_REDACTED.*` and `phase2_study_20261111/REDACTION_LOG.md` (field, replacement, original SHA256, copy SHA256). A modified file is **never** presented under the original hash. Public readers cannot recompute the five original hashes from the redacted copies. The unredacted originals, whose SHA256 values are printed in the manuscript, are available to the editor and reviewers on request:

  - `REGISTRATION_PHASE2_20261111.json` — `caf07cc98efd5e2d6b4fa60d5d5c3bf6cdb622d8f9ea9d70caac3ea6ca84ab4f`
  - `ADDENDUM_PHASE2_20261111b.md` — `fc637ae54afaae645fa21c2ac7439476db9f0fea46c601ed75d3dcf2f3a96dec`
  - `REGISTRATION_PHASE2B_20261111.json` — `9afb4dc3180c04367edc857187404997cb5a4273ac866b6507dd2ffc83795a23`

  Two further preregistration Markdown files are listed *inside* those registrations (`PREREG_PHASE2_20261111.md` `808072be…c4ae`, `PREREG_PHASE2B_20261111.md` `ec219caa…2c54`) and are likewise redacted in public.

- Other hash-locked scripts, designs, and binaries are deposited byte-identical. Some of them still contain absolute paths from the authors' machine; those paths are not claims that the files exist at those locations in this repository.
- Several locked Chinese texts (notably `AMPLIFICATION2_PREREG_20261104.md`) are accompanied by unofficial English translations labelled as such; the Chinese original is authoritative.
- Registrations were not lodged with a public trial registry; their timing is attested by commit history and hashes.
- Result JSONs record `"runtime_LLM_calls": 0`. No language model is invoked by the controller, the simulator, or the mirror at run time.

## What is not included (available on reasonable request, identified by SHA256)

Contact the corresponding author. These raw trees are **not** part of this deposit.

- Native packet-level archive of the forty-case screen (about 676 MB), SHA256 `fdf083436532c88613103363ea548f243cae0b5b525ab1cbc656ffa7d865674d`. All reported packet-level counts for the screen were taken from this archive. The two diagnosis scripts in `observation_study_20261016/` require it.
- The compiled, pinned ns-3.44 build used for the forty-case screen. The driver *source* is in `control_budget_study_20261015/engine/ns3/`. `environment.json` records the binary hash.
- Raw Amplification-1 closed-loop runs (768 runs; on the order of 9.6 GB).
- Raw Amplification-2 closed-loop runs (384 runs; on the order of 2.8 GB).
- Raw ablation / generalization case trees (on the order of 1.7 GB).
- Raw V&V run outputs: `scratch_phase2/doe` (about 3.56 GB, 432 runs) and `scratch_phase2/flocklab_full` (about 1.25 GB). Paths that used to point at those trees are written as `raw_on_request/…` in unlocked files.
- Unredacted copies of the five Phase-2 / 2b registration files (editor and reviewers only).

Bit-level identity of new simulation runs with the archived ones has only been checked in the pinned environments recorded with each study.

## Reproducing the forty-case screen tables and original figures

Requires Python 3.11 or later. `analyze.py` uses only the standard library.

```
cd observation_study_20261016
pip install -r requirements.txt   # matplotlib, only needed for the figures
python analyze.py                 # recomputes paired effects, screen gates, and Tables 3 and S2 from the committed records
python make_figures.py            # redraws the original Figs. 1 and 2 from the committed summaries
```

The manuscript-version figures in `figures_v2/` are redrawn from the same forty-case records plus the V&V summaries:

```
cd figures_v2
python3 make_figures_v2.py
python3 cvd_check.py
```

## Re-running the forty-case simulations (optional)

The engine under `control_budget_study_20261015/engine/` is the prepared engine exactly as executed. `prepare_engine.py` is already applied and must **not** be run again. Every `.py`, `.cc`, and `.h` file there, together with the study-level sources, matches the `source_sha256` values in `results/horizon_development_registration.json`. Three registered files are left out on purpose, and none is imported by the screen: a scratch compiler-test file (`tmprokgqxpj/test.cc`) and two report-packaging helpers (`tools/build_observable_report.py`, `tools/build_observable_delivery.py`).

Running the screen requires ns-3.44 at commit `43dce6710b8df69685e3479c1d33a571dda714ea` (see `RECREATE.md`, `build_environment.py`), g++ with C++20, and numpy (`control_budget_study_20261015/requirements.txt`). Run from `control_budget_study_20261015/`:

```
python run_horizon_development.py --register-only   # after building the driver: checks the frozen registration against the source and binary hashes
python run_horizon_development.py --workers 3
```

## Scope and limitations

- The forty-case screen is a **negative-result** study of three registered observation repairs. No positive method claim is made for those repairs.
- Amplification-1 (natural-pressure recipe) yielded Joint E1 lockout in **0/96** cells. Amplification-2's **26/48** lockouts are properties of a **controlled** gateway install-drop jointly with fixed downstream relay faults, not a spontaneous deployment rate. A-tier evidence holds only under that controlled induction, never as natural prevalence.
- PostExit releases only the unconfirmed-installation premise *T*. It is an ablation, not a recommended protocol, and it is not uniformly beneficial on non-induced layouts.
- V&V: Mode C docking passed 248/248; free-running docking (Mode F and Mode F′) failed as registered; FlockLab is **trace replay**, not a hardware run; the 432-run factorial passed one conformance hypothesis and failed another on an endpoint-definition boundary case. These failures are part of the result.
- Some unlocked reports are provided as English public versions of Chinese working notes. Hash-locked Chinese originals remain authoritative where a translation is marked unofficial.
- The study uses ns-3.44 with IEEE 802.15.4 unscheduled access and this controller's observation and budget model.

## Citation

Please cite the paper once it is published. Until then, cite this repository using `CITATION.cff` (GitHub's "Cite this repository" button):

> S.-C. Chu, Y.-Y. Zhang, C.-C. Chen, Z. Meng, and J.-S. Pan, "Multi-Level Verification and Validation of a Packet-Level Wireless Sensor Network Simulation: Preregistered Docking and Trace-Driven Replay of Confirmation-Contract Lockout," public materials, 2026. https://github.com/ya-yu-zhang/wsn-recovery-lockout-nr

## License

- Code (all `.py`, `.cc`, and `.h` files), except ns-3-derived drivers noted below, is released under the MIT License: [`LICENSE`](LICENSE).
- Data records, numerical summaries, figures, protocols, and notes are released under Creative Commons Attribution 4.0 International: [`LICENSE-DATA`](LICENSE-DATA).
- The ns-3 closed-loop driver and the FlockLab trace driver (`control_budget_study_20261015/engine/ns3/wsn-closed-loop.cc`, `phase2_study_20261111/flocklab/wsn-closed-loop-trace.cc` and `trace_link_error_model.h`) are derived from ns-3 and are licensed under the GNU General Public License v2.0 (the ns-3 license).
- The SimPy 4.1.1 library used by the docking mirror is **not** vendored here; install SimPy 4.1.1 separately. Some hash-locked registration files still mention a vendored copy used on the authors' machine; that copy is not part of this deposit.
- Prepared FlockLab subgraphs in `phase2_study_20261111/flocklab/traces/` are derived from the FlockLab link-quality dataset, available under CC BY 4.0 (Jacob et al., Zenodo, doi:10.5281/zenodo.3727526).
