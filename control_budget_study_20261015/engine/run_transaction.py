"""Preregistered isolated revision; all failed predecessors are retained."""
import argparse,hashlib,json,time,traceback
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
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
from run_factorial import independent_context_audit

# guard, feedback-aware exploration, installation budget, report retry/budget
PROFILES={'txn_full':(True,True,True,True,True),
 'txn_no_interrupt':(True,True,True,True,True),
 'txn_no_guard':(False,True,True,True,True),
 'txn_single_attempt':(True,False,True,True,True),
 'txn_no_install_budget':(True,True,False,True,True),
 'txn_no_report_retry':(True,True,True,False,False),
 'txn_fixed_retry':(True,True,True,True,False),
 'aligned_budget':None}
def identity(c):return '_'.join(str(c[k])for k in('topology','scenario','model','profile','seed'))
def configs(stage):
 if stage=='functional':
  out=[dict(model='stable6',profile=p,scenario=sc,seed=seed,topology='base',generation_stop=90,faults=[[35,2]]if sc=='failure'else[],**extra)
    for sc,seed,extra in [('steady',1000711,{}),('failure',1000712,{'reject':True}),('steady',1000713,{'missing':True}),('overload',1000714,{})]
    for p in ('txn_full','txn_no_guard','txn_single_attempt','aligned_budget')]
  return out+[dict(model='stable6',profile='txn_full',scenario='steady',seed=1000715,topology='base',generation_stop=90,faults=[],broken=True),dict(model='stable6',profile='txn_full',scenario='multi_failure',seed=1000716,topology='base',generation_stop=90,faults=[[25,2],[40,3]])]
 out=[]
 for seed in (1000801,1000802):
  for top in ('base','jitter_b'):
   for scene in ('multi_failure','overload'):
    common=dict(scenario=scene,seed=seed,topology=top,generation_stop=330,faults=[[65,2],[145,3],[225,6]]if scene=='multi_failure'else[])
    out.extend(dict(model=m,profile='txn_full',**common)for m in MODELS)
    out.extend(dict(model='stable6',profile=p,**common)for p in PROFILES if p!='txn_full')
 return out
def signature():
 paths=list(ROOT.glob('*.py'))+list((ROOT/'wsn').glob('*.py'))+list((ROOT/'tests').glob('*.py'))+list((ROOT/'ns3').glob('*.cc'))+list((ROOT/'ns3').glob('*.h'))
 paths+=[ROOT/'tools'/p for p in('audit_revision_service.py','audit_epoch.py','audit_report_recovery.py','audit_aligned.py','audit_safety.py','audit_transaction.py')]
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(paths)}
def registration(stage):
 path=ROOT/'docs'/f'transaction_{stage}_registration.json';cfg=configs(stage);sig=signature()
 if path.exists():
  r=json.loads(path.read_text());assert r['configs']==cfg and r['source_sha256']==sig,'frozen source/configuration drift';return r
 previous=json.loads((ROOT.parent/'safety_cost_study_20261011/docs/safety_development_registration.json').read_text())
 r=dict(stage=stage,configs=cfg,source_sha256=sig,registered_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),primary={'model':'stable6','profile':'txn_full'},gates=previous['gates'],formal_validation=False,LLM_runtime_calls=0,
  hypotheses=['Old-route missing evidence must not cancel a newer partially confirmed installation.','Censored exposure is an attempt, not qualified arm feedback; allow at most two event exposures per arm and eight total.','Wait one additional source-report period after the locked reward bucket settles before safety censoring.','The stricter mechanism must still show service, contextual and communication benefits under the unchanged joint screen.'],
  guard={'requires':'both fresh source versions equal pending expected pair and sampled after selection','missing':'sustained missing relay must be in pending target','grace_ns_after_bucket_end':5200000000,'qualified_credit_priority':True,'installation_truth_online':False},
  exploration={'selected_outcomes_only':True,'maximum_event_attempts':8,'maximum_attempts_per_arm':2,'order':'unattempted feasible uncredited arms before repeated censored arms; tie by index','credits':'any earlier noncensored selected reward, including initial decisions','imputed_censored_rewards':0},
  prior_failed_gates_preserved=True,post_run_primary_selection_forbidden=True,statistics='Development only: two known ten-node geometries x two new common offered streams; equal-weight paired effects, no formal inference.',limitations=['No cross-run training or counterfactual labels.','Additional exploration is budgeted but need not be beneficial.','Fixed-window installation/report allowance does not guarantee lower total overhead.','Formal held-out scale/protocol/sensitivity matrix not automatically admitted.'])
 atomic(path,r);return r
def execute(payload):
 cfg,binary,stage=payload;folder=ROOT/'results'/stage/(identity(cfg)+'_'+str(time.time_ns()));folder.mkdir(parents=True)
 try:
  flags=PROFILES[cfg['profile']]
  if flags is None:marker='_ops_epoch_aligned_';retry=budget=True
  else:
   guard,credit,ibudget,retry,budget=flags
   marker='_ops_epoch_aligned_safe_'+('interrupt_'if cfg['profile']!='txn_no_interrupt'else'')+('installbudget_'if ibudget else'')+'transaction_'+('txguard_'if guard else'')+('creditexplore_'if credit else'')
  policy=MODELS[cfg['model']].replace('_ops_',marker)
  r=one(Path(binary),policy=policy,profile='lease10_15',extended=True,source_only=True,folder=folder,queue_discipline='fifo',epoch_certificate=True,report_retry=retry,report_budget=budget,**{k:v for k,v in cfg.items()if k not in('model','profile')})
  r.update(model=cfg['model'],profile=cfg['profile'],freshness='fixed16',stage=stage,configuration_key=identity(cfg),evidence_directory=str(folder.relative_to(ROOT)))
  a=audit_case(r,folder);a['settled_service']=audit_service(r,folder);a['queue_and_age']=audit_epoch(r,folder);a['report_recovery']=audit_report_recovery(r,folder);a['stable_context']=independent_context_audit(r,folder);r['audit']=a
  a['aligned_reward_and_budget']=audit_aligned(r,folder);a['safety_and_cost']=audit_safety(r,folder);a['transaction_guard_and_exposure']=audit_transaction(r,folder)
  atomic(folder/'case.json',r);return r
 except BaseException:(folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),required=True);p.add_argument('--register-only',action='store_true');p.add_argument('--workers',type=int,default=4);a=p.parse_args();assert 1<=a.workers<=4
 reg=registration(a.stage)
 if a.register_only:print('REGISTERED',a.stage,len(reg['configs']));return
 if a.stage=='development':
  f=json.loads((ROOT/'results/transaction_functional_manifest.json').read_text());assert len(f)==18 and all(r['audit']['status']=='passed'for r in f)
 binary=compile_driver();path=ROOT/'results'/f'transaction_{a.stage}_manifest.json';rows=json.loads(path.read_text())if path.exists()else[];done={r['configuration_key']for r in rows}
 with ProcessPoolExecutor(max_workers=a.workers)as pool:
  for future in as_completed([pool.submit(execute,(c,str(binary),a.stage))for c in reg['configs']if identity(c)not in done]):
   r=future.result();rows.append(r);rows.sort(key=lambda r:r['configuration_key']);atomic(path,rows)
   print(json.dumps(dict(audited=len(rows),registered=len(reg['configs']),case=r['configuration_key'],service=r['worst_party_timely'],control=r['native']['control_psdu_bytes'],transaction=r['audit']['transaction_guard_and_exposure'])),flush=True)
 print('BATCH_COMPLETE',a.stage,len(rows),flush=True)
if __name__=='__main__':main()
