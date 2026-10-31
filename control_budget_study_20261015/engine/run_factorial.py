"""Registered development factorial; unique attempts and complete raw audit."""
import argparse,hashlib,json,os,time,traceback
from pathlib import Path
from run_closed_loop import ROOT,compile_driver,one
from audit_closed_loop import audit_case
from tools.audit_revision_service import audit_service

MODELS={
 'stable6':'linucb_event_scalar4_failure_current_ops_ctx6_noop_cache20_retry_',
 'legacy4':'linucb_event_scalar4_failure_current_ops_low4_noop_cache20_retry_',
 'rule':'event_rule_scalar_failure_current_ops_ctx6_noop_cache20_retry_',
 'resource':'force0_scalar_failure_current_ops_ctx6_noop_cache20_retry_'}

def configurations(stage):
 if stage=='functional':
  return [dict(model='stable6',schedule='periodic',freshness='fixed16',scenario='steady',seed=996011,topology='base',generation_stop=90,faults=[]),
          dict(model='stable6',schedule='lease',freshness='fixed16',scenario='failure',seed=996012,topology='base',generation_stop=90,faults=[[35,2]],reject=True),
          dict(model='stable6',schedule='lease',freshness='scaled',scenario='steady',seed=996013,topology='base',generation_stop=90,faults=[],missing=True),
          dict(model='stable6',schedule='lease',freshness='fixed16',scenario='overload',seed=996014,topology='base',generation_stop=90,faults=[])]
 return [dict(model=model,schedule=schedule,freshness=freshness,scenario=scene,seed=996201,topology=topology,generation_stop=180,
              faults=[[65,2],[145,3]] if scene=='multi_failure' else [])
         for topology in ('base','jitter_b') for scene in ('multi_failure','overload')
         for model in MODELS for schedule in ('periodic','lease') for freshness in ('fixed16','scaled')]

def source_hashes():
 paths=list(ROOT.glob('*.py'))+list((ROOT/'wsn').glob('*.py'))+list((ROOT/'ns3').glob('*.cc'))+list((ROOT/'ns3').glob('*.h'))+list((ROOT/'tests').glob('*.py'))+[ROOT/'tools/audit_revision_service.py']
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}

def key(cfg):return '_'.join(str(cfg[x]) for x in ('topology','scenario','model','schedule','freshness','seed'))

def independent_context_audit(row,folder):
 steps=json.loads((folder/(row['id']+'.controller.json')).read_text())['steps']
 for step in steps:
  obs=step['observation'];t=obs['time_ns'];fresh={}
  for report in obs['reports']:
   n=report['node'];limit=8_000_000_000 if n<2 else 16_000_000_000 if row['freshness']=='fixed16' else report['period_s']*1_600_000_000
   if t-report['stamp_ns']<=limit:fresh[n]=report
  expected_states={str(n):('unknown' if n not in {r['node'] for r in obs['reports']} else 'fresh' if n in fresh else 'expired') for n in range(9)}
  assert step['event']['observation_states']==expected_states
  if row['model']=='legacy4':continue
  x=step['context'];service=step['event']['settled_service'];known=service['known']
  queue=max([fresh.get(f,{}).get('depth',0) for f in (0,1)])/16
  assert len(x)==6 and x[3]==min(queue,1)
  assert x[4]==(1-service['worst_timely'] if known else 0.) and x[5]==(0. if known else 1.)
 return {'status':'passed','snapshots':len(steps),'context_and_freshness_independently_reconstructed':True}

def atomic_json(path,data):
 temp=path.with_suffix('.partial');temp.write_text(json.dumps(data,indent=2)+'\n')
 with temp.open('rb') as handle:os.fsync(handle.fileno())
 os.replace(temp,path)

def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),required=True)
 p.add_argument('--register-only',action='store_true');p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=4);a=p.parse_args()
 if a.start<0 or a.count<1:raise ValueError('invalid batch')
 cfgs=configurations(a.stage);regpath=ROOT/'docs'/f'factorial_{a.stage}_registration.json'
 signature=source_hashes()
 if regpath.exists():
  saved=json.loads(regpath.read_text());assert saved['configs']==cfgs and saved['source_sha256']==signature,'source/configuration drift'
 else:
  atomic_json(regpath,dict(stage=a.stage,formal_validation=False,registered_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),configs=cfgs,source_sha256=signature,
   context_schema=['intercept','current_route_missing_node_fraction','fresh_aggregate_busy_fraction','maximum_observed_fresh_source_queue_fraction','masked_settled_service_deficit','settled_service_unknown_indicator'],
   unknown_semantics='service deficit zero is a mask only; paired indicator distinguishes unknown from measured perfect service; queue always means observed fresh source queue',
   report_factor={'periodic':'source5/relay10','lease':'source5/active_relay10/idle_relay20; local reception lease12s'},
   freshness_factor={'fixed16':'source8/relay16 regardless of schedule','scaled':'source8/relay1.6 times actually advertised reporting period'},
   primary_configuration={'model':'stable6','schedule':'lease','freshness':'fixed16'},primary_endpoint='whole_generation_worst_source_timely',
   primary_gates={'stable6_vs_rule_service_margin':0.,'stable6_vs_resource_service_margin':0.,'lease_vs_periodic_fixed16_service_margin':-.01,'lease_vs_periodic_fixed16_control_reduction':.05,'stable6_vs_legacy4_service_margin':-.01,'worst_topology_service_margin':-.03},
   statistics='paired mean over two development geometries and one offered stream; no p-values, population inference or held-out validation claim',
   all_cases_retained=True,counterfactual_rewards_for_learning=False,LLM_runtime_calls=0,
   limitations=['two-source ten-node prototype','change in context dimension changes UCB geometry; no claim that comparisons isolate missingness alone','conditional control/freshness interaction retained','source_service evidence uses received denominators and sink-local settled numerators'],
   checkpoint_policy='audited per-case JSON and raw archive saved before proceeding to the next small batch; failed attempts retained'))
 if a.register_only:print('REGISTERED',a.stage,len(cfgs),flush=True);return
 binary=compile_driver();out=ROOT/'results'/f'factorial_{a.stage}';out.mkdir(exist_ok=True)
 manifest=ROOT/'results'/f'factorial_{a.stage}_manifest.json';rows=json.loads(manifest.read_text()) if manifest.exists() else []
 done={r['configuration_key'] for r in rows}
 for cfg in cfgs[a.start:a.start+a.count]:
  ident=key(cfg)
  if ident in done:continue
  attempt=out/(ident+'_'+str(time.time_ns()));attempt.mkdir()
  try:
   model=cfg['model'];schedule=cfg['schedule'];freshness=cfg['freshness'];policy=MODELS[model]+('freshfixed_' if freshness=='fixed16' else 'freshscaled_')+'mask'
   kwargs={k:v for k,v in cfg.items() if k not in ('model','schedule','freshness')}
   row=one(binary,policy=policy,profile='hybrid5_10' if schedule=='periodic' else 'lease10_20',extended=True,source_only=True,folder=attempt,**kwargs)
   row.update(model=model,schedule=schedule,freshness=freshness,stage=a.stage,configuration_key=ident,evidence_directory=str(attempt.relative_to(ROOT)))
   audit=audit_case(row,attempt);audit['settled_service']=audit_service(row,attempt);audit['context_freshness']=independent_context_audit(row,attempt)
   row['audit']=audit;atomic_json(attempt/'case.json',row)
   rows.append(row);rows.sort(key=lambda r:r['configuration_key']);atomic_json(manifest,rows)
   print(json.dumps({'audited':len(rows),'registered':len(cfgs),'case':ident,'mac_jobs':audit['mac_jobs'],'worst_timely':row['worst_party_timely']}),flush=True)
  except BaseException:
   (attempt/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
 print('BATCH_COMPLETE',len(rows),'/',len(cfgs),flush=True)

if __name__=='__main__':main()
