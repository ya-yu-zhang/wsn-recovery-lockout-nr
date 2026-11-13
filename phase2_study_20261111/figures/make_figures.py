"""Presentation only (no new analysis): docking probe table and FlockLab probe outcomes."""
import json, os
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..')
C = json.load(open(f'{R}/results/dock_C_probe.json'))['summary']; F = json.load(open(f'{R}/results/dock_F_probe.json'))['summary']
rows = [('Mode C', 'C1 per-case E1', C['C1'], .95), ('Mode C', 'C2 exit times', C['C2'], .95), ('Mode C', 'C3 per-tick Φ', C['C3'], .98), ('Mode C', 'C4 reason class', C['C4'], .95)]
for arm, v in F['per_arm'].items(): rows += [('Mode F', f'F1 gate outcome ({arm})', v['F1'], .95), ('Mode F', f'F2 first exit ({arm})', v['F2'], .95)]
md = ['| Mode | Endpoint | Agreement | Threshold | Pass |', '|---|---|---|---|---|'] + [f'| {m} | {e} | {a:.3f} | ≥ {t} | {"yes" if a >= t else "NO"} |' for m, e, a, t in rows]
open(f'{H}/docking_probe_table.md', 'w').write('\n'.join(md) + f"\n\nProbe set n = {C['n']} (36 Amp-2 subset + 8 adverse). F3 (exploratory on probe): ns-3 Joint E1 {F['F3']['ns3_joint_e1']}/{F['F3']['n']}, mirror 95% interval {F['F3']['mirror_interval_95']}.\n")
fig, ax = plt.subplots(figsize=(7.5, 3.6)); ax.axis('off')
t = ax.table(cellText=[[m, e, f'{a:.2f}', f'≥{t}', 'yes' if a >= t else 'NO'] for m, e, a, t in rows], colLabels=['Mode', 'Endpoint', 'Agreement', 'Threshold', 'Pass'], loc='center', cellLoc='left')
t.auto_set_font_size(False); t.set_fontsize(8); t.scale(1, 1.25)
for (i, j), cell in t.get_celld().items():
    if i > 0 and j == 4 and cell.get_text().get_text() == 'NO': cell.set_facecolor('#f4c7c3')
ax.set_title('Phase-2 probe A: SimPy mirror vs ns-3 (adverse cell + Amp-2 subset)', fontsize=9)
fig.savefig(f'{H}/fig_docking_probe_table.png', dpi=200, bbox_inches='tight')
fl = json.load(open(f'{R}/flocklab/results_probe/summary.json'))
lab = [f"{o['scenario']}/{o['arm']}" for o in fl['outcomes']]; x = range(len(lab))
fig, ax = plt.subplots(figsize=(6.5, 3.2))
ax.bar([i - .2 for i in x], [o['E1'] for o in fl['outcomes']], .2, label='Joint-type E1 lockout')
ax.bar([i for i in x], [o['with_unconfirmed_exit'] for o in fl['outcomes']], .2, label='≥1 unconfirmed exit')
ax.bar([i + .2 for i in x], [o['installs_after_exit_cases'] for o in fl['outcomes']], .2, label='installs after exit')
ax.set_xticks(list(x)); ax.set_xticklabels(lab); ax.set_ylabel('runs (of 2)'); ax.legend(fontsize=7)
ax.set_title('Phase-2 probe B: FlockLab Day A 2019-09-15 (R2 replay, subgraphs A0, A1)', fontsize=9)
fig.savefig(f'{H}/fig_flocklab_probe_outcomes.png', dpi=200, bbox_inches='tight'); print('ok')
