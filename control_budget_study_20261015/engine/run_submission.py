"""Frozen, paired no-LLM submission study; records every registered case."""
import argparse,concurrent.futures,hashlib,json,os,time
from pathlib import Path
from run_closed_loop import ROOT,compile_driver,one
from run_development import source_hashes
from audit_closed_loop import audit_case

MODELS=('full','low4','intercept','frozen','random','low4_noop','intercept_noop')
def policy(model):
 if model not in MODELS:raise ValueError(model)
 return 'linucb_event_scalar4_failure_current_'+(model+'_' if model!='full' else '')+'retry_mask'

def configs(stage):
 if stage=='functional':
  return [dict(scenario='steady',policy=policy('low4_noop'),seed=994011,source_only=True,generation_stop=90,faults=[]),
          dict(scenario='failure',policy=policy('low4_noop'),seed=994012,source_only=True,generation_stop=90,faults=[[35,2]],reject=True),
          dict(scenario='steady',policy=policy('low4_noop'),seed=994013,source_only=True,generation_stop=90,faults=[],missing=True),
          dict(scenario='overload',policy=policy('low4'),seed=994014,source_only=True,generation_stop=90,faults=[])]
 topologies=('base','jitter_b') if stage=='pilot' else tuple(f'heldout_{s}' for s in range(994301,994307))
 seeds=(994101,) if stage=='pilot' else (994201,994202)
 return [dict(scenario=scene,policy=policy(model),seed=seed,source_only=True,generation_stop=330,
              faults=[[65,2],[145,3],[225,6]] if scene=='multi_failure' else [],topology=topology,model=model)
         for topology in topologies for scene in ('multi_failure','overload') for seed in seeds for model in MODELS]

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',choices=('functional','pilot','heldout'),required=True)
 parser.add_argument('--register-only',action='store_true');parser.add_argument('--workers',type=int,default=3)
 args=parser.parse_args();stage=args.stage
 regpath=ROOT/'docs'/f'{stage}_registration.json';manifest=ROOT/'results'/f'{stage}_manifest.json';folder=ROOT/'results'/stage
 cases=configs(stage);hashes=source_hashes()
 if regpath.exists():
  reg=json.loads(regpath.read_text());assert reg['configs']==cases and reg['source_sha256']==hashes,'registered source/config changed'
 else:
  if stage=='heldout':
   audit=json.loads((ROOT/'results/pilot_audit.json').read_text());assert audit['status']=='passed'
   assert audit['native_runs']==len(configs('pilot'))
  reg={'stage':stage,'formal_matrix':stage=='heldout','configs':cases,'source_sha256':hashes,'LLM_calls':0,
       'primary_endpoint':'whole-generation worst-source timely delivery; paired by geometry/scenario/offered stream',
       'planned_comparisons':[['low4_noop','low4'],['intercept_noop','intercept'],['low4','intercept'],['low4','full'],['low4','frozen'],['low4','random']],
       'statistical_unit':'six independently generated ten-node geometries; two offered streams reused across geometry, no pseudoreplication',
       'analysis':'paired geometry means, topology bootstrap95% intervals; all signs reported; exploratory controller comparisons',
       'practical_thresholds':{'control_data_reduction_fraction':.05,'timely_noninferiority_margin':.01},
       'domain':'two sources, ten static nodes; failure and overload dynamics; no scale or physical-deployment claim',
       'intervention':'physical4D context; conservative unchanged-route admission after >=20 current-version source completions, no failure gate and confirmed installation',
       'alpha':.6,'seed_rules':'geometry streams994301..994306 and offered994201/994202 reserved before study, not used in pilot',
       'exclusion_rule':'no service failure or missing feedback excluded; infrastructure reruns retained separately'}
  regpath.write_text(json.dumps(reg,indent=2)+'\n')
 if args.register_only:print(json.dumps({'registered':len(cases),'stage':stage}),flush=True);return
 rows=json.loads(manifest.read_text()) if manifest.exists() else [];done={(r.get('model'),r['scenario'],r['topology'],r['seed'],r['policy']) for r in rows}
 binary=compile_driver();folder.mkdir(exist_ok=True);audits=[]
 def execute(cfg):
  kwargs={k:v for k,v in cfg.items() if k!='model'}
  row=one(binary,folder=folder,profile='hybrid5_10',extended=True,**kwargs);row.update(stage=stage,model=cfg.get('model','functional'))
  audit=audit_case(row,folder);return row,audit
 pending=[c for c in cases if (c.get('model','functional'),c['scenario'],c.get('topology','base'),c['seed'],c['policy']) not in done]
 started=time.time()
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
  for row,audit in map(lambda f:f.result(),concurrent.futures.as_completed([pool.submit(execute,c) for c in pending])):
   rows.append(row);audits.append(audit);rows.sort(key=lambda r:r['id'])
   temp=manifest.with_suffix('.partial');temp.write_text(json.dumps(rows,indent=2));os.replace(temp,manifest)
   print(json.dumps({'stage':stage,'completed':len(rows),'total':len(cases),'model':row['model'],'scene':row['scenario'],'topology':row['topology'],'jobs':audit['mac_jobs'],'elapsed_s':round(time.time()-started,1)}),flush=True)
 assert len(rows)==len(cases)
 # Existing resumed rows must also be audited before a completed stage is attested.
 if len(audits)!=len(rows):audits=[audit_case(r,folder) for r in rows]
 out={'status':'passed','native_runs':len(rows),'cases':audits,'jobs':sum(x['mac_jobs'] for x in audits),'stage':stage}
 (ROOT/'results'/f'{stage}_audit.json').write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':main()
