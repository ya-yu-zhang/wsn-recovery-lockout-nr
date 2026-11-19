"""Figures for merging the substrate-verification and scale layers into the Nov-13 SIMPAT manuscript.

Uses the Nov-13 manuscript's figstyle (140 mm, Okabe-Ito, >= 7 pt). Data are read only from the committed
records of simpat_study_20261117; every plotted value is asserted against the numbers quoted in the inserts.
Outputs: Fig4_vv_overview_5lanes (replaces Fig4), FigD_substrate_docking, FigE_scale.
"""
import json, math, os, statistics
from pathlib import Path
import matplotlib.font_manager as _fm
# Liberation Sans (SIL OFL) must be available so these figures match figures_v2; point WSN_FONT_DIR at its TTFs.
for _f in Path(os.environ.get('WSN_FONT_DIR', '.')).glob('Liberation*-*.ttf'):
    _fm.fontManager.addfont(str(_f))
assert any(f.name == 'Liberation Sans' for f in _fm.fontManager.ttflist), 'Liberation Sans not found: set WSN_FONT_DIR'
from figstyle import plt, MM, W140, OI, ARM, panel, save
from matplotlib.patches import FancyBboxPatch, Circle

OUT = Path(__file__).resolve().parent / 'figures'
OUT.mkdir(exist_ok=True)
_HERE = Path(__file__).resolve().parents[1]
S = _HERE / 'results' if (_HERE / 'results' / 'analysis.json').exists() else _HERE / 'simpat_study_20261117' / 'results'
J = lambda p: json.loads(Path(p).read_text())


def wilson(k, n, z=1.959963984540054):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def check(ax, x, y, s, col):
    ax.plot([x - s, x - s * 0.25, x + s], [y, y - s * 0.75, y + s * 0.9], color=col, lw=1.4, solid_capstyle='round')


def cross(ax, x, y, s, col):
    ax.plot([x - s, x + s], [y - s, y + s], color=col, lw=1.4); ax.plot([x - s, x + s], [y + s, y - s], color=col, lw=1.4)


def void(ax, x, y, s, col):
    ax.add_patch(Circle((x, y), s, fc='none', ec=col, lw=1.1)); ax.plot([x - s * 0.7, x + s * 0.7], [y - s * 0.7, y + s * 0.7], color=col, lw=1.1)


def fig_overview_5lanes():
    """Nov-13 Fig. 4 with lane (v) added; lanes (i)-(iv) are reproduced verbatim from make_figures_v2.py."""
    H = 108
    fig, ax = plt.subplots(figsize=(W140, H * MM)); fig.subplots_adjust(0, 0, 1, 1); ax.set_xlim(0, 140); ax.set_ylim(0, H); ax.axis('off')
    ax.add_patch(FancyBboxPatch((1.5, 11), 19, H - 21, boxstyle='round,pad=0.4,rounding_size=1.5', fc='#F2F2F2', ec='#333333', lw=0.8))
    ax.text(11, H - 14.5, 'Reference', ha='center', fontsize=7.5, fontweight='bold')
    ax.text(11, (H + 1) / 2, 'ns-3.44\npacket-level\nWSN model\n\nfrozen records:\nobservations,\ndecisions,\nevaluation\ntimes\n\nfrozen\nAmplification-2\nrecords\n(SHA256\n1f37be33…)', ha='center', va='center', fontsize=7, linespacing=1.12)
    for x, t in ((25, 'Comparison model or input'), (63, 'Registered endpoint'), (92, 'Verdict'), (104, 'Claim licensed or restricted')):
        ax.text(x, H - 6, t, fontsize=7.5, fontweight='bold', ha='left')
    G, R, P = OI['green'], OI['vermillion'], '#555555'
    lanes = [('(i) Conditioned docking', 'recorded observations,\ndecisions, evaluation times →\nseparately coded SimPy mirror', 'C1–C4 ≥ 0.95–0.98\non 248 frozen cases', [('pass', 'pass')], 'logic claims hold for the\nrecorded runs'),
             ('(ii) Free-running docking', 'abstract network model\n(± contention submodel) →\nfree-running mirror', 'F1, F2 ≥ 0.95 per arm;\nF3 inside 95% interval', [('fail', 'fail')], 'incidence claims stay with\nthe packet-level model'),
             ('(iii) Trace-driven replay', 'FlockLab measured link\ntraces → trace driver\n(192 runs)', 'completion, native audits,\ningestion audit (R2, R1)', [('fail', 'audit fail')], 'replay results conditional\non the audit; no hardware\nclaim'),
             ('(iv) Registered factorial', '3$^{5-2}$ design of induction\nsettings (432 runs)', 'H1 ≥ 0.95; H2 = 0;\nH3 prospective docking', [('pass', 'H1'), ('fail', 'H2'), ('void', 'H3')], 'conformance across the\ndesign; boundary cases\nidentified'),
             ('(v) Substrate docking', 'single-hop CSMA-CA grid →\nindependent standard-based\nreference (250 runs)', '≥ 90% of 125 comparisons\nwithin 0.02 (10% for\nservice time)', [('fail', '65.6%')], 'access procedure reproduced;\nns-3 optimistic on access\nfailure (capture, CCA reset)')]
    for k, (name, comp, ep, verd, claim) in enumerate(lanes):
        y = H - 16 - k * 18
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
    save(fig, OUT, 'Fig4_vv_overview_5lanes')


def metrics(r):
    d = r['success'] + r['channel_access_failure'] + r['no_ack']
    return dict(p_caf=r['channel_access_failure'] / d, cca_busy=r['cca_busy'] / max(1, r['cca']), service_ms=r['service_mean_ms'])


def agg(rows):
    g = {}
    for r in rows:
        g.setdefault((r['stations'], r['load']), []).append(metrics(r))
    return {k: {m: (statistics.mean(x[m] for x in v), statistics.stdev(x[m] for x in v) / math.sqrt(len(v))) for m in v[0]} for k, v in g.items()}


def jl(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]


def fig_docking():
    ns3 = agg(jl(S / 'docking/ns3.jsonl'))
    pat = agg(jl(S / 'docking/ns3_cca_patched.jsonl'))
    var = jl(S / 'docking/reference_variants.jsonl')
    ref = {v: agg([r for r in var if r['variant'] == v]) for v in ('standard', 'capture', 'capture+peak_reset')}
    d = J(S / 'docking/diagnosis.json')
    assert d['registered']['agreeing'] == 82 and d['variants']['capture+peak_reset']['agreeing'] == 119
    assert d['ns3_cca_patched']['capture']['agreeing'] == 124
    loads = sorted({k[1] for k in ns3})
    fig, axs = plt.subplots(1, 3, figsize=(W140, 64 * MM))
    fig.subplots_adjust(left=0.07, right=0.99, bottom=0.33, top=0.9, wspace=0.42)
    specs = [('p_caf', 'P(access failure)'), ('cca_busy', 'CCA busy fraction'), ('service_ms', 'MAC service time (ms)')]
    for j, (m, lab) in enumerate(specs):
        ax = axs[j]
        for n, col in ((4, OI['sky']), (16, OI['vermillion'])):
            ax.plot(loads, [ref['standard'][(n, g)][m][0] for g in loads], '-', color=col, lw=0.9)
            ax.plot(loads, [ref['capture+peak_reset'][(n, g)][m][0] for g in loads], ':', color=col, lw=0.9)
            ax.errorbar(loads, [ns3[(n, g)][m][0] for g in loads], yerr=[1.96 * ns3[(n, g)][m][1] for g in loads], fmt='o', ms=3, mfc='white', color=col, lw=0.7)
            ax.plot(loads, [pat[(n, g)][m][0] for g in loads], 'x', ms=3.5, color=col, mew=0.8)
        ax.set_xlabel('offered DATA airtime $G$'); ax.set_title(lab)
        panel(ax, 'abc'[j])
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color='k', lw=0.9, label='reference (registered)'),
                        Line2D([], [], color='k', lw=0.9, ls=':', label='reference + capture + CCA peak reset'),
                        Line2D([], [], color='k', ls='', marker='o', mfc='white', ms=3, label='ns-3.44 (95% CI)'),
                        Line2D([], [], color='k', ls='', marker='x', ms=3.5, label='ns-3.44, CCA patched'),
                        Line2D([], [], color=OI['sky'], lw=2, label='N = 4'), Line2D([], [], color=OI['vermillion'], lw=2, label='N = 16')],
               loc='lower center', ncol=3, fontsize=7, handlelength=1.6, columnspacing=1.2, bbox_to_anchor=(0.5, 0.0))
    save(fig, OUT, 'FigD_substrate_docking')


def fig_scale():
    """Three panels so that no axis mixes units: (a) incidence, (b) service vs Legacy (pp), (c) control-DATA reduction (%)."""
    a = J(S / 'analysis.json')['scale']
    e1 = J(S / 'a_endpoint_E1.json')['scale']
    sizes = (10, 20, 40)
    models = (('full_v2', 'Full v2', OI['blue'], 'o'), ('horizon', 'Horizon', OI['orange'], 's'))
    fig, axs = plt.subplots(1, 3, figsize=(W140, 58 * MM))
    fig.subplots_adjust(left=0.075, right=0.995, bottom=0.30, top=0.88, wspace=0.42)
    off = lambda k: [i + (k - .5) * 0.2 for i in range(3)]
    ax = axs[0]
    for k, (m, lab, col, mk) in enumerate(models):
        ex = [a['incidence_by_size_arm'][f'{n}|{m}|joint']['unconfirmed_exit'] for n in sizes]
        ax.errorbar(off(k), [v['proportion'] for v in ex], yerr=[[v['proportion'] - v['wilson95'][0] for v in ex], [v['wilson95'][1] - v['proportion'] for v in ex]],
                    fmt=mk, ms=3.5, color=col, lw=0.8, capsize=1.5)
        e = [e1[f'{n}|{m}|joint|base'] for n in sizes]
        assert all(v['E1_iu_only'] == 0 and v['cells'] == 40 for v in e)
        ax.errorbar(off(k), [0] * 3, yerr=[[0] * 3, [v['wilson95'][1] for v in e]], fmt=mk, ms=3.5, mfc='white', color=col, lw=0.8, capsize=1.5)
    ax.text(1, 0.12, 'IU-only E1: 0/40 each', ha='center', fontsize=7, color='#444444')
    ax.text(1, 0.70, 'unconfirmed exit', ha='center', fontsize=7, color='#444444')
    ax.set_xticks(range(3), [str(n) for n in sizes]); ax.set_xlabel('Nodes'); ax.set_ylabel('Fraction of 40 cells (Joint)')
    ax.set_ylim(-0.03, 0.8); ax.set_title('Natural incidence')
    panel(ax, 'a')
    checks = {'full_v2': ([-2.1, -8.8, -23.6], [21.6, 33.2, 45.2])}
    for j, (key, title, ylab) in enumerate((('service_pp', 'Worst-source service', 'Change vs. Legacy (pp)'),
                                            ('control_reduction_pct', 'Control-DATA bytes', 'Reduction vs. Legacy (%)'))):
        ax = axs[j + 1]
        for k, (m, lab, col, mk) in enumerate(models):
            v = [a['versus_legacy'][f'{m}/joint'][str(n)][key] for n in sizes]
            if m in checks:
                assert [round(x[0], 1) for x in v] == checks[m][j]
            ax.errorbar(off(k), [x[0] for x in v], yerr=[[x[0] - x[1] for x in v], [x[2] - x[0] for x in v]], fmt=mk + '-', ms=3.5, color=col, lw=0.9, capsize=1.5)
        if key == 'service_pp':
            ax.axhline(0, color='#999999', lw=0.6); ax.set_ylim(-30, 2)
        else:
            ax.set_ylim(0, 50)
        ax.set_xticks(range(3), [str(n) for n in sizes]); ax.set_xlabel('Nodes'); ax.set_ylabel(ylab); ax.set_title(title)
        panel(ax, 'bc'[j])
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color=OI['blue'], marker='o', ls='', ms=3.5, label='Full v2'),
                        Line2D([], [], color=OI['orange'], marker='s', ls='', ms=3.5, label='Horizon'),
                        Line2D([], [], color='#444444', marker='o', mfc='white', ls='', ms=3.5, label='open: IU-only E1 (a)')],
               loc='lower center', ncol=3, fontsize=7, bbox_to_anchor=(0.5, 0.0), columnspacing=1.5)
    save(fig, OUT, 'FigE_scale')


def fig_architecture():
    """Lock-step co-simulation architecture in the figures_v2 style (140 mm, Liberation Sans, >= 7 pt)."""
    fig, ax = plt.subplots(figsize=(W140, 56 * MM)); fig.subplots_adjust(0, 0, 1, 1)
    ax.set_xlim(0, 140); ax.set_ylim(0, 56); ax.axis('off')

    def box(x, y, w, h, title, lines, ec):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.3,rounding_size=1.5', fc='white', ec=ec, lw=1.0))
        ax.text(x + w / 2, y + h - 3.0, title, ha='center', va='center', fontsize=8, fontweight='bold')
        ax.text(x + w / 2, y + h - 6.4, '\n'.join(lines), ha='center', va='top', fontsize=7, linespacing=1.3)
    box(2, 13, 51, 40, 'ns-3.44 network model (C++)',
        ['IEEE 802.15.4, 2.4 GHz O-QPSK PHY', 'log-distance loss, exponent 3', 'unslotted CSMA-CA, ACK, two retries',
         '16-request FIFO per node', 'source pacing; per-hop byte reservation', 'relay removals; frozen Poisson arrivals',
         'optional FlockLab trace driver and', 'gateway install drop (induction only)',
         'outputs: protocol events, MAC jobs,', 'radio states (SHA-256)'], OI['blue'])
    box(87, 13, 51, 40, 'Gateway controller (Python)',
        ['received reports only, no simulator truth', 'version and epoch bookkeeping',
         'installation transaction, 10 s wait', 'evidence-qualified admission (Ψ, $F_s$, Φ)',
         'route-pair search (≤ 64 scored pairs)', 'arms: Joint, PostExit, sham,', 'competing explanations',
         'output: per-step transcript (JSON)'], OI['vermillion'])
    for y, lab, sub, d in ((38, 'STEP {observation}', 'every 5 s of simulated time', 1), (22, 'decision or install', 'simulator waits (lock-step)', -1)):
        ax.annotate('', xy=(86.5, y) if d > 0 else (53.5, y), xytext=(53.5, y) if d > 0 else (86.5, y),
                    arrowprops=dict(arrowstyle='-|>', lw=0.9, color='#333333', mutation_scale=8))
        ax.text(70, y + 2.0, lab, ha='center', fontsize=7, family='Liberation Mono' if d > 0 else None)
        ax.text(70, y - 3.2, sub, ha='center', fontsize=7, color='#555555')
    ax.text(70, 5, 'Independent audits rebuild service, control bytes, byte credit and admission from the raw outputs',
            ha='center', fontsize=7, style='italic')
    save(fig, OUT, 'Fig_architecture')


if __name__ == '__main__':
    fig_overview_5lanes(); fig_docking(); fig_scale(); fig_architecture()
    print('written to', OUT)
