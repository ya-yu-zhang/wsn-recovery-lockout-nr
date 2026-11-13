# Theory–Code Digital Twin Map

This repository’s analysis and controller modules were co-designed with the
manuscript’s Proposition 1 / confirmation-contract vocabulary. The table below
is the reviewer-facing “digital twin”: every primary claim symbol maps to a
named function or CLI flag. Paths are relative to this package
(`theory_code_refs/` mirrors the study tree; ablation copies also live under
`ablation_study_20261103/`).

**Claim bound:** code implements a *diagnostic protocol* for a *conditional*
recovery boundary under sparse feedback. It does **not** claim a better routing
protocol or natural lockout prevalence.

| # | Manuscript symbol / claim | Code locus | What the code does |
|---|---------------------------|------------|--------------------|
| 1 | **Prop.1 premise T** (confirmation-contract / transaction stays open after unconfirmed install exit) | `theory_code_refs/contract_ablation.py` module docstring; Joint arm (`contract='joint'`) | Documents that only premise T is varied; Joint keeps the global contract after `abandoned_unconfirmed`. |
| 2 | **IU** (`installation_unconfirmed`) | `analyze_contract_ablation.post_exit` → `reason == 'installation_unconfirmed'` | IU is the settled-service reason that blocks admission after an unconfirmed exit. |
| 3 | **E1 (IU-only lockout to stop)** | `post_exit(...).lockout_to_stop` in `analyze_contract_ablation.py` | `lock = all(reason==IU and not install)` from first/last exit to `action_stop`. **Not** widened to MFS. |
| 4 | **F_s** (failure-eligibility / failure-state rule) | `contract_ablation.py` docstring (“No … failure-eligibility rule (F_s) … is changed”); Amp arms `fs_relax_*` in `amplification_arms.py` / `amplification2_stages.ARMS` | PostExit ablation does **not** touch F_s; competing `fs_relax_*` arms are exploratory and **not** S3 adjudicators. |
| 5 | **PostExit** (T-only release / ablation arm) | `PostExitMixin` in `contract_ablation.py`; factory `make(base)` → `PostExit*` | On `contract=='post_exit'`, after `abandoned_unconfirmed` and no pending feedback TX, clears `self.installation` so admission can re-evaluate from observed per-source state. |
| 6 | **Abandoned unconfirmed exit** | `analyze_amplification.detail` / `post_exit` history filter `outcome=='abandoned_unconfirmed' && closed && !late_confirmation` | Defines the exit clock that starts the lockout window. |
| 7 | **Amp-2 M1 induction** (gateway timed install drop) | `amplification2_stages.M1` (`drop_install_{start,end}_sec`, `drop_install_mask=3`); `wsn-closed-loop.cc` `dropInstallStartSec/EndSec/Mask` + `install_dropped` protocol event | Geometry-decoupled confirmation loss: mask=3 drops both sources’ install packets in `[0,200)`. |
| 8 | **Co-intervention** (downstream relay removals) | `M1['faults']=[[145,3],[225,6]]` in `amplification2_stages.py` | Service-harm backdrop; **not** the confirmation-loss cause; S1 is joint (drop + faults), not pure-drop marginal. |
| 9 | **Arm set** (Joint / PostExit / sham / competitors) | `amplification2_stages.ARMS` | Eight arms including pre-registered competitors `wait_extend`, `thresh_relax_scoped` and exploratory `fs_relax_*`. |
| 10 | **opened(·)** (gate re-open with explained gain) | `analyze_amplification_confirm.opened` | `authorized≥1 ∧ installs_after_exit≥1 ∧ Δservice≥1.0 pp`. |
| 11 | **S1** (≥3 IU lockout cells, ≥2 layouts) | `analyze_amplification2_confirm.main`: `S1 = len(lock)≥3 and #topologies≥2` | Confirm Attempt-2 met **26/48**, **8/8** layouts. |
| 12 | **S2** (PostExit opens on lockout cells, same first-exit time) | same file: `pe_ok` requires `post_exit.opened` and `first_exit_s == joint_first_exit_s` | Confirm: **26/26**. |
| 13 | **S3** (competitor non-replication + sham identity) | `COMPETING=('wait_extend','thresh_relax_scoped')`; `S3 = pe_ok ∧ sham_ok ∧ any(comp[k]==∅)` | Confirm: both competitors opened **0** on S2 cells; sham **48/48** identical to Joint. |
| 14 | **A_tier** | `A_tier = S1 ∧ S2 ∧ S3` | Confirm JSON: `true` (controlled induction). |
| 15 | **Attempt-1 negative** (natural / geometric pressure) | `amplification1_20261103/AMPLIFICATION_CONFIRM_RESULTS_20261104.json` → `incidence.overall = [0,96]` | Must be reported **alongside** Attempt-2; not overwritten by Amp-2 success. |
| 16 | **Registration freeze** | `amplification2_confirm_registration.json` SHA256 `1f37be33…6a24`; receipt + results fields | `--register-only` before scoring; scripts re-hash on every zero-friction run. |
| 17 | **Horizon / budget controllers under PostExit** | `horizon_controller.py` (`HorizonController` et al.) + `FACTORIES` in `contract_ablation.py` | PostExit is a mixin over the same horizon/budget controllers — shared engineering, not a one-off fork. |
| 18 | **Exploratory MFS dilution** | `AMPLIFICATION2_CONFIRM_RESULTS_20261104.json` → `exploratory_MFS` | **22/48** cells lost strict E1 solely from MFS mix while gate stayed closed; **does not** redefine E1. |
| 19 | **Zero-friction paper endpoints** | `scripts/print_paper_endpoints.py` | Stdlib-only console print of the multiplicity table + SHA (no ns-3). |
| 20 | **Sham release** (implementation sanity) | arm `sham_release`; identity check in confirm analyzers | Bitwise service/control identity with Joint → negative not an implementation crash. |

## Design note (not a post-hoc dump)

- Prop.1 / PostExit / IU lockout definitions were registered in
  `contract_ablation.py` **before** ablation runs (file header).
- Amp-2 mechanism change (dropInstall) was frozen in
  `AMPLIFICATION2_PREREG_20261104.md` + `amplification2_stages.M1` **before**
  confirm scoring; registration SHA precedes result mtime
  (`06:13:57` vs results `06:20`, America/Los_Angeles).
- The Amp-2 co-intervention (gateway timedrop + downstream faults
  `[[145,3],[225,6]]`) is that frozen preregistered recipe, not a later
  adjustment after scoring. Sham is bit-identical to Joint; competitor and
  PostExit arms are scored on the same induced state (within-recipe S2/S3
  contrasts, not comparisons across different induction conditions).
- Endpoint thresholds S1–S3 are shared code between Attempt-1 and Attempt-2
  analyzers; Attempt-2 did **not** redefine E1 after seeing MFS dilution.

## How to spot-check the twin

```bash
python3 scripts/print_paper_endpoints.py
python3 scripts/verify_registration_sha.py
# Optional: open theory_code_refs/contract_ablation.py and jump to PostExitMixin
```
