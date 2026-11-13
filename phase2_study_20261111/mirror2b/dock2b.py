"""Phase-2b Mode F' docking (registered in PREREG_PHASE2B_20261111.md). Usage: dock2b.py <probe|holdout|joint48> <out.json> [R]
Same scorer as Phase-2 dock.py (mode_f / free_case / poisson_binomial_interval) with NetworkCQ substituted for Network."""
import sys, os, json, glob, concurrent.futures
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'mirror')); sys.path.insert(0, os.path.join(HERE, '..', 'vendor'))
import dock, ccmirror_cq as Q
dock.M.Network = Q.NetworkCQ
HOLDOUT = tuple(f'budget_10_{L}' for L in range(2026110412, 2026110418))
def sets(name):
    amp, adv = dock.frozen_sets('full')
    pick = lambda topos, arms: [f for f in amp if (lambda c: c['topology'] in topos and c['arm'] in arms)(json.load(open(f + '/case.json'))['configuration'])]
    arms3 = ('joint', 'sham_release', 'post_exit')
    if name == 'probe': return pick(('budget_10_2026110410', 'budget_10_2026110411'), arms3) + adv
    if name == 'holdout': return pick(HOLDOUT, arms3)
    raise ValueError(name)
def main():
    which, out = sys.argv[1], sys.argv[2]; Rn = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    fs = sets(which)
    with concurrent.futures.ProcessPoolExecutor(int(os.environ.get('PH2B_WORKERS', '6'))) as ex: rows = list(ex.map(dock.mode_f, [(f, Rn) for f in fs]))
    a = [r for r in rows if r['group'] == 'amp2']
    per_arm = {arm: dict(n=len(v), F1=sum(r['F1'] for r in v) / len(v), F2=sum(r['F2'] for r in v) / len(v), mean_p_gate_open=sum(r['mirror']['p_gate_open'] for r in v) / len(v))
               for arm in sorted({r['arm'] for r in a}) for v in [[r for r in a if r['arm'] == arm]]}
    joint = [r for r in a if r['arm'] == 'joint']
    lo, hi, mean = dock.poisson_binomial_interval([r['mirror']['p_e1'] for r in joint]) if joint else (None, None, None)
    summ = dict(set=which, n=len(rows), R=Rn, per_arm=per_arm, pass_F1_F2=all(v['F1'] >= .95 and v['F2'] >= .95 for v in per_arm.values()),
                joint_e1=dict(ns3=sum(r['ns3']['e1'] for r in joint), n=len(joint), mirror_interval_95=[lo, hi], mirror_expected=mean),
                adverse=[dict(model=r['model'], arm=r['arm'], mirror=r['mirror'], ns3_e1=r['ns3']['e1'], ns3_exits=r['ns3']['exits_s'], F1=r['F1'], F2=r['F2']) for r in rows if r['group'] == 'adverse'])
    json.dump(dict(summary=summ, rows=rows), open(out, 'w'), indent=1); print(json.dumps(summ, indent=1)[:3000])
if __name__ == '__main__': main()
