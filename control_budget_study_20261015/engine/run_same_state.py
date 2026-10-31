"""Registered same-state actual-action diagnosis; offline branches are not learning."""
import argparse,base64,gzip,hashlib,json,os,time,traceback
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from run_closed_loop import ROOT,one
from run_mechanisms import policy,signature
from run_aligned import atomic
from wsn.fork_controller import ForkController
from tools.fork_evidence import audit_fork,window_metrics
import run_observable as audits
from tools.audit_candidate import audit_candidate
from tools.audit_selective_retry import audit_selective_retry
def key(c):
    base='_'.join(str(c[k])for k in ('topology','scenario','seed'))
    return base if 'fork_arm'not in c else base+'_anchor'+str(c['anchor_s'])+'_arm'+str(c['fork_arm'])
def references(stage):
    if stage=='functional':
        return[dict(topology='protect_1032301',scenario=s,seed=1033101+i,generation_stop=90,faults=[[35,2]]if s=='failure'else [])for i,s in enumerate(('failure','overload'))]
    return[dict(topology=t,scenario=s,seed=n,generation_stop=330,faults=[[65,2],[145,3],[225,6]]if s=='multi_failure'else [])for t in ('protect_1032301','protect_1032302')for s in ('multi_failure','overload')for n in (1032601,1032602)]
def registration():
    path=ROOT/'docs/registration.json';sig=signature();cfg={s:references(s)for s in ('functional','development')}
    binary_hash=hashlib.sha256((ROOT/'ns3/wsn-closed-loop').read_bytes()).hexdigest()
    if path.exists():
        r=json.loads(path.read_text());assert r['source_sha256']==sig and r['reference_configs']==cfg and r['native_binary_sha256']==binary_hash,'source/config/binary drift';return r
    r=dict(reference_configs=cfg,source_sha256=sig,native_binary_sha256=binary_hash,registered_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        parent_commit='879d30ab8de19a7509c8aeaf46af3e9677d80221',functional_windows_s=[[10,50]],development_windows_s=[[75,125],[175,225]],arms=[0,1,2,3],
        selection='first original emitted resource decision within each inclusive window with closed transaction, unused install budget, four feasible equal pools; no outcome-based replacement',
        cohort_s=30,timely_deadline_s=.2,cost_window_s=30.2,maximum_development_forks=64,
        held_constant=['all actual observations and physical prefix','arrival stream and geometry','native binary and report always/budget rules','10s install deadline/one source install retry','common pool and64-FE cap','received version feedback'],
        post_fork='disable new decisions and safety-triggered new transactions; preserve installation retries and qualified/censored feedback; identical for every branch arm',
        selection_bindings_published_before_branch_runs=True,reference_development_replays_are_new_independent_repeats=False,
        necessary_signal=dict(mean_oracle_worst_service_advantage_over_best_fixed=.005,at_least_two_topology_stream_clusters_with_opposite_strict_rankings=True),
        signal_scope='descriptive necessary action heterogeneity, not a learned-policy effect or proof of predictability; offline full outcomes never fed into online updates',
        statistics='16 conditional state slots within4 topology-stream clusters; scenarios/anchors/four arms are correlated, not independent repetitions',
        runtime_LLM_calls=0,online_learning=False,formal_matrix_admitted=False,ready_to_submit=False)
    atomic(path,r);return r
def checkpoint(row,stage):
    raw=json.dumps(row,separators=(',',':')).encode();encoded=base64.b64encode(gzip.compress(raw,mtime=0));assert gzip.decompress(base64.b64decode(encoded))==raw
    p=ROOT/'results/checkpoints'/stage/(row['configuration_key']+'.json.gz.b64');p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.staging')
    with tmp.open('wb')as f:f.write(encoded);f.flush();os.fsync(f.fileno())
    tmp.replace(p)
def execute(payload):
    cfg,stage,kind=payload;folder=ROOT/'results'/(stage+'_'+kind)/(key(cfg)+'_'+str(time.time_ns()));folder.mkdir(parents=True)
    try:
        kwargs={}if kind=='reference'else dict(fork_time_ns=cfg['fork_time_ns'],fork_arm=cfg['fork_arm'])
        native_cfg={k:v for k,v in cfg.items()if k in ('topology','scenario','seed','generation_stop','faults')}
        r=one(ROOT/'ns3/wsn-closed-loop',policy=policy('resource10_on'),profile='local15_event',extended=True,source_only=True,folder=folder,queue_discipline='fifo',epoch_certificate=True,report_retry=True,report_budget=True,report_retry_mode='always',controller_factory=ForkController,controller_kwargs=kwargs,**native_cfg)
        r.update(model='same_state_'+kind,profile='same_state',freshness='fixed16',stage=stage,kind=kind,configuration_key=key(cfg),evidence_directory=str(folder.relative_to(ROOT)))
        a=audits.audit_case(r,folder,controller_factory=ForkController);r['audit']=a
        for name,fn in [('settled_service',audits.audit_service),('queue_and_age',audits.audit_epoch),('report_recovery',audits.audit_report_recovery),('stable_context',audits.independent_context_audit),('aligned_reward_and_budget',audits.audit_aligned),('safety_and_cost',audits.audit_safety),('transaction_guard',audits.audit_transaction),('observable_control',audits.audit_observable),('fixed_control_algebra',audit_candidate),('selective_retry',audit_selective_retry)]:a[name]=fn(r,folder)
        if kind=='fork':
            assert r['fork_info']['snapshot_sha256']==cfg['expected_snapshot_sha256'],'registered state binding mismatch'
            refs=json.loads((ROOT/'results'/f'{stage}_reference_manifest.json').read_text());ref=next(x for x in refs if x['configuration_key']==cfg['reference_key'])
            a['same_state_prefix']=audit_fork(r,folder,ref,ROOT/ref['evidence_directory']);r['window_metrics']=window_metrics(r,folder);r['anchor_s']=cfg['anchor_s'];r['reference_key']=cfg['reference_key']
        elif stage=='development':
            old=json.loads((ROOT.parent/'selective_report_validation_20261013/results/selective_development_manifest.json').read_text());o=next(x for x in old if x['topology']==r['topology']and x['scenario']==r['scenario']and x['seed']==r['seed']and x['model']=='always')
            match={h:r['hashes'][h]==o['hashes'][h]for h in ('arrivals','positions','.csv','.jobs.csv','.protocol.jsonl','.radio.csv')};assert all(match.values());a['original_reference_replay']=dict(status='passed',hash_matches=match,extra_independent_repeat=False)
        assert r['bandit_updates']==[0]*4;atomic(folder/'case.json',r);return r
    except BaseException:(folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
def bind(stage):
    reg=registration();rows=json.loads((ROOT/'results'/f'{stage}_reference_manifest.json').read_text());assert len(rows)==len(references(stage))
    slots=[];cfg=[]
    for row in sorted(rows,key=lambda r:r['configuration_key']):
        native_cfg=next(c for c in references(stage)if key(c)==row['configuration_key'])
        for lo,hi in reg[stage+'_windows_s']:
            candidates=[c for c in row['state_candidates']if lo*10**9<=c['time_ns']<=hi*10**9]
            valid=[c for c in candidates if c['eligible']and c['decision_emitted']]
            c=min(valid,key=lambda c:c['time_ns'])if valid else None
            slots.append(dict(reference_key=row['configuration_key'],anchor_s=lo,upper_s=hi,valid=c is not None,
                fork_time_ns=c['time_ns']if c else None,snapshot_sha256=c['snapshot_sha256']if c else None,
                missing_reasons=[dict(time_ns=x['time_ns'],reasons=x['reasons'],decision_emitted=x['decision_emitted'])for x in candidates]if c is None else []))
            if c is not None:
                cfg.extend(dict(**native_cfg,reference_key=row['configuration_key'],anchor_s=lo,fork_time_ns=c['time_ns'],fork_arm=a,expected_snapshot_sha256=c['snapshot_sha256'])for a in range(4))
    result=dict(stage=stage,state_slots=slots,valid_states=sum(s['valid']for s in slots),missing_states=sum(not s['valid']for s in slots),fork_configs=cfg,source_sha256=reg['source_sha256'],outcomes_used_for_selection=False,runtime_LLM_calls=0)
    p=ROOT/'docs'/f'{stage}_binding.json'
    if p.exists():assert json.loads(p.read_text())==result,'binding drift'
    else:atomic(p,result)
    print(json.dumps(dict(stage=stage,valid_states=result['valid_states'],missing_states=result['missing_states'],fork_configs=len(cfg))))
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),default='functional');p.add_argument('--kind',choices=('reference','fork'),default='reference');p.add_argument('--register-only',action='store_true');p.add_argument('--bind-only',action='store_true');p.add_argument('--workers',type=int,default=3);args=p.parse_args();assert 1<=args.workers<=4
    os.environ['TMPDIR']=str(ROOT.parent/'build_tmp');registration()
    if args.register_only:print('REGISTERED_SAME_STATE');return
    if args.bind_only:bind(args.stage);return
    cfg=references(args.stage)if args.kind=='reference'else json.loads((ROOT/'docs'/f'{args.stage}_binding.json').read_text())['fork_configs']
    path=ROOT/'results'/f'{args.stage}_{args.kind}_manifest.json';rows=json.loads(path.read_text())if path.exists()else[];done={r['configuration_key']for r in rows};failures=[]
    with ProcessPoolExecutor(max_workers=args.workers)as pool:
        futures={pool.submit(execute,(c,args.stage,args.kind)):c for c in cfg if key(c)not in done}
        for f in as_completed(futures):
            try:
                r=f.result();rows.append(r);rows.sort(key=lambda r:r['configuration_key']);atomic(path,rows);checkpoint(r,args.stage+'_'+args.kind);print('SAME_STATE_AUDITED',args.stage,args.kind,len(rows),len(cfg),r['configuration_key'],flush=True)
            except BaseException:failures.append(dict(config=futures[f],traceback=traceback.format_exc()));atomic(ROOT/'results'/f'{args.stage}_{args.kind}_failures.json',failures);print('SAME_STATE_FAILED',flush=True)
    if failures:raise RuntimeError('Failed attempts retained')
    assert len(rows)==len(cfg);print('SAME_STATE_COMPLETE',args.stage,args.kind,len(rows),flush=True)
if __name__=='__main__':main()
