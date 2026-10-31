"""Separate predeclared development revision; all predecessors remain failed."""
import argparse,hashlib,json,time,traceback
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
from run_closed_loop import ROOT,compile_driver,one
from run_recovery import MODELS
from run_aligned import atomic
from audit_closed_loop import audit_case
from tools.audit_revision_service import audit_service
from tools.audit_epoch import audit_epoch
from tools.audit_report_recovery import audit_report_recovery
from tools.audit_aligned import audit_aligned
from tools.audit_safety import audit_safety
from tools.audit_transaction import audit_transaction
from tools.audit_observable import audit_observable
from run_factorial import independent_context_audit

# score-only, bounded install exit, local ordinary reports, install budget,
# safety interruption, source report retry, retry reservation.
PROFILES={'obs_full':(True,True,True,True,True,True,True),
          'obs_exposure4':(False,True,True,True,True,True,True),
          'obs_old_deadline':(True,False,True,True,True,True,True),
          'obs_legacy_reports':(True,True,False,True,True,True,True),
          'obs_no_install_budget':(True,True,True,False,True,True,True),
          'obs_no_interrupt':(True,True,True,True,False,True,True),
          'obs_no_report_retry':(True,True,True,True,True,False,False),
          'obs_fixed_retry':(True,True,True,True,True,True,False),
          'legacy_retry8':None}
def identity(c):return '_'.join(str(c[k])for k in('topology','scenario','model','profile','seed'))
def configs(stage):
    if stage=='functional':
        scenes=[('steady',1000911,{}),('failure',1000912,{'reject':True}),('steady',1000913,{'missing':True}),('overload',1000914,{}),('steady',1000915,{'broken':True}),('multi_failure',1000916,{'faults':[[25,2],[40,3]]})]
        out=[]
        for scene,seed,extra in scenes:
            common=dict(scenario=scene,seed=seed,topology='base',generation_stop=90,faults=[[35,2]]if scene=='failure'else[]);common.update(extra)
            out.extend(dict(model='stable6',profile=p,**common)for p in('obs_full','legacy_retry8'))
        out.extend(dict(model='stable6',profile=p,scenario='overload',seed=1000917,topology='base',generation_stop=90,faults=[])for p in('obs_exposure4','obs_old_deadline','obs_legacy_reports','obs_no_install_budget','obs_no_report_retry','obs_fixed_retry'))
        return out
    out=[]
    for seed in(1001001,1001002):
        for top in('base','jitter_b'):
            for scene in('multi_failure','overload'):
                common=dict(scenario=scene,seed=seed,topology=top,generation_stop=330,faults=[[65,2],[145,3],[225,6]]if scene=='multi_failure'else[])
                out.extend(dict(model=m,profile='obs_full',**common)for m in MODELS)
                out.extend(dict(model='stable6',profile=p,**common)for p in PROFILES if p!='obs_full')
    return out
def signature():
    files=list(ROOT.glob('*.py'))+list((ROOT/'wsn').glob('*.py'))+list((ROOT/'tests').glob('*.py'))+list((ROOT/'ns3').glob('*.cc'))+list((ROOT/'ns3').glob('*.h'))
    files += [ROOT/'tools'/n for n in('audit_revision_service.py','audit_epoch.py','audit_report_recovery.py','audit_aligned.py','audit_safety.py','audit_transaction.py','audit_observable.py')]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(files)}
def registration(stage):
    p=ROOT/'docs'/f'observable_{stage}_registration.json';cfg=configs(stage);sig=signature()
    if p.exists():
        r=json.loads(p.read_text());assert r['configs']==cfg and r['source_sha256']==sig,'frozen source/configuration drift';return r
    previous=json.loads((ROOT/'docs/transaction_development_registration.json').read_text())
    r=dict(stage=stage,registered_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),configs=cfg,source_sha256=sig,
           primary={'model':'stable6','profile':'obs_full'},gates=previous['gates'],
           additional_component_gates={'ordinary_reporting_service_margin':-.01,'ordinary_reporting_control_reduction':.05,'explicit_exposure_service_margin':0.,'installation_exit_service_margin':0.},
           formal_validation=False,LLM_runtime_calls=0,prior_failed_gates_preserved=True,post_run_primary_selection_forbidden=True,
           hypotheses=['Remove forced event exposures; UCB uncertainty remains active and unselected rewards remain unknown.',
                       'Stable relay reports use a 15-second keepalive; received-local queue/busy/lease changes permit a report after at least 10 seconds. Source reports remain every five seconds.',
                       'An unconfirmed installation exits after ten seconds with at most one per-source retry; lack of confirmation is not physical failure. Late confirmation reconciles the route without retroactive learning.',
                       'Confirmed reward transaction safety interruption retains two-source version and bucket-grace qualification.'],
           components={'report_state':'local queue depth bins 0/1-2/3-8/9-16, completed application busy fraction >.35, locally received application lease',
                       'installation_exit':'deadline and retry-limit bundle, not isolated deadline causality',
                       'comparison_legacy_retry8':'compound comparison to preceding complete mechanism; not isolated component causality',
                       'wire':'unchanged source/relay body sizes and received epoch certificate'},
           statistics='Development only: two known geometries and two new common offered streams; all four paired effects and all planned controls; no p-values or held-out generalization.',
           formal_admission='all original joint gates AND additional component gates AND qualification/cost/opportunity gates; prior gates are not lowered',
           limitations=['Reporting admission bounds emitted originals, not total retransmissions, forwarding or delivery age.','The ten-second exit does not guarantee either installation was unapplied.','A ten-node prototype does not establish scalability or standardized RPL superiority.'])
    atomic(p,r);return r
def execute(payload):
    cfg,binary,stage=payload;folder=ROOT/'results'/stage/(identity(cfg)+'_'+str(time.time_ns()));folder.mkdir(parents=True)
    try:
        flags=PROFILES[cfg['profile']]
        if flags is None:
            marker='_ops_epoch_aligned_safe_interrupt_installbudget_transaction_txguard_creditexplore_';profile='lease10_15';retry=budget=True
        else:
            score,exit,local,ib,interrupt,retry,budget=flags
            marker='_ops_epoch_aligned_safe_'+('interrupt_'if interrupt else'')+('installbudget_'if ib else'')+'transaction_txguard_observable_'+('scoreonly_'if score else'')+('installexit_'if exit else'')
            profile='local15_event'if local else'lease10_15'
        policy=MODELS[cfg['model']].replace('_ops_',marker)
        row=one(Path(binary),policy=policy,profile=profile,extended=True,source_only=True,folder=folder,queue_discipline='fifo',epoch_certificate=True,report_retry=retry,report_budget=budget,**{k:v for k,v in cfg.items()if k not in('model','profile')})
        row.update(model=cfg['model'],profile=cfg['profile'],freshness='fixed16',stage=stage,configuration_key=identity(cfg),evidence_directory=str(folder.relative_to(ROOT)))
        a=audit_case(row,folder);row['audit']=a
        a['settled_service']=audit_service(row,folder);a['queue_and_age']=audit_epoch(row,folder);a['report_recovery']=audit_report_recovery(row,folder);a['stable_context']=independent_context_audit(row,folder)
        a['aligned_reward_and_budget']=audit_aligned(row,folder);a['safety_and_cost']=audit_safety(row,folder);a['transaction_guard_and_exposure']=audit_transaction(row,folder);a['observable_control']=audit_observable(row,folder)
        atomic(folder/'case.json',row);return row
    except BaseException:
        (folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),required=True);p.add_argument('--register-only',action='store_true');p.add_argument('--workers',type=int,default=4);a=p.parse_args();assert 1<=a.workers<=4
    reg=registration(a.stage)
    if a.register_only:print('REGISTERED',a.stage,len(reg['configs']),flush=True);return
    if a.stage=='development':
        f=json.loads((ROOT/'results/observable_functional_manifest.json').read_text());assert len(f)==len(configs('functional'))and all(r['audit']['status']=='passed'for r in f)
    binary=compile_driver();path=ROOT/'results'/f'observable_{a.stage}_manifest.json';rows=json.loads(path.read_text())if path.exists()else[];done={r['configuration_key']for r in rows};failures=[]
    with ProcessPoolExecutor(max_workers=a.workers)as pool:
        futures={pool.submit(execute,(c,str(binary),a.stage)):c for c in reg['configs']if identity(c)not in done}
        for future in as_completed(futures):
            try:
                r=future.result();rows.append(r);rows.sort(key=lambda r:r['configuration_key']);atomic(path,rows)
                print(json.dumps(dict(audited=len(rows),registered=len(reg['configs']),case=r['configuration_key'],service=r['worst_party_timely'],control=r['native']['control_psdu_bytes'],observable=r['audit']['observable_control'])),flush=True)
            except BaseException:
                failure=dict(configuration=futures[future],error=traceback.format_exc());failures.append(failure);atomic(ROOT/'results'/f'observable_{a.stage}_failures.json',failures);print('FAILED',identity(futures[future]),flush=True)
    if failures:raise RuntimeError(f'{len(failures)} failed attempts retained; completed cases preserved')
    assert len(rows)==len(reg['configs']);print('BATCH_COMPLETE',a.stage,len(rows),flush=True)
if __name__=='__main__':main()
