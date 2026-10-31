"""One frozen, causal report-protection screen; no runtime learning or LLM."""
import argparse,hashlib,json,os,time,traceback
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from run_closed_loop import ROOT,one,compile_driver
from run_aligned import atomic
from run_mechanisms import policy,key,signature
import run_observable as old
from tools.audit_candidate import audit_candidate
from tools.audit_selective_retry import audit_selective_retry
MODELS={'always':(True,'always'),'never':(False,'always'),'queue':(True,'queue'),'critical_queue':(True,'critical_queue')}
def configs(stage):
    if stage=='functional':
        return [dict(model=m,scenario=s,seed=1032501+i,topology='protect_1032301',generation_stop=90,faults=[[35,2]]if s=='failure'else [],reject=s=='failure')for i,(m,s)in enumerate((m,s)for m in MODELS for s in ('failure','overload'))]
    return [dict(model=m,scenario=s,seed=seed,topology=t,generation_stop=330,faults=[[65,2],[145,3],[225,6]]if s=='multi_failure'else [])for t in ('protect_1032301','protect_1032302')for s in ('multi_failure','overload')for seed in (1032601,1032602)for m in MODELS]
def registration(stage):
    path=ROOT/'docs'/f'selective_{stage}_registration.json';cfg=configs(stage);sig=signature()
    if path.exists():
        r=json.loads(path.read_text());assert r['configs']==cfg and r['source_sha256']==sig,'source/config drift';return r
    r=dict(stage=stage,registered_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),configs=cfg,source_sha256=sig,primary='critical_queue',
        parent_mechanism_commit='119fbdcfd765095a6cd7494cccb258005047a005',runtime_LLM_calls=0,online_learning=False,
        rule=dict(critical_reports=2,waiting_queue_threshold=4,queue_capacity=16,report_age_limit_s=3,application_retry_limit=1,local_retry_budget='one allocation/node/20s'),
        critical_definition='first two distinct report stamps actually observed at this forwarding node for a monotonically advancing source version; initial version included; duplicate retries do not consume another stamp',
        causal_inputs=['actual locally received/created report header source/version/stamp','local waiting queue depth at MAC failure'],
        forbidden_inputs=['sink receipt acknowledgement not transmitted on wire','global physical installed state','future failures','scenario label','application timely outcome truth'],
        held_constant=['resource operator','10s install deadline','one installation retry/source','FIFO','report generation/encoding','64-FE search cap','source-only epoch certificate','local retry reservation'],
        baselines=['always: current complete retry rule','never: no report retry','queue: congestion-only admission; removes version protection'],
        gain_gate=dict(service_gain=.005,DATA_increase_limit=.05,alternative_service_margin=-.005,alternative_DATA_reduction=.05),
        admission_rule='original joint gain gate versus always must pass in BOTH scenarios; protection versus queue must be noninferior within0.5pp in both and improve service>=0.5pp in at least one; gate results retained even if failed',
        reserved_confirmation_geometries=['protect_1032303','protect_1032304'],reserved_confirmation_streams=[1032701,1032702],
        no_parameter_adjustment_after_results=True,independent_cells_per_scene=4,statistics='descriptive paired screening only; not broad significance, scale or topology-family generalization',
        learning_contribution_established=False,formal_matrix_admitted=False,ready_to_submit=False)
    atomic(path,r);return r
def execute(payload):
    cfg,binary,stage=payload;folder=ROOT/'results'/('selective_'+stage)/(key(cfg)+'_'+str(time.time_ns()));folder.mkdir(parents=True)
    try:
        retry,mode=MODELS[cfg['model']]
        r=one(Path(binary),policy=policy('resource10_on'),profile='local15_event',extended=True,source_only=True,folder=folder,queue_discipline='fifo',epoch_certificate=True,report_retry=retry,report_budget=True,report_retry_mode=mode,**{k:v for k,v in cfg.items()if k!='model'})
        r.update(model=cfg['model'],profile='selective_report',freshness='fixed16',stage=stage,configuration_key=key(cfg),evidence_directory=str(folder.relative_to(ROOT)))
        a=old.audit_case(r,folder);r['audit']=a
        for name,fn in [('settled_service',old.audit_service),('queue_and_age',old.audit_epoch),('report_recovery',old.audit_report_recovery),('stable_context',old.independent_context_audit),('aligned_reward_and_budget',old.audit_aligned),('safety_and_cost',old.audit_safety),('transaction_guard',old.audit_transaction),('observable_control',old.audit_observable),('fixed_control_algebra',audit_candidate),('selective_retry',audit_selective_retry)]:a[name]=fn(r,folder)
        assert r['bandit_updates']==[0,0,0,0]and all(d['action']==0 and d['fe']<=64 for d in r['decisions'])
        atomic(folder/'case.json',r);return r
    except BaseException:(folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),required=True);p.add_argument('--register-only',action='store_true');p.add_argument('--workers',type=int,default=2);a=p.parse_args();assert 1<=a.workers<=4
    os.environ['TMPDIR']=str(ROOT.parent/'build_tmp');reg=registration(a.stage)
    if a.register_only:print('REGISTERED_SELECTIVE',a.stage,len(reg['configs']));return
    if a.stage=='development':
        f=json.loads((ROOT/'results/selective_functional_manifest.json').read_text());assert len(f)==8 and all(r['audit']['status']=='passed'for r in f)
    binary=ROOT/'ns3/wsn-closed-loop'
    if not binary.exists():binary=compile_driver()
    path=ROOT/'results'/f'selective_{a.stage}_manifest.json';rows=json.loads(path.read_text())if path.exists()else[];done={r['configuration_key']for r in rows};failed=[]
    with ProcessPoolExecutor(max_workers=a.workers)as pool:
        futures={pool.submit(execute,(c,str(binary),a.stage)):c for c in reg['configs']if key(c)not in done}
        for f in as_completed(futures):
            try:
                r=f.result();rows.append(r);rows.sort(key=lambda r:r['configuration_key']);atomic(path,rows);print('SELECTIVE_AUDITED',a.stage,len(rows),r['configuration_key'],flush=True)
            except BaseException:failed.append(dict(config=futures[f],traceback=traceback.format_exc()));atomic(ROOT/'results'/f'selective_{a.stage}_failures.json',failed);print('SELECTIVE_FAILED',flush=True)
    if failed:raise RuntimeError('Failed attempts preserved')
    assert len(rows)==len(reg['configs']);print('SELECTIVE_COMPLETE',a.stage,len(rows),flush=True)
if __name__=='__main__':main()
