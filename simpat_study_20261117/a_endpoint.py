"""Recompute the Nov-13 manuscript's IU-only E1 lockout (analyze_contract_ablation.post_exit.lockout_to_stop)
from the registered lockout windows: after the LAST unconfirmed exit, >=1 evaluated check, every one with
service reason installation_unconfirmed, and no installation before the action stop."""
import json, glob, collections, math

def e1(lock):
    w = lock['windows']
    if not w:
        return False
    last = w[-1]
    r = last['settled_service_reasons']
    return bool(last['reaches_action_stop'] and last['evaluated_checks'] >= 1
                and set(r) == {'installation_unconfirmed'} and not last['late_confirmation'])

def load(stage):
    out = []
    for f in glob.glob(f'results/{stage}/shard_*.jsonl'):
        out += [json.loads(x) for x in open(f)]
    return out

def wilson(k, n, z=1.959964):
    p = k / n; d = 1 + z*z/n; c = p + z*z/(2*n); h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return round((c-h)/d, 3), round((c+h)/d, 3)

if __name__ == '__main__':
    res = {}
    for stage in ('contract', 'scale', 'sensitivity', 'cca_patch'):
        g = collections.defaultdict(lambda: [0, 0, 0])
        for r in load(stage):
            c = r['configuration']
            if c['model'] == 'legacy':
                continue
            n = c['topology'].split('_')[1]
            st = (f"wait{c['install_exit_s']}" if c['install_exit_s'] != 10 else f"rate{c['control_rate']}" if c['control_rate'] != 305 else 'base')
            k = f"{n}|{c['model']}|{c['contract']}|{st}"
            g[k][0] += 1; g[k][1] += e1(r['lockout']); g[k][2] += r['lockout']['strict_lockout']
        res[stage] = {k: dict(cells=v[0], E1_iu_only=v[1], wilson95=wilson(v[1], v[0]), strict=v[2]) for k, v in sorted(g.items())}
    json.dump(res, open('results/a_endpoint_E1.json', 'w'), indent=1)
    for s, d in res.items():
        for k, v in d.items():
            if v['E1_iu_only'] or v['strict'] or 'joint' in k:
                print(s, k, v)
