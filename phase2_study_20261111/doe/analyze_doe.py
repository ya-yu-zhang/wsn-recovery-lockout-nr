"""H1-H3 and exploratory phase diagram / main effects for the registered DOE."""
import json, collections, math
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
def main():
    d = json.load(open(HERE / 'runs.json')); pred = json.load(open(HERE / 'predictions_FDOE.json')); design = json.load(open(HERE / 'design.json'))
    P = {r['key']: r for r in pred.get('rows', [])}; byk = {c['key']: c for c in design['cases']}
    rows = d['rows']; out = dict(n_cases=d['n_cases'], n_done=d['n_done'], n_failed=len(d['failures']), technical_failure_rate=len(d['failures']) / d['n_cases'],
                                 audit_all_passed=all(r['audit'] == 'passed' for r in rows), predictions_sha256=d['predictions_sha256'])
    J = [r for r in rows if r['configuration']['arm'] == 'joint']; PE = [r for r in rows if r['configuration']['arm'] == 'post_exit']
    h1 = [r for r in J if r['unconfirmed_exits'] and r['fs_after_last_exit'] is False]
    out['H1'] = dict(eligible=len(h1), gate_closed=sum(r['gate_closed'] for r in h1), fraction=(sum(r['gate_closed'] for r in h1) / len(h1)) if h1 else None)
    out['H1']['pass'] = out['H1']['fraction'] is not None and out['H1']['fraction'] >= .95
    out['H1']['note'] = 'gate_closed = no install at/after first unconfirmed exit before action stop (post_exit() accounting)'
    out['H2'] = dict(n=len(PE), E1=sum(r['E1'] for r in PE), pass_=sum(r['E1'] for r in PE) == 0)
    ex_agree = gate_agree = 0; n = 0
    for r in ([] if pred.get('void') else rows):
        p = P[r['key']]['mirror']; n += 1
        ex_agree += (p['p_exit'] >= .5) == bool(r['unconfirmed_exits'])
        gate_agree += (p['p_gate_open'] >= .5) == (r['installs_after_exit'] > 0)
    out['H3'] = dict(void=True, reason=pred.get('reason')) if pred.get('void') else dict(n=n, exit_agreement=ex_agree / n, gate_agreement=gate_agree / n, pass_=ex_agree / n >= .9 and gate_agree / n >= .9)
    # exploratory: Joint incidence by design point and factor main effects
    cell = collections.defaultdict(list)
    for r in J: cell[r['configuration']['point']].append(r)
    pts = {c['point']['idx']: c['point'] for c in design['cases']}
    out['points'] = [dict(**{k: pts[i][k] for k in ('idx', 'A', 'B', 'C', 'D', 'E', 'drop_start', 'drop_end', 'mask', 'wait_s')}, faults=pts[i]['faults'], n=len(v),
                          exit=sum(bool(x['unconfirmed_exits']) for x in v), E1=sum(x['E1'] for x in v), gate_closed=sum(x['gate_closed'] for x in v),
                          postexit_E1=sum(x['E1'] for x in PE if x['configuration']['point'] == i)) for i, v in sorted(cell.items())]
    me = {}
    for f in 'ABCDE':
        me[f] = [dict(level=l, n=len(v), E1_rate=sum(x['E1'] for x in v) / len(v), gate_closed_rate=sum(x['gate_closed'] for x in v) / len(v))
                 for l in range(3) for v in [[x for x in J if pts[x['configuration']['point']][f] == l]]]
    out['main_effects_joint'] = me
    # exploratory logistic (Newton, ridge 1e-3) on E1 with dummy-coded factors
    X = []; y = []
    for x in J:
        p = pts[x['configuration']['point']]; X.append([1] + [int(p[f] == l) for f in 'ABCDE' for l in (1, 2)]); y.append(int(x['E1']))
    X = np.array(X, float); y = np.array(y, float); b = np.zeros(X.shape[1])
    for _ in range(50):
        mu = 1 / (1 + np.exp(-X @ b)); W = mu * (1 - mu); H = X.T @ (X * W[:, None]) + 1e-3 * np.eye(len(b)); b += np.linalg.solve(H, X.T @ (y - mu) - 1e-3 * b)
    names = ['intercept'] + [f'{f}{l}' for f in 'ABCDE' for l in (1, 2)]
    se = np.sqrt(np.diag(np.linalg.inv(H))); out['logistic_E1_joint'] = [dict(term=nm, coef=float(c), se=float(s)) for nm, c, s in zip(names, b, se)]
    json.dump(out, open(HERE / 'summary.json', 'w'), indent=1); print(json.dumps({k: out[k] for k in ('n_done', 'n_failed', 'audit_all_passed', 'H1', 'H2', 'H3')}, indent=1))
if __name__ == '__main__': main()
