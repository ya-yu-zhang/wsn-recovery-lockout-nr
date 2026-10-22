"""Recompute the completed 40-case study; no new simulations or inference tests."""
from pathlib import Path
import csv, hashlib, json, math, statistics

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'control_budget_study_20261015' / 'results'
OUT = ROOT / 'results'
MODELS = ('legacy', 'full_v2', 'horizon', 'cohort', 'closing')

def load(name):
    return json.loads((SOURCE / name).read_text())

def mean(v):
    return statistics.mean(v)

def main():
    rows = load('horizon_development_manifest.json')
    reg = load('horizon_development_registration.json')
    admission = load('horizon_development_admission_audit.json')
    frozen = load('horizon_development_analysis.json')
    with (SOURCE / 'horizon_development_case_metrics.csv').open(newline='') as f:
        csvrows = list(csv.DictReader(f))
    assert len(rows) == len(csvrows) == len(reg['configs']) == admission['cases'] == 40
    canon = lambda c: json.dumps(c, sort_keys=True)
    assert {canon(r['configuration']) for r in rows} == {canon(c) for c in reg['configs']}
    keys = {r['configuration_key'] for r in rows}
    assert len(keys) == 40
    assert keys == {r['configuration_key'] for r in csvrows} == {r['configuration_key'] for r in admission['records']}
    audits = {r['configuration_key']: r for r in admission['records']}
    csvmap = {r['configuration_key']: r for r in csvrows}
    grid = {}
    for r in rows:
        c, a = r['configuration'], r['audit']
        assert a['status'] == audits[r['configuration_key']]['status'] == 'passed'
        assert r['bandit_updates'] == [0, 0, 0, 0]
        assert a['runtime_LLM_calls'] == 0
        recomputed = min(t / n for t, n in zip(a['timely'], a['offered']))
        assert math.isclose(recomputed, a['worst_source_service'], abs_tol=1e-14)
        assert a['control_DATA_bytes'] == a['report_DATA_bytes'] + a['install_DATA_bytes']
        cr = csvmap[r['configuration_key']]
        for field in ('worst_source_service', 'control_DATA_bytes', 'report_DATA_bytes', 'install_DATA_bytes', 'application_DATA_bytes', 'network_ACK_bytes'):
            assert math.isclose(float(cr[field]), a[field], rel_tol=0, abs_tol=1e-13)
        assert float(cr['estimated_radio_joules']) == r['estimated_radio_joules']
        key = (int(c['topology'].split('_')[1]), c['scenario'], c['seed'])
        assert c['model'] not in grid.setdefault(key, {})
        grid[key][c['model']] = r
    assert len(grid) == 8
    for g in grid.values():
        assert set(g) == set(MODELS)
        assert len({tuple(r['audit']['offered']) for r in g.values()}) == 1
    pairs = []
    for (n, scenario, seed), g in sorted(grid.items()):
        for model in MODELS[1:]:
            a, b, p = g[model], g['legacy'], g['full_v2']
            pairs.append(dict(nodes=n, scenario=scenario, seed=seed, model=model,
                service_vs_legacy_pp=100 * (a['audit']['worst_source_service'] - b['audit']['worst_source_service']),
                control_reduction_vs_legacy_percent=100 * (1 - a['audit']['control_DATA_bytes'] / b['audit']['control_DATA_bytes']),
                service_vs_v2_pp=100 * (a['audit']['worst_source_service'] - p['audit']['worst_source_service']),
                radio_change_percent=100 * (a['estimated_radio_joules'] / b['estimated_radio_joules'] - 1)))
    summary, counts = {}, {}
    for n in (10, 20):
        for model in MODELS:
            rr = [g[model] for k, g in grid.items() if k[0] == n]
            aa = [audits[r['configuration_key']] for r in rr]
            known = sum(a['known_service_snapshots_checked'] for a in aa)
            checks = sum(r['audit']['budget_admissions'] for r in rr)
            rejected = sum(r['audit']['budget_rejections'] for r in rr)
            counts[f'{n}_{model}'] = dict(cases=4, known_service_snapshots=known,
                postbootstrap_gated_decisions=sum(a['postbootstrap_gated_decisions_checked'] for a in aa),
                control_admission_checks=checks, rejected_control_requests=rejected,
                admitted_control_requests=checks-rejected,
                byte_bound_audited=(model != 'legacy' and all(r['audit']['control_budget_bound_verified'] for r in rr)))
            if model == 'legacy':
                continue
            pp = [p for p in pairs if p['nodes'] == n and p['model'] == model]
            fields = ('service_vs_legacy_pp', 'control_reduction_vs_legacy_percent', 'service_vs_v2_pp', 'radio_change_percent')
            v = {f: mean(p[f] for p in pp) for f in fields}
            v['service_pair_range_pp'] = [min(p['service_vs_legacy_pp'] for p in pp), max(p['service_vs_legacy_pp'] for p in pp)]
            for field in fields[:3]:
                assert math.isclose(v[field], frozen['variants'][model]['by_size'][str(n)][field], rel_tol=0, abs_tol=1e-12)
            summary[f'{n}_{model}'] = v
    selected = []
    for model in MODELS[2:]:
        gain = mean(p['service_vs_v2_pp'] for p in pairs if p['model'] == model)
        passed = gain >= .5 and all(summary[f'{n}_{model}']['service_vs_legacy_pp'] >= -.5 and summary[f'{n}_{model}']['control_reduction_vs_legacy_percent'] >= 20 for n in (10, 20))
        assert passed == frozen['variants'][model]['development_gate_passed']
        if passed:
            selected.append(model)
    assert not selected and frozen['selected'] is None and frozen['no_further_method_revision']
    sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE / name for name in ('horizon_development_manifest.json', 'horizon_development_registration.json', 'horizon_development_case_metrics.csv', 'horizon_development_admission_audit.json', 'horizon_development_analysis.json'))}
    result = dict(native_cases=40, matched_size_scenario_seed_cells=8,
        independent_input_seeds=2, development_layout_seeds=1, fixed_size_specific_layouts=2,
        no_new_experiments=True, confirmatory_inference=False,
        all_original_gates_reproduced=True, stop_method_revision=True,
        offered_counts_equal_within_matched_cells=True,
        source_sha256=sources, summary=summary, observation_audit=counts, paired_results=pairs,
        note='Snapshots and decisions are repeated observations, not independent samples. The historical audit field budget_admissions counts checks including rejections; admitted counts subtract rejections. Known cohorts are policy-qualified historical evidence, not unobserved current service.',
        runtime_LLM_calls=0)
    OUT.mkdir(exist_ok=True)
    (OUT / 'reanalysis.json').write_text(json.dumps(result, indent=2) + '\n')
    with (OUT / 'paired_effects.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0])); w.writeheader(); w.writerows(pairs)
    print(json.dumps({k: result[k] for k in ('native_cases', 'all_original_gates_reproduced', 'stop_method_revision', 'offered_counts_equal_within_matched_cells')}))

if __name__ == '__main__':
    main()
