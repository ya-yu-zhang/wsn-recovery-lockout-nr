"""Four independent functional cases, never used as development replications."""
import json
from run_closed_loop import ROOT,compile_driver,one
from run_development import source_hashes,policy
from audit_closed_loop import audit_case

def main():
    folder=ROOT/'results/functional'
    if folder.exists():raise ValueError('functional outputs already exist')
    configs=[dict(scenario='overload',policy=policy('full',protocol),seed=983010,source_only=True,generation_stop=90,faults=[]) for protocol in ('baseline20','grace5')]
    configs.extend([dict(scenario='failure',policy=policy('full','grace5'),seed=983011,source_only=True,generation_stop=90,faults=[[35,2]],reject=True),dict(scenario='steady',policy=policy('full','grace5'),seed=983012,source_only=True,generation_stop=90,faults=[],missing=True)])
    (ROOT/'docs/functional_registration.json').write_text(json.dumps(dict(configs=configs,source_sha256=source_hashes(),functional_only=True),indent=2))
    binary=compile_driver();rows=[];audits=[]
    for cfg in configs:
        row=one(binary,folder=folder,profile='hybrid5_10',extended=True,**cfg);audits.append(audit_case(row,folder));rows.append(row)
        print('functional audited',len(rows),'/4',cfg['scenario'],flush=True)
    assert rows[-1]['bandit_updates']==[0]*4 and all(f['reward'] is None for f in rows[-1]['feedbacks'])
    (ROOT/'results/functional_manifest.json').write_text(json.dumps(rows,indent=2));(ROOT/'results/functional_audit.json').write_text(json.dumps(dict(status='passed',cases=audits),indent=2))

if __name__=='__main__':main()
