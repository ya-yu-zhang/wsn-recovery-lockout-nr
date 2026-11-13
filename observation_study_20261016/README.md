# Forty-case screen — analysis, figures, and notes

This folder holds the analysis scripts, committed numerical summaries, original
figures, and Repository Notes R1–R6 (named Supplementary Notes S1–S6 here) for
the forty-case observation-repair screen.

These materials support the manuscript

*"Multi-Level Verification and Validation of a Packet-Level Wireless Sensor Network Simulation: Preregistered Docking and Trace-Driven Replay of Confirmation-Contract Lockout"*

They recompute Table 3 and Supplementary Table S2 and draw the original versions
of Figs. 2–3. The diagnostic chain in Supplementary Table S3 is taken from the
same adverse-cell records. The later vector figures in `../figures_v2/` were
redrawn from these records (and from the V&V summaries) by `make_figures_v2.py`.

An earlier standalone manuscript text that used to live in this folder is **not**
redistributed here. The notes in `supplementary_notes.md` are unchanged scientific
appendices; they are not a substitute for the current manuscript.

Correspondence: Jeng-Shyang Pan, jspan@ieee.org

## Reproduce

```
python analyze.py          # standard library only
python make_figures.py     # requires matplotlib (see requirements.txt)
```

`analyze.py` reads `../control_budget_study_20261015/results/` directly.

`diagnose_traces.py` and `diagnose_partial_installation.py` are provided for
inspection. They require the native packet-level archive (about 676 MB,
SHA256 `fdf083436532c88613103363ea548f243cae0b5b525ab1cbc656ffa7d865674d`),
which is available from the corresponding author on request and is not in
this repository.
