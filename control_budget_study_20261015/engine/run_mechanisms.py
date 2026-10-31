"""Predeclared non-learning mechanism validation after failed learning screens."""
import argparse,hashlib,json,os,time,traceback
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
from run_closed_loop import ROOT,one,compile_driver
from run_aligned import atomic
import run_observable as old
from tools.audit_candidate import audit_candidate
BASE='scalar4_failure_current_ops_epoch_aligned_safe_interrupt_installbudget_transaction_txguard_observable_installexit_reviewmechanism_'
TAIL='scoreonly_ctx6_noop_cache20_retry_freshfixed_mask'
MODELS={'resource10_on':(0,10,True,False),'resource15_on':(0,15,True,False),
        'resource10_off':(0,10,False,False),'resource15_off':(0,15,False,False),
        'risk10_on':(1,10,True,False),'separation10_on':(2,10,True,False),
        'stability10_on':(3,10,True,False),'hop10_on':(0,10,True,True)}
def policy(m):
    a,d,retry,hop=MODELS[m]
    return 'force'+str(a)+'_'+BASE+('install15_'if d==15 else '')+('hopref_'if hop else '')+TAIL
def key(c):return '_'.join(str(c[k])for k in ('topology','scenario','model','seed'))
def configs(stage):
    if stage=='functional':
        pairs=[('resource10_on','failure',{'reject':True}),('resource15_on','failure',{'reject':True}),
            ('resource10_off','steady',{'broken':True}),('resource15_off','steady',{'broken':True}),
            ('risk10_on','overload',{}),('separation10_on','failure',{}),('stability10_on','overload',{}),('hop10_on','steady',{})]
        return [dict(model=m,scenario=s,seed=1031601+i,topology='review_1031301',generation_stop=90,
            faults=[[35,2]] if s=='failure'else [],**e)for i,(m,s,e)in enumerate(pairs)]
    return [dict(model=m,scenario=s,seed=seed,topology=t,generation_stop=330,
        faults=[[65,2],[145,3],[225,6]]if s=='multi_failure'else [])
        for t in ('review_1031301','review_1031302')for s in ('multi_failure','overload')for seed in (1031501,1031502)for m in MODELS]
def signature():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.rglob('*'))
        if p.is_file()and p.suffix in ('.py','.cc','.h')and '__pycache__'not in p.parts}
def registration(stage):
    path=ROOT/'docs'/('mechanism_'+stage+'_registration.json');cfg=configs(stage);sig=signature()
    if path.exists():
        j=json.loads(path.read_text());assert j['configs']==cfg and j['source_sha256']==sig,'source/configuration drift';return j
    j=dict(stage=stage,registered_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),parent_commit='3023efb8c9e0859e8afffd5323983b8ca8543e7e',
        configs=cfg,policies={m:policy(m)for m in MODELS},source_sha256=sig,primary='resource10_on',LLM_runtime_calls=0,
        primary_question='Do source-confirmation waiting and report retransmission improve service under complete communication costs?',
        factorial={'deadline_seconds':[10,15],'source_report_retry':[True,False],
            'held_constant':['one installation retry per source','late received confirmation reconciliation','selected version-qualified cohort','wire format','install reservation','fixed resource operator']},
        baselines=['four fixed observable operators','geometry-hop reference within common admitted pool'],
        controls_scope='No runtime learning/exposure in any arm; previous contextual-learning failures remain unchanged.',
        gate={'service_gain':.005,'DATA_increase_limit':.05,'alternative_service_margin':-.005,'alternative_DATA_reduction':.05},
        statistics='four paired layout-stream cells per scene; descriptive development, not significance or population generalization',
        independent_input_scope='new preregistered relay-coordinate seeds and offered streams; layouts share a ten-node scaffold; this is a fresh development screen, not broad independent confirmation',
        primary_selection_after_results=False,formal_validation=False,ready_to_submit=False,
        reserved_geometries=['review_1031303','review_1031304'],
        limitations=['Same admitted pool limits hop-reference scope; not an official RPL/ETX-Dijkstra implementation.',
            'Deadline comparison isolates10vs15seconds, not bounded-vs-unbounded installation.',
            'Retry information changes causally with packet delivery; total costs include ordinary reports, forwarding and ACK.',
            'Only two sources and ten nodes; scaling, sink placement and burst regimes remain for later validation.',
            '20us per search evaluation is a fixed simulated computation-delay model, not measured real-time deployment performance.'])
    atomic(path,j);return j
def execute(payload):
    cfg,binary,stage=payload;folder=ROOT/'results'/('mechanism_'+stage)/(key(cfg)+'_'+str(time.time_ns()));folder.mkdir(parents=True)
    try:
        m=cfg['model'];r=one(Path(binary),policy=policy(m),profile='local15_event',extended=True,source_only=True,folder=folder,
            queue_discipline='fifo',epoch_certificate=True,report_retry=MODELS[m][2],report_budget=True,**{k:v for k,v in cfg.items()if k!='model'})
        r.update(model=m,profile='review_mechanism',freshness='fixed16',stage=stage,configuration_key=key(cfg),evidence_directory=str(folder.relative_to(ROOT)))
        a=old.audit_case(r,folder);a['settled_service']=old.audit_service(r,folder);a['queue_and_age']=old.audit_epoch(r,folder)
        a['report_recovery']=old.audit_report_recovery(r,folder);a['stable_context']=old.independent_context_audit(r,folder);r['audit']=a
        a['aligned_reward_and_budget']=old.audit_aligned(r,folder);a['safety_and_cost']=old.audit_safety(r,folder)
        a['transaction_guard']=old.audit_transaction(r,folder);a['observable_control']=old.audit_observable(r,folder)
        a['fixed_control_algebra']=audit_candidate(r,folder)
        assert r['bandit_updates']==[0,0,0,0] and not any(d['selection_phase']=='event_exploration'for d in r['decisions'])
        assert all(d['action']==MODELS[m][0]and d['mechanism_treatment']['installation_retry_limit']==1 for d in r['decisions'])
        assert all(d['fe']<=64 for d in r['decisions']);atomic(folder/'case.json',r);return r
    except BaseException:(folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),required=True);p.add_argument('--register-only',action='store_true');p.add_argument('--workers',type=int,default=2);args=p.parse_args()
    assert 1<=args.workers<=4;os.environ['TMPDIR']=str(ROOT.parent/'build_tmp');reg=registration(args.stage)
    if args.register_only:print('REGISTERED',args.stage,len(reg['configs']));return
    if args.stage=='development':
        f=json.loads((ROOT/'results/mechanism_functional_manifest.json').read_text());assert len(f)==8 and all(v['audit']['status']=='passed'for v in f)
    binary=compile_driver();path=ROOT/'results'/('mechanism_'+args.stage+'_manifest.json');rows=json.loads(path.read_text())if path.exists()else [];done={r['configuration_key']for r in rows};fail=[]
    with ProcessPoolExecutor(max_workers=args.workers)as pool:
        futures={pool.submit(execute,(c,str(binary),args.stage)):c for c in reg['configs']if key(c)not in done}
        for f in as_completed(futures):
            try:
                r=f.result();rows.append(r);rows.sort(key=lambda r:r['configuration_key']);atomic(path,rows)
                print(json.dumps(dict(audited=len(rows),planned=len(reg['configs']),case=r['configuration_key'],service=r['worst_party_timely'],DATA=r['native']['control_psdu_bytes'])),flush=True)
            except BaseException:
                fail.append(dict(configuration=futures[f],traceback=traceback.format_exc()));atomic(ROOT/'results'/('mechanism_'+args.stage+'_failures.json'),fail);print('FAILED',key(futures[f]),flush=True)
    if fail:raise RuntimeError('Failed attempts preserved; inspect before exact-case rerun')
    assert len(rows)==len(reg['configs']);print('COMPLETE',args.stage,len(rows),flush=True)
if __name__=='__main__':main()
