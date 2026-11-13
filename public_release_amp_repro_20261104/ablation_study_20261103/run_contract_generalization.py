"""Fresh-layout/fresh-input generalization of the confirmation-contract ablation.
Registered 2026-11-03 after the adverse-cell ablation, before any run on these
layouts or inputs. Layout seeds 2026110301-04 and input seeds 2026110311/12 are
new; nothing else (thresholds, faults, budgets, native driver) differs from the
forty-case study. Arms: legacy (reference), horizon/joint, horizon/post_exit.
Pre-specified endpoints (computed by analyze_contract_ablation.py):
  E1 lockout incidence under joint: an unconfirmed installation exit after which
     every evaluated check up to the action stop reports installation_unconfirmed
     and no further installation is issued;
  E2 paired worst-source service difference post_exit - joint (pp);
  E3 paired control-DATA difference post_exit - joint (%);
  E4 service of post_exit vs legacy (pp).
No outcome-based change of arms, thresholds or cells is permitted."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,json,os,traceback
from run_study import ROOT,ENGINE
from fast_native_run import one
from run_mechanisms import policy
from contract_ablation import FACTORIES
from budget_controller import BudgetController
from audit_case import audit
CONFIGS=[dict(topology=f'budget_{n}_{L}',scenario=s,seed=sd,model=m,contract=k)
         for n in(10,20)for L in(2026110301,2026110302,2026110303,2026110304)for s in('multi_failure','overload')for sd in(2026110311,2026110312)
         for m,k in(('legacy','none'),('horizon','joint'),('horizon','post_exit'))]
def execute(c):
    key=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()[:20];folder=ROOT/'results/contract_generalization'/key;folder.mkdir(parents=True,exist_ok=True)
    if(folder/'case.json').exists():return json.loads((folder/'case.json').read_text())
    legacy=c['model']=='legacy'
    fac=BudgetController if legacy else FACTORIES[c['model']]
    kw={'pacing':False,'evidence_gate':False}if legacy else{'pacing':True,'evidence_gate':True,'contract':c['contract']}
    try:
        row=one(ENGINE/'ns3/wsn-closed-loop',c['scenario'],policy('resource10_on'),c['seed'],folder=folder,profile='local15_event',topology=c['topology'],extended=True,source_only=True,generation_stop=330,faults=[[65,2],[145,3],[225,6]]if c['scenario']=='multi_failure'else[],queue_discipline='fifo',epoch_certificate=True,report_retry=True,report_budget=True,report_retry_mode='always',controller_factory=fac,controller_kwargs=kw,unified_budget=not legacy,protect_evidence=True,version_pacing=not legacy,report_phase_seed=c['seed'])
        row.update(configuration=c,configuration_key=key,evidence_directory=str(folder.relative_to(ROOT)))
        row['audit']=audit(row,folder);tmp=folder/'case.staging';tmp.write_text(json.dumps(row,indent=2)+'\n');tmp.replace(folder/'case.json');return row
    except BaseException:(folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=3);p.add_argument('--register-only',action='store_true');a=p.parse_args();os.environ['TMPDIR']=str(ROOT/'build_tmp')
    fs=['contract_ablation.py','run_contract_generalization.py','horizon_controller.py','budget_controller.py','fast_native_run.py']
    reg=dict(configs=CONFIGS,source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in fs},native_sha256=hashlib.sha256((ENGINE/'ns3/wsn-closed-loop').read_bytes()).hexdigest(),runtime_LLM_calls=0)
    t=ROOT/'results/contract_generalization_registration.json'
    if t.exists():assert json.loads(t.read_text())==reg,'registration drift'
    else:t.write_text(json.dumps(reg,indent=2)+'\n')
    print('REGISTERED',len(CONFIGS),flush=True)
    if a.register_only:return
    n=0;fail=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers)as pool:
        tasks={pool.submit(execute,c):c for c in CONFIGS}
        for f in concurrent.futures.as_completed(tasks):
            try:r=f.result();n+=1;print('DONE',n,r['configuration'],r['audit']['status'],r['audit']['worst_source_service'],r['audit']['control_DATA_bytes'],flush=True)
            except BaseException:fail.append(dict(configuration=tasks[f],traceback=traceback.format_exc()));print('FAILED',tasks[f],flush=True)
    (ROOT/'results/contract_generalization_failures.json').write_text(json.dumps(fail,indent=2))
if __name__=='__main__':main()
