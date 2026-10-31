"""Separate predeclared alignment and reservation development study."""
import argparse,hashlib,json,os,time,traceback
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from run_closed_loop import ROOT,compile_driver,one
from run_recovery import MODELS
from audit_closed_loop import audit_case
from tools.audit_revision_service import audit_service
from tools.audit_epoch import audit_epoch
from tools.audit_report_recovery import audit_report_recovery
from tools.audit_aligned import audit_aligned
from run_factorial import independent_context_audit
PROFILES={'aligned_no_retry':(True,False,False),'aligned_budget':(True,True,True),'aligned_fixed':(True,True,False),'legacy_fixed':(False,True,False)}
def atomic(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.partial');tmp.write_text(json.dumps(d,indent=2)+'\n');os.replace(tmp,p)
def configs(stage):
 if stage=='functional':
  rows=[dict(model='stable6',profile=p,scenario=sc,seed=seed,topology='base',generation_stop=90,faults=[[35,2]]if sc=='failure'else[],**extras)for sc,seed,extras in [('steady',999511,{}),('failure',999512,{'reject':True}),('steady',999513,{'missing':True}),('overload',999514,{})]for p in('aligned_no_retry','aligned_budget')]
  rows+=[dict(model='stable6',profile='aligned_fixed',scenario='overload',seed=999514,topology='base',generation_stop=90,faults=[]),dict(model='stable6',profile='aligned_budget',scenario='steady',seed=999515,topology='base',generation_stop=90,faults=[],broken=True)]
  return rows
 rows=[]
 for t in('base','jitter_b'):
  for sc in('multi_failure','overload'):
   for m in MODELS:
    for p in('aligned_no_retry','aligned_budget'):rows.append(dict(model=m,profile=p,scenario=sc,seed=999601,topology=t,generation_stop=330,faults=[[65,2],[145,3],[225,6]]if sc=='multi_failure'else[]))
   for p in('aligned_fixed','legacy_fixed'):rows.append(dict(model='stable6',profile=p,scenario=sc,seed=999601,topology=t,generation_stop=330,faults=[[65,2],[145,3],[225,6]]if sc=='multi_failure'else[]))
 return rows
def identity(c):return '_'.join(str(c[k])for k in('topology','scenario','model','profile','seed'))
def signature():
 files=list(ROOT.glob('*.py'))+list((ROOT/'wsn').glob('*.py'))+list((ROOT/'tests').glob('*.py'))+list((ROOT/'ns3').glob('*.cc'))+list((ROOT/'ns3').glob('*.h'))+[ROOT/'tools'/f for f in('audit_epoch.py','audit_revision_service.py','audit_report_recovery.py','audit_aligned.py')]
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(files)}
def registration(stage):
 p=ROOT/'docs'/f'aligned_{stage}_registration.json';cfg=configs(stage);sig=signature()
 if p.exists():
  d=json.loads(p.read_text());assert d['configs']==cfg and d['source_sha256']==sig,'source/configuration drift';return d
 d=dict(stage=stage,formal_validation=False,registered_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),configs=cfg,source_sha256=sig,primary={'model':'stable6','profile':'aligned_budget'},LLM_runtime_calls=0,prior_failed_gates_preserved=True,post_run_primary_selection_forbidden=True,
  hypotheses=['Qualified received source epochs and one complete post-confirmation bucket avoid credit to earlier routes.','A local prepaid retry allocation budget bounds extra DATA and may reduce transport overhead.','Contextual policy must improve on intercept and deterministic controls under identical communication.'],
  reward_protocol={'expected_versions':'decision version for installs; observed source versions for admitted holds','bucket_start':'max(ceil(decision time / 5 s), both received version epoch anchors)','bucket_count':1,'minimum_offered_per_source':20,'maximum_wait_from_decision_s':30,'delivery_deadline_s':.2,'censored_rewards_not_imputed':True,'no_native_truth_online':True,'fee_scope':'existing FE and nominal installation budget; report cost separately measured, not included as a full-network observed reward fee'},
  communication_budget={'fixed_window_s':20,'per_local_node_retry_allocations':1,'prepaid_extra_DATA_bytes_per_allocation':1143,'scope':'remaining-hop retry DATA; excludes ACK, energy and service guarantees','no_unused_credit_release':True,'same_packet_body_and_original_timestamp':True},
  gates={'mixed_route_or_version_reward_packets':0,'service_margin_vs_no_retry':-.01,'control_increase_limit_vs_no_retry':.05,'known_service_fraction_gain_vs_no_retry':.05,'service_margin_vs_fixed_retry':-.01,'control_reduction_minimum_vs_fixed_retry':.05,'rule_service_margin':0.,'resource_service_margin':0.,'worst_topology_service_margin':-.03,'context_service_gain':.005,'context_cost_increase_limit':.05,'context_alternative_service_margin':-.005,'context_alternative_control_reduction':.05,'primary_trained_score_choices_minimum':20,'trained_choices_minimum_per_primary_run':3},
  statistics='Development only: two known ten-node layouts, one new offered stream. Paired descriptive effects, no confirmatory p-values.',limitations=['Alignment also changes the reward cohort from three buckets to one; the legacy comparison does not isolate eligibility alone.','No preemption of pending reward/installation is implemented. Wait causes are logged for diagnosis.','A per-allocation bound does not guarantee overall control traffic is below a desired percentage of baseline.','No ordinary stationary LinUCB regret guarantee is claimed under endogenous missing feedback.','No acceptance, scalability or institutional eligibility claim.'])
 atomic(p,d);return d
def execute(payload):
 cfg,binary,stage=payload;folder=ROOT/'results'/stage/(identity(cfg)+'_'+str(time.time_ns()));folder.mkdir(parents=True)
 try:
  aligned,retry,budget=PROFILES[cfg['profile']];policy=MODELS[cfg['model']].replace('_ops_','_ops_epoch_aligned_'if aligned else'_ops_epoch_')
  row=one(Path(binary),policy=policy,profile='lease10_15',extended=True,source_only=True,folder=folder,queue_discipline='fifo',epoch_certificate=True,report_retry=retry,report_budget=budget,**{k:v for k,v in cfg.items()if k not in('model','profile')})
  row.update(model=cfg['model'],profile=cfg['profile'],freshness='fixed16',stage=stage,configuration_key=identity(cfg),evidence_directory=str(folder.relative_to(ROOT)))
  audit=audit_case(row,folder);audit['settled_service']=audit_service(row,folder);audit['queue_and_age']=audit_epoch(row,folder);audit['report_recovery']=audit_report_recovery(row,folder);audit['stable_context']=independent_context_audit(row,folder);row['audit']=audit;audit['aligned_reward_and_budget']=audit_aligned(row,folder)
  atomic(folder/'case.json',row);return row
 except BaseException:(folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),required=True);p.add_argument('--register-only',action='store_true');p.add_argument('--workers',type=int,default=4);a=p.parse_args();assert 1<=a.workers<=4
 reg=registration(a.stage)
 if a.register_only:print('REGISTERED',a.stage,len(reg['configs']),flush=True);return
 if a.stage=='development':
  f=json.loads((ROOT/'results/aligned_functional_manifest.json').read_text());assert len(f)==10 and all(r['audit']['status']=='passed'for r in f)
 binary=compile_driver();path=ROOT/'results'/f'aligned_{a.stage}_manifest.json';rows=json.loads(path.read_text())if path.exists()else[];done={r['configuration_key']for r in rows};pending=[c for c in reg['configs']if identity(c)not in done]
 with ProcessPoolExecutor(max_workers=a.workers)as pool:
  for future in as_completed([pool.submit(execute,(c,str(binary),a.stage))for c in pending]):
   r=future.result();rows.append(r);rows.sort(key=lambda r:r['configuration_key']);atomic(path,rows);print(json.dumps(dict(audited=len(rows),registered=len(reg['configs']),case=r['configuration_key'],service=r['worst_party_timely'],control=r['native']['control_psdu_bytes'],aligned=r['audit']['aligned_reward_and_budget'])),flush=True)
 print('BATCH_COMPLETE',a.stage,len(rows),flush=True)
if __name__=='__main__':main()
