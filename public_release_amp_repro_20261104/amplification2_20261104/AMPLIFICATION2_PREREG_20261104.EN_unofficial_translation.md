# Unofficial English translation — Amplification-2 pre-registration

**Unofficial English translation; the Chinese original
`AMPLIFICATION2_PREREG_20261104.md` is authoritative.** That original is
hash-locked and is deposited byte-identical (including an absolute path on
the authors' machine). This translation is not a substitute for the original
and is not presented under the original hash.

---

# Second amplification pre-registration: gateway timed drop of install packets to elicit condition C (Amplification-2 Pre-registration)

- **Multiplicity statement.** The first confirmation (`AMPLIFICATION_CONFIRM_REPORT_20261104` / `AMPLIFICATION_PREREG_20261103`) **did not meet the A-tier thresholds** — Joint E1 lockout **0/96** (Wilson 95% CI 0–3.85%), S1/S2/S3 all false. This is the **second attempt**; all inference must disclose multiplicity; the first 0/96 **must** be reported beside this attempt's primary endpoint. Exploratory *p*-values are not used as a pass criterion.
- Registration date: 2026-11-04 (America/Los_Angeles). This file and `results/amplification2_<stage>_registration.json` **must be frozen before any scoring run** of `manip_check` or `confirm`.
- Code location (authors' machine; see the locked original for the recorded path).
- Freeze method: `PYTHONPATH=engine python3 run_amplification2.py --stage <stage> --register-only` writes a registration JSON (all configurations and source/native SHA256 values). A formal run aborts if any file or configuration has drifted.
- Runtime LLM calls: 0. No fabrication; no substitution of cells, arms, or thresholds in light of results; no cells may be added after outcomes have been seen.

## 0. Why the mechanism hypothesis changed (relative to Attempt 1)

Attempt 1 used **S1_overload_R0** (overload + the registered three-relay faults) and selected layouts with **d(4,0) ≥ 54 m**, expecting “a weak last control hop → lost installs → F_s-blind lockout.” Development-layout pilots had produced lockouts, but **confirmation on new layouts was 0/96**, showing that the recipe overfit the development set; geometric hypothesis H2 was not supported.

Mechanism facts that still hold, but whose elicitation method must change:

1. Install confirmation is **not** an independent ACK; it is inferred when the source reports with the **new version** after the install (`BoundedInstallation.observe`).
2. Installs follow the fixed control route 9→5→4→source (`SendInstall`), independent of the data path.
3. Proposition: *T* and no eligible *F_s* ⇒ the gate closes. After an unconfirmed exit, settled service is `installation_unconfirmed` (service unknown), so `positive_recovery_evidence` can open the gate **only** via *F_s*; Joint does not clear the installation object.
4. A permanent `brokenInstall` (rerouting via unreachable 9→7→source) would also fail **new installs after post_exit**, so S2 could not be tested — and is therefore not used.

**Change made in this attempt.** At gateway `SendInstall`, install packets are dropped according to **simulation clock** (`install_dropped`), producing “an install was intended and accounted for, but the source did not receive it → no version confirmation.” After the drop window, delivery resumes, so post_exit has an opportunity to open the gate and complete an install. Elicitation **does not depend** on d(4,0) or on overload+R0 geometric pressure.

## 1. Selected elicitation manipulation (primary recipe M1)

| Field | Frozen value |
|---|---|
| Name | `M1_drop_both_0_200_dn36` |
| `dropInstallStartSec` | 0 |
| `dropInstallEndSec` | 200 |
| `dropInstallMask` | 3 (source 0 and source 1) |
| scenario | `multi_failure` |
| faults | `[[145,3],[225,6]]` (**only** downstream relays 3 then 6; source first-hop 2 is retained; **not** the cause of confirmation loss, only an S2 service-impairment background; decoupled from Attempt-1 overload+R0 and d(4,0) layout selection) |
| Everything else | 10 nodes, generation_stop 330 s, action deadline 320 s, local15_event, unified control budget, evidence protection, version cadence, FIFO, epoch certificates, report retry, thresholds / *F_s* / packet formats / driver as in Attempt 1 (the native driver gained the three CLI options above; defaults off equal the previous behaviour) |

**In one sentence.** During [0, 200) s the gateway drops install packets to both sources (the direct cause of confirmation loss), thereby opening an unconfirmed window independently of layout geometry; the preregistered removal of downstream relays 3/6 is only a service-impairment background; delivery resumes after 200 s so that post_exit can be tested.

**Why this is decoupled from geometry.** Confirmation loss is determined by a gateway clock drop. It does not read node coordinates or d(4,0) and does not use overload plus control-route pressure to select cells. The downstream 3/6 fault table is applied uniformly to all confirmation layouts, with no geometric filter.

### Appendix alternative (not the primary confirmation recipe; consider only if M1's manipulation check fails and a third registration is opened)

`M2_drop_src0_0_200_downstream`: mask=1 (drop only source 0) + faults `[[145,3],[225,6]]` (downstream relays, source first-hop 2 retained). Intent: asymmetric lack of confirmation plus possible service impairment; still no d(4,0) layout selection.

## 2. Layered design

### Layer A — manipulation check (`manip_check`)

**Aim.** Verify that the manipulation stably produces a window of “no confirmation and no eligible *F_s*” — **not** an A-tier endpoint.

- Cells: 4 new layouts `budget_10_{2026110401..404}` × 2 input seeds `2026110601..602` = **8 Joint cells**; the same cells are also run with `post_exit` as a recovery smoke test (16 runs in total). Layouts and seeds do not appear in the first confirmation or in development pilots.
- **Layer-A success (per Joint cell):** (i) at least one `abandoned_unconfirmed` and no `late_confirmation`; (ii) at least one `install_dropped` in the protocol log; (iii) after the first unconfirmed exit and before the action deadline, the number of *allowed* evaluated admissions with `reason=installation_unconfirmed` is **0** (no *F_s* unlock).
- **Amplification rule (frozen).** If **≥ 6 of 8** Joint cells (≥ 75%) meet Layer A, confirmation may proceed and the recipe/thresholds are not changed. If fewer than 6/8: **stop** within this registration; do not amplify. Any further change of the manipulation requires a new, third pre-registration and disclosure.
- Analysis script: `analyze_amplification2_manip.py` (frozen with the registration).

### Layer B — lockout endpoint and A-tier (`confirm`)

Executed only after the Layer-A amplification rule is met. Success uses the **same E1 / opened / S1–S3** definitions as Attempt 1 (`analyze_amplification_confirm.py` logic; path prefix `amplification2_confirm`).

- Layouts: `2026110410..417` (8, new, not used in manip_check or Amplification-1).
- Inputs: `2026110611..616` (6).
- Cells: 8×6 = **48 cells**; 8 arms per cell → **384** closed-loop runs (fewer than Attempt 1's 768 because the manipulation is stronger and a higher incidence is expected; independent layout coverage is still required).
- Arms: the same as Attempt 1 (joint / post_exit / sham_release / wait_extend / fs_relax_scoped / thresh_relax_scoped / fs_relax_global / thresh_relax_global).

**A-tier thresholds (unchanged):**

- **S1:** Joint E1 lockout cells ≥ 3, covering ≥ 2 layouts.
- **S2:** Among those lockout cells, post_exit opened ≥ 2 (opened: after the exit, ≥ 1 authorisation and ≥ 1 install, and worst-source service ≥ +1.0 pp versus Joint; post_exit also requires the first-exit time to match Joint).
- **S3:** On every S2-successful cell, at least one competitor (`wait_extend` or `thresh_relax_scoped`) does **not** open; and sham_release is bit-identical to Joint on all confirmation cells.
- A-tier ⇔ S1 ∧ S2 ∧ S3 (S4 is a writing constraint: a conditional boundary, not a better protocol).

## 3. Stopping rules

1. manip_check: all 16 runs are completed in one campaign (or the full registered set without a limit); mask/window are not changed because of early results.
2. If Layer A is not met: stop, do not enter confirm, and report a manipulation failure.
3. confirm: all 384 runs are completed in one campaign; no early stop and no added cells or inputs; on a crash, keep `FAILED_ATTEMPT.txt`, rerun the same configuration, and record it in the report.
4. Runs that fail the native audit are retained; cells that contain a failed run are excluded from the S1–S3 numerators.
5. If S1 is not met: **stop pursuing A-tier**; the write-up remains a rare pathology plus a **double negative confirmation** (first geometric recipe 0/96, plus a second direct-drop attempt that did not meet the lockout threshold). The contribution standing would remain at the margin of submitability, or the work would be directed to a negative-result venue.
6. If S1 is met but S2 or S3 is not: report “lockout can be elicited, but the specificity of *T* was not reproduced.”
7. It is **forbidden** to change this pre-registration's manipulation parameters, cell list, or thresholds after any scoring result has been seen.

## 4. Side-by-side reporting with Attempt 1 (required in the main text / supplement)

| Attempt | Pre-registration | Induction | Joint E1 | S1 | S2 | S3 |
|---|---|---|---|---|---|---|
| 1 | AMPLIFICATION_PREREG_20261103 | S1_overload_R0 + d(4,0) stratification | **0/96** | no | no | no |
| 2 (this registration) | AMPLIFICATION2_PREREG_20261104 | M1_drop_both_0_200_dn36 (drop + downstream 3/6 co-intervention) | (fill after confirmation) | (fill) | (fill) | (fill) |

Multiplicity: both primary endpoints are disclosed; exploratory contrasts or manip_check incidence must not replace S1.

## 5. Data availability (as registered)

To be made public: this pre-registration, `amplification2_*_registration.json`, SHA256 values of the frozen analysis scripts and sources, SHA256 of the native `wsn-closed-loop.cc`, summary JSON, and `install_dropped` counts in the protocol logs. Do not publish a fabricated or filtered subset as if it were the full table.

## 6. Claim bounds (S4)

Even if A-tier is met, the claim remains a **conditional confirmation-contract pathology boundary** (persistent lockout is possible under *T* ∧ ¬*F_s*; releasing only *T* can reopen the gate). It does **not** propose a better routing or transport protocol. The induction is a **controlled gateway drop** (an external manipulation). Extrapolation to “natural wireless loss” must remain cautious, and the first attempt's natural-pressure negative must be reported alongside.

## 7. Risks known at registration

1. **Strictness of E1.** E1 requires that, after the last unconfirmed exit and before the deadline, **every** evaluated admission has settled reason `installation_unconfirmed`. A brief `missing_fresh_source` also yields a non-lockout (already seen in smoke tests at 1/28 steps). Layer A does not require E1; S1 still uses the frozen E1.
2. **Service-gain / *F_s* tension.** Downstream 3/6 are intended to lower service during lockout so that S2 can be judged; if source-side *F_s* thereby becomes eligible, the gate opens and E1 fails. This tension is acknowledged in advance; the fault table is not changed after results are seen.
3. **Window length.** end=200 leaves ≥ 120 s for post_exit recovery; the window is not changed because of smoke tests (except under a new registration).
4. **Native-driver change.** A small change to `SendInstall` plus CLI; the protocol records `install_dropped`. Do not fake observations.
5. **If the second attempt is still 0 lockouts:** stop pursuing A-tier (stopping rule 5).

## Appendix A: disclosure addendum before confirm start (2026-11-04; not a rescoring amendment)

This appendix does **not** change Sections 1–3: recipe M1, E1, S1–S3, the cell/arm lists, or the stopping rules. It only records process facts and disclosure duties that already held before the confirmation scoring run.

1. **Layer-A status (before confirm).** `manip_check` has been completed; Joint Layer A succeeded in **8/8** cells, so the amplification rule is met. On manip_check, exploratory strict E1 incidence was **2/8**, and non-lockout cells show mixing of `missing_fresh_source` (MFS) and `installation_unconfirmed` (IU). This must **not** be used to rewrite the E1 success definition, to relax IU-only, or to change the confirmation sample size or cell list. E1 remains **IU-only**.
2. **Registration before scoring.** The confirm stage must first run `python3 run_amplification2.py --stage confirm --register-only`, generating and freezing `results/amplification2_confirm_registration.json` (all 384 configurations and source/native/this-preregistration SHA256 values), and **only then** may the first scoring run proceed. The registration file's mtime and SHA256 must be written into the confirmation report so that reviewers can check “registered, then run.”
3. **Co-intervention disclosure.** Primary recipe `M1_drop_both_0_200_dn36` applies the gateway install drop (`dropInstall*`) **jointly** with faults `[[145,3],[225,6]]`. S1/S2/S3 are estimated under the joint condition “drop installs + downstream relay removals” and must **not** be written as the marginal effect of “dropping installs alone.” The drop remains the direct mechanism of confirmation loss; the downstream removals are the preregistered service-impairment background.
4. **S4 / methodological bounds.** Induction is a **controlled gateway drop** (external manipulation). Extrapolation to natural wireless loss must be cautious. The main text / supplement must report this attempt alongside Attempt-1 Joint E1 **0/96** (multiplicity).
