# Numbers cross-check script

`check_phase23_numbers.py` recomputes Phase-2/3 numbers from the JSON files in
this V&V package and checks that they appear in the manuscript LaTeX.

The manuscript source and the unredacted registration files are **not** part of
this public deposit. To run the checker, set `SIMPAT_TEX_DIR` to a directory
that contains `manuscript.tex` and `supplementary.tex`, and provide the
unredacted registrations (available to the editor and reviewers on request).

Reviewers who only need the frozen Amplification endpoints should use

```
python3 ../../public_release_amp_repro_20261104/scripts/print_paper_endpoints.py
```

instead. No manuscript file is required for that path.
