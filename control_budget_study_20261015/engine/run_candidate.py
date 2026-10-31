"""Second registered development revision; no previous raw matrix claimed restored."""
import argparse,hashlib,json,os,time,traceback
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from run_closed_loop import ROOT,one,compile_driver
from run_aligned import atomic
import run_observable as old
from tools.audit_candidate import audit_candidate

BASE='scalar4_failure_current_ops_epoch_aligned_safe_interrupt_installbudget_transaction_txguard_observable_installexit_learnstudy_candidate2_'
TAIL='ctx6_noop_cache20_retry_freshfixed_mask'
POLICIES={'candidate':'linucb_event_'+BASE+'gated_'+TAIL,
 'intercept':'linucb_event_'+BASE+'gated_intercept_'+TAIL,
 'freeze4':'linucb_event_'+BASE+'gated_freeze4_'+TAIL,
 'plain3':'linucb_event_'+BASE+'gated_plain3_'+TAIL,
 'legacygate':'linucb_event_'+BASE+'gated_legacygate_'+TAIL,
 'score0':'linucb_event_'+BASE+'scoreonly_'+TAIL,
 'resource':'force0_'+BASE+'scoreonly_'+TAIL}
def key(c):return '_'.join(str(c[k]) for k in ('topology','scenario','model','seed'))
def configs(stage):
    if stage=='functional':
        items=[('candidate','steady',{}),('candidate','failure',{'reject':True}),('candidate','steady',{'missing':True}),
               ('candidate','overload',{}),('candidate','steady',{'broken':True}),('intercept','failure',{}),('freeze4','overload',{}),('plain3','overload',{})]
        return [dict(model=m,scenario=sc,topology='base',seed=1002200+i,generation_stop=90,
                     faults=[[35,2]] if sc=='failure' else [],**ex) for i,(m,sc,ex) in enumerate(items)]
    return [dict(model=m,scenario=sc,topology=top,seed=seed,generation_stop=330,
                 faults=[[65,2],[145,3],[225,6]] if sc=='multi_failure' else [])
            for top in ('base','jitter_b') for sc in ('multi_failure','overload') for seed in (1002301,1002302) for m in POLICIES]
def signature():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*'))
            if p.is_file() and p.suffix in ('.py','.cc','.h') and '__pycache__' not in p.parts}
def registration(stage):
    p=ROOT/'docs'/f'candidate_{stage}_registration.json';cfg=configs(stage);sig=signature()
    if p.exists():
        r=json.loads(p.read_text());assert r['configs']==cfg and r['source_sha256']==sig,'source/configuration drift';return r
    r=dict(stage=stage,parent_source_commit='c81a5f0064a8f9f0fc4fd4f439b311c2be29c06e',configs=cfg,policies=POLICIES,source_sha256=sig,
           registered_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),primary='candidate',LLM_runtime_calls=0,
           prior_results_provenance='conversation-recorded aggregate; original matrix and Library index not recovered',
           changed_admission={'failure_evidence':'received current-source MAC failures OR known settled same-version worst timely<.8',
               'congestion':'fresh-source positive CCA samples,busy<=.25,queue<=2; unmeasured relay congestion explicitly remains unknown',
               'candidate':'geometry/freshness witness, no unselected objective or reward evaluation',
               'cooldown':'20 seconds since last exposure feedback closure, not every normal transaction',
               'budget':'at most3 exposures, one per uncredited nonresource arm; censoring consumes opportunity'},
           matched_plain_control='same quotas, common confirmation/feedback/candidate constraints and exposure cooldown; omit failure and source-congestion screens',
           unchanged=['stable6','alpha=.6','four route objectives','selected-only aligned reward','local15_event/source5',
               'one targeted retry/10s unconfirmed exit','native queues and costs','FE<=64 with20us/FE'],
           context_gate={'service_gain':.005,'DATA_increase_limit':.05,'alternative_service_margin':-.005,'alternative_DATA_reduction':.05},
           update_gate={'service_gain':.005,'DATA_increase_limit':.05,'alternative_service_margin':-.005,'alternative_DATA_reduction':.05},
           exploration_screen={'service_margin_vs_score0':0.,'DATA_increase_limit_vs_score0':.05,'service_margin_vs_resource':0.},
           statistical_scope='two known geometries,two new paired input streams; descriptive development, not independent topology confirmation',
           old_joint_gates=json.loads((ROOT/'docs/observable_development_registration.json').read_text())['gates'],
           formal_validation=False,formal_matrix_admitted=False,ready_to_submit=False,
           formal_admission_requires='original joint gates, new learning screens and independent confirmation; absent component controls cannot imply old gates passed',
           post_run_primary_selection_forbidden=True,limitations=['source-local congestion does not prove safe relay performance',
              'legacy-to-candidate comparison bundles three admission changes; no single-component causal claim',
              'state changes after routing interventions and action-related censoring prevent automatic standard bandit regret guarantees'])
    atomic(p,r);return r
def execute(payload):
    cfg,binary,stage=payload;folder=ROOT/'results'/('candidate_'+stage)/(key(cfg)+'_'+str(time.time_ns()));folder.mkdir(parents=True)
    try:
        row=one(Path(binary),policy=POLICIES[cfg['model']],profile='local15_event',extended=True,source_only=True,folder=folder,
                queue_discipline='fifo',epoch_certificate=True,report_retry=True,report_budget=True,**{k:v for k,v in cfg.items() if k!='model'})
        row.update(model=cfg['model'],profile='candidate_full',freshness='fixed16',stage=stage,
                   configuration_key=key(cfg),evidence_directory=str(folder.relative_to(ROOT)))
        a=old.audit_case(row,folder);a['settled_service']=old.audit_service(row,folder);a['queue_and_age']=old.audit_epoch(row,folder)
        a['report_recovery']=old.audit_report_recovery(row,folder);a['stable_context']=old.independent_context_audit(row,folder);row['audit']=a
        a['aligned_reward_and_budget']=old.audit_aligned(row,folder);a['safety_and_cost']=old.audit_safety(row,folder)
        a['transaction_guard']=old.audit_transaction(row,folder);a['observable_control']=old.audit_observable(row,folder)
        a['candidate_admission']=audit_candidate(row,folder);atomic(folder/'case.json',row);return row
    except BaseException:(folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),required=True);p.add_argument('--register-only',action='store_true');p.add_argument('--workers',type=int,default=2);args=p.parse_args()
    assert 1<=args.workers<=4;tmp=ROOT.parent/'build_tmp';tmp.mkdir(exist_ok=True);os.environ['TMPDIR']=str(tmp)
    reg=registration(args.stage)
    if args.register_only:print('REGISTERED',args.stage,len(reg['configs']));return
    if args.stage=='development':
        f=json.loads((ROOT/'results/candidate_functional_manifest.json').read_text());assert len(f)==8 and all(r['audit']['status']=='passed' for r in f)
    binary=compile_driver();p=ROOT/'results'/f'candidate_{args.stage}_manifest.json';rows=json.loads(p.read_text()) if p.exists() else [];done={r['configuration_key'] for r in rows};failed=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(execute,(cfg,str(binary),args.stage)):cfg for cfg in reg['configs'] if key(cfg) not in done}
        for future in as_completed(futures):
            try:
                r=future.result();rows.append(r);rows.sort(key=lambda x:x['configuration_key']);atomic(p,rows)
                print(json.dumps(dict(audited=len(rows),registered=len(reg['configs']),case=r['configuration_key'],service=r['worst_party_timely'],DATA=r['native']['control_psdu_bytes'],exposures=len(r['audit']['candidate_admission'].get('exposure_actions',[])))),flush=True)
            except BaseException:
                failed.append(dict(config=futures[future],traceback=traceback.format_exc()));atomic(ROOT/'results'/f'candidate_{args.stage}_failures.json',failed);print('FAILED',key(futures[future]),flush=True)
    if failed:raise RuntimeError('Failed attempts retained; do not treat them as completed cases')
    assert len(rows)==len(reg['configs']);print('COMPLETE',args.stage,len(rows),flush=True)
if __name__=='__main__':main()
