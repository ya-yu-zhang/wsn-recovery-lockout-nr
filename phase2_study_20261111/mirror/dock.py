"""Docking runner/scorer (registered). Usage:
  dock.py C <set> <out.json>        Mode C on frozen ns-3 cases
  dock.py F <set> <out.json> [R]    Mode F free-running SimPy replicates
  dock.py FDOE <design.json> <out.json> [R]   prospective Mode-F predictions for the DOE
sets: probe | full.  Reference ns-3 outcomes are read-only from the frozen results tree."""
import sys, os, json, glob, gzip, csv, random, statistics, concurrent.futures, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'vendor'))
import ccmirror as M
ENG = '/workspace/wsn_ablation/repo/control_budget_study_20261015'
R = ENG + '/results'
S = M.S

def frozen_sets(name):
    amp = []
    for f in sorted(glob.glob(R + '/amplification2_confirm/*/case.json')):
        c = json.load(open(f)); cfg = c['configuration']
        arms = ('joint', 'sham_release', 'post_exit') if name == 'probe' else ('joint', 'sham_release', 'post_exit', 'wait_extend', 'thresh_relax_scoped')
        if cfg['arm'] not in arms: continue
        if name == 'probe' and cfg['topology'] not in ('budget_10_2026110410', 'budget_10_2026110411'): continue
        amp.append(os.path.dirname(f))
    adv = []
    for f in sorted(glob.glob(R + '/contract_ablation/*/case.json')):
        cfg = json.load(open(f))['configuration']
        if cfg.get('topology') == 'budget_10_2026101501' and cfg.get('scenario') == 'multi_failure' and cfg.get('seed') == 2026101511:
            adv.append(os.path.dirname(f))
    return amp, adv

def describe(folder):
    c = json.load(open(folder + '/case.json')); cfg = c['configuration']
    if 'arm' in cfg: arm, model, group = cfg['arm'], 'horizon', 'amp2'
    else: arm, model, group = ('post_exit' if cfg['contract'] == 'post_exit' else 'joint'), cfg['model'], 'adverse'
    return c, cfg, arm, model, group

def ns3_outcome(folder, c):
    sys.path.insert(0, ENG)
    from analyze_contract_ablation import post_exit
    from pathlib import Path
    pe = post_exit(Path(folder), c)
    return dict(exits_s=pe['unconfirmed_exits'], e1=pe['lockout_to_stop'], installs_after_exit=pe.get('installs_after_exit', 0),
                first_authorized_s=pe['first_authorized_s'])

def mode_c(folder):
    c, cfg, arm, model, group = describe(folder)
    ctl = json.load(open(glob.glob(folder + '/*.controller.json')[0]))
    fsm = M.GateFSM(model=model, arm=arm, action_stop_ns=c['action_stop_ns'])
    tick_rows = []
    for s in ctl['steps']:
        d = s.get('decision'); dec = (d['decision'], d['paths']) if d and d.get('paths') else None
        eq = (s.get('constraints') or {}).get('evidence_qualified_admission')
        row = fsm.tick(s['observation'], decision=dec, evaluated=eq is not None)
        sv = (s.get('event') or {}).get('settled_service') or {}
        code_reason = 'known' if sv.get('known') else sv.get('reason')
        tick_rows.append(dict(t=row['t'] // S, mirror_reason=row['reason'], code_reason=code_reason,
                              evaluated=eq is not None, mirror_phi=row['phi'], code_phi=None if eq is None else bool(eq['allowed'])))
    ref = ns3_outcome(folder, c)
    mex = [x / S for x in fsm.exits()]
    return dict(folder=os.path.basename(folder), group=group, arm=arm, model=model, topology=cfg['topology'], seed=cfg['seed'],
                ns3=ref, mirror=dict(exits_s=mex, e1=fsm.e1(True), e1_all_ticks=fsm.e1(False), installs_after_first_exit=fsm.installs_after_first_exit()),
                C1=ref['e1'] == fsm.e1(True), C2=[float(x) for x in ref['exits_s']] == mex,
                ticks=len(tick_rows), phi_eval=sum(r['evaluated'] for r in tick_rows),
                phi_agree=sum(r['evaluated'] and r['mirror_phi'] == r['code_phi'] for r in tick_rows),
                reason_agree=sum(r['mirror_reason'] == r['code_reason'] for r in tick_rows),
                reason_mismatch=[r for r in tick_rows if r['mirror_reason'] != r['code_reason']][:6],
                phi_mismatch=[r for r in tick_rows if r['evaluated'] and r['mirror_phi'] != r['code_phi']][:6])

def load_arrivals(folder):
    p = glob.glob(folder + '/*_arrivals.csv')[0]
    return [(float(r['time']), int(r['flow'])) for r in csv.DictReader(open(p))]

CAL = None
def calib():
    global CAL
    if CAL is None: CAL = json.load(open(os.path.join(HERE, 'calibration.json')))
    return CAL

def free_case(spec, Rn):
    pts = {int(k): tuple(v) for k, v in spec['points'].items()}
    out = []
    for i in range(Rn):
        rng = random.Random(20261111 + i)
        fsm = M.run_free(pts, spec['arrivals'], spec['faults'], spec['drop'], spec['arm'], spec['model'], spec['wait_s'], calib(), spec['seed'], rng, spec.get('generation_stop', 330))
        ex = fsm.exits()
        out.append(dict(first_exit_s=ex[0] / S if ex else None, n_exits=len(ex), gate_open=fsm.installs_after_first_exit() > 0, e1=fsm.e1(True)))
    fe = [o['first_exit_s'] for o in out if o['first_exit_s'] is not None]
    p_exit = sum(o['n_exits'] > 0 for o in out) / Rn
    # replicate-median first exit at tick resolution; None when most replicates have no exit (pre-freeze amendment)
    return dict(p_exit=p_exit, p_gate_open=sum(o['gate_open'] for o in out) / Rn,
                p_e1=sum(o['e1'] for o in out) / Rn, median_first_exit_s=statistics.median_low(fe) if fe and p_exit >= .5 else None)

def mode_f(args):
    folder, Rn = args
    c, cfg, arm, model, group = describe(folder)
    drop = (c.get('drop_install') or {})
    spec = dict(points=c['points'], arrivals=load_arrivals(folder), faults=c.get('faults') or [], arm=arm, model=model,
                wait_s=10, seed=cfg['seed'], drop=(drop.get('start_sec', -1.0), drop.get('end_sec', -1.0), drop.get('mask', 0)))
    pred = free_case(spec, Rn); ref = ns3_outcome(folder, c)
    ns3_gate = ref['installs_after_exit'] > 0
    return dict(folder=os.path.basename(folder), group=group, arm=arm, model=model, topology=cfg['topology'], seed=cfg['seed'],
                ns3=ref, mirror=pred, F1=(pred['p_gate_open'] >= .5) == ns3_gate,
                F2=(pred['median_first_exit_s'] == (ref['exits_s'][0] if ref['exits_s'] else None)))

def poisson_binomial_interval(ps, lo=.025, hi=.975):
    dist = [1.0]
    for p in ps:
        new = [0.0] * (len(dist) + 1)
        for k, v in enumerate(dist): new[k] += v * (1 - p); new[k + 1] += v * p
        dist = new
    cdf = 0; a = b = None
    for k, v in enumerate(dist):
        cdf += v
        if a is None and cdf >= lo: a = k
        if b is None and cdf >= hi: b = k
    return a, b, sum(k * v for k, v in enumerate(dist))

def main():
    mode, which, out = sys.argv[1], sys.argv[2], sys.argv[3]
    Rn = int(sys.argv[4]) if len(sys.argv) > 4 else 100
    if mode == 'C':
        amp, adv = frozen_sets(which)
        with concurrent.futures.ProcessPoolExecutor(6) as ex: rows = list(ex.map(mode_c, amp + adv))
        n = len(rows); summ = dict(n=n, C1=sum(r['C1'] for r in rows) / n, C2=sum(r['C2'] for r in rows) / n,
            C3=sum(r['phi_agree'] for r in rows) / max(1, sum(r['phi_eval'] for r in rows)),
            C4=sum(r['reason_agree'] for r in rows) / sum(r['ticks'] for r in rows))
        summ['pass'] = summ['C1'] >= .95 and summ['C2'] >= .95 and summ['C3'] >= .98 and summ['C4'] >= .95
    elif mode == 'F':
        amp, adv = frozen_sets(which)
        with concurrent.futures.ProcessPoolExecutor(6) as ex: rows = list(ex.map(mode_f, [(f, Rn) for f in amp + adv]))
        a = [r for r in rows if r['group'] == 'amp2']
        per_arm = {arm: dict(n=len(v), F1=sum(r['F1'] for r in v) / len(v), F2=sum(r['F2'] for r in v) / len(v))
                   for arm in sorted({r['arm'] for r in a}) for v in [[r for r in a if r['arm'] == arm]]}
        joint = [r for r in a if r['arm'] == 'joint']
        lo, hi, mean = poisson_binomial_interval([r['mirror']['p_e1'] for r in joint]) if joint else (None, None, None)
        obs = sum(r['ns3']['e1'] for r in joint)
        brier = sum((r['mirror']['p_e1'] - r['ns3']['e1']) ** 2 for r in joint) / max(1, len(joint))
        summ = dict(n=len(rows), per_arm=per_arm, F3=dict(ns3_joint_e1=obs, n=len(joint), mirror_interval_95=[lo, hi], mirror_expected=mean,
                    inside=lo is not None and lo <= obs <= hi), brier_e1_joint=brier,
                    adverse=[dict(model=r['model'], arm=r['arm'], mirror=r['mirror'], ns3_e1=r['ns3']['e1'], ns3_exits=r['ns3']['exits_s']) for r in rows if r['group'] == 'adverse'])
        summ['pass_F1_F2'] = all(v['F1'] >= .95 and v['F2'] >= .95 for v in per_arm.values())
        if which == 'full': summ['pass_F3'] = summ['F3']['inside']
    elif mode == 'FDOE':
        design = json.load(open(which))
        with concurrent.futures.ProcessPoolExecutor(6) as ex: preds = list(ex.map(free_case, [d['mirror_spec'] for d in design['cases']], [Rn] * len(design['cases'])))
        rows = [dict(key=d['key'], **{k: d[k] for k in ('point', 'layout', 'arm')}, mirror=p) for d, p in zip(design['cases'], preds)]
        summ = dict(n=len(rows), design_sha256=hashlib.sha256(open(which, 'rb').read()).hexdigest())
    json.dump(dict(summary=summ, rows=rows), open(out, 'w'), indent=1)
    print(json.dumps(summ, indent=1)[:3000])

if __name__ == '__main__': main()
