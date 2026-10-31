"""Isolated preregistered received-evidence safety and cost development."""
import argparse,hashlib,json,os,time,traceback
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from run_closed_loop import ROOT,compile_driver,one
from run_recovery import MODELS
from run_aligned import atomic,signature as base_signature
from audit_closed_loop import audit_case
from tools.audit_revision_service import audit_service
from tools.audit_epoch import audit_epoch
from tools.audit_report_recovery import audit_report_recovery
from tools.audit_aligned import audit_aligned
from tools.audit_safety import audit_safety
from run_factorial import independent_context_audit
PROFILES={'safe_full':(True,True,True,True,True),'aligned_budget':(False,False,False,True,True),'safe_no_interrupt':(True,False,True,True,True),'safe_no_install_budget':(True,True,False,True,True),'safe_no_report_retry':(True,True,True,False,False),'safe_fixed_retry':(True,True,True,True,False)}
def identity(c):return '_'.join(str(c[k])for k in('topology','scenario','model','profile','seed'))
def configs(stage):
 if stage=='functional':
  rows=[dict(model='stable6',profile=p,scenario=sc,seed=seed,topology='base',generation_stop=90,faults=[[35,2]]if sc=='failure'else[],**extras)for sc,seed,extras in [('steady',999711,{}),('failure',999712,{'reject':True}),('steady',999713,{'missing':True}),('overload',999714,{})]for p in('safe_full','safe_no_interrupt','safe_no_install_budget','aligned_budget')]
  rows+=[dict(model='stable6',profile='safe_full',scenario='steady',seed=999715,topology='base',generation_stop=90,faults=[],broken=True),dict(model='stable6',profile='safe_full',scenario='multi_failure',seed=999716,topology='base',generation_stop=90,faults=[[25,2],[40,3]])];return rows
 rows=[]
 for seed in(999801,999802):
  for top in('base','jitter_b'):
   for sc in('multi_failure','overload'):
    common=dict(scenario=sc,seed=seed,topology=top,generation_stop=330,faults=[[65,2],[145,3],[225,6]]if sc=='multi_failure'else[])
    for model in MODELS:
     for profile in('safe_full','aligned_budget'):rows.append(dict(model=model,profile=profile,**common))
    for profile in('safe_no_interrupt','safe_no_install_budget','safe_no_report_retry','safe_fixed_retry'):rows.append(dict(model='stable6',profile=profile,**common))
 return rows

def signature():
 d=base_signature();p=ROOT/'tools/audit_safety.py';d[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();return d

def registration(stage):
 p=ROOT/'docs'/f'safety_{stage}_registration.json';cfg=configs(stage);sig=signature()
 if p.exists():
  d=json.loads(p.read_text());assert d['configs']==cfg and d['source_sha256']==sig,'registered source/configuration drift';return d
 prev=json.loads((ROOT.parent/'aligned_budget_study_20261011/docs/aligned_development_registration.json').read_text())
 d=dict(stage=stage,registered_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),formal_validation=False,configs=cfg,source_sha256=sig,primary={'model':'stable6','profile':'safe_full'},LLM_runtime_calls=0,prior_failed_gates_preserved=True,post_run_primary_selection_forbidden=True,
  safety={'triggers':'two consecutive steps with missing current interior relay OR fresh received current-version source failure n>=20 fraction>=0.2','requires':'two fresh sources age8s; pending age>=5s; before cutoff','version_guard':'failure matches pending expected version and stamp after decision','priority':'available qualified credit precedes explicit interruption censor','no_fault_truth_online':True,'all_models_same_safety':True},
  costs={'sink_meter':'sink-local control DATA','received_meter':'maximum received cumulative control DATA per remote node, stale values lower bound','installation_reservation':'5994 DATA per install including up to2 retries per source; no refunds; maxone per20s fixedwindow','report_reservation':'1143 extra DATA per local-node allocation; maxone per20s fixedwindow','scope':'separate transaction bounds; no total traffic savings guarantee; ACK and radio evaluated separately'},
  gates=prev['gates']|{'safety_service_margin_vs_no_interrupt':0.,'installation_budget_service_margin':-.01,'installation_budget_control_reduction_minimum':.05,'observed_cost_lower_bound_violations':0},
  statistics='Development only: two known ten-node geometries, two new common offered streams. Pair at geometry x seed; no confirmatory p-values.',
  limitations=['One-bucket horizon identical across new contrasts; no horizon-effect claim.','Partial confirmations and late old commands possible; audit every credited packet.','No global control traffic cap.','Endogenous censoring: no stationary LinUCB regret guarantee.','Scale and standardized routing comparisons outstanding.'])
 atomic(p,d);return d

def execute(payload):
 cfg,binary,stage=payload;folder=ROOT/'results'/stage/(identity(cfg)+'_'+str(time.time_ns()));folder.mkdir(parents=True)
 try:
  safe,interrupt,budget,retry,rbudget=PROFILES[cfg['profile']]
  marker='_ops_epoch_aligned_'+('safe_'+('interrupt_'if interrupt else'')+('installbudget_'if budget else'')if safe else'')
  policy=MODELS[cfg['model']].replace('_ops_',marker)
  row=one(Path(binary),policy=policy,profile='lease10_15',extended=True,source_only=True,folder=folder,queue_discipline='fifo',epoch_certificate=True,report_retry=retry,report_budget=rbudget,**{k:v for k,v in cfg.items()if k not in('model','profile')})
  row.update(model=cfg['model'],profile=cfg['profile'],freshness='fixed16',stage=stage,configuration_key=identity(cfg),evidence_directory=str(folder.relative_to(ROOT)))
  audit=audit_case(row,folder);audit['settled_service']=audit_service(row,folder);audit['queue_and_age']=audit_epoch(row,folder);audit['report_recovery']=audit_report_recovery(row,folder);audit['stable_context']=independent_context_audit(row,folder);row['audit']=audit
  audit['aligned_reward_and_budget']=audit_aligned(row,folder);audit['safety_and_cost']=audit_safety(row,folder)
  atomic(folder/'case.json',row);return row
 except BaseException:(folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise

def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),required=True);p.add_argument('--register-only',action='store_true');p.add_argument('--workers',type=int,default=4);a=p.parse_args();assert 1<=a.workers<=4
 reg=registration(a.stage)
 if a.register_only:print('REGISTERED',a.stage,len(reg['configs']),flush=True);return
 if a.stage=='development':
  f=json.loads((ROOT/'results/safety_functional_manifest.json').read_text());assert len(f)==18 and all(r['audit']['status']=='passed'for r in f)
 binary=compile_driver();path=ROOT/'results'/f'safety_{a.stage}_manifest.json';rows=json.loads(path.read_text())if path.exists()else[];done={r['configuration_key']for r in rows};pending=[c for c in reg['configs']if identity(c)not in done]
 with ProcessPoolExecutor(max_workers=a.workers)as pool:
  for future in as_completed([pool.submit(execute,(c,str(binary),a.stage))for c in pending]):
   r=future.result();rows.append(r);rows.sort(key=lambda r:r['configuration_key']);atomic(path,rows);print(json.dumps(dict(audited=len(rows),registered=len(reg['configs']),case=r['configuration_key'],service=r['worst_party_timely'],control=r['native']['control_psdu_bytes'],safety=r['audit']['safety_and_cost'])),flush=True)
 print('BATCH_COMPLETE',a.stage,len(rows),flush=True)
if __name__=='__main__':main()
