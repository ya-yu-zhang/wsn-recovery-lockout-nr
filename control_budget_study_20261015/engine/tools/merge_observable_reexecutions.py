"""Complete canonical coverage after the original executor has stopped."""
import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from run_observable import registration,identity,atomic

def main():
    reg=registration('development');p=ROOT/'results/observable_development_manifest.json'
    rows=json.loads(p.read_text());replacement=json.loads((ROOT/'results/observable_reexecution_cases.json').read_text())
    expected={identity(c)for c in reg['configs']};by={r['configuration_key']:r for r in rows}
    checks=[]
    for r in replacement:
        key=r['configuration_key'];assert key not in by and r['audit']['status']=='passed'
        originals=[f.parent for f in(ROOT/'results/development').glob(key+'_*/FAILED_ATTEMPT.txt')]
        assert originals
        summaries=[]
        for folder in originals:
            native=folder/(r['id']+'.json');old=json.loads(native.read_text());assert old==r['native'],'replacement native summary differs'
            summaries.append(dict(directory=str(folder.relative_to(ROOT)),native_summary_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),summary_equal_to_replacement=True))
        by[key]=r;checks.append(dict(configuration_key=key,replacement_directory=r['evidence_directory'],retained_original_attempts=summaries))
    assert set(by)==expected and len(by)==112
    backup=p.with_name('observable_development_before_reexecution_merge.json')
    assert not backup.exists();shutil.copy2(p,backup)
    atomic(p,[by[k]for k in sorted(by)])
    atomic(ROOT/'results/observable_completion_receipt.json',dict(status='complete',unique_development_configs=112,original_audited=len(rows),reexecuted_configs=len(replacement),
           added_independent_replicates=0,failed_original_attempts_preserved=True,native_summaries_equal=True,reexecution_checks=checks,
           source_registration_commit='ae942dbb7dc79adcbbd6a5822e166c055bdac16c',LLM_runtime_calls=0))
    print('CANONICAL_COMPLETE',len(by),'REPLACEMENTS',len(replacement))
if __name__=='__main__':main()
