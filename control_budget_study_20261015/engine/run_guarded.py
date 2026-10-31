"""Pre-registered longer development and bounded-reporting experiment."""
import argparse, json, os, time, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from run_closed_loop import ROOT, compile_driver, one
from audit_closed_loop import audit_case
from tools.audit_revision_service import audit_service
from run_factorial import source_hashes, independent_context_audit

MODELS = {
 'stable6':'linucb_event_scalar4_failure_current_ops_ctx6_noop_cache20_retry_freshfixed_mask',
 'intercept6':'linucb_event_scalar4_failure_current_ops_ctx6_intercept_noop_cache20_retry_freshfixed_mask',
 'rule':'event_rule_scalar_failure_current_ops_ctx6_noop_cache20_retry_freshfixed_mask',
 'resource':'force0_scalar_failure_current_ops_ctx6_noop_cache20_retry_freshfixed_mask'}
PROFILES={'periodic':'hybrid5_10','lease20':'lease10_20','guard15':'lease10_15'}


def atomic(path,obj):
 temp=path.with_suffix('.partial');temp.write_text(json.dumps(obj,indent=2)+'\n');os.replace(temp,path)


def configurations(stage):
 if stage=='functional':
  return [dict(model='stable6',schedule='periodic',scenario='steady',seed=996011,topology='base',generation_stop=90,faults=[],legacy_regression=True),
          dict(model='stable6',schedule='guard15',scenario='failure',seed=997012,topology='base',generation_stop=90,faults=[[35,2]],reject=True),
          dict(model='stable6',schedule='guard15',scenario='steady',seed=997013,topology='base',generation_stop=90,faults=[],missing=True),
          dict(model='stable6',schedule='guard15',scenario='overload',seed=997014,topology='base',generation_stop=90,faults=[])]
 return [dict(model=model,schedule=schedule,scenario=scene,seed=996301,topology=topology,generation_stop=330,
              faults=[[65,2],[145,3],[225,6]] if scene=='multi_failure' else [])
         for topology in ('base','jitter_b') for scene in ('multi_failure','overload')
         for model in MODELS for schedule in PROFILES]


def identity(cfg):return '_'.join(str(cfg[k]) for k in ('topology','scenario','model','schedule','seed'))


def registration(stage):
 cfgs=configurations(stage);path=ROOT/'docs'/f'guarded_{stage}_registration.json';signature=source_hashes()
 if path.exists():
  reg=json.loads(path.read_text());assert reg['configs']==cfgs and reg['source_sha256']==signature
 else:
  reg=dict(stage=stage,formal_validation=False,registered_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
           configs=cfgs,source_sha256=signature,LLM_runtime_calls=0,
           primary_configuration={'model':'stable6','schedule':'guard15'},
           primary_endpoint='whole_generation_worst_source_timely',
           hypotheses=['An idle period 20 exceeds fixed relay freshness 16; period 15 reduces scheduled gaps while keeping fixed freshness.',
                       'A 330-second horizon provides more opportunities for feedback-informed choices than the previous 180-second runs.',
                       'Context-dependent LinUCB must show a practical improvement over context-free InterceptLinUCB under the same reporting profile.'],
           reporting_bound={'base_tick_s':5,'active_period_s':10,'guarded_idle_period_s':15,'fixed_relay_freshness_s':16,
                            'scope':'scheduled emission gaps only; no guarantee on receipt under loss or queueing','scheduler':'elapsed age since last generated report; only guarded profile changes global-slot scheduling',
                            'message_length_unchanged':True,'legacy_5_10_20_wire_tags_unchanged':True},
           untouched_components=['LLM-free controller','reward and feedback protocol','exploration cap 4','FE budget','source report interval','freshness semantics'],
           gates={'report_service_margin':-.01,'report_control_reduction':.05,'rule_service_margin':0.,'resource_service_margin':0.,
                  'worst_topology_service_margin':-.03,'context_service_gain':.005,'context_cost_increase_limit':.05,
                  'context_alternative_service_margin':-.005,'context_alternative_control_reduction':.05,'primary_trained_ucb_choices_minimum':20},
           statistics='Two known development geometries and one new offered-stream seed. No p-values, confidence intervals or held-out inference.',
           limitations=['Ten nodes and two sources.','Longer horizon changes the development task; it is not an additional independent replay of the previous 64 cases.',
                        'The bounded reporter is an engineering correction until practical service and cost gates pass.','Proxy route differences are not counterfactual network outcomes.'],
           post_run_selection_forbidden=True)
  atomic(path,reg)
 return reg


def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),required=True)
 p.add_argument('--register-only',action='store_true');p.add_argument('--start',type=int,default=0)
 p.add_argument('--count',type=int,default=4);p.add_argument('--workers',type=int,default=2);args=p.parse_args()
 assert args.start>=0 and args.count>=1 and 1<=args.workers<=4
 reg=registration(args.stage)
 if args.register_only:print('REGISTERED',args.stage,len(reg['configs']));return
 binary=compile_driver();manifest=ROOT/'results'/f'guarded_{args.stage}_manifest.json'
 rows=json.loads(manifest.read_text()) if manifest.exists() else [];done={r['configuration_key']for r in rows}
 base=ROOT/'results'/args.stage;base.mkdir(exist_ok=True)
 def execute(cfg):
  folder=base/(identity(cfg)+'_'+str(time.time_ns()));folder.mkdir()
  try:
   kwargs={k:v for k,v in cfg.items() if k not in ('model','schedule','legacy_regression')}
   row=one(binary,policy=MODELS[cfg['model']],profile=PROFILES[cfg['schedule']],extended=True,source_only=True,folder=folder,**kwargs)
   row.update(model=cfg['model'],schedule=cfg['schedule'],freshness='fixed16',stage=args.stage,
              configuration_key=identity(cfg),evidence_directory=str(folder.relative_to(ROOT)))
   audit=audit_case(row,folder);audit['settled_service']=audit_service(row,folder)
   audit['stable_context']=independent_context_audit(row,folder);row['audit']=audit
   if cfg.get('legacy_regression'):
    old=json.loads((ROOT.parent/'factorial_study_20261010/results/factorial_functional_manifest.json').read_text())
    frozen=next(r for r in old if r['seed']==996011)
    keys=('native','offered','timely_by_party','worst_party_timely','mean_timely','estimated_radio_joules','total_fe','bandit_updates')
    assert all(row[k]==frozen[k]for k in keys),'legacy wire/native regression'
    row['legacy_regression']={'matched':True,'reference':'factorial functional seed996011','fields':list(keys)}
   atomic(folder/'case.json',row);return row
  except BaseException:
   (folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
 pending=[c for c in reg['configs'][args.start:args.start+args.count]if identity(c)not in done]
 with ThreadPoolExecutor(max_workers=args.workers)as pool:
  for future in as_completed([pool.submit(execute,c)for c in pending]):
   row=future.result();rows.append(row);rows.sort(key=lambda r:r['configuration_key']);atomic(manifest,rows)
   print(json.dumps({'stage':args.stage,'audited':len(rows),'registered':len(reg['configs']),'case':row['configuration_key'],'mac_jobs':row['audit']['mac_jobs']}),flush=True)
 print('BATCH_COMPLETE',args.stage,len(rows),flush=True)


if __name__=='__main__':main()
