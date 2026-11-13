"""Redraw of all data and explanatory figures for the SIMPAT submission (2026-11-11).
Data are read only from frozen result files; every plotted value is asserted against the frozen numbers
reported in the manuscript before drawing. No simulation is run and no value is transformed except
Wilson 95% intervals, which are recomputed from the frozen counts exactly as in the manuscript."""
import json, math, csv, statistics, hashlib
from pathlib import Path
import numpy as np
from figstyle import plt, MM, W140, OI, ARM, panel, save
import matplotlib
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap
OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / 'observation_study_20261016/results'
P2 = ROOT / 'phase2_study_20261111'
J = lambda p: json.loads(Path(p).read_text())
SOURCES = {}
def src(p):
    p = Path(p); SOURCES[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest(); return p
def wilson(k, n, z=1.959963984540054):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)

# ---------------------------------------------------------------- Fig. 1 state machine (explanatory)
def fig_state_machine():
    fig, ax = plt.subplots(figsize=(W140, 80 * MM)); ax.set_xlim(0, 140); ax.set_ylim(10, 90); ax.axis('off')
    fig.subplots_adjust(0, 0, 1, 1)
    C_J, C_L, C_P, C_G = '#333333', OI['vermillion'], OI['blue'], OI['green']
    def box(x, y, w, h, title, sub, ec=C_J, fc='white', ls='-'):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle='round,pad=0.6,rounding_size=2', fc=fc, ec=ec, lw=0.9, ls=ls))
        ax.text(x, y + h * 0.22, title, ha='center', va='center', fontsize=7.5, fontweight='bold')
        ax.text(x, y - h * 0.2, sub, ha='center', va='center', fontsize=7, linespacing=1.15)
    box(17, 70, 28, 12, 'S1 Authorized', r'$\Phi=1$; install issued')
    box(66, 70, 34, 12, 'S2 Install wait', '$T$ pending; at most 10 s,\none retry per source')
    box(116, 70, 34, 12, 'S3 Confirmed', '$T$ = Confirmed;\n' + r'$\Psi$ computable (Good or Poor)')
    box(62, 40, 30, 12, 'S4 Unconfirmed exit', 'wait ended;\n$T$ = Unconfirmed')
    box(116, 40, 36, 14, 'S5 Lockout', r'$\Psi$ = Unknown (IU);' + '\nall $F_s$ Ineligible, ' + r'$\Phi=0$', ec=C_L, fc='#FBE6D9')
    box(17, 22, 30, 12, 'S6 Released (PostExit)', 'per-source observed view;\n' + r'$\Psi$ from received versions', ec=C_P, fc='#E3EEF7', ls='--')
    def arr(p, q, txt=None, col=C_J, ls='-', rad=0.0, tx=None, ty=None, ha='center'):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle='-|>', mutation_scale=8, lw=0.9, color=col, ls=ls, connectionstyle=f'arc3,rad={rad}', shrinkA=1, shrinkB=1))
        if txt:
            ax.text((p[0] + q[0]) / 2 if tx is None else tx, (p[1] + q[1]) / 2 if ty is None else ty, txt, fontsize=7, ha=ha, va='center', color=col,
                    bbox=dict(fc='white', ec='none', pad=0.3), linespacing=1.1)
    arr((31.6, 70), (48.4, 70), 'install', ty=73.5)
    arr((83.6, 70), (98.4, 70), 'all confirm', ty=73.5)
    arr((62, 63.4), (62, 46.6), 'no joint\nconfirmation\nin 10 s', tx=65, ty=55, ha='left')
    arr((77.6, 40), (97.4, 40), 'no eligible $F_s$', tx=87.5, ty=43.5)
    arr((116, 47.6), (116, 63.4), 'late\nconfirmation', col=C_G, tx=119, ty=55.5, ha='left')
    arr((100, 77.5), (24, 77.5), r'$\Psi$ = Poor or some $F_s$ Eligible', col=C_G, rad=0.18, tx=62, ty=84.5)
    arr((46.4, 37), (24, 63.5), 'eligible $F_s$\n(from S4 or S5)', col=C_G, rad=-0.12, tx=32, ty=50)
    ax.add_patch(FancyArrowPatch((134.5, 37), (134.5, 43), arrowstyle='-|>', mutation_scale=8, lw=0.9, color=C_L, connectionstyle='arc3,rad=1.8'))
    ax.text(116, 27.5, 'self-loop under Horizon, Cohort, Closing\n(they do not rewrite $T$ or $F_s$)', fontsize=7, ha='center', va='center', color=C_L)
    arr((98, 33.5), (32.4, 20), 'PostExit: release $T$ in S5 (after an unconfirmed exit)', col=C_P, ls='--', tx=66, ty=17.5)
    arr((8, 28.6), (8, 63.4), r'known $\Psi$ = Poor', col=C_P, ls='--', tx=3, ty=46, ha='left')
    hs = [Line2D([], [], color=C_J, lw=0.9, label='Joint contract'), Line2D([], [], color=C_G, lw=0.9, label='Joint exits from S3–S5'),
          Line2D([], [], color=C_P, lw=0.9, ls='--', label='PostExit ablation (releases $T$ only)')]
    ax.legend(handles=hs, loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.01), handlelength=2.2, columnspacing=1.4)
    save(fig, OUT, 'Fig1')

# ---------------------------------------------------------------- Fig. 2 paired effects
def fig_paired():
    rows = list(csv.DictReader(open(src(OBS / 'paired_effects.csv'))))
    assert len(rows) == 32
    models = ['full_v2', 'horizon', 'cohort', 'closing']; labels = ['Full v2', 'Horizon', 'Cohort', 'Closing']
    get = lambda n, m: [r for r in rows if int(r['nodes']) == n and r['model'] == m]
    red10 = [round(statistics.mean(float(r['control_reduction_vs_legacy_percent']) for r in get(10, m)), 2) for m in models]
    assert red10 == [23.02, 22.80, 22.61, 22.14], red10
    assert round(statistics.mean(float(r['control_reduction_vs_legacy_percent']) for r in get(20, 'full_v2')), 2) == 35.27
    assert round(statistics.mean(float(r['service_vs_legacy_pp']) for r in get(20, 'full_v2')), 2) == 1.51
    seeds = sorted({r['seed'] for r in rows}); assert len(seeds) == 2
    C = '#333333'; mk = {'multi_failure': 'o', 'overload': 's'}; SH = '#EDEDED'
    fig, axes = plt.subplots(2, 2, figsize=(W140, 98 * MM))
    fig.subplots_adjust(left=0.1, right=0.985, top=0.95, bottom=0.25, hspace=0.62, wspace=0.28)
    spec = {(10, 'service_vs_legacy_pp'): (-30.5, 3), (20, 'service_vs_legacy_pp'): (-0.8, 3.2),
            (10, 'control_reduction_vs_legacy_percent'): (8, 38), (20, 'control_reduction_vs_legacy_percent'): (18, 40)}
    for i, n in enumerate((10, 20)):
        for j, field in enumerate(('service_vs_legacy_pp', 'control_reduction_vs_legacy_percent')):
            ax = axes[i, j]; lo, hi = spec[(n, field)]; thr = -0.5 if j == 0 else 20
            ax.axvspan(lo, thr, color=SH, lw=0, zorder=0); ax.axvline(thr, color='black', ls=(0, (1, 1.5)), lw=0.8, zorder=1)
            for y, m in enumerate(models):
                pts = sorted(get(n, m), key=lambda r: (r['scenario'], r['seed']))
                for k, r in enumerate(pts):
                    ax.plot(float(r[field]), y + (k - 1.5) * 0.11, mk[r['scenario']], ms=3.8, mew=0.8, color=C,
                            mfc=C if r['seed'] == seeds[0] else 'white', zorder=3)
                ax.plot(statistics.mean(float(r[field]) for r in pts), y, '|', ms=11, mew=1.6, color='black', zorder=4)
            ax.set_yticks(range(4), labels); ax.set_xlim(lo, hi); ax.set_ylim(3.5, -0.5)
            ax.tick_params(axis='y', length=0)
            ax.set_xlabel('Worst-source service vs. Legacy (percentage points)' if j == 0 else 'Control-DATA reduction vs. Legacy (%)')
            ax.set_title(f'{n} nodes', loc='left', pad=3); ax.set_title(''); ax.text(0, 1.03, f"({'abcd'[2 * i + j]})", transform=ax.transAxes, fontsize=9, fontweight='bold', va='bottom'); ax.text(0.09, 1.035, f'{n} nodes', transform=ax.transAxes, fontsize=7.5, va='bottom')
    hs = [Line2D([], [], marker='o', ls='', color=C, ms=3.8, label=f'Relay removals, input seed {seeds[0]}'),
          Line2D([], [], marker='o', ls='', color=C, mfc='white', ms=3.8, label=f'Relay removals, input seed {seeds[1]}'),
          Line2D([], [], marker='|', ls='', color='black', ms=9, mew=1.6, label='Mean of the four cells'),
          Line2D([], [], marker='s', ls='', color=C, ms=3.8, label=f'Overload, input seed {seeds[0]}'),
          Line2D([], [], marker='s', ls='', color=C, mfc='white', ms=3.8, label=f'Overload, input seed {seeds[1]}'),
          Line2D([], [], color='black', ls=(0, (1, 1.5)), lw=0.8, label='Frozen criterion (−0.5 pp; 20%)'),
          Rectangle((0, 0), 1, 1, fc=SH, ec='none', label='Below service criterion (≤ −0.5 pp; a, c)\nor DATA criterion (< 20%; b, d)')]
    hs = [hs[0], hs[3], hs[1], hs[4], hs[2], hs[5], hs[6]]
    fig.legend(handles=hs, loc='lower left', ncol=2, bbox_to_anchor=(0.02, 0.0), handletextpad=0.4, columnspacing=2.0)
    save(fig, OUT, 'Fig2')

# ---------------------------------------------------------------- Fig. 3 adverse cell (schematic + timeline)
def fig_adverse():
    F = J(src(OBS / 'recovery_mechanism_findings.json')); D = J(src(OBS / 'partial_installation_diagnosis.json'))
    assert F['target_cell'] == [10, 'multi_failure', 2026101511]
    fv, cl = F['full_v2'], F['closing']
    assert fv['checks'] == 15 and fv['gate_blocked'] == 15 and fv['geometry_available'] == 5 and fv['service_reasons'] == {'installation_unconfirmed': 5, 'missing_fresh_source': 10}
    assert cl['checks'] == 15 and cl['gate_blocked'] == 15 and cl['geometry_available'] == 15 and cl['shadow_deficit'] == 11
    fs = cl['first_shadow']; assert fs['time_s'] == 265 and fs['offered'] == [36, 60] and fs['timely'] == [0, 59]
    for m in ('horizon', 'cohort', 'closing'):
        obs = D['models'][m]['observed']; assert len(obs) == 15 and all(o['geometry_available'][0] for o in obs)
        assert {o['service_reason'] for o in obs} == {'installation_unconfirmed'}
    times = [o['time_s'] for o in D['models']['closing']['observed']]; assert times[0] == 245 and times[-1] == 315
    assert F['native_installs'][0] == {'kind': 'fault_injected', 'node': 6, 'time_ns': 225000000000}
    rd = {(r['source'], r['version']): r['path'] for r in F['route_distribution']}; assert rd[(0, 2)] == [0, 8, 6, 9] and rd[(1, 3)] == [1, 4, 5, 9]
    req = [r['time_ns'] / 1e9 for r in F['source0_install_requests']]; assert [round(t) for t in req] == [235, 240]
    jobs = F['source0_install_jobs']; assert all(j['status'] == F['channel_access_failure_enum']['value'] == 225 and j['attempts'] == 0 for j in jobs)
    assert all(c['admitted'] for c in F['source0_install_budget_checks'])
    fig = plt.figure(figsize=(W140, 80 * MM))
    axa = fig.add_axes([0.0, 0.0, 0.33, 0.92]); axb = fig.add_axes([0.35, 0.0, 0.65, 0.92])
    for ax in (axa, axb): ax.axis('off')
    axa.set_xlim(0, 46); axa.set_ylim(0, 74); axb.set_xlim(0, 91); axb.set_ylim(0, 74)
    
    axa.text(1, 75.5, '(a)', fontsize=9, fontweight='bold', va='bottom'); axa.text(8, 75.8, 'Topology after relay removal', fontsize=7.5, va='bottom')
    axb.text(1, 75.5, '(b)', fontsize=9, fontweight='bold', va='bottom'); axb.text(8, 75.8, 'Recovery decisions, 225–315 s', fontsize=7.5, va='bottom')
    pos = {0: (5, 52), 8: (16, 52), 6: (27, 52), 1: (5, 22), 4: (16, 22), 5: (27, 22), 9: (39, 37)}
    def edge(a, b, ok):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        axa.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=7, lw=1.0, shrinkA=8, shrinkB=8,
                                      color='#222222' if ok else '#777777', ls='-' if ok else (0, (3, 2))))
        if not ok: axa.text((x1 + x2) / 2, (y1 + y2) / 2, '×', color='#222222', fontsize=9, ha='center', va='center', fontweight='bold')
    for a, b in ((0, 8), (8, 6), (6, 9)): edge(a, b, False)  # broken route: dark grey dashed
    for a, b in ((1, 4), (4, 5), (5, 9)): edge(a, b, True)
    for n, (x, y) in pos.items():
        fc = '#E8E8E8' if n == 6 else ('#FFFFFF' if n not in (0, 1, 9) else ('#CFCFCF' if n == 9 else '#F2F2F2'))
        axa.add_patch(Circle((x, y), 3.6, fc=fc, ec='#333333', lw=0.8, ls='--' if n == 6 else '-'))
        axa.text(x, y, str(n), ha='center', va='center', fontsize=7.5, fontweight='bold')
    axa.text(27, 58.5, 'removed at 225 s', ha='center', fontsize=7, color='#222222')
    axa.text(3, 64, 'Source 0 keeps v2: 0–8–6–9 (broken)', fontsize=7, color='#222222')
    axa.text(3, 12, 'Source 1 installed v3: 1–4–5–9 (intact)', fontsize=7, color='#222222')
    axa.text(3, 4, 'Node 9: gateway. Schematic positions.', fontsize=7, color='#555555')
    # timeline
    x0, x1, t0, t1 = 6, 84, 220, 320; X = lambda t: x0 + (t - t0) / (t1 - t0) * (x1 - x0); yT = 56
    axb.annotate('', xy=(x1 + 4, yT), xytext=(x0 - 3, yT), arrowprops=dict(arrowstyle='-|>', lw=0.8, color='#333333', mutation_scale=7))
    axb.text(x1 + 5, yT - 4.5, 't (s)', fontsize=7, ha='right', va='top')
    axb.add_patch(Rectangle((X(245), yT - 1.6), X(315) - X(245), 3.2, fc='#E6E6E6', ec='#555555', lw=0.7))
    for t in times: axb.plot([X(t), X(t)], [yT - 1.6, yT + 1.6], color='#555555', lw=0.5)
    axb.plot(X(225), yT, 'o', ms=3.5, color='#555555', zorder=4)
    axb.plot([X(225)] * 2, [yT + 2, 61.5], color='#555555', lw=0.6)
    axb.text(X(225), 62, 'relay 6\nremoved', fontsize=7, ha='center', va='bottom', color='#555555', linespacing=1.05)
    for tt in (235, 240): axb.plot(X(tt), yT, 'o', ms=3, color=OI['sky'], zorder=4)
    axb.plot([X(235), X(240)], [yT + 2.4] * 2, color=OI['sky'], lw=0.8)
    axb.plot([X(237.5)] * 2, [yT + 2.4, 68.5], color=OI['sky'], lw=0.6)
    axb.text(X(237.5), 69, 'install requests', fontsize=7, ha='center', va='bottom', color=OI['sky'])
    axb.plot(X(245), yT, 'o', ms=3.5, color='#000000', zorder=4); axb.plot([X(245)] * 2, [yT + 2, 61.5], color='#000000', lw=0.6)
    axb.text(X(245) - 0.5, 62, 'unconfirmed\nexit', fontsize=7, ha='left', va='bottom', color='#000000', linespacing=1.05)
    axb.plot(X(265), yT, 'D', ms=3.5, color=OI['purple'], zorder=4); axb.plot([X(265)] * 2, [yT + 2, 61.5], color=OI['purple'], lw=0.6)
    axb.text(X(265) - 0.5, 62, 'offline audit\n(no action)', fontsize=7, ha='left', va='bottom', color=OI['purple'], linespacing=1.05)
    for t in (225, 235, 245, 265, 315): axb.text(X(t), yT - 3, f'{t}', fontsize=7, ha='center', va='top')
    axb.text((X(245) + X(315)) / 2, yT - 7.5, '245–315 s: 15 blocked recovery checks (every 5 s)', fontsize=7, color='#555555', ha='center', va='top')
    def note(y, h, title, body, ec):
        axb.add_patch(FancyBboxPatch((3, y), 85, h, boxstyle='round,pad=0.4,rounding_size=1.2', fc='white', ec=ec, lw=0.8))
        axb.text(5, y + h - 1.6, title, fontsize=7, fontweight='bold', va='top', color=ec)
        axb.text(5, y + h - 5.6, body, fontsize=7, va='top', linespacing=1.12)
    note(32.5, 10.5, 'Install at 235 s and 240 s', 'byte credit admits both source-0 requests; each MAC job ends with\nCHANNEL_ACCESS_FAILURE and zero DATA attempts', OI['sky'])
    note(23, 8, 'Horizon, Cohort, Closing: candidates at 15/15 checks', 'reason installation_unconfirmed; no eligible $F_s$; all 15 rejected', '#555555')
    note(13.5, 8, 'Full v2: candidates at 5/15 checks', '5 installation_unconfirmed + 10 missing_fresh_source; all 15 rejected', '#555555')
    note(1, 11, 'Received-only audit at 265 s', 'offered [36, 60], timely [0, 59]: historical deficit identified\n(at 11/15 checks); no recovery action executed', OI['purple'])
    save(fig, OUT, 'Fig3')

# ---------------------------------------------------------------- Fig. 4 multi-level V&V overview (explanatory)
def check(ax, x, y, s, col):  # drawn glyphs so that no symbol font is needed
    ax.plot([x - s, x - s * 0.25, x + s], [y, y - s * 0.75, y + s * 0.9], color=col, lw=1.4, solid_capstyle='round')
def cross(ax, x, y, s, col):
    ax.plot([x - s, x + s], [y - s, y + s], color=col, lw=1.4); ax.plot([x - s, x + s], [y + s, y - s], color=col, lw=1.4)
def void(ax, x, y, s, col):
    ax.add_patch(Circle((x, y), s, fc='none', ec=col, lw=1.1)); ax.plot([x - s * 0.7, x + s * 0.7], [y - s * 0.7, y + s * 0.7], color=col, lw=1.1)
def fig_overview():
    fig, ax = plt.subplots(figsize=(W140, 90 * MM)); fig.subplots_adjust(0, 0, 1, 1); ax.set_xlim(0, 140); ax.set_ylim(0, 90); ax.axis('off')
    ax.add_patch(FancyBboxPatch((1.5, 11), 19, 69, boxstyle='round,pad=0.4,rounding_size=1.5', fc='#F2F2F2', ec='#333333', lw=0.8))
    ax.text(11, 75.5, 'Reference', ha='center', fontsize=7.5, fontweight='bold')
    ax.text(11, 46, 'ns-3.44\npacket-level\nWSN model\n\nfrozen records:\nobservations,\ndecisions,\nevaluation\ntimes\n\nfrozen\nAmplification-2\nrecords\n(SHA256\n1f37be33…)', ha='center', va='center', fontsize=7, linespacing=1.12)
    for x, t in ((25, 'Comparison model or input'), (63, 'Registered endpoint'), (92, 'Verdict'), (104, 'Claim licensed or restricted')):
        ax.text(x, 84, t, fontsize=7.5, fontweight='bold', ha='left')
    G, R, P = OI['green'], OI['vermillion'], '#555555'
    lanes = [('(i) Conditioned docking', 'recorded observations,\ndecisions, evaluation times →\nseparately coded SimPy mirror', 'C1–C4 ≥ 0.95–0.98\non 248 frozen cases', [('pass', 'pass')], 'logic claims hold for the\nrecorded runs'),
             ('(ii) Free-running docking', 'abstract network model\n(± contention submodel) →\nfree-running mirror', 'F1, F2 ≥ 0.95 per arm;\nF3 inside 95% interval', [('fail', 'fail')], 'incidence claims stay with\nthe packet-level model'),
             ('(iii) Trace-driven replay', 'FlockLab measured link\ntraces → trace driver\n(192 runs)', 'completion, native audits,\ningestion audit (R2, R1)', [('fail', 'audit fail')], 'replay results conditional\non the audit; no hardware\nclaim'),
             ('(iv) Registered factorial', '3$^{5-2}$ design of induction\nsettings (432 runs)', 'H1 ≥ 0.95; H2 = 0;\nH3 prospective docking', [('pass', 'H1'), ('fail', 'H2'), ('void', 'H3')], 'conformance across the\ndesign; boundary cases\nidentified')]
    for k, (name, comp, ep, verd, claim) in enumerate(lanes):
        y = 72 - k * 18
        ax.add_patch(FancyBboxPatch((23.5, y - 7.6), 115, 15.2, boxstyle='round,pad=0.3,rounding_size=1.2', fc='white', ec='#BBBBBB', lw=0.6))
        ax.annotate('', xy=(23.3, y), xytext=(21, y), arrowprops=dict(arrowstyle='-|>', lw=0.7, color='#333333', mutation_scale=6))
        ax.text(25, y + 5, name, fontsize=7.5, fontweight='bold', va='center')
        ax.text(25, y - 2, comp, fontsize=7, va='center', linespacing=1.1)
        ax.text(63, y, ep, fontsize=7, va='center', linespacing=1.1)
        for m, (v, lab) in enumerate(verd):
            cx = 91.5 + m * 4.2 if len(verd) > 1 else 97.4; cy = y + 1.8
            col = {'pass': G, 'fail': R, 'void': P}[v]
            {'pass': check, 'fail': cross, 'void': void}[v](ax, cx, cy, 1.4, col)
            ax.text(cx, y - 3.2, lab, fontsize=7, ha='center', va='center', color=col)
        ax.text(104, y, claim, fontsize=7, va='center', linespacing=1.1)
    check(ax, 26, 4, 1.2, G); ax.text(28.5, 4, 'registered criterion met', fontsize=7, va='center')
    cross(ax, 66, 4, 1.2, R); ax.text(68.5, 4, 'registered criterion not met', fontsize=7, va='center')
    void(ax, 108, 4, 1.2, P); ax.text(110.5, 4, 'void before runs', fontsize=7, va='center')
    save(fig, OUT, 'Fig4')

# ---------------------------------------------------------------- Fig. 5 trace-driven replay
def fig_flocklab():
    fl = J(src(P2 / 'flocklab/results_full/summary.json'))
    assert fl['n_cases'] == fl['n_done'] == 192 and fl['n_failed'] == 0
    O = {(o['day'], o['mode'], o['scenario'], o['arm']): o for o in fl['outcomes']}
    N = [o for o in fl['outcomes'] if o['scenario'] == 'N']; M = [o for o in fl['outcomes'] if o['scenario'] == 'M1']
    assert sum(o['E1'] for o in N) == 0 and sum(o['n'] for o in N) == 96
    assert sum(o['E1'] for o in M if o['arm'] == 'joint') == 24 and sum(o['installs_after_exit_cases'] for o in M if o['arm'] == 'post_exit') == 48
    assert sum(o['gate_closed'] for o in M if o['arm'] == 'joint') == 48
    conds = [('A', 'R2'), ('B', 'R2'), ('A', 'R1')]
    outs = [('with_unconfirmed_exit', 'At least one unconfirmed exit'), ('E1', 'IU-only E1 lockout to the action deadline'), ('installs_after_exit_cases', 'Installation after the exit')]
    fig, axes = plt.subplots(1, 2, figsize=(W140, 86 * MM), sharey=True)
    fig.subplots_adjust(left=0.115, right=0.86, top=0.885, bottom=0.17, wspace=0.5)
    tr = None; yt, yl = [], []
    for ax, scen, title, letter in zip(axes, ('N', 'M1'), ('Scenario N: relay faults, no install drop', 'Scenario M1: frozen Amplification-2 recipe'), 'ab'):
        tr = ax.get_yaxis_transform(); y = 0
        for g, (key, lab) in enumerate(outs):
            ax.text(0.0, y, lab, transform=tr, fontsize=7, fontweight='bold', va='center'); y += 1
            for d, m in conds:
                for a, off in (('joint', -0.16), ('post_exit', 0.16)):
                    o = O[(d, m, scen, a)]; k, n = o[key], o['n']; p, lo, hi = wilson(k, n)
                    mk = 'o' if a == 'joint' else 's'
                    ax.errorbar(p, y + off, xerr=[[p - lo], [hi - p]], fmt=mk, ms=3.4, color=ARM[a], mfc='white' if k == 0 else ARM[a], mew=0.9, elinewidth=0.8, capsize=1.6, zorder=3)
                    ax.text(1.17 if a == 'joint' else 1.43, y + off, f'{k}/{n}', transform=tr, fontsize=7, va='center', ha='right', color=ARM[a], clip_on=False)
                if scen == 'N': yt.append(y); yl.append(f"Day {d}, {m}{'†' if m == 'R1' else ''}")
                y += 1
            if g < 2: ax.axhline(y - 0.5, color='#CCCCCC', lw=0.5)
        ax.set_xlim(-0.04, 1.04); ax.set_ylim(y - 0.5, -0.6); ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
        ax.grid(axis='x', color='#E3E3E3', lw=0.5, zorder=0); ax.set_xlabel('Fraction of 16 runs (Wilson 95% CI)')
        ax.text(0, 1.045, f'({letter})', transform=ax.transAxes, fontsize=9, fontweight='bold', va='bottom')
        ax.text(0.11, 1.05, title, transform=ax.transAxes, fontsize=7.5, va='bottom')
        ax.text(1.17, 1.005, 'Joint', transform=ax.transAxes, fontsize=7, ha='right', va='bottom', color=ARM['joint'])
        ax.text(1.43, 1.005, 'PostExit', transform=ax.transAxes, fontsize=7, ha='right', va='bottom', color=ARM['post_exit'])
        ax.tick_params(axis='y', length=0)
    axes[0].set_yticks(yt, yl)
    hs = [Line2D([], [], marker='o', ls='-', color=ARM['joint'], ms=3.4, lw=0.8, label='Joint'), Line2D([], [], marker='s', ls='-', color=ARM['post_exit'], ms=3.4, lw=0.8, label='PostExit (ablation)'),
          Line2D([], [], marker='o', ls='', color='#555555', mfc='white', ms=3.4, label='open marker: 0/16')]
    fig.legend(handles=hs, loc='lower center', ncol=3, bbox_to_anchor=(0.5, 0.0))
    save(fig, OUT, 'Fig5')

# ---------------------------------------------------------------- Fig. 6 factorial phase diagram
FAULT = {0: 'no faults', 1: 'early faults', 2: 'late faults'}
def fig_doe():
    d = J(src(P2 / 'doe/summary.json')); pts = d['points']
    assert d['n_cases'] == d['n_done'] == 432 and d['n_failed'] == 0 and len(pts) == 27
    assert (d['H1']['gate_closed'], d['H1']['eligible']) == (95, 96) and (d['H2']['E1'], d['H2']['n']) == (1, 216)
    assert sum(p['n'] for p in pts) == 216 and all(p['n'] == 8 for p in pts)  # Joint arm; PostExit is the other 216
    ft = {0: [], 1: [100, 180], 2: [145, 225]}
    assert all([round(f[0]) for f in p['faults']] == ft[p['D']] for p in pts), [(p['D'], p['faults']) for p in pts[:3]]
    cmap = plt.get_cmap('cividis')
    starts, lengths = (0, 120, 240), (20, 60, 120)
    fig, axes = plt.subplots(1, 3, figsize=(W140, 76 * MM), sharey=True)
    fig.subplots_adjust(left=0.085, right=0.99, top=0.9, bottom=0.33, wspace=0.06)
    for ax, m, letter in zip(axes, (1, 2, 3), 'abc'):
        Z = np.full((3, 3), np.nan)
        for p in pts:
            if p['mask'] != m: continue
            i, j = lengths.index(round(p['drop_end'] - p['drop_start'])), starts.index(round(p['drop_start'])); v = p['E1'] / p['n']; Z[i, j] = v
            c = 'black' if v > 0.55 else 'white'
            ax.text(j, i + 0.2, f"{p['E1']}/{p['n']}", ha='center', va='center', fontsize=8, fontweight='bold', color=c)
            ax.text(j, i - 0.17, f"exits {p['exit']}\n{FAULT[p['D']]}\nwait {p['wait_s']} s", ha='center', va='center', fontsize=7, color=c, linespacing=1.05)
        im = ax.imshow(Z, origin='lower', cmap=cmap, vmin=0, vmax=1, aspect='auto')
        for k in (0.5, 1.5): ax.axhline(k, color='white', lw=1); ax.axvline(k, color='white', lw=1)
        ax.set_xticks(range(3), [str(s) for s in starts]); ax.set_xlabel('Drop-window start (s)')
        ax.set_title({1: 'Install drop: source 0', 2: 'Install drop: source 1', 3: 'Install drop: both sources'}[m], pad=3)
        panel(ax, letter, x=0.0, y=1.075, ha='left') if False else None
        for sp in ax.spines.values(): sp.set_visible(False)
        ax.tick_params(length=0)
    for ax, letter in zip(axes, 'abc'): ax.text(-0.02, 1.02, f'({letter})', transform=ax.transAxes, fontsize=9, fontweight='bold', ha='right' if letter == 'a' else 'left', va='bottom') if False else None
    for ax, letter in zip(axes, 'abc'): ax.set_title(f'({letter})  ' + ax.get_title(), pad=3) if False else None
    for ax, letter in zip(axes, 'abc'):
        t = ax.get_title(loc='left'); ax.set_title('', loc='left'); ax.text(0, 1.03, f'({letter})', transform=ax.transAxes, fontsize=9, fontweight='bold', va='bottom')
        ax.text(0.17, 1.03, t, transform=ax.transAxes, fontsize=7.5, va='bottom')
    axes[0].set_yticks(range(3), [str(l) for l in lengths]); axes[0].set_ylabel('Drop-window length (s)')
    cax = fig.add_axes([0.3, 0.135, 0.4, 0.03]); cb = fig.colorbar(im, cax=cax, orientation='horizontal'); cb.outline.set_linewidth(0.5)
    cb.set_label('Joint IU-only E1 fraction (bold: count per 8 Joint runs)')
    save(fig, OUT, 'Fig6')

def fig_doe_main():
    d = J(src(P2 / 'doe/summary.json')); me = d['main_effects_joint']
    names = {'A': ('Drop start (s)', ['0', '120', '240']), 'B': ('Drop length (s)', ['20', '60', '120']), 'C': ('Install drop', ['src 0', 'src 1', 'both']),
             'D': ('Relay faults', ['none', 'early', 'late']), 'E': ('Install wait (s)', ['10', '15', '20'])}
    fig, axes = plt.subplots(1, 5, figsize=(W140, 50 * MM), sharey=True)
    fig.subplots_adjust(left=0.085, right=0.99, top=0.82, bottom=0.17, wspace=0.12)
    for ax, f, letter in zip(axes, 'ABCDE', 'abcde'):
        v = me[f]; assert all(x['n'] == 72 for x in v)
        ks = [round(x['E1_rate'] * x['n']) for x in v]; ps = [wilson(k, 72) for k in ks]
        ax.errorbar(range(3), [p[0] for p in ps], yerr=[[p[0] - p[1] for p in ps], [p[2] - p[0] for p in ps]], fmt='o' if f in 'CD' else 'o-', color=ARM['joint'], ms=3.2, lw=0.8, capsize=2, elinewidth=0.7)
        for x, (k, p) in enumerate(zip(ks, ps)): ax.text(x, p[2] + 0.04, f'{k}/72', fontsize=7, ha='center', va='bottom')
        ax.set_xticks(range(3), names[f][1]); ax.set_xlim(-0.5, 2.5); ax.set_ylim(-0.02, 1.02)
        ax.grid(axis='y', color='#E3E3E3', lw=0.5)
        ax.text(0, 1.04, f'({letter})', transform=ax.transAxes, fontsize=9, fontweight='bold', va='bottom'); ax.text(0.22, 1.045, names[f][0], transform=ax.transAxes, fontsize=7.5, va='bottom')
    axes[0].set_ylabel('Joint IU-only E1 (Wilson 95% CI)')
    save(fig, OUT, 'FigS1')

# ---------------------------------------------------------------- graphical abstract (separate upload; not in the article PDF)
def graphical_abstract():
    w, h = 140 * MM, 56 * MM  # 5:2; PNG at 600 dpi = 3307 x 1323 px (>= 1328 x 531 required)
    fig, ax = plt.subplots(figsize=(w, h)); fig.subplots_adjust(0, 0, 1, 1); ax.set_xlim(0, 140); ax.set_ylim(0, 56); ax.axis('off')
    ax.add_patch(FancyBboxPatch((1.5, 9.5), 30, 44.5, boxstyle='round,pad=0.5,rounding_size=2', fc='#F2F2F2', ec='#333333', lw=1))
    ax.text(16.5, 31.8, 'Packet-level\nWSN simulation\n+\nevidence-gated\nrecovery logic', ha='center', va='center', fontsize=10, linespacing=1.2)
    ax.annotate('', xy=(37, 31.8), xytext=(32.5, 31.8), arrowprops=dict(arrowstyle='-|>', lw=1.3, color='#333333', mutation_scale=11))
    lay = ['(i) Conditioned\ndocking', '(ii) Free-running\ndocking', '(iii) Measured-\ntrace replay', '(iv) Registered\nfactorial']
    res = ['Gate logic verified on\nrecorded inputs (248/248)', 'Incidence not reproduced by\nthe two abstract models tested', 'Contrast kept on measured\nlinks (input audit failed)', 'Induction boundary\nmapped (exploratory)']
    for k in range(4):
        y = 48.6 - k * 11.2
        ax.add_patch(FancyBboxPatch((38, y - 4.4), 33, 8.8, boxstyle='round,pad=0.3,rounding_size=1.2', fc='white', ec='#333333', lw=0.9))
        ax.text(54.5, y, lay[k], ha='center', va='center', fontsize=9.5, fontweight='bold', linespacing=1.05)
        ax.annotate('', xy=(79, y), xytext=(72, y), arrowprops=dict(arrowstyle='-|>', lw=1.1, color='#333333', mutation_scale=9))
        ax.text(80.5, y, res[k], ha='left', va='center', fontsize=10.5, linespacing=1.1)
    ax.text(70, 3.4, 'Controlled induction — not a prevalence estimate', ha='center', va='center', fontsize=9.5, style='italic')
    save(fig, OUT, 'Graphical_abstract')

if __name__ == '__main__':
    fig_state_machine(); fig_paired(); fig_adverse(); fig_overview(); fig_flocklab(); fig_doe(); fig_doe_main(); graphical_abstract()
    (OUT / 'figure_sources_sha256.json').write_text(json.dumps(SOURCES, indent=1))
    print('figures written; sources:', len(SOURCES))
