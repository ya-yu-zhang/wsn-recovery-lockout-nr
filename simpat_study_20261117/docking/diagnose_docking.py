"""E1 diagnosis (exploratory, after the registered comparison failed its 90 % criterion).

Runs the reference under the two ns-3 properties identified from the ns-3.44 source and compares
every variant -- and, when present, the CCA-patched ns-3 run -- with the same frozen tolerances.
Writes results/docking/diagnosis.json.
"""
from pathlib import Path
import concurrent.futures, json, math, statistics, sys

HERE = Path(__file__).resolve().parent
RES = HERE.parent / 'results' / 'docking'
sys.path.insert(0, str(HERE))
from csma_reference import simulate  # noqa: E402
from run_docking import grid  # noqa: E402

VARIANTS = {'standard': dict(capture=False, cca_window='standard'),
            'capture': dict(capture=True, cca_window='standard'),
            'peak_reset': dict(capture=False, cca_window='peak_reset'),
            'capture+peak_reset': dict(capture=True, cca_window='peak_reset')}


def run(args):
    name, c = args
    r = simulate(c['stations'], c['rate'], payload=64, retries=2, stop_s=120., warm_s=5., seed=1000 + c['seed'],
                 **VARIANTS[name])
    r['load'] = c['load']
    r['variant'] = name
    return r


def metrics(r):
    d = r['success'] + r['channel_access_failure'] + r['no_ack']
    return dict(p_success=r['success'] / d, p_caf=r['channel_access_failure'] / d, p_noack=r['no_ack'] / d,
                cca_busy=r['cca_busy'] / max(1, r['cca']), service_ms=r['service_mean_ms'])


def agg(rows):
    g = {}
    for r in rows:
        g.setdefault((r['stations'], r['load']), []).append(metrics(r))
    return {k: {m: (statistics.mean(x[m] for x in v), statistics.stdev(x[m] for x in v) / math.sqrt(len(v)))
                for m in v[0]} for k, v in g.items()}


def compare(a, b):
    ok = tot = 0
    worst = {}
    for k in a:
        for m in a[k]:
            x, y = a[k][m][0], b[k][m][0]
            good = abs(x - y) <= (0.10 * y if m == 'service_ms' else 0.02)
            ok += good
            tot += 1
            dev = abs(x - y) / (y if m == 'service_ms' else 1)
            worst[m] = max(worst.get(m, 0.), dev)
    return dict(agreeing=ok, comparisons=tot, fraction=ok / tot, max_abs_deviation=worst)


def main():
    cases = [(n, c) for n in VARIANTS for c in grid()]
    with concurrent.futures.ProcessPoolExecutor(8) as pool:
        rows = list(pool.map(run, cases))
    (RES / 'reference_variants.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows))
    ns3 = agg([json.loads(x) for x in (RES / 'ns3.jsonl').read_text().splitlines()])
    refs = {n: agg([r for r in rows if r['variant'] == n]) for n in VARIANTS}
    out = dict(registered=compare(ns3, refs['standard']),
               variants={n: compare(ns3, refs[n]) for n in VARIANTS})
    lo, hi = refs['standard'], refs['capture']
    inside = tot = 0
    for k in ns3:
        for m in ns3[k]:
            a, se = ns3[k][m]
            tol = 2 * math.hypot(se, lo[k][m][1])
            inside += min(lo[k][m][0], hi[k][m][0]) - tol <= a <= max(lo[k][m][0], hi[k][m][0]) + tol
            tot += 1
    out['bracketed_by_standard_and_capture'] = dict(inside=inside, comparisons=tot, fraction=inside / tot)
    p = RES / 'ns3_cca_patched.jsonl'
    if p.exists():
        patched = agg([json.loads(x) for x in p.read_text().splitlines()])
        out['ns3_cca_patched'] = {n: compare(patched, refs[n]) for n in VARIANTS}
        out['ns3_cca_patched_vs_unpatched'] = compare(patched, ns3)
    out['scope'] = ('exploratory diagnosis after the registered comparison; the registered verdict is '
                    'out["registered"] and is not replaced')
    (RES / 'diagnosis.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'scope'}, indent=1))


if __name__ == '__main__':
    main()
