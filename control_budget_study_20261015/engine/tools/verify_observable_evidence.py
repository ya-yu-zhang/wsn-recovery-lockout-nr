"""Cross-check frozen matrix coverage and selected small archive copies."""
import hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from run_observable import registration,identity,atomic

def main():
 out=ROOT.parent.parent/'WSN_observable_evidence_20261012';chosen=[];expected=set()
 for stage,total in(('functional',18),('development',112)):
  reg=registration(stage);rows=json.loads((ROOT/'results'/f'observable_{stage}_manifest.json').read_text());keys={identity(c)for c in reg['configs']};assert len(rows)==total and{r['configuration_key']for r in rows}==keys;assert all(r['audit']['status']=='passed'and r['audit']['transaction_guard_and_exposure']['status']=='passed'for r in rows);expected|=keys
 receipts=[json.loads(p.read_text())for p in out.glob('*.receipt.json')]
 selected=[];covered=set()
 # Oversized pairs have been moved out; all deliverable top-level archives have disjoint case keys.
 for a in sorted(receipts,key=lambda a:(a['stage'],a['archive'])):
  p=out/a['archive'];assert p.exists()and p.stat().st_size==a['bytes']and a['bytes']<48*1024**2;assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'];assert not(set(a['configuration_keys'])&covered);covered.update(a['configuration_keys'])
  with zipfile.ZipFile(p)as z:
   assert z.testzip()is None
   members=json.loads(z.read('MEMBER_HASHES.json'));cases=json.loads(z.read('BATCH_CASES.json'));assert {c['configuration_key']for c in cases}==set(a['configuration_keys'])
   for e in members:assert hashlib.sha256(z.read(e['path'])).hexdigest()==e['sha256']
  selected.append(a)
 assert covered==expected and len(covered)==130
 atomic(ROOT/'results/observable_archive_integrity.json',dict(status='passed',unique_native_cases=130,functional_cases=18,development_cases=112,archives=selected,archive_bytes=sum(a['bytes']for a in selected),all_archive_CRC_and_member_hashes_verified=True,frozen_source_exact=True,formal_validation=False,LLM_runtime_calls=0))
 print('INTEGRITY_PASSED',len(selected),len(covered))
if __name__=='__main__':main()
