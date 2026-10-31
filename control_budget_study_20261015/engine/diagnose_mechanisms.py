"""Post-run observable mechanism diagnostics; never learner input or validation."""
import collections, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INITIAL = [[0, 2, 3, 9], [1, 2, 3, 9]]


def winner(rows, action, current, poor):
    valid = [r for r in rows if r['objectives'] is not None]
    alternatives = [r for r in valid if r['paths'] != current]
    pool = alternatives if poor and alternatives else valid
    def score(r):
        z = r['objectives']; shared = r['shared_relay_fraction']
        changes = r['changed_source_fraction']
        return (.85*z[2]+.15*sum(z[:2])/2 if action == 0 else
                .85*max(z[:2])+.15*z[2] if action == 1 else
                .55*shared+.35*max(z[:2])+.10*z[2] if action == 2 else
                .55*max(z[:2])+.25*z[2]+(.02 if poor else .20)*changes)
    return min(pool, key=lambda r: (score(r), r['paths']))['paths'] if pool else None


def case_diagnostic(row):
    controller = json.loads((ROOT / row['evidence_directory'] /
                             (row['id']+'.controller.json')).read_text())
    steps = controller['steps']; versions = {0: INITIAL}; current = INITIAL
    summary = collections.Counter(); snapshots = []
    for step in steps:
        obs = step['observation']; t = obs['time_ns']; event = step['event']
        reports = {r['node']: r for r in obs['reports']}
        current = [list(p) for p in current]
        for source in (0, 1):
            if source in reports and reports[source]['version'] in versions:
                current[source] = versions[reports[source]['version']][source]
        summary['snapshots'] += 1
        summary['service_known_snapshots'] += bool(event['settled_service']['known'])
        summary['both_sources_fresh_snapshots'] += all(
            event['observation_states'][str(f)] == 'fresh' for f in (0, 1))
        summary['current_route_missing_snapshots'] += event['missing'] > 0
        summary['idle20_expired_relay_snapshots'] += any(
            n >= 2 and r.get('period_s') == 20 and
            event['observation_states'][str(n)] == 'expired' for n, r in reports.items())
        decision = step.get('decision')
        if decision is None:
            continue
        summary['decisions'] += 1
        summary['forced_exploration'] += decision['selection_rule'] == 'forced_exploration'
        is_ucb = decision['selection_rule'] == 'linucb_score'
        trained = sum(decision['updates_before_selection']) > 0
        summary['ucb_decisions'] += is_ucb
        summary['trained_ucb_decisions'] += is_ucb and trained
        if is_ucb and trained:
            summary['trained_ucb_action_'+str(decision['action'])] += 1
        poor = decision['search']['poor_settled_service']
        winners = [winner(decision['evaluated'], a, current, poor) for a in range(4)]
        expected = decision.get('admission', {}).get('proposed_paths', decision['paths'])
        assert winners[decision['action']] == expected, 'proxy reconstruction mismatch'
        distinct = len({json.dumps(p) for p in winners})
        summary['proxy_winner_distinct_snapshots'] += distinct > 1
        snapshots.append(dict(time_ns=t, decision=decision['decision'],
                              action=decision['action'], current_paths=current,
                              distinct_proxy_winners=distinct, proxy_winners=winners,
                              selection_rule=decision['selection_rule'],
                              updates_before_selection=decision['updates_before_selection'],
                              ucb_scores=decision['ucb_scores']))
        if decision['paths']:
            versions[decision['decision']] = decision['paths']
    summary['feedback_total'] = len(row['feedbacks'])
    summary['feedback_valid'] = sum(f['reward'] is not None for f in row['feedbacks'])
    summary['feedback_missing_closed_buckets'] = sum(
        f['missing_reason'] == 'closed generation buckets not received before deadline'
        for f in row['feedbacks'])
    return dict(configuration_key=row['configuration_key'], model=row['model'],
                topology=row['topology'], scene=row['scenario'],
                schedule=row['schedule'], freshness=row['freshness'],
                worst_party_timely=row['worst_party_timely'],
                control_data_bytes=row['native']['control_psdu_bytes'],
                counts=dict(summary), proxy_snapshots=snapshots)


def main():
    rows = json.loads((ROOT/'results/factorial_development_manifest.json').read_text())
    assert len(rows) == 64 and len({r['configuration_key'] for r in rows}) == 64
    cases = [case_diagnostic(r) for r in rows]
    totals = {}
    for model in sorted({c['model'] for c in cases}):
        combined = collections.Counter()
        for case in cases:
            if case['model'] == model:
                combined.update(case['counts'])
        totals[model] = dict(combined)
    output = dict(stage='post_run_development_diagnostic', formal_validation=False,
                  scope='received observation and existing proxy rows only; no unselected network reward',
                  limitations=['Counts describe these runs, not causal effects.',
                               'Proxy route differences do not establish physical recovery gains.',
                               'No offline diagnostic is fed back to any completed run.'],
                  cases=cases, totals_by_model=totals, LLM_runtime_calls=0)
    path = ROOT/'analysis/mechanism_diagnostic.json'
    path.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(totals, indent=2))


if __name__ == '__main__':
    main()
