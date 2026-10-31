"""Descriptive complete development analysis; no publication superiority gate."""
import collections,csv,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from run_learning_diagnosis import registration
from run_aligned import atomic

def contrast(rows,target,baseline):
    a={(r['topology'],r['scenario'],r['seed']):r for r in rows if r['model']==target}
    b={(r['topology'],r['scenario'],r['seed']):r for r in rows if r['model']==baseline}
    out=[]
    for scene in ('multi_failure','overload'):
        pairs=[]
        for k in sorted(a.keys()&b.keys()):
            if k[1]!=scene:continue
            x,y=a[k],b[k]
            pairs.append(dict(topology=k[0],seed=k[2],service_delta=x['worst_party_timely']-y['worst_party_timely'],
                              DATA_reduction=1-x['native']['control_psdu_bytes']/y['native']['control_psdu_bytes']))
        out.append(dict(scene=scene,target=target,baseline=baseline,pairs=pairs,
                        mean_service_delta=float(np.mean([p['service_delta'] for p in pairs])),
                        mean_DATA_reduction=float(np.mean([p['DATA_reduction'] for p in pairs]))))
    return out
def main():
    reg=registration('development');runs=json.loads((ROOT/'results/learning_development_manifest.json').read_text())
    assert len(runs)==len(reg['configs'])==104 and all(r['audit']['status']=='passed' for r in runs)
    sel=[r for r in runs if r['group']=='selectors'];fixed=[r for r in runs if r['group']=='fixed_arms']
    primary=[r for r in sel if r['model']=='gated'];diag=[]
    for r in sel:
        steps=json.loads((ROOT/r['evidence_directory']/(r['id']+'.controller.json')).read_text())['steps']
        feedback=collections.Counter((f['action'],'valid' if f['reward'] is not None else f['missing_reason']) for f in r['feedbacks'])
        gates=[s['learning_admission'] for s in steps if s['learning_admission'] is not None]
        X=np.array([d['context'] for d in r['decisions']],dtype=float)
        diag.append(dict(key=r['configuration_key'],scene=r['scenario'],model=r['model'],seed=r['seed'],topology=r['topology'],
            action_counts=dict(collections.Counter(d['action'] for d in r['decisions'])),
            update_counts=r['bandit_updates'],feedback_counts={f'{a}:{reason}':n for (a,reason),n in feedback.items()},
            checked_exposure_admissions=len(gates),admission_reason_counts=dict(collections.Counter(reason for g in gates for reason in g['reasons'])),
            admitted_exposures=sum(d['selection_phase']=='event_exploration' for d in r['decisions']),
            context_min=X.min(axis=0).tolist() if len(X) else [],context_max=X.max(axis=0).tolist() if len(X) else [],
            contexts=[dict(decision=d['decision'],time_ns=d['time_ns'],context=d['context'],action=d['action'],phase=d['selection_phase'],
                updates_before=d['updates_before_selection'],scores=d['score_decomposition'],admission=d['learning_admission']) for d in r['decisions']]))
    comparisons=[]
    for baseline in ('score0','intercept','freeze4','exposure4','arm0'):comparisons+=contrast(runs,'gated',baseline)
    for arm in ('arm1','arm2','arm3'):comparisons+=contrast(fixed,arm,'arm0')
    context=[x for x in comparisons if x['baseline']=='intercept']
    context_gates={x['scene']:((x['mean_service_delta']>=.005 and x['mean_DATA_reduction']>=-.05) or
                            (x['mean_service_delta']>=-.005 and x['mean_DATA_reduction']>=.05)) for x in context}
    matches={}
    for baseline in ('score0','intercept','freeze4'):
        mapping={(r['topology'],r['scenario'],r['seed']):r for r in sel if r['model']==baseline};n=0
        for r in primary:
            k=(r['topology'],r['scenario'],r['seed'])
            trajectory=lambda q:[(d['time_ns'],d['action'],d['paths'],d.get('admission',{}).get('proposed_paths')) for d in q['decisions']]
            n+=trajectory(r)==trajectory(mapping[k])
        matches[baseline]=dict(identical=n,total=len(primary))
    rankings=[]
    for scene in ('multi_failure','overload'):
        means={m:float(np.mean([r['worst_party_timely'] for r in fixed if r['scenario']==scene and r['model']==m])) for m in ('arm0','arm1','arm2','arm3')}
        rankings.append(dict(scene=scene,mean_whole_run_service=means,highest_mean_arm=max(means,key=means.get),
                             scope='Different whole-policy trajectories, not same-state arm causal rewards.'))
    result=dict(complete=True,cases=104,functional_configs=8,actual_fixed_arm_configs=64,selector_configs=40,
        primary='gated',primary_exposure_count=sum(d['selection_phase']=='event_exploration' for r in primary for d in r['decisions']),
        primary_action_counts=dict(collections.Counter(d['action'] for r in primary for d in r['decisions'])),
        context_gate_by_scene=context_gates,trajectory_matches=matches,comparisons=comparisons,fixed_arm_rankings=rankings,
        formal_matrix_admitted=False,ready_to_submit=False,old_joint_gates_not_recomputed=True,
        diagnostic_scope='104 new registered diagnostic development configurations; not192 screening or independent confirmation',LLM_runtime_calls=0)
    atomic(ROOT/'analysis/learning_analysis.json',result);atomic(ROOT/'analysis/learning_score_feedback_diagnostic.json',dict(cases=diag))
    metrics=[dict(key=r['configuration_key'],group=r['group'],model=r['model'],scene=r['scenario'],topology=r['topology'],seed=r['seed'],
                 service=r['worst_party_timely'],DATA=r['native']['control_psdu_bytes'],ACK=r['native']['ack_psdu_bytes'],energy=r['estimated_radio_joules'],
                 decisions=len(r['decisions']),updates=sum(r['bandit_updates']),valid_feedback=sum(f['reward'] is not None for f in r['feedbacks']),
                 censored_feedback=sum(f['reward'] is None for f in r['feedbacks'])) for r in runs]
    with (ROOT/'analysis/learning_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
    print(json.dumps({k:v for k,v in result.items() if k not in ('comparisons',)},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
