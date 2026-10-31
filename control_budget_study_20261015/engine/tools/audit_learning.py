"""Independent selected-update algebra and exposure input reconstruction."""
import collections,json,math
import numpy as np

def audit_learning(row,folder):
    steps=json.loads((folder/(row['id']+'.controller.json')).read_text())['steps']
    A=np.repeat(np.eye(6)[None,:,:],4,axis=0);b=np.zeros((4,6));count=[0]*4;exposures=[];credited=set();valid=0;last_closed=None
    for s in steps:
        fb=s['feedback']
        if fb is not None:
            last_closed=fb['time_ns']
            if fb['reward'] is not None:
                valid+=1;credited.add(fb['action'])
            if fb['updated_action'] is not None:
                origin=next(d for d in row['decisions'] if d['decision']==fb['decision']);x=np.array(origin['context'])
                if '_intercept_' in row['policy']:x=np.array([1.,0,0,0,0,0])
                a=fb['action'];A[a]+=np.outer(x,x);b[a]+=fb['reward']*x;count[a]+=1
        d=s['decision']
        if d is None:continue
        z=d['score_decomposition'];x=np.array(z['model_context'])
        for a in range(4):
            v=np.linalg.solve(A[a],x);mean=float(b[a]@v);bonus=.6*math.sqrt(max(0.,x@v))
            assert math.isclose(mean,z['mean'][a],abs_tol=1e-12) and math.isclose(bonus,z['bonus'][a],abs_tol=1e-12)
            if d['ucb_scores'] is not None:assert math.isclose(mean+bonus,d['ucb_scores'][a],abs_tol=1e-12)
        if '_gated_' in row['policy'] and d['selection_phase']=='event_exploration':
            o=s['observation'];t=o['time_ns'];r={p['node']:p for p in o['reports'] if 0<=t-p['stamp_ns']<=(8_000_000_000 if p['node']<2 else 16_000_000_000)}
            g=d['learning_admission'];used=set(g['used_nodes'])
            paths=s['safety_assessment']['current_paths']
            assert used=={n for p in paths for n in p[:-1]}
            versions={0:((0,2,3,9),(1,2,3,9))}
            versions.update({v['decision']:v['paths'] for v in row['decisions'] if v['time_ns']<t and v['paths'] is not None})
            assert all(r[f]['version'] in versions and tuple(versions[r[f]['version']][f])==tuple(paths[f]) for f in (0,1))
            assert g['admitted'] and not g['reasons'] and valid>0 and all(f in r for f in (0,1))
            assert used<=set(r) and all(r[n]['cca']>0 and r[n]['busy']/r[n]['cca']<=.25 and r[n]['depth']<=2 for n in used)
            assert any(r[f]['current_n']>=20 and r[f]['current_failed']/r[f]['current_n']>=.2 for f in (0,1))
            assert last_closed is not None and t-last_closed>=20_000_000_000
            assert d['action'] in (1,2,3) and d['action'] not in exposures and d['action'] not in credited
            exposures.append(d['action']);assert len(exposures)<=3
    assert count==row['bandit_updates']
    if '_freeze4_' in row['policy']:assert sum(count)<=4
    return dict(status='passed',score_decompositions=sum(s['decision'] is not None for s in steps),
                valid_selected_feedback=valid,actual_model_updates=sum(count),exposure_actions=exposures,
                unselected_reward_labels=0,censor_imputation=0,LLM_runtime_calls=0)
