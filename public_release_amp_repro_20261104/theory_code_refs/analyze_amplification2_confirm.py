"""Confirm-stage analyzer for Amplification-2 (same S1–S3 thresholds as attempt 1).

Reuses analyze_amplification_confirm logic but reads results/amplification2_confirm/.
Do not run until manip_check scale-up rule is met (already recorded in draft).
"""
import json, math, collections, sys
from pathlib import Path
from analyze_contract_ablation import post_exit
from analyze_amplification import detail
from analyze_amplification_confirm import opened, fisher_one_sided, wilson, COMPETING, MIN_GAIN_PP

ROOT = Path(__file__).resolve().parent
R = ROOT / 'results'


def load(stage='confirm'):
    out = []
    for f in sorted((R / ('amplification2_' + stage)).glob('*/case.json')):
        case = json.loads(f.read_text())
        a = case['audit']
        pe = post_exit(f.parent, case)
        out.append(dict(configuration=case['configuration'], key=case['configuration_key'],
                        audit_status=a['status'], worst_source_service=a['worst_source_service'],
                        control_DATA_bytes=a['control_DATA_bytes'],
                        budget_bound_verified=a.get('control_budget_bound_verified'),
                        **pe, **detail(f.parent, case)))
    return out


def main(stage='confirm'):
    # Mirror analyze_amplification_confirm.main with amp2 path + attempt metadata
    rows = load(stage)
    cells = collections.defaultdict(dict)
    for r in rows:
        c = r['configuration']
        cells[(c['topology'], c['seed'], c.get('stratum'))][c['arm']] = r
    table = []
    sham_ok = True
    for (topo, seed, stratum), arms in sorted(cells.items()):
        j = arms['joint']
        row = dict(topology=topo, seed=seed, stratum=stratum,
                   joint_service=j['worst_source_service'], joint_control=j['control_DATA_bytes'],
                   joint_lockout_to_stop=j['lockout_to_stop'],
                   joint_unconfirmed_exit=bool(j['exits']),
                   joint_first_exit_s=j['exits'][0][0] if j['exits'] else None,
                   joint_blocked_checks=j['blocked_unconfirmed'],
                   audits=sorted({a['audit_status'] for a in arms.values()}), arms={})
        for name, a in arms.items():
            row['arms'][name] = dict(
                service=a['worst_source_service'], control=a['control_DATA_bytes'],
                delta_service_pp=100 * (a['worst_source_service'] - j['worst_source_service']),
                delta_control_pct=100 * (a['control_DATA_bytes'] / j['control_DATA_bytes'] - 1),
                authorized_after_exit=a['authorized'], first_authorized_s=a['first_authorized_s'],
                installs_after_exit=a.get('installs_after_exit', 0),
                lockout_to_stop=a['lockout_to_stop'],
                first_exit_s=a['exits'][0][0] if a['exits'] else None,
                opened=opened(a, j) if name != 'joint' else None)
        s = arms.get('sham_release')
        if s is None or s['worst_source_service'] != j['worst_source_service'] or s['control_DATA_bytes'] != j['control_DATA_bytes']:
            sham_ok = False
            row['sham_mismatch'] = True
        table.append(row)
    lock = [r for r in table if r['joint_lockout_to_stop']]
    S1 = len(lock) >= 3 and len({r['topology'] for r in lock}) >= 2
    pe_ok = [r for r in lock if r['arms']['post_exit']['opened'] and r['arms']['post_exit']['first_exit_s'] == r['joint_first_exit_s']]
    S2 = len(pe_ok) >= 2
    comp = {k: [r['topology'] + '/' + str(r['seed']) for r in pe_ok if r['arms'][k]['opened']]
            for k in COMPETING + ('sham_release', 'fs_relax_scoped', 'fs_relax_global', 'thresh_relax_global')}
    S3 = bool(pe_ok) and sham_ok and any(len(comp[k]) == 0 for k in COMPETING)
    summary = dict(
        stage=stage, attempt=2, prior_joint_lockout_attempt1='0/96',
        cells=len(table), runs=len(rows),
        all_audits_passed=all(r['audits'] == ['passed'] for r in table),
        sham_identical_to_joint_all_cells=sham_ok,
        lockout_cells=[dict(topology=r['topology'], seed=r['seed'], stratum=r['stratum'],
                            first_exit_s=r['joint_first_exit_s'], blocked=r['joint_blocked_checks'])
                       for r in lock],
        thresholds=dict(
            S1=dict(met=S1, lockout_cells=len(lock), layouts=sorted({r['topology'] for r in lock})),
            S2=dict(met=S2, post_exit_opened=[r['topology'] + '/' + str(r['seed']) for r in pe_ok]),
            S3=dict(met=S3, replicating_cells_by_arm=comp),
            A_tier=S1 and S2 and S3),
        table=table)
    (R / f'amplification2_{stage}_summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'table'}, indent=1))


if __name__ == '__main__':
    main(*(sys.argv[1:] or ['confirm']))
