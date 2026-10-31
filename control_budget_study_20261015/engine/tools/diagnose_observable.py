"""Post-run descriptive mechanism checks; native truth never goes online."""
import collections,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from run_observable import registration,identity,atomic

def trajectory(row):
    return [(d['time_ns'],d['action'],d['paths']or d.get('admission',{}).get('proposed_paths'))for d in row['decisions']]

def main():
    reg=registration('development');rows=json.loads((ROOT/'results/observable_development_manifest.json').read_text());assert len(rows)==len(reg['configs'])==112
    assert {r['configuration_key']for r in rows}=={identity(c)for c in reg['configs']}
    by={(r['topology'],r['scenario'],r['seed'],r['model'],r['profile']):r for r in rows};primary=[];contrasts=[]
    for r in rows:
        if(r['model'],r['profile'])!=('stable6','obs_full'):continue
        folder=ROOT/r['evidence_directory'];p=folder/r['id']
        messages=[json.loads(x)for x in gzip.open(str(p)+'.protocol.jsonl.gz','rt')]
        steps=json.loads(Path(str(p)+'.controller.json').read_text())['steps']
        applied=[m for m in messages if m['kind']=='install_applied'];exits=[]
        for s in steps:
            i=s.get('installation')
            if i is None or i.get('outcome')!='abandoned_unconfirmed':continue
            t=s['observation']['time_ns'];known=set(i['confirmations'])
            physically_applied=[f for f in(0,1)if any(a['source']==f and a['decision']==i['decision']and a['time_ns']<=t for a in applied)]
            exits.append(dict(decision=i['decision'],time_ns=t,received_confirmations=sorted(known),physically_applied_sources_at_exit=physically_applied,
                              offline_truth_only=True,used_for_online_selection=False,physical_failure_asserted=False))
        actual=r['native']['control_psdu_bytes'];install=r['audit']['safety_and_cost']['actual_install_DATA_bytes'];extra=r['audit']['report_recovery']['extra_report_data_bytes'];ordinary=actual-install-extra;assert ordinary>=0
        primary.append(dict(configuration_key=r['configuration_key'],scene=r['scenario'],topology=r['topology'],seed=r['seed'],
                            action_counts=dict(collections.Counter(d['action']for d in r['decisions'])),
                            forced_exposures=sum(d['selection_phase']=='event_exploration'for d in r['decisions']),
                            valid_rewards=sum(f['reward']is not None for f in r['feedbacks']),
                            qualified_reward_actions=sorted({f['action']for f in r['feedbacks']if f['reward']is not None}),
                            actual_control_DATA_bytes=actual,actual_install_DATA_bytes=install,actual_extra_report_DATA_bytes=extra,ordinary_report_and_forwarding_DATA_bytes=ordinary,
                            installation_exits=exits,observable_audit=r['audit']['observable_control']))
        for model,profile in[('intercept6','obs_full'),('resource','obs_full'),('stable6','obs_exposure4'),('stable6','obs_old_deadline'),('stable6','obs_legacy_reports')]:
            b=by[r['topology'],r['scenario'],r['seed'],model,profile]
            assert r['hashes']['arrivals']==b['hashes']['arrivals']and r['hashes']['positions']==b['hashes']['positions']
            contrasts.append(dict(scene=r['scenario'],topology=r['topology'],seed=r['seed'],baseline=[model,profile],
                                  same_decision_action_path_trajectory=trajectory(r)==trajectory(b),
                                  service_delta=r['worst_party_timely']-b['worst_party_timely'],
                                  control_DATA_reduction=1-actual/b['native']['control_psdu_bytes']))
    assert len(primary)==8 and len(contrasts)==40
    result=dict(complete=True,primary_runs=primary,paired_mechanism_checks=contrasts,
                primary_forced_exposures=sum(p['forced_exposures']for p in primary),
                primary_installation_exits=sum(len(p['installation_exits'])for p in primary),
                primary_late_reconciliations=sum(p['observable_audit']['late_installation_reconciliations']for p in primary),
                ordinary_report_and_forwarding_DATA_fraction=sum(p['ordinary_report_and_forwarding_DATA_bytes']for p in primary)/sum(p['actual_control_DATA_bytes']for p in primary),
                scope='descriptive complete trajectories and post-run native classification, not counterfactual online feedback or causal mediation',
                formal_validation=False,LLM_runtime_calls=0)
    atomic(ROOT/'analysis/observable_diagnostic.json',result)
    print(json.dumps({k:v for k,v in result.items()if k not in('primary_runs','paired_mechanism_checks')}))
if __name__=='__main__':main()
