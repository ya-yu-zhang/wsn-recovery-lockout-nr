"""Registered analysis of the SIMPAT stages (PROTOCOL.md).  Writes results/analysis.json."""
from pathlib import Path
import json, math, random, statistics

STUDY = Path(__file__).resolve().parent
RES = STUDY / 'results'
BASE = STUDY.parent / 'control_budget_study_20261015'


def load(stage):
    rows = []
    for p in sorted((RES / stage).glob('shard_*.jsonl')):
        rows += [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    keys = [r['configuration_key'] for r in rows]
    assert len(keys) == len(set(keys)), 'duplicate case records'
    return rows


def wilson(k, n, z=1.959964):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(c - h) / d, (c + h) / d]


def cluster_boot(values_by_cluster, reps=10000, seed=20261117):
    """Mean over all units with layout clusters resampled; returns (mean, lo, hi)."""
    clusters = [v for v in values_by_cluster.values() if v]
    allv = [x for v in clusters for x in v]
    if not allv:
        return [None, None, None]
    rng = random.Random(seed)
    means = []
    for _ in range(reps):
        pick = [x for _ in clusters for x in rng.choice(clusters)]
        means.append(sum(pick) / len(pick))
    means.sort()
    return [sum(allv) / len(allv), means[int(.025 * reps)], means[int(.975 * reps) - 1]]


def native(r):
    # native trace hashes only; the controller transcript also records the contract label
    return {k: v for k, v in r['hashes'].items() if k != 'controller'}


def layout_of(c):
    return c['topology'].split('_')[2]


def size_of(c):
    return int(c['topology'].split('_')[1])


def cell(c):
    return (c['topology'], c['scenario'], c['seed'], c.get('install_exit_s', 10), c.get('control_rate', 305))


def smoke():
    rows = load('smoke')
    out = []
    expected = {('legacy', 'joint'): (0.8697490837327319, 98550)}
    archived = {('full_v2', 'joint'): (0.5928888888888889, 67812), ('horizon', 'joint'): (0.5928888888888889, 67812)}
    expected.update(archived)
    for r in rows:
        c = r['configuration']
        e = expected.get((c['model'], c['contract'])) if c['topology'].endswith('2026101501') else None
        a = r['audit']
        out.append(dict(model=c['model'], contract=c['contract'], topology=c['topology'],
                        service=a['worst_source_service'], control=a['control_DATA_bytes'],
                        reproduces_archive=None if e is None else (a['worst_source_service'] == e[0] and a['control_DATA_bytes'] == e[1]),
                        lockout=r['lockout'], wall_seconds=r['wall_seconds']))
    return out


def contract():
    rows = load('contract')
    import csv
    archived = {}
    with (BASE / 'results/horizon_development_case_metrics.csv').open(newline='') as h:
        for x in csv.DictReader(h):
            archived[(x['topology'], x['scenario'], int(x['seed']), x['model'])] = (float(x['worst_source_service']), int(x['control_DATA_bytes']))
    pairs = {}
    for r in rows:
        c = r['configuration']
        pairs.setdefault((c['topology'], c['scenario'], c['seed'], c['model']), {})[c['contract']] = r
    out, reproduced = [], 0
    for k, v in sorted(pairs.items()):
        j, p = v['joint'], v['post_exit']
        arch = archived[k]
        same = (j['audit']['worst_source_service'], j['audit']['control_DATA_bytes']) == arch
        reproduced += same
        out.append(dict(topology=k[0], scenario=k[1], seed=k[2], model=k[3], joint_reproduces_archive=same,
                        joint_service=j['audit']['worst_source_service'], post_exit_service=p['audit']['worst_source_service'],
                        delta_service_pp=100 * (p['audit']['worst_source_service'] - j['audit']['worst_source_service']),
                        joint_control=j['audit']['control_DATA_bytes'], post_exit_control=p['audit']['control_DATA_bytes'],
                        delta_control_pct=100 * (p['audit']['control_DATA_bytes'] / j['audit']['control_DATA_bytes'] - 1),
                        joint_lockout=j['lockout'], post_exit_lockout=p['lockout'],
                        identical=native(j) == native(p)))
    return dict(pairs=out, joint_reproduced=reproduced, cases=len(rows))


def incidence(rows, by):
    groups = {}
    for r in rows:
        groups.setdefault(by(r['configuration']), []).append(r)
    out = {}
    for g, rs in sorted(groups.items()):
        n = len(rs)
        d = dict(cells=n)
        for name, f in (('unconfirmed_exit', lambda r: r['lockout']['unconfirmed_exits'] > 0),
                        ('broad_lockout', lambda r: r['lockout']['broad_lockout']),
                        ('strict_lockout', lambda r: r['lockout']['strict_lockout'])):
            k = sum(map(f, rs))
            byl = {}
            for r in rs:
                byl.setdefault(layout_of(r['configuration']), []).append(1. if f(r) else 0.)
            d[name] = dict(count=k, proportion=k / n, wilson95=wilson(k, n), layout_cluster95=cluster_boot(byl)[1:])
        out[str(g)] = d
    return out


def paired(rows, model, base_contract='joint', alt_contract='post_exit', group=lambda c: size_of(c)):
    idx = {}
    for r in rows:
        c = r['configuration']
        idx[(cell(c), c['model'], c['contract'])] = r
    groups = {}
    for (cl, m, ct), r in idx.items():
        if m != model or ct != base_contract:
            continue
        alt = idx.get((cl, m, alt_contract))
        if alt is None:
            continue
        c = r['configuration']
        groups.setdefault(group(c), []).append((layout_of(c), r, alt))
    out = {}
    for g, items in sorted(groups.items()):
        ds, db = {}, {}
        changed = 0
        for lay, j, p in items:
            s = 100 * (p['audit']['worst_source_service'] - j['audit']['worst_source_service'])
            b = 100 * (p['audit']['control_DATA_bytes'] / j['audit']['control_DATA_bytes'] - 1)
            ds.setdefault(lay, []).append(s)
            db.setdefault(lay, []).append(b)
            changed += native(j) != native(p)
        flat = [x for v in ds.values() for x in v]
        out[str(g)] = dict(pairs=len(items), cells_changed=changed,
                           service_pp=cluster_boot(ds), control_pct=cluster_boot(db),
                           improved=sum(x > 1e-9 for x in flat), worsened=sum(x < -1e-9 for x in flat),
                           min_pp=min(flat), max_pp=max(flat))
    return out


def versus_legacy(rows):
    idx = {}
    for r in rows:
        c = r['configuration']
        idx[(cell(c), c['model'], c['contract'])] = r
    out = {}
    for arm in (('full_v2', 'joint'), ('full_v2', 'post_exit'), ('horizon', 'joint'), ('horizon', 'post_exit')):
        groups = {}
        for (cl, m, ct), r in idx.items():
            if (m, ct) != arm:
                continue
            leg = idx.get((cl, 'legacy', 'joint'))
            c = r['configuration']
            g = groups.setdefault(str(size_of(c)), ({}, {}))
            g[0].setdefault(layout_of(c), []).append(100 * (r['audit']['worst_source_service'] - leg['audit']['worst_source_service']))
            g[1].setdefault(layout_of(c), []).append(100 * (1 - r['audit']['control_DATA_bytes'] / leg['audit']['control_DATA_bytes']))
        out['/'.join(arm)] = {k: dict(service_pp=cluster_boot(v[0]), control_reduction_pct=cluster_boot(v[1])) for k, v in sorted(groups.items())}
    return out


def scale():
    rows = load('scale')
    coupled = [r for r in rows if r['configuration']['model'] != 'legacy']
    return dict(cases=len(rows),
                incidence_by_size_arm=incidence(coupled, lambda c: f"{size_of(c)}|{c['model']}|{c['contract']}"),
                incidence_by_size_workload_arm=incidence(coupled, lambda c: f"{size_of(c)}|{c['scenario']}|{c['model']}|{c['contract']}"),
                post_exit_minus_joint={m: paired(rows, m) for m in ('full_v2', 'horizon')},
                versus_legacy=versus_legacy(rows),
                wall_seconds_by_size={str(n): statistics.mean(r['wall_seconds'] for r in rows if size_of(r['configuration']) == n) for n in (10, 20, 40)})


def sensitivity():
    rows = load('sensitivity')
    base = [r for r in load('scale') if size_of(r['configuration']) == 10 and r['configuration']['model'] == 'horizon']
    allr = rows + base

    def setting(c):
        if c['install_exit_s'] != 10:
            return f"wait_{c['install_exit_s']}s"
        if c['control_rate'] != 305:
            return f"rate_{c['control_rate']}"
        return 'baseline'
    return dict(cases=len(rows),
                incidence=incidence(allr, lambda c: f"{setting(c)}|{c['contract']}"),
                post_exit_minus_joint=paired(allr, 'horizon', group=setting))


def cca_patch():
    rows = load('cca_patch')
    base = {}
    for r in load('scale'):
        c = r['configuration']
        base[(cell(c), c['model'], c['contract'])] = r
    coupled = [r for r in rows if r['configuration']['model'] != 'legacy']
    diffs = {}
    for r in rows:
        c = r['configuration']
        b = base[(cell(c), c['model'], c['contract'])]
        g = diffs.setdefault(f"{size_of(c)}|{c['model']}|{c['contract']}", ({}, {}))
        g[0].setdefault(layout_of(c), []).append(100 * (r['audit']['worst_source_service'] - b['audit']['worst_source_service']))
        g[1].setdefault(layout_of(c), []).append(100 * (r['audit']['control_DATA_bytes'] / b['audit']['control_DATA_bytes'] - 1))
    flips = {}
    for r in coupled:
        c = r['configuration']
        b = base[(cell(c), c['model'], c['contract'])]
        k = f"{size_of(c)}|{c['contract']}"
        f = flips.setdefault(k, dict(broad_both=0, broad_patched_only=0, broad_unpatched_only=0, neither=0))
        x, y = r['lockout']['broad_lockout'], b['lockout']['broad_lockout']
        f['broad_both' if x and y else 'broad_patched_only' if x else 'broad_unpatched_only' if y else 'neither'] += 1
    return dict(cases=len(rows),
                incidence_by_size_arm=incidence(coupled, lambda c: f"{size_of(c)}|{c['model']}|{c['contract']}"),
                post_exit_minus_joint=paired(rows, 'horizon'),
                patched_minus_unpatched={k: dict(service_pp=cluster_boot(v[0]), control_pct=cluster_boot(v[1]))
                                         for k, v in sorted(diffs.items())},
                broad_lockout_agreement=flips)


def docking():
    d = RES / 'docking'
    if not (d / 'ns3.jsonl').exists():
        return None
    ns3 = [json.loads(x) for x in (d / 'ns3.jsonl').read_text().splitlines()]
    ref = [json.loads(x) for x in (d / 'reference.jsonl').read_text().splitlines()]

    def metrics(r):
        done = r['success'] + r['channel_access_failure'] + r['no_ack']
        return dict(p_success=r['success'] / done, p_caf=r['channel_access_failure'] / done,
                    p_noack=r['no_ack'] / done, cca_busy=r['cca_busy'] / max(1, r['cca']), service_ms=r['service_mean_ms'])

    def agg(rows):
        g = {}
        for r in rows:
            g.setdefault((r['stations'], r['load']), []).append(metrics(r))
        return {k: {m: (statistics.mean(x[m] for x in v), statistics.stdev(x[m] for x in v) / math.sqrt(len(v)))
                    for m in v[0]} for k, v in g.items()}
    a, b = agg(ns3), agg(ref)
    cells, agree, total = [], 0, 0
    for k in sorted(a):
        row = dict(stations=k[0], load=k[1])
        for m in a[k]:
            x, y = a[k][m][0], b[k][m][0]
            ok = (abs(x - y) <= 0.10 * max(y, 1e-9)) if m == 'service_ms' else abs(x - y) <= 0.02
            row[m] = dict(ns3=x, ns3_se=a[k][m][1], reference=y, reference_se=b[k][m][1], agree=ok)
            agree += ok
            total += 1
        cells.append(row)
    return dict(cells=cells, comparisons=total, agreeing=agree, fraction=agree / total, docked=agree / total >= .9)


def main():
    out = {}
    for name, f in (('smoke', smoke), ('contract', contract), ('scale', scale), ('sensitivity', sensitivity), ('cca_patch', cca_patch), ('docking', docking)):
        try:
            out[name] = f()
        except (FileNotFoundError, AssertionError, KeyError, StopIteration, ValueError) as e:
            out[name] = dict(unavailable=repr(e))
    (RES / 'analysis.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: (v if k == 'smoke' else '...') for k, v in out.items()}, indent=1)[:6000])


if __name__ == '__main__':
    main()
