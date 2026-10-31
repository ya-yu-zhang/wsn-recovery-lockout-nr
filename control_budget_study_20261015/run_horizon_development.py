"""One bounded observation-protocol repair, frozen before development runs."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,json,os,traceback
from run_study import ROOT,ENGINE,source_hashes
from fast_native_run import one
from run_mechanisms import policy
from budget_controller import BudgetController
from horizon_controller import HorizonController,HorizonCohortController,HorizonClosingController
from audit_case import audit

MODELS=('legacy','full_v2','horizon','cohort','closing')
def configs():return[dict(topology=f'budget_{n}_2026101501',scenario=s,seed=k,model=m,generation_stop=330,evidence_gate=m!='legacy',stage='horizon_development')for n in(10,20)for s in('multi_failure','overload')for k in(2026101511,2026101512)for m in MODELS]
def signature():
    fs=['HORIZON_REPAIR_PROTOCOL.md','CADENCE_REPAIR_PROTOCOL.md','horizon_controller.py','cadence_controller.py','run_horizon_development.py','fast_native_run.py']
    return source_hashes()|{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in fs}
def execute(c):
    key=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()[:20];folder=ROOT/'results/horizon_development'/key;folder.mkdir(parents=True,exist_ok=True)
    if(folder/'case.json').exists():return json.loads((folder/'case.json').read_text())
    pacing=c['model']!='legacy';factory={'horizon':HorizonController,'cohort':HorizonCohortController,'closing':HorizonClosingController}.get(c['model'],BudgetController)
    try:
        row=one(ENGINE/'ns3/wsn-closed-loop',c['scenario'],policy('resource10_on'),c['seed'],folder=folder,profile='local15_event',topology=c['topology'],extended=True,source_only=True,generation_stop=330,faults=[[65,2],[145,3],[225,6]]if c['scenario']=='multi_failure'else[],queue_discipline='fifo',epoch_certificate=True,report_retry=True,report_budget=True,report_retry_mode='always',controller_factory=factory,controller_kwargs={'pacing':pacing,'evidence_gate':c['evidence_gate']},unified_budget=pacing,protect_evidence=True,version_pacing=pacing,report_phase_seed=c['seed'])
        row.update(configuration=c,configuration_key=key,evidence_directory=str(folder.relative_to(ROOT)),host_postprocess='bitwise-equivalent ordered energy terms, one radio scan')
        row['audit']=audit(row,folder);tmp=folder/'case.staging';tmp.write_text(json.dumps(row,indent=2)+'\n');tmp.replace(folder/'case.json');return row
    except BaseException:(folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=3);p.add_argument('--register-only',action='store_true');a=p.parse_args();os.environ['TMPDIR']=str(ROOT/'build_tmp')
    assert(ROOT/'results/fast_host_equivalence.json').exists()
    reg=dict(configs=configs(),source_sha256=signature(),native_sha256=hashlib.sha256((ENGINE/'ns3/wsn-closed-loop').read_bytes()).hexdigest(),scope='development only',runtime_LLM_calls=0)
    target=ROOT/'results/horizon_development_registration.json'
    if target.exists():assert json.loads(target.read_text())==reg
    else:target.write_text(json.dumps(reg,indent=2)+'\n')
    print('REGISTERED',40,flush=True)
    if a.register_only:return
    rows=[];failures=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers)as pool:
        tasks={pool.submit(execute,c):c for c in configs()}
        for f in concurrent.futures.as_completed(tasks):
            try:
                row=f.result();rows.append(row);index=[{k:r[k]for k in('configuration','configuration_key','evidence_directory','audit','estimated_radio_joules','bandit_updates')}for r in rows]
                p=ROOT/'results/horizon_development_manifest.json';t=p.with_suffix('.staging');t.write_text(json.dumps(index,indent=2)+'\n');t.replace(p)
                print('AUDITED',len(rows),40,row['configuration']['model'],row['audit']['worst_source_service'],row['audit']['control_DATA_bytes'],flush=True)
            except BaseException:failures.append(dict(configuration=tasks[f],traceback=traceback.format_exc()));(ROOT/'results/horizon_development_failures.json').write_text(json.dumps(failures,indent=2)+'\n');print('FAILED',flush=True)
    assert signature()==reg['source_sha256']
    if failures:raise RuntimeError('failed attempts retained')
    assert len(rows)==40;print('COMPLETE',40,flush=True)
if __name__=='__main__':main()
