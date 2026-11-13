# figures_v2 — manuscript figures redrawn from frozen records

Figures for

*"Multi-Level Verification and Validation of a Packet-Level Wireless Sensor Network Simulation: Preregistered Docking and Trace-Driven Replay of Confirmation-Contract Lockout"*

**Regenerate:** from this directory, `python3 make_figures_v2.py`, then
`python3 cvd_check.py`.

`make_figures_v2.py` resolves paths relative to the repository root (the parent
of this folder).

## Inputs (read-only, frozen)

Hashes are written to `figure_sources_sha256.json` (paths in that file are
repository-relative):

- `observation_study_20261016/results/paired_effects.csv`
- `observation_study_20261016/results/recovery_mechanism_findings.json`
- `observation_study_20261016/results/partial_installation_diagnosis.json`
- `phase2_study_20261111/flocklab/results_full/summary.json`
- `phase2_study_20261111/doe/summary.json`

Every plotted number is asserted against the frozen values quoted in the
manuscript before drawing. The only derived quantities are Wilson 95% intervals,
computed from the frozen counts.

## Style (`figstyle.py`)

- Liberation Sans (Arial metrics), 7–8 pt; panel letters 9 pt bold; every text
  element is asserted ≥ 7 pt.
- 140 mm final width, included at `width=140mm`, so no scaling.
- PDF/EPS with embedded TrueType fonts, plus 600-dpi PNG previews.
- Okabe–Ito colours: Joint #D55E00, PostExit #0072B2, sham #999999,
  wait_extend #E69F00, thresh_relax #009E73.
- Heat map uses cividis.

Colour checks (`cvd_check/`): greyscale plus deutan, protan and tritan
simulations (Machado 2009). Joint and PostExit also differ by marker shape
(circle versus square).

| File | Role |
|---|---|
| Fig1 | State machine |
| Fig2 | Forty-case paired effects |
| Fig3 | Adverse-cell diagnosis |
| Fig4 | V&V overview |
| Fig5 | FlockLab replay (Wilson CIs, k/n) |
| Fig6 | DOE phase diagram |
| FigS1 | Supplementary factorial main effects |
| Graphical_abstract | Optional separate upload |

Correspondence: jspan@ieee.org
