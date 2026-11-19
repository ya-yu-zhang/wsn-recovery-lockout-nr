"""Figures for merging the substrate-verification and scale layers into the Nov-13 SIMPAT manuscript.

Uses the Nov-13 manuscript's figstyle (140 mm, Okabe-Ito, >= 7 pt). Data are read only from the committed
records of simpat_study_20261117; every plotted value is asserted against the numbers quoted in the inserts.
Outputs: Fig4_vv_overview_5lanes (replaces Fig4), FigD_substrate_docking, FigE_scale.
"""
import json, math, statistics
from pathlib import Path
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
    a = J(S / 'analysis.json')['scale']
    e1 = J(S / 'a_endpoint_E1.json')['scale']
    fig, axs = plt.subplots(1, 2, figsize=(W140, 62 * MM))
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.2, top=0.88, wspace=0.32)
    ax = axs[0]
    sizes = (10, 20, 40)
    for k, (model, col, mk) in enumerate((('full_v2', OI['blue'], 'o'), ('horizon', OI['orange'], 's'))):
        x = [i + (k - .5) * 0.18 for i in range(3)]
        ex = [a['incidence_by_size_arm'][f'{n}|{model}|joint']['unconfirmed_exit'] for n in sizes]
        ax.errorbar(x, [v['proportion'] for v in ex], yerr=[[v['proportion'] - v['wilson95'][0] for v in ex], [v['wilson95'][1] - v['proportion'] for v in ex]],
                    fmt=mk, ms=3.5, color=col, lw=0.8, label=f"{'Full v2' if model == 'full_v2' else 'Horizon'} exit")
        e = [e1[f'{n}|{model}|joint|base'] for n in sizes]
        assert all(v['E1_iu_only'] == 0 and v['cells'] == 40 for v in e)
        ax.errorbar(x, [0] * 3, yerr=[[0] * 3, [v['wilson95'][1] for v in e]], fmt=mk, ms=3.5, mfc='white', color=col, lw=0.8,
                    label=f"{'Full v2' if model == 'full_v2' else 'Horizon'} E1")
    ax.set_xticks(range(3), [str(n) for n in sizes]); ax.set_xlabel('nodes'); ax.set_ylabel('fraction of 40 cells (Joint)')
    ax.set_ylim(-0.03, 1.0); ax.legend(fontsize=7, loc='upper right', ncol=2, columnspacing=0.6, handlelength=1.0, title='Joint; E1 = IU-only, 0/40 each', title_fontsize=7); ax.set_title('Natural incidence over new layouts')
    panel(ax, 'a')
    ax = axs[1]
    vl = a['versus_legacy']['full_v2/joint']
    s = [vl[str(n)]['service_pp'] for n in sizes]; c = [vl[str(n)]['control_reduction_pct'] for n in sizes]
    assert [round(v[0], 1) for v in s] == [-2.1, -8.8, -23.6] and [round(v[0], 1) for v in c] == [21.6, 33.2, 45.2]
    ax.errorbar(range(3), [v[0] for v in s], yerr=[[v[0] - v[1] for v in s], [v[2] - v[0] for v in s]], fmt='o-', ms=3.5, color=OI['vermillion'], lw=0.9, label='service (pp)')
    ax.errorbar(range(3), [v[0] for v in c], yerr=[[v[0] - v[1] for v in c], [v[2] - v[0] for v in c]], fmt='s-', ms=3.5, color=OI['blue'], lw=0.9, label='control-DATA cut (%)')
    ax.axhline(0, color='#999999', lw=0.6)
    for i, (sv, cv) in enumerate(zip(s, c)):
        ax.text(i - 0.1, sv[0] - 4, f'{sv[0]:.1f}', fontsize=7, color=OI['vermillion'], va='top', ha='right')
        ax.text(i - 0.1, cv[0] + 3, f'{cv[0]:.1f}', fontsize=7, color=OI['blue'], ha='right')
    ax.set_xticks(range(3), [str(n) for n in sizes]); ax.set_xlabel('nodes'); ax.set_ylabel('Full v2 (Joint) vs. Legacy')
    ax.set_xlim(-0.5, 2.3); ax.set_ylim(-38, 75); ax.legend(fontsize=7, loc='upper left', ncol=1, handlelength=1.5); ax.set_title('Trade-off grows with scale')
    panel(ax, 'b')
    save(fig, OUT, 'FigE_scale')


if __name__ == '__main__':
    fig_overview_5lanes(); fig_docking(); fig_scale()
    print('written to', OUT)
