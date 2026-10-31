"""New inputs and complete native audits; diagnostic development, not confirmation."""
import argparse,hashlib,json,time,traceback
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import run_observable as old
from run_closed_loop import ROOT,compile_driver,one
from run_aligned import atomic

PARENT='84d981176cbdd2e32ee8b0619fb8f9e34ba0d755'
BASE='scalar4_failure_current_ops_epoch_aligned_safe_interrupt_installbudget_transaction_txguard_observable_installexit_learnstudy_'
SUFFIX='ctx6_noop_cache20_retry_freshfixed_mask'
POLICIES={
 'score0':'linucb_event_'+BASE+'scoreonly_'+SUFFIX,
 'gated':'linucb_event_'+BASE+'gated_'+SUFFIX,
 'intercept':'linucb_event_'+BASE+'gated_intercept_'+SUFFIX,
 'freeze4':'linucb_event_'+BASE+'gated_freeze4_'+SUFFIX,
 'exposure4':'linucb_event_'+BASE+SUFFIX,
 **{f'arm{a}':f'force{a}_'+BASE+'scoreonly_'+SUFFIX for a in range(4)}}

def key(c):return '_'.join(str(c[k]) for k in ('group','topology','scenario','model','seed'))
def configs(stage):
    if stage=='functional':
        return [dict(group='functional',model=m,topology='base',scenario=s,seed=1002000+i,
                     generation_stop=90,faults=[[35,2]] if s=='failure' else [],**e)
                for i,(m,s,e) in enumerate([('gated','steady',{}),('gated','failure',{'reject':True}),
                    ('gated','steady',{'missing':True}),('gated','overload',{}),('gated','steady',{'broken':True}),
                    ('freeze4','overload',{}),('intercept','failure',{}),('arm3','failure',{})])]
    out=[]
    for top in ('base','jitter_b'):
        for scene in ('multi_failure','overload'):
            for seed in (1002101,1002102,1002103,1002104):
                common=dict(topology=top,scenario=scene,seed=seed,generation_stop=330,
                            faults=[[65,2],[145,3],[225,6]] if scene=='multi_failure' else [])
                out.extend(dict(group='fixed_arms',model=f'arm{a}',**common) for a in range(4))
                if seed in (1002101,1002102):out.extend(dict(group='selectors',model=m,**common) for m in ('score0','gated','intercept','freeze4','exposure4'))
    return out
def signature():
    paths=[p for p in ROOT.rglob('*') if p.is_file() and p.suffix in ('.py','.cc','.h') and '__pycache__' not in p.parts]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
def registration(stage):
    p=ROOT/'docs'/f'learning_{stage}_registration.json';cfg=configs(stage);sig=signature()
    if p.exists():
        r=json.loads(p.read_text());assert r['configs']==cfg and r['source_sha256']==sig,'registered source/config drift';return r
    r=dict(stage=stage,parent_commit=PARENT,registered_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
           configs=cfg,policies=POLICIES,source_sha256=sig,formal_validation=False,ready_to_submit=False,LLM_runtime_calls=0,
           primary='gated',old_failed_gates_preserved=True,post_run_primary_selection_forbidden=True,
           unchanged=['stable6','alpha=.6','four route objectives','selected-only version-aligned reward','source5/relay local15_event',
                      'FE<=64 and declared20us/FE','ten-second unconfirmed exit','one targeted per-source retry','native FIFO and full costs'],
           proposed_exposure={'cap':3,'max_attempts_nonresource_arm':1,'prior_qualified_reward':True,'current_received_failure_n':20,
             'current_received_failure_fraction':.2,'known_current_route_busy_max':.25,'known_current_route_queue_max':2,
             'transaction_cooldown_s':20,'no_pending_transaction':True,'censoring_consumes_attempt':True},
           freeze={'qualified_updates_before_freeze':4,'within_run_only':True,'whole_run_evaluation':True},
           statistics='Development diagnostic: two known geometries; fixed arms four new streams, selectors two. Descriptive paired effects; no held-out or causal arm reward claim.',
           context_gate={'service_gain':.005,'DATA_increase_limit':.05,'alternative_service_margin':-.005,'alternative_DATA_reduction':.05},
           full_prior_gates=json.loads((ROOT/'docs/observable_development_registration.json').read_text())['gates'],
           scope='64 actual fixed-arm trajectories plus40 selector configurations; not the192-case screening or formal matrix',
           independent_raw_recovery=False)
    atomic(p,r);return r
def execute(payload):
    cfg,binary,stage=payload;folder=ROOT/'results'/('learning_'+stage)/(key(cfg)+'_'+str(time.time_ns()));folder.mkdir(parents=True)
    try:
        row=one(Path(binary),policy=POLICIES[cfg['model']],profile='local15_event',extended=True,source_only=True,
                folder=folder,queue_discipline='fifo',epoch_certificate=True,report_retry=True,report_budget=True,
                **{k:v for k,v in cfg.items() if k not in ('group','model')})
        row.update(model=cfg['model'],group=cfg['group'],profile='learning_full',freshness='fixed16',stage=stage,
                   configuration_key=key(cfg),evidence_directory=str(folder.relative_to(ROOT)))
        a=old.audit_case(row,folder)
        a['settled_service']=old.audit_service(row,folder);a['queue_and_age']=old.audit_epoch(row,folder)
        a['report_recovery']=old.audit_report_recovery(row,folder);a['stable_context']=old.independent_context_audit(row,folder)
        row['audit']=a
        a['aligned_reward_and_budget']=old.audit_aligned(row,folder);a['safety_and_cost']=old.audit_safety(row,folder)
        a['transaction_guard_and_exposure']=old.audit_transaction(row,folder);a['observable_control']=old.audit_observable(row,folder)
        from tools.audit_learning import audit_learning
        a['learning']=audit_learning(row,folder)
        atomic(folder/'case.json',row);return row
    except BaseException:
        (folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),required=True)
    p.add_argument('--register-only',action='store_true');p.add_argument('--workers',type=int,default=2);args=p.parse_args()
    assert 1<=args.workers<=4;reg=registration(args.stage)
    if args.register_only:print('REGISTERED',args.stage,len(reg['configs']));return
    if args.stage=='development':
        f=json.loads((ROOT/'results/learning_functional_manifest.json').read_text());assert len(f)==8 and all(r['audit']['status']=='passed' for r in f)
    binary=compile_driver();p=ROOT/'results'/f'learning_{args.stage}_manifest.json'
    rows=json.loads(p.read_text()) if p.exists() else [];done={r['configuration_key'] for r in rows};failures=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(execute,(c,str(binary),args.stage)):c for c in reg['configs'] if key(c) not in done}
        for f in as_completed(futures):
            try:
                r=f.result();rows.append(r);rows.sort(key=lambda x:x['configuration_key']);atomic(p,rows)
                print(json.dumps(dict(audited=len(rows),registered=len(reg['configs']),case=r['configuration_key'],service=r['worst_party_timely'],DATA=r['native']['control_psdu_bytes'])),flush=True)
            except BaseException:
                failures.append(dict(config=futures[f],traceback=traceback.format_exc()));atomic(ROOT/'results'/f'learning_{args.stage}_failures.json',failures)
                print('FAILED',key(futures[f]),flush=True)
    if failures:raise RuntimeError(f'{len(failures)} attempts failed; evidence retained')
    assert len(rows)==len(reg['configs']);print('COMPLETE',args.stage,len(rows),flush=True)
if __name__=='__main__':main()
