"""Mode-F calibration (registered): per-hop MAC job success h(d) = 1/(1+exp(k(d-d0))) and a
constant per-hop latency, fitted ONLY on amplification2_manip_check + amplification_pilot2/3
ten-node cases, excluding layout budget_10_2026101501 (adverse) and all Amp-1/Amp-2 confirm layouts.
Jobs whose receiver had been removed by a fault are excluded (a dead receiver is modelled explicitly)."""
import json, glob, gzip, csv, io, math, os, sys, hashlib, concurrent.futures
import numpy as np
R = '/workspace/wsn_ablation/repo/control_budget_study_20261015/results'
EXCL = {'budget_10_2026101501'}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calibration.json')

def monitor_path(n):
    return {5: (5, 9), 4: (4, 5, 9), 3: (3, 5, 9)}.get(n, (n, 4, 5, 9))

def one(folder):
    case = json.load(open(folder + '/case.json')); cfg = case['configuration']
    pts = {int(k): tuple(v) for k, v in case['points'].items()}
    dead = {relay: when * 1e9 for when, relay in (case.get('faults') or [])}
    paths = {}; ctl = {}
    for l in gzip.open(glob.glob(folder + '/*.protocol.jsonl.gz')[0], 'rt'):
        if '"generated"' in l:
            e = json.loads(l); paths[(e['flow'], e['sequence'])] = e['path']
        elif '"report_packet"' in l:
            e = json.loads(l); ctl[(65000, e['sequence'])] = monitor_path(e['source'])
        elif '"install_packet"' in l:
            e = json.loads(l); ctl[(65001, e['sequence'])] = (9, 5, 4, e['source'])
    rows = []; lat = []
    txt = gzip.open(glob.glob(folder + '/*.jobs.csv.gz')[0], 'rt').read()
    for r in csv.DictReader(io.StringIO(txt)):
        n = int(r['node']); flow = int(r['flow']); seq = int(r['sequence'])
        p = paths.get((flow, seq)) if flow < 2 else ctl.get((flow, seq))
        if not p or n not in p or p.index(n) + 1 >= len(p): continue
        rx = p[p.index(n) + 1]
        if rx in dead and int(r['request_ns']) >= dead[rx]: continue
        ok = r['status'] == '0'
        rows.append((math.dist(pts[n], pts[rx]), ok))
        if ok: lat.append(int(r['J_ns']))
    return cfg['topology'], rows, lat

def main():
    folders = []
    for st in ('amplification2_manip_check', 'amplification_pilot2', 'amplification_pilot3'):
        for f in sorted(glob.glob(f'{R}/{st}/*/case.json')):
            top = json.load(open(f))['configuration']['topology']
            if top.startswith('budget_10_') and top not in EXCL: folders.append(os.path.dirname(f))
    with concurrent.futures.ProcessPoolExecutor(6) as ex: res = list(ex.map(one, folders))
    d = np.array([x for _, rows, _ in res for x, _ in rows]); y = np.array([o for _, rows, _ in res for _, o in rows], float)
    lat = np.array([v for _, _, l in res for v in l])
    # IRLS logistic: logit P(success) = a + b d  ->  k=-b, d0=-a/b
    X = np.c_[np.ones_like(d), d]; w = np.zeros(2)
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ w)); W = p * (1 - p) + 1e-9
        w = w + np.linalg.solve(X.T @ (X * W[:, None]), X.T @ (y - p))
    bins = [(lo, lo + 10) for lo in range(0, 80, 10)]
    table = [dict(d=f'{lo}-{hi}', n=int(((d >= lo) & (d < hi)).sum()), success=float(y[(d >= lo) & (d < hi)].mean()) if ((d >= lo) & (d < hi)).any() else None) for lo, hi in bins]
    cal = dict(logit_k=float(-w[1]), logit_d0=float(-w[0] / w[1]), hop_latency_s=float(np.median(lat) / 1e9),
               n_jobs=int(len(y)), n_cases=len(folders), layouts=sorted({t for t, _, _ in res}), empirical_by_distance=table,
               overall_success=float(y.mean()))
    s = json.dumps(cal, indent=1, sort_keys=True); open(OUT, 'w').write(s + '\n')
    print(s[:1500]); print('SHA256', hashlib.sha256((s + '\n').encode()).hexdigest())

if __name__ == '__main__': main()
