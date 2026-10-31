"""Separate preregistered development; older failed gates remain unchanged."""
import argparse,hashlib,json,os,time,traceback
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from run_closed_loop import ROOT,compile_driver,one
from run_guarded import MODELS
from audit_closed_loop import audit_case
from tools.audit_revision_service import audit_service
from tools.audit_epoch import audit_epoch
from run_factorial import independent_context_audit
PROFILES={'legacy_fifo':('fifo',False),'epoch_fifo':('fifo',True),'epoch_age':('bounded_age',True)}
def atomic(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_suffix('.partial');temp.write_text(json.dumps(d,indent=2)+'\n');os.replace(temp,p)
def configs(stage):
 if stage=='functional':
  out=[dict(model='stable6',profile=p,scenario='steady',seed=998011,topology='base',generation_stop=90,faults=[])for p in PROFILES]
  out+=[dict(model='stable6',profile='epoch_age',scenario='failure',seed=998012,topology='base',generation_stop=90,faults=[[35,2]],reject=True),dict(model='stable6',profile='epoch_age',scenario='steady',seed=998013,topology='base',generation_stop=90,faults=[],missing=True)]
  out+=[dict(model='stable6',profile=p,scenario='overload',seed=998014,topology='base',generation_stop=90,faults=[])for p in PROFILES];return out
 return [dict(model=m,profile=p,scenario=s,seed=998301,topology=t,generation_stop=330,faults=[[65,2],[145,3],[225,6]]if s=='multi_failure'else[])for t in ('base','jitter_b')for s in ('multi_failure','overload')for m in MODELS for p in PROFILES]
def identity(c):return '_'.join(str(c[k])for k in ('topology','scenario','model','profile','seed'))
def signature():
 files=list(ROOT.glob('*.py'))+list((ROOT/'wsn').glob('*.py'))+list((ROOT/'tests').glob('*.py'))+list((ROOT/'ns3').glob('*.cc'))+list((ROOT/'ns3').glob('*.h'))+[ROOT/'tools/audit_epoch.py',ROOT/'tools/audit_revision_service.py']
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(files)}
def registration(stage):
 p=ROOT/'docs'/f'epoch_{stage}_registration.json';cfg=configs(stage);sig=signature()
 if p.exists():
  d=json.loads(p.read_text());assert d['configs']==cfg and d['source_sha256']==sig,'registered source/configuration drift';return d
 d=dict(stage=stage,formal_validation=False,registered_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),configs=cfg,source_sha256=sig,primary={'model':'stable6','profile':'epoch_age'},LLM_runtime_calls=0,
  hypotheses=['A received source-local version-start certificate can recover complete, settled same-version buckets hidden by first-report-time anchoring without increasing the frame length.','Age-triggered bounded report overtaking can improve observability with measured service and radio cost.','Contextual learning must improve on context-free and deterministic controls with the identical wire and queue mechanism.'],
  report_wire={'source_body_bytes':80,'relay_body_bytes':72,'source_psdu_bytes':127,'epoch_slot':'slot zero sentinel U32 plus first whole bucket after local installation; replaces open bucket which is ineligible for feedback','closed_bucket_count':3,'version_zero_first_bucket':0},
  scheduling={'queue_capacity_including_active':16,'minimum_nonreport_requests_before_overtaking':4,'report_age_threshold_ns':1000000000,'report_fifo_retained':True,'drops_or_out_of_band_delivery_added':False,'bound_scope':'request order, not delivery age or absolute time'},
  gates={'service_margin_vs_epoch_fifo':-.01,'control_increase_limit_vs_epoch_fifo':.05,'known_service_fraction_gain_vs_legacy_fifo':.05,'rule_service_margin':0.,'resource_service_margin':0.,'worst_topology_service_margin':-.03,'context_service_gain':.005,'context_cost_increase_limit':.05,'context_alternative_service_margin':-.005,'context_alternative_control_reduction':.05,'primary_trained_score_choices_minimum':20,'trained_choices_minimum_per_primary_run':3},
  statistics='Two known ten-node geometries and one new stream; development only, paired descriptive effects; no confirmatory p-values or deployment inference.',
  prior_failed_gates_preserved=True,post_run_primary_selection_forbidden=True,
  limitations=['The certificate is conservative source-local information, not authentication or sink access to hidden installation state.','The unused open-bucket slot is a prototype wire choice requiring explicitly matched encoder and decoder.','Finite request fairness does not guarantee wall-time or receiver freshness.','No acceptance, contextual gain or scalability claim until evidence supports it.'])
 atomic(p,d);return d
def execute(payload):
 cfg,binary,stage=payload;folder=ROOT/'results'/stage/(identity(cfg)+'_'+str(time.time_ns()));folder.mkdir(parents=True)
 try:
  queue,epoch=PROFILES[cfg['profile']];policy=MODELS[cfg['model']]
  if epoch:policy=policy.replace('_ops_','_ops_epoch_')
  kw={k:v for k,v in cfg.items()if k not in ('model','profile')}
  row=one(Path(binary),policy=policy,profile='lease10_15',extended=True,source_only=True,folder=folder,queue_discipline=queue,epoch_certificate=epoch,**kw)
  row.update(model=cfg['model'],profile=cfg['profile'],freshness='fixed16',stage=stage,configuration_key=identity(cfg),evidence_directory=str(folder.relative_to(ROOT)))
  audit=audit_case(row,folder);audit['settled_service']=audit_service(row,folder);audit['queue_and_age']=audit_epoch(row,folder);audit['stable_context']=independent_context_audit(row,folder);row['audit']=audit
  atomic(folder/'case.json',row);return row
 except BaseException:(folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),required=True);p.add_argument('--register-only',action='store_true');p.add_argument('--workers',type=int,default=4);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=48);a=p.parse_args();assert 1<=a.workers<=4
 reg=registration(a.stage)
 if a.register_only:print('REGISTERED',a.stage,len(reg['configs']),flush=True);return
 if a.stage=='development':
  functional=json.loads((ROOT/'results/epoch_functional_manifest.json').read_text());assert len(functional)==8 and all(r['audit']['status']=='passed'for r in functional)
 binary=compile_driver();manifest=ROOT/'results'/f'epoch_{a.stage}_manifest.json';rows=json.loads(manifest.read_text())if manifest.exists()else[];done={r['configuration_key']for r in rows};pending=[c for c in reg['configs'][a.start:a.start+a.count]if identity(c)not in done]
 with ProcessPoolExecutor(max_workers=a.workers)as pool:
  for f in as_completed([pool.submit(execute,(c,str(binary),a.stage))for c in pending]):
   row=f.result();rows.append(row);rows.sort(key=lambda r:r['configuration_key']);atomic(manifest,rows);print(json.dumps(dict(audited=len(rows),registered=len(reg['configs']),case=row['configuration_key'],service=row['worst_party_timely'],control=row['native']['control_psdu_bytes'],bypasses=row['audit']['queue_and_age']['bypasses'])),flush=True)
 print('BATCH_COMPLETE',a.stage,len(rows),flush=True)
if __name__=='__main__':main()
