"""Frozen matched mechanism comparison; no outcome-based replacements."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,json,os,sys,time,traceback
ROOT=Path(__file__).resolve().parent;ENGINE=ROOT/'engine';sys.path.insert(0,str(ENGINE))
from run_closed_loop import one
from run_mechanisms import policy
from budget_controller import BudgetController
from audit_case import audit

MODELS={'legacy_resource':('resource10_on',False,False,True),'pacing_resource':('resource10_on',True,False,True),'budget_resource':('resource10_on',False,True,True),'full_resource':('resource10_on',True,True,True),'unprotected_resource':('resource10_on',True,True,False),'legacy_stability':('stability10_on',False,False,True),'full_stability':('stability10_on',True,True,True),'legacy_hop':('hop10_on',False,False,True),'full_hop':('hop10_on',True,True,True)}

def source_hashes():
    fixed=['PROTOCOL.md','prepare_engine.py','budget_controller.py','audit_case.py','run_study.py','build_environment.py','test_mechanism.cc']
    files=[ROOT/n for n in fixed]+[p for p in ENGINE.rglob('*')if p.suffix in('.py','.cc','.h')and 'results'not in p.parts and '__pycache__'not in p.parts]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(files)}

def configs(stage):
    if stage=='amendment':return [dict(topology='budget_20_2026101501',scenario=scenario,seed=seed,model=model,generation_stop=330,evidence_gate=True)for scenario in('multi_failure','overload')for seed in(2026101511,2026101512)for model in('legacy_gate_resource','full_gate_resource')]
    if stage=='development':return [dict(topology='budget_20_2026101501',scenario=scenario,seed=seed,model=model,generation_stop=330)for scenario in('multi_failure','overload')for seed in(2026101511,2026101512)for model in('legacy_resource','pacing_resource','budget_resource','full_resource')]
    if stage=='functional':return [dict(topology=f'budget_{n}_2026101500',scenario='failure',seed=2026101500+n,model=m,generation_stop=90)for n in(10,20,40)for m in('legacy_resource','full_resource')]
    if stage=='confirmation':
        return [dict(topology=f'budget_{n}_{layout}',scenario=scenario,seed=2026102000+ni*1000+li*100+rep,model=model,generation_stop=330)for ni,n in enumerate((10,20,40))for li,layout in enumerate((2026101521,2026101522,2026101523))for rep in range(10)for scenario in('multi_failure','overload')for model in('legacy_resource','full_resource','legacy_stability','full_stability','legacy_hop','full_hop')]
    raise ValueError(stage)

def execute(c):
    key=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()[:20]
    folder=ROOT/'results'/c['stage']/key;folder.mkdir(parents=True,exist_ok=True)
    if(folder/'case.json').exists():return json.loads((folder/'case.json').read_text())
    model,pacing,budget,protected=MODELS[c['model'].replace('_gate_','_')]
    faults=([[35,2]]if c['generation_stop']==90 else[[65,2],[145,3],[225,6]])if c['scenario']in('multi_failure','failure')else[]
    try:
        row=one(ENGINE/'ns3/wsn-closed-loop',c['scenario'],policy(model),c['seed'],folder=folder,profile='local15_event',topology=c['topology'],extended=True,source_only=True,generation_stop=c['generation_stop'],faults=faults,queue_discipline='fifo',epoch_certificate=True,report_retry=True,report_budget=True,report_retry_mode='always',controller_factory=BudgetController,controller_kwargs={'pacing':pacing,'evidence_gate':c.get('evidence_gate',False)},unified_budget=budget,protect_evidence=protected,version_pacing=pacing,report_phase_seed=c['seed'])
        row.update(configuration=c,configuration_key=key,evidence_directory=str(folder.relative_to(ROOT)))
        row['audit']=audit(row,folder)
        target=folder/'case.json';temp=target.with_suffix('.staging');temp.write_text(json.dumps(row,indent=2)+'\n');temp.replace(target)
        return row
    except BaseException:
        (folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development','amendment','confirmation'),required=True);p.add_argument('--workers',type=int,default=3);p.add_argument('--register-only',action='store_true');args=p.parse_args()
    os.environ['TMPDIR']=str(ROOT/'build_tmp');cs=[dict(**c,stage=args.stage)for c in configs(args.stage)]
    root=ROOT/'results';root.mkdir(exist_ok=True);registration=root/f'{args.stage}_registration.json'
    r={'configs':cs,'source_sha256':source_hashes(),'runtime_LLM_calls':0,'no_outcome_based_replacement':True,'ready_to_submit':False}
    if registration.exists():assert json.loads(registration.read_text())==r,'source or configuration changed after registration'
    else:registration.write_text(json.dumps(r,indent=2)+'\n')
    if args.register_only:print('REGISTERED',args.stage,len(cs));return
    rows=[];failures=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers)as pool:
        futures={pool.submit(execute,c):c for c in cs}
        for f in concurrent.futures.as_completed(futures):
            try:
                row=f.result();rows.append(row);(root/f'{args.stage}_manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
                print('AUDITED',args.stage,len(rows),len(cs),row['configuration']['model'],row['audit']['worst_source_service'],row['audit']['control_DATA_bytes'],flush=True)
            except BaseException:
                failures.append({'config':futures[f],'traceback':traceback.format_exc()});(root/f'{args.stage}_failures.json').write_text(json.dumps(failures,indent=2)+'\n');print('FAILED',args.stage,flush=True)
    if failures:raise RuntimeError('Failures retained; no automatic parameter or outcome replacement')
    assert len(rows)==len(cs);print('COMPLETE',args.stage,len(rows),flush=True)

if __name__=='__main__':main()
