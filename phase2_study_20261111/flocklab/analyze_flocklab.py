"""Ingestion audit + outcomes for FlockLab replay. Usage: analyze_flocklab.py <probe|full|neutral>"""
import sys, json, csv, math, gzip, hashlib, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
FROZEN = Path('/workspace/wsn_ablation/repo/control_budget_study_20261015/results/amplification2_confirm')
def splitmix(x):
    x = (x + 0x9e3779b97f4a7c15) & (2**64 - 1); z = x
    z = ((z ^ (z >> 30)) * 0xbf58476d1ce4e5b9) & (2**64 - 1); z = ((z ^ (z >> 27)) * 0x94d049bb133111eb) & (2**64 - 1)
    return z ^ (z >> 31)
def load_trace(fn):
    t = {}
    for r in csv.DictReader(open(fn)): t[(int(r['src']), int(r['dst']))] = (float(r['prr']), r['bits'])
    return t
def link_audit(row):
    c = row['configuration']; tr = load_trace(c['trace_file']); res = []; ok = True
    for r in csv.DictReader(open(row['tracelinks_file'])):
        a, b, ev, dr = int(r['src']), int(r['dst']), int(r['evaluated']), int(r['dropped'])
        prr, bits = tr.get((a, b), (0.0, ''))
        x = {'src': a, 'dst': b, 'prr': prr, 'evaluated': ev, 'dropped': dr, 'drop_frac': dr / ev if ev else None}
        if c['trace_mode'] == 2 and bits:
            h = (c['seed'] * 1000003 + a * 1009 + b) & (2**64 - 1); off = splitmix(h) % len(bits)
            zeros = sum(bits[(off + k) % len(bits)] == '0' for k in range(ev)); x['expected_drops'] = zeros; x['exact'] = zeros == dr; ok &= x['exact']
            if ev >= 100: x['within_0.03_of_1-prr'] = abs(dr / ev - (1 - prr)) <= 0.03
        elif c['trace_mode'] == 1 and ev >= 100:
            se = math.sqrt(max(prr * (1 - prr), 1e-12) / ev); x['tol'] = max(0.03, 3 * se); x['pass'] = abs(dr / ev - (1 - prr)) <= x['tol']; ok &= x['pass']
        res.append(x)
    return ok, res
def main():
    which = sys.argv[1]; d = json.load(open(HERE / f'results_{which}/runs.json')); out = dict(stage=which, n_cases=d['n_cases'], n_done=d['n_done'], n_failed=len(d['failures']))
    rows = d['rows']; out['all_complete'] = d['n_done'] == d['n_cases']; out['audit_all_passed'] = all(r['audit'] == 'passed' for r in rows)
    if which == 'neutral':
        cmp = []
        for r in rows:
            rec = json.load(open(next(Path(r['folder']).glob('*.record.json'))))
            fz = [json.load(open(p)) for p in FROZEN.glob('*/case.json')]
            m = [z for z in fz if z['configuration']['topology'] == r['configuration']['topology'] and z['configuration']['seed'] == r['configuration']['seed'] and z['configuration']['arm'] == 'joint']
            cmp.append(dict(topology=r['configuration']['topology'], frozen_found=len(m), hashes_equal={k: (m[0]['hashes'][k] == rec['hashes'][k]) for k in ('.csv', '.jobs.csv', '.protocol.jsonl', '.radio.csv')} if m else None))
        out['neutrality'] = cmp
    else:
        aud = []; allok = True
        for r in rows:
            ok, res = link_audit(r); allok &= ok
            aud.append(dict(key=r['key'], ok=ok, links=res))
        out['ingestion_audit_passed'] = allok
        out['pass'] = out['all_complete'] and out['audit_all_passed'] and allok
        g = collections.defaultdict(list)
        for r in rows:
            c = r['configuration']; g[(c['day'], c['trace_mode'], c['scenario_tag'], c['arm'])].append(r)
        out['outcomes'] = [dict(day=k[0], mode='R2' if k[1] == 2 else 'R1', scenario=k[2], arm=k[3], n=len(v), with_unconfirmed_exit=sum(bool(x['unconfirmed_exits']) for x in v),
                                E1=sum(x['E1'] for x in v), gate_closed=sum(x['gate_closed'] for x in v), installs_after_exit_cases=sum(x['installs_after_exit'] > 0 for x in v),
                                median_worst_service=sorted(x['worst_source_service'] for x in v)[len(v) // 2]) for k, v in sorted(g.items())]
        out['per_run'] = [dict(key=r['key'], cfg={k: r['configuration'][k] for k in ('day', 'subgraph', 'trace_mode', 'seed', 'scenario_tag', 'arm')}, exits=r['unconfirmed_exits'], E1=r['E1'],
                               gate_closed=r['gate_closed'], installs_after_exit=r['installs_after_exit'], fs_after_last_exit=r['fs_after_last_exit'], worst=r['worst_source_service']) for r in rows]
        json.dump(aud, open(HERE / f'results_{which}/link_audit.json', 'w'), indent=1)
    json.dump(out, open(HERE / f'results_{which}/summary.json', 'w'), indent=1); print(json.dumps({k: v for k, v in out.items() if k != 'per_run'}, indent=1))
if __name__ == '__main__': main()
