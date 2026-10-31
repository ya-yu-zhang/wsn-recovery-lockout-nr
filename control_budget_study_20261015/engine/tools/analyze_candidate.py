"""Complete registered comparisons; all gate failures remain visible."""
import collections,csv,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from run_candidate import registration
from run_aligned import atomic

def compare(rows,baseline):
    target={(r['topology'],r['scenario'],r['seed']):r for r in rows if r['model']=='candidate'}
    control={(r['topology'],r['scenario'],r['seed']):r for r in rows if r['model']==baseline};out=[]
    for scene in ('multi_failure','overload'):
        pairs=[]
        for k in sorted(target):
            if k[1]!=scene:continue
            a,b=target[k],control[k]
            assert a['hashes']['arrivals']==b['hashes']['arrivals'] and a['hashes']['positions']==b['hashes']['positions']
            pairs.append(dict(topology=k[0],seed=k[2],service_delta=a['worst_party_timely']-b['worst_party_timely'],
                DATA_reduction=1-a['native']['control_psdu_bytes']/b['native']['control_psdu_bytes']))
        out.append(dict(scene=scene,baseline=baseline,pairs=pairs,mean_service_delta=float(np.mean([p['service_delta'] for p in pairs])),
                        mean_DATA_reduction=float(np.mean([p['DATA_reduction'] for p in pairs]))))
    return out
def gain(c):
    return ((c['mean_service_delta']>=.005 and c['mean_DATA_reduction']>=-.05) or
            (c['mean_service_delta']>=-.005 and c['mean_DATA_reduction']>=.05))
def main():
    reg=registration('development');rows=json.loads((ROOT/'results/candidate_development_manifest.json').read_text())
    assert len(rows)==len(reg['configs'])==56 and all(r['audit']['status']=='passed' for r in rows)
    primary=[r for r in rows if r['model']=='candidate'];contrasts=[]
    for baseline in ('intercept','freeze4','score0','plain3','legacygate','resource'):contrasts+=compare(rows,baseline)
    gates=[]
    for scene in ('multi_failure','overload'):
        by={c['baseline']:c for c in contrasts if c['scene']==scene}
        checks=dict(context_gain=gain(by['intercept']),online_update_gain=gain(by['freeze4']),
                    net_service_vs_score0=by['score0']['mean_service_delta']>=0,
                    DATA_cost_vs_score0=by['score0']['mean_DATA_reduction']>=-.05,
                    net_service_vs_resource=by['resource']['mean_service_delta']>=0)
        gates.append(dict(scene=scene,checks=checks,passed=all(checks.values())))
    metrics=[];primary_details=[];matches={}
    for r in rows:
        f=r['feedbacks'];d=r['decisions'];exposed=[v for v in d if v['selection_phase']=='event_exploration']
        metrics.append(dict(key=r['configuration_key'],model=r['model'],scene=r['scenario'],topology=r['topology'],seed=r['seed'],
            service=r['worst_party_timely'],DATA=r['native']['control_psdu_bytes'],ACK=r['native']['ack_psdu_bytes'],energy=r['estimated_radio_joules'],
            decisions=len(d),exposures=len(exposed),qualified=sum(v['reward'] is not None for v in f),updates=sum(r['bandit_updates']),
            censored=sum(v['reward'] is None for v in f),nonresource_updates=sum(r['bandit_updates'][1:]),
            qualified_exposure_feedback=sum(v['reward'] is not None and v['decision'] in {z['decision'] for z in exposed} for v in f)))
        if r['model']=='candidate':
            steps=json.loads((ROOT/r['evidence_directory']/(r['id']+'.controller.json')).read_text())['steps']
            checks=[s['learning_admission'] for s in steps if s['learning_admission'] is not None]
            primary_details.append(dict(key=r['configuration_key'],updates_by_arm=r['bandit_updates'],
                action_counts=dict(collections.Counter(v['action'] for v in d)),exposure_actions=[v['action'] for v in exposed],
                refusal_counts=dict(collections.Counter(k for c in checks for k in c['reasons'])),
                decisions=[dict(decision=v['decision'],time_ns=v['time_ns'],action=v['action'],phase=v['selection_phase'],
                                context=v['context'],scores=v['score_decomposition'],admission=v['learning_admission']) for v in d]))
    for m in ('intercept','freeze4','score0','resource','legacygate'):
        controls={(r['topology'],r['scenario'],r['seed']):r for r in rows if r['model']==m}
        trajectory=lambda r:[(v['time_ns'],v['action'],v['paths'],v.get('admission',{}).get('proposed_paths')) for v in r['decisions']]
        matches[m]=sum(trajectory(r)==trajectory(controls[r['topology'],r['scenario'],r['seed']]) for r in primary)
    pm=[m for m in metrics if m['model']=='candidate']
    result=dict(complete=True,development_cases=56,functional_cases=8,primary='candidate',
        primary_exposures=sum(m['exposures'] for m in pm),primary_qualified_exposure_feedback=sum(m['qualified_exposure_feedback'] for m in pm),
        primary_nonresource_updates=sum(m['nonresource_updates'] for m in pm),
        primary_action_counts=dict(collections.Counter(v['action'] for r in primary for v in r['decisions'])),
        primary_updates_by_arm=[sum(r['bandit_updates'][a] for r in primary) for a in range(4)],
        identical_primary_trajectories=matches,primary_runs=len(primary),gates=gates,comparisons=contrasts,
        old_original_matrix_restored=False,old_joint_gates_recomputed=False,formal_matrix_admitted=False,ready_to_submit=False,
        scope='two known geometries and two new paired streams; descriptive second development round',LLM_runtime_calls=0)
    atomic(ROOT/'analysis/candidate_analysis.json',result)
    for item in primary_details:atomic(ROOT/'analysis'/('candidate_diagnostic_'+item['key']+'.json'),item)
    with (ROOT/'analysis/candidate_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
    print(json.dumps({k:v for k,v in result.items() if k!='comparisons'}),flush=True)
if __name__=='__main__':main()
