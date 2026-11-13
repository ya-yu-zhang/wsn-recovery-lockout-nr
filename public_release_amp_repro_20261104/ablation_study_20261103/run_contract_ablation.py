"""Paired confirmation-contract ablation; registration frozen before execution."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,json,os,traceback,sys
from run_study import ROOT,ENGINE,source_hashes
from fast_native_run import one
from run_mechanisms import policy
from contract_ablation import FACTORIES
from audit_case import audit

STAGES={
 'adverse':[dict(topology='budget_10_2026101501',scenario='multi_failure',seed=2026101511,model=m,contract=k)for m in('full_v2','horizon','cohort','closing')for k in('joint','post_exit')],
 'matrix':[dict(topology=f'budget_{n}_2026101501',scenario=s,seed=sd,model=m,contract=k)for n in(10,20)for s in('multi_failure','overload')for sd in(2026101511,2026101512)for m in('full_v2','horizon')for k in('joint','post_exit')],
}
def execute(c):
    key=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()[:20];folder=ROOT/'results/contract_ablation'/key;folder.mkdir(parents=True,exist_ok=True)
    if(folder/'case.json').exists():return json.loads((folder/'case.json').read_text())
    try:
        row=one(ENGINE/'ns3/wsn-closed-loop',c['scenario'],policy('resource10_on'),c['seed'],folder=folder,profile='local15_event',topology=c['topology'],extended=True,source_only=True,generation_stop=330,faults=[[65,2],[145,3],[225,6]]if c['scenario']=='multi_failure'else[],queue_discipline='fifo',epoch_certificate=True,report_retry=True,report_budget=True,report_retry_mode='always',controller_factory=FACTORIES[c['model']],controller_kwargs={'pacing':True,'evidence_gate':True,'contract':c['contract']},unified_budget=True,protect_evidence=True,version_pacing=True,report_phase_seed=c['seed'])
        row.update(configuration=c,configuration_key=key,evidence_directory=str(folder.relative_to(ROOT)))
        row['audit']=audit(row,folder);tmp=folder/'case.staging';tmp.write_text(json.dumps(row,indent=2)+'\n');tmp.replace(folder/'case.json');return row
    except BaseException:(folder/'FAILED_ATTEMPT.txt').write_text(traceback.format_exc());raise
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=STAGES,required=True);p.add_argument('--workers',type=int,default=2);p.add_argument('--register-only',action='store_true');a=p.parse_args();os.environ['TMPDIR']=str(ROOT/'build_tmp')
    fs=['contract_ablation.py','run_contract_ablation.py','horizon_controller.py','cadence_controller.py','budget_controller.py','fast_native_run.py']
    reg=dict(stage=a.stage,configs=STAGES[a.stage],source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in fs},native_sha256=hashlib.sha256((ENGINE/'ns3/wsn-closed-loop').read_bytes()).hexdigest(),
        primary_endpoint='recovery authorization after unconfirmed installation exit (post-exit checks with admitted recovery / installs issued)',
        secondary_endpoints=['worst_source_service','control_DATA_bytes'],decision_rule='Joint arm must reproduce the archived 40-case values for the same configuration before any PostExit contrast is interpreted; no criterion is changed after outcomes.',runtime_LLM_calls=0)
    t=ROOT/f'results/contract_ablation_{a.stage}_registration.json'
    if t.exists():assert json.loads(t.read_text())==reg,'registration drift'
    else:t.write_text(json.dumps(reg,indent=2)+'\n')
    print('REGISTERED',len(STAGES[a.stage]),flush=True)
    if a.register_only:return
    rows=[];fail=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers)as pool:
        tasks={pool.submit(execute,c):c for c in STAGES[a.stage]}
        for f in concurrent.futures.as_completed(tasks):
            try:r=f.result();rows.append(r);print('DONE',len(rows),r['configuration'],r['audit'].get('worst_source_service'),r['audit'].get('control_DATA_bytes'),flush=True)
            except BaseException:fail.append(dict(configuration=tasks[f],traceback=traceback.format_exc()));print('FAILED',tasks[f],flush=True)
    (ROOT/f'results/contract_ablation_{a.stage}_failures.json').write_text(json.dumps(fail,indent=2))
if __name__=='__main__':main()
