"""Registered phase16 feedback-protocol development study; not formal testing."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse,hashlib,json,os
from run_closed_loop import ROOT,compile_driver,one
from audit_closed_loop import audit_case

PREFIX='linucb_event_scalar4_failure_current_'
MODELS=('full','random','intercept','frozen')

def policy(model,protocol):
    if model not in MODELS or protocol not in ('baseline20','grace5'):raise ValueError('invalid method')
    return PREFIX+(model+'_' if model!='full' else '')+('grace5_' if protocol=='grace5' else '')+'retry_mask'

def configurations():
    return [dict(group='feedback',method=protocol+'_'+model,model=model,protocol=protocol,scenario=scenario,seed=seed,
                 policy=policy(model,protocol),source_only=True,topology='base',generation_stop=330,
                 faults=[[65,2],[145,3],[225,6]] if scenario=='multi_failure' else [])
            for scenario in ('multi_failure','overload') for seed in (983201,983202)
            for protocol in ('baseline20','grace5') for model in MODELS]

def source_hashes():
    files=list(ROOT.glob('*.py'))+list((ROOT/'wsn').glob('*.py'))+list((ROOT/'ns3').glob('*.cc'))+list((ROOT/'ns3').glob('*.h'))+list((ROOT/'tests').glob('*.py'))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}

def identity(row):return row['study_group'],row['method'],row['scenario'],row['topology'],row['seed']

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--resume',action='store_true');p.add_argument('--replay-only',action='store_true');p.add_argument('--register-only',action='store_true');a=p.parse_args()
    folder=ROOT/'results/development';manifest=ROOT/'results/development_manifest.json';registration=ROOT/'docs/development_registration.json'
    configs=configurations();total=len(configs)
    if a.replay_only:
        registered=json.loads(registration.read_text());assert registered['source_sha256']==source_hashes() and registered['configs']==configs
        rows=json.loads(manifest.read_text());assert len(rows)==total
        for row in rows:audit_case(row,folder)
        print(f'all{total} native records replayed',flush=True);return
    if a.resume:
        registered=json.loads(registration.read_text());assert registered['configs']==configs and registered['source_sha256']==source_hashes()
        rows=json.loads(manifest.read_text()) if manifest.exists() else []
        for row in rows:audit_case(row,folder)
    else:
        if folder.exists() or registration.exists():raise ValueError('outputs/registration exist; use --resume or a fresh copy')
        registration.write_text(json.dumps(dict(stage='phase16_development',formal_matrix=False,configs=configs,source_sha256=source_hashes(),
            primary_metric='worst_party_timely',mechanism_metrics=['valid_feedback','missing_feedback','extra_wait_seconds','observed_event_ticks_blocked'],
            secondary_metrics=['mean_timely','control_DATA_bytes','report_DATA_bytes','FE','model_choices_after_feedback'],
            intervention='Closed actually received generation-bucket cache + at most one5s feedback grace. No added reports, retries, features or objective penalties.',
            parent_diagnosis='Parent66 learning missing; cache-only recovery0; original-trajectory coverage after5s44/66, not intervention results.',
            design_limit='base known10-node geometry, two new offered streams per scenario, descriptive development only'),indent=2));rows=[]
    if a.register_only:print(f'registered{total} cases before native generation',flush=True);return
    binary=compile_driver();completed={identity(r) for r in rows}
    pending=[c for c in configs if (c['group'],c['method'],c['scenario'],c['topology'],c['seed']) not in completed]
    def execute(cfg):
        kwargs={k:v for k,v in cfg.items() if k not in ('group','method','model','protocol')}
        row=one(binary,folder=folder,profile='hybrid5_10',extended=True,**kwargs)
        row.update(study_group=cfg['group'],method=cfg['method'],model=cfg['model'],protocol=cfg['protocol'])
        audit=audit_case(row,folder)
        return row,audit
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(execute,c) for c in pending]
        for future in as_completed(futures):
            row,audit=future.result();rows.append(row);rows.sort(key=lambda r:r['id'])
            temp=manifest.with_suffix('.json.partial');temp.write_text(json.dumps(rows,indent=2));os.replace(temp,manifest)
            print('audited',len(rows),'/',total,row['scenario'],row['method'],'jobs',audit['mac_jobs'],flush=True)
    assert len(rows)==total and len({identity(r) for r in rows})==total
    print(f'development native matrix completed{total}',flush=True)

if __name__=='__main__':main()
