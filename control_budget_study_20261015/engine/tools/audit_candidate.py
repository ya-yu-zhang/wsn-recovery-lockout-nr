"""Independent score algebra, selected feedback and bounded exposure audit."""
import json,math
import numpy as np
from wsn.rng import uniform
from tools.audit_learning import audit_learning

def audit_candidate(row,folder):
    if '_legacygate_' in row['policy']:return audit_learning(row,folder)
    steps=json.loads((folder/(row['id']+'.controller.json')).read_text())['steps']
    A=np.repeat(np.eye(6)[None,:,:],4,axis=0);b=np.zeros((4,6));count=[0]*4
    seen=[];credited=set();valid=0;exposure_ids=set();last_exposure_closed=None
    decisions={d['decision']:d for d in row['decisions']};versions={0:((0,2,3,9),(1,2,3,9))}
    latest_install=None;confirmed={};unknown_relay_exposures=0
    for s in steps:
        o=s['observation'];t=o['time_ns'];i=s.get('installation')
        if i is not None:confirmed[i['decision']]=i['closed'] and i['outcome']=='confirmed'
        fb=s['feedback']
        if fb is not None:
            if fb['decision'] in exposure_ids:last_exposure_closed=fb['time_ns']
            if fb['reward'] is not None:valid+=1;credited.add(fb['action'])
            if fb['updated_action'] is not None:
                d=decisions[fb['decision']];x=np.array(d['context'],dtype=float)
                if '_intercept_' in row['policy']:x=np.array([1.,0,0,0,0,0])
                a=fb['action'];A[a]+=np.outer(x,x);b[a]+=fb['reward']*x;count[a]+=1
            else:
                if fb['reward'] is None:assert fb['offered']==[] and fb['probabilities'] is None
        d=s['decision']
        if d is None:continue
        z=d['score_decomposition'];x=np.array(d['context'],dtype=float)
        if '_intercept_' in row['policy']:x=np.array([1.,0,0,0,0,0])
        assert z['model_context']==list(x)
        scores=[]
        for a in range(4):
            v=np.linalg.solve(A[a],x);mean=float(b[a]@v);bonus=.6*math.sqrt(max(0.,x@v));scores.append(mean+bonus)
            assert math.isclose(z['mean'][a],mean,abs_tol=1e-12) and math.isclose(z['bonus'][a],bonus,abs_tol=1e-12)
        if d['ucb_scores'] is not None:assert np.allclose(d['ucb_scores'],scores,rtol=0,atol=1e-12)
        if d['selection_phase']=='event_exploration':
            g=d['learning_admission'];assert g['admitted'] and not g['reasons'] and valid>0
            fresh={r['node']:r for r in o['reports'] if 0<=t-r['stamp_ns']<=(8_000_000_000 if r['node']<2 else 16_000_000_000)}
            assert all(f in fresh for f in (0,1))
            current=s['safety_assessment']['current_paths']
            assert all(fresh[f]['version'] in versions and tuple(versions[fresh[f]['version']][f])==tuple(current[f]) for f in (0,1))
            if latest_install is not None:assert confirmed.get(latest_install,False)
            eligible=[]
            for a,v in enumerate(d['constraints']['available']):
                witness=d['constraints']['witnesses'][str(a)]
                if v and a!=0 and a not in seen and a not in credited and witness is not None and all(n in fresh or n==9 for p in witness for n in p):eligible.append(a)
            eligible.sort(key=lambda a:(uniform(row['selection_seed'],'gated-single-exposure',a),a))
            assert eligible and d['action']==eligible[0] and g['eligible']==eligible
            for a in eligible:
                witness=d['constraints']['witnesses'][str(a)]
                assert witness==g['candidate_witnesses'][str(a)]
                unknown=sorted({n for p in witness for n in p[1:-1] if fresh[n]['cca']==0})
                assert unknown==g['unmeasured_candidate_relays'][str(a)]
            source_known=all(fresh[f]['cca']>0 for f in (0,1))
            assert g['source_congestion_known']==source_known
            if '_plain3_' not in row['policy']:
                assert source_known and max(fresh[f]['busy']/fresh[f]['cca'] for f in (0,1))<=.25
                assert max(fresh[f]['depth'] for f in (0,1))<=2
                macfail=any(fresh[f]['current_n']>=20 and fresh[f]['current_failed']/fresh[f]['current_n']>=.2 for f in (0,1))
                service=s['event']['settled_service'];poor=service['known'] and service['worst_timely']<.8
                assert macfail or poor
                assert g['poor_received_service']==poor and g['received_service']==service
            assert last_exposure_closed is None or t-last_exposure_closed>=20_000_000_000
            assert g['previous_exposure_closed_ns']==last_exposure_closed
            assert d['constraints']['install_budget_exhausted'] is False
            unknown_relay_exposures+=bool(g['unmeasured_candidate_relays'][str(d['action'])])
            seen.append(d['action']);exposure_ids.add(d['decision']);assert len(seen)<=3 and len(set(seen))==len(seen)
        elif d['ucb_scores'] is not None:
            allowed=[a for a,v in enumerate(d['constraints']['available']) if v]
            assert d['action']==max(allowed,key=lambda a:(scores[a],-a))
        if d['paths'] is not None:
            versions[d['decision']]=d['paths'];latest_install=d['decision'];confirmed[latest_install]=False
    assert count==row['bandit_updates']
    if '_freeze4_' in row['policy']:assert sum(count)<=4
    return dict(status='passed',qualified_feedback=valid,actual_updates=sum(count),exposure_actions=seen,
                exposures_with_unmeasured_candidate_relays=unknown_relay_exposures,
                unselected_labels=0,imputed_censored_rewards=0,LLM_runtime_calls=0)
