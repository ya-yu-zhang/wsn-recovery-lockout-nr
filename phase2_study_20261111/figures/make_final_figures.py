"""Publication figures/tables for Phase 2/2b (presentation of registered + exploratory results; no new inference).
Outputs PDF+PNG in figures/final/ and tables in figures/final/*.md."""
import json, os, math
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.linewidth': .6, 'xtick.major.width': .6, 'ytick.major.width': .6, 'savefig.dpi': 400, 'pdf.fonttype': 42})
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..'); O = os.path.join(H, 'final'); os.makedirs(O, exist_ok=True)
def save(fig, name): fig.savefig(f'{O}/{name}.pdf', bbox_inches='tight'); fig.savefig(f'{O}/{name}.png', bbox_inches='tight'); plt.close(fig)
def wilson(k, n, z=1.96):
    if n == 0: return (float('nan'),) * 3
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)
L = lambda p: json.load(open(os.path.join(R, p)))
md = []
# ---------- 1. docking agreement table ----------
rows = []
for name, p in (('Mode C, registered probe (n=44)', 'results/dock_C_probe.json'), ('Mode C, registered full (n=248)', 'results/dock_C_full.json')):
    s = L(p)['summary']; rows.append((name, s['C1'], s['C2'], s['C3'], s['C4'], 'PASS' if s['pass'] else 'FAIL'))
for name, p in (('Mode C, 9 frozen sets, strict exits (E, n=1,653)', 'results/dock_C_extended.json'), ('Mode C, 9 frozen sets, frozen exit rule (E)', 'results/dock_C_extended_incl_late.json')):
    S = L(p)['summary'].values(); n = sum(v['n'] for v in S)
    rows.append((name, sum(v['C1'] for v in S) / n, sum(v['C2'] for v in S) / n, sum(v['phi_agree'] for v in S) / sum(v['phi_eval'] for v in S), sum(v['reason_agree'] for v in S) / sum(v['ticks'] for v in S), 'E'))
md += ['## Docking agreement', '', '| Comparison | C1 E1 | C2 exit times | C3 Φ/tick | C4 reason/tick | Verdict |', '|---|---|---|---|---|---|']
md += [f'| {r[0]} | {r[1]:.3f} | {r[2]:.3f} | {r[3]:.3f} | {r[4]:.3f} | {r[5]} |' for r in rows]
frows = []
for name, p in (('Mode F (Phase 2), probe', 'results/dock_F_probe.json'), ("Mode F' (Phase 2b), probe", 'results/dock2b_probe.json'), ("Mode F' (Phase 2b), holdout", 'results/dock2b_holdout.json')):
    if not os.path.exists(os.path.join(R, p)): continue
    s = L(p)['summary']
    for arm, v in s['per_arm'].items(): frows.append((name, arm, v['n'], v['F1'], v['F2']))
md += ['', '| Free-running comparison | Arm | n | F1 gate outcome | F2 first exit |', '|---|---|---|---|---|'] + [f'| {r[0]} | {r[1]} | {r[2]} | {r[3]:.3f} | {r[4]:.3f} |' for r in frows]
fig, ax = plt.subplots(figsize=(7.0, 1.0 + .22 * (len(rows) + len(frows)))); ax.axis('off')
cell = [[r[0], f'{r[1]:.3f}', f'{r[2]:.3f}', f'{r[3]:.3f}', f'{r[4]:.3f}', r[5]] for r in rows] + [['Mode', 'Arm', 'n', 'F1', 'F2', '']] + [[r[0], r[1].replace('sham_release', 'sham').replace('post_exit', 'PostExit'), str(r[2]), f'{r[3]:.3f}', f'{r[4]:.3f}', 'arm ok' if min(r[3], r[4]) >= .95 else 'FAIL'] for r in frows]
t = ax.table(cellText=cell, colLabels=['Comparison', 'C1 E1', 'C2 exits', 'C3 Φ', 'C4 reason', 'Verdict'], loc='center', cellLoc='left', colWidths=[.46, .12, .1, .1, .11, .09])
t.auto_set_font_size(False); t.set_fontsize(6.5); t.scale(1, 1.2)
for (i, j), c in t.get_celld().items():
    c.set_linewidth(.3)
    if i == 0 or (i == len(rows) + 1): c.set_text_props(weight='bold'); c.set_facecolor('#eeeeee')
    if c.get_text().get_text() == 'FAIL': c.set_facecolor('#f4c7c3')
save(fig, 'Fig_P2_docking_table')
# ---------- 2. FlockLab outcomes ----------
fl = L('flocklab/results_full/summary.json')
md += ['', '## FlockLab replay (full registered set)', '', f"Complete {fl['n_done']}/{fl['n_cases']}; audit_case all passed: {fl['audit_all_passed']}; ingestion audit passed: {fl['ingestion_audit_passed']}.", '',
       '| Day | Mode | Scenario | Arm | n | ≥1 unconfirmed exit | E1 lockout (95 % CI) | gate closed | median worst service |', '|---|---|---|---|---|---|---|---|---|']
for o in fl['outcomes']:
    p, lo, hi = wilson(o['E1'], o['n']); md.append(f"| {o['day']} | {o['mode']} | {o['scenario']} | {o['arm']} | {o['n']} | {o['with_unconfirmed_exit']} | {o['E1']} ({lo:.2f}–{hi:.2f}) | {o['gate_closed']} | {o['median_worst_service']:.3f} |")
fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.4), sharey=True)
for ax, scen in zip(axes, ('N', 'M1')):
    os_ = [o for o in fl['outcomes'] if o['scenario'] == scen]; lab = [f"{o['day']}-{o['mode']}\n{o['arm'].replace('_', '-')}" for o in os_]
    for k, (key, col, off) in enumerate((('with_unconfirmed_exit', '#7f7f7f', -.2), ('E1', '#c0392b', 0), ('installs_after_exit_cases', '#2e86c1', .2))):
        ps = [wilson(o[key], o['n']) for o in os_]
        ax.bar(np.arange(len(os_)) + off, [p[0] for p in ps], .2, color=col, label={'with_unconfirmed_exit': '≥1 unconfirmed exit', 'E1': 'E1 lockout to stop', 'installs_after_exit_cases': 'install after exit'}[key],
               yerr=[[p[0] - p[1] for p in ps], [p[2] - p[0] for p in ps]], error_kw=dict(lw=.5, capsize=1.5))
    ax.set_xticks(range(len(os_))); ax.set_xticklabels(lab, fontsize=6); ax.set_title({'N': 'Scenario N (relay faults, no install drop)', 'M1': 'Scenario M1 (frozen Amp-2 recipe)'}[scen], fontsize=7.5)
    ax.set_ylim(0, 1.05); ax.spines[['top', 'right']].set_visible(False)
axes[0].set_ylabel('fraction of runs (Wilson 95 % CI)'); h, l = axes[1].get_legend_handles_labels(); fig.legend(h, l, fontsize=6.5, frameon=False, loc='lower center', ncol=3, bbox_to_anchor=(.5, -.16))
save(fig, 'Fig_P2_flocklab_outcomes')
# ---------- 3. DOE phase diagram ----------
d = L('doe/summary.json'); pts = d['points']
md += ['', '## DOE (3^(5−2), 8 new layouts, 432 runs)', '', f"Complete {d['n_done']}/{d['n_cases']}; technical failures {d['n_failed']}; audit all passed: {d['audit_all_passed']}.",
       f"H1 (Joint, ≥1 unconfirmed exit and no eligible F_s after last exit ⇒ gate closed to stop): {d['H1']['gate_closed']}/{d['H1']['eligible']} = {d['H1']['fraction'] if d['H1']['fraction'] is None else round(d['H1']['fraction'], 3)} → {'PASS' if d['H1']['pass'] else 'FAIL'} (threshold 0.95).",
       f"H2 (PostExit E1 = 0): {d['H2']['E1']}/{d['H2']['n']} → {'PASS' if d['H2']['pass_'] else 'FAIL'}. H3: VOID (Addendum 1).", '',
       '| pt | start s | length s | mask | faults | wait s | Joint exit | Joint E1 (95 % CI) | Joint gate closed | PostExit E1 |', '|---|---|---|---|---|---|---|---|---|---|']
for p in pts:
    k, lo, hi = wilson(p['E1'], p['n']); md.append(f"| {p['idx']} | {p['drop_start']:.0f} | {p['drop_end'] - p['drop_start']:.0f} | {p['mask']} | {p['D']} | {p['wait_s']} | {p['exit']}/{p['n']} | {p['E1']}/{p['n']} ({lo:.2f}–{hi:.2f}) | {p['gate_closed']}/{p['n']} | {p['postexit_E1']}/{p['n']} |")
cmap = LinearSegmentedColormap.from_list('w2r', ['#ffffff', '#f5b7b1', '#c0392b', '#641e16'])
fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.5), sharey=True)
starts = (0, 120, 240); lengths = (20, 60, 120); masks = (1, 2, 3)
for ax, m in zip(axes, masks):
    Z = np.full((3, 3), np.nan); A = {}
    for p in pts:
        if p['mask'] != m: continue
        i, j = lengths.index(round(p['drop_end'] - p['drop_start'])), starts.index(round(p['drop_start'])); Z[i, j] = p['E1'] / p['n']; A[(i, j)] = p
    im = ax.imshow(Z, origin='lower', cmap=cmap, vmin=0, vmax=1, aspect='auto')
    for (i, j), p in A.items():
        ax.text(j, i, f"{p['E1']}/{p['n']}\nexit {p['exit']}\nD{p['D']} W{p['wait_s']}", ha='center', va='center', fontsize=5.3, color='white' if p['E1'] / p['n'] > .6 else 'black')
    ax.set_xticks(range(3)); ax.set_xticklabels([f'{s}' for s in starts]); ax.set_xlabel('drop window start (s)')
    ax.set_title({1: 'mask 1 (source 0 only)', 2: 'mask 2 (source 1 only)', 3: 'mask 3 (both sources)'}[m], fontsize=7.5)
axes[0].set_yticks(range(3)); axes[0].set_yticklabels([f'{l}' for l in lengths]); axes[0].set_ylabel('drop window length (s)')
cb = fig.colorbar(im, ax=axes, fraction=.025, pad=.02); cb.set_label('Joint E1 lockout fraction (8 layouts)')
save(fig, 'Fig_P2_doe_phase_diagram')
fig, axes = plt.subplots(1, 5, figsize=(7.0, 1.9), sharey=True)
names = {'A': ('drop start', ['0', '120', '240']), 'B': ('drop length', ['20', '60', '120']), 'C': ('mask', ['1', '2', '3']), 'D': ('relay faults', ['none', '100/180', '145/225']), 'E': ('install wait', ['10', '15', '20'])}
for ax, f in zip(axes, 'ABCDE'):
    v = d['main_effects_joint'][f]; ps = [wilson(round(x['E1_rate'] * x['n']), x['n']) for x in v]
    ax.errorbar(range(3), [p[0] for p in ps], yerr=[[p[0] - p[1] for p in ps], [p[2] - p[0] for p in ps]], fmt='o-', color='#c0392b', ms=3, lw=.8, capsize=2)
    ax.set_xticks(range(3)); ax.set_xticklabels(names[f][1], fontsize=6); ax.set_title(names[f][0], fontsize=7.5); ax.set_ylim(-.02, 1.02); ax.spines[['top', 'right']].set_visible(False)
axes[0].set_ylabel('Joint E1 (Wilson 95 % CI)')
save(fig, 'Fig_P2_doe_main_effects')
open(f'{O}/TABLES_PHASE2.md', 'w').write('\n'.join(md) + '\n'); print('ok', O)
