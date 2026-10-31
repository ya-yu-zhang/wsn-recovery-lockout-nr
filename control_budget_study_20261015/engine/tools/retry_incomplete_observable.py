"""Replace incomplete native evidence without changing registered treatments."""
import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from run_observable import registration,identity,execute,atomic

def main():
    reg=registration('development');binary=ROOT/'ns3/wsn-closed-loop';assert binary.is_file()
    source=hashlib.sha256((ROOT/'ns3/wsn-closed-loop.cc').read_bytes()).hexdigest()
    assert source==reg['source_sha256']['ns3/wsn-closed-loop.cc']
    failures=json.loads((ROOT/'results/observable_development_failures.json').read_text())
    cfgs=[]
    for f in failures:
        if f['configuration']not in cfgs:cfgs.append(f['configuration'])
    path=ROOT/'results/observable_reexecution_cases.json';done=json.loads(path.read_text())if path.exists()else[]
    attempts=[]
    for cfg in cfgs:
        key=identity(cfg)
        if any(r['configuration_key']==key for r in done):continue
        start=time.time()
        r=execute((cfg,str(binary),'development'));done.append(r);atomic(path,done)
        attempts.append(dict(configuration_key=key,replacement_evidence_directory=r['evidence_directory'],audit_status=r['audit']['status'],wall_seconds=time.time()-start))
        atomic(ROOT/'results/observable_reexecution_receipt.json',dict(reason='retained native trace was truncated and failed parsing before audit',configuration_and_policy_unchanged=True,
              original_failed_attempts_preserved=True,source_registration_commit='ae942dbb7dc79adcbbd6a5822e166c055bdac16c',
              driver_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),additional_independent_replicates=0,attempts=attempts))
        print('REEXECUTION_AUDITED',key,flush=True)
if __name__=='__main__':main()
