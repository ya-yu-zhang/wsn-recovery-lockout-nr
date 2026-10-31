"""Atomic raw-evidence packages; excluded from the frozen policy source set."""
import argparse, fcntl, hashlib, io, json, os, uuid, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=('functional','development'),required=True)
 p.add_argument('--first',type=int,required=True);p.add_argument('--last',type=int,required=True);a=p.parse_args()
 reg=json.loads((ROOT/'docs'/f'observable_{a.stage}_registration.json').read_text())
 rows=json.loads((ROOT/'results'/f'observable_{a.stage}_manifest.json').read_text());by={r['configuration_key']:r for r in rows}
 def key(c):return '_'.join(str(c[k])for k in ('topology','scenario','model','profile','seed'))
 keys=[key(c)for c in reg['configs'][a.first:a.last]];chosen=[by[k]for k in keys];assert chosen
 out=ROOT.parent.parent/'WSN_observable_evidence_20261012';out.mkdir(exist_ok=True)
 archive=out/f'WSN_observable_{a.stage}_20261012_{a.first+1:03d}_{a.last:03d}.zip';receipt=archive.with_suffix('.receipt.json')
 with (out/(archive.name+'.lock')).open('ab')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if archive.exists():
   saved=json.loads(receipt.read_text());assert saved['configuration_keys']==keys
   assert hashlib.sha256(archive.read_bytes()).hexdigest()==saved['sha256']
   with zipfile.ZipFile(archive)as z:assert z.testzip()is None
   print(json.dumps(saved));return
  building=out/('.archive-'+uuid.uuid4().hex+'.zip');entries=[];buffer=io.BytesIO()
  files=[p for r in chosen for p in (ROOT/r['evidence_directory']).glob('*')if p.is_file()]+[ROOT/'docs'/f'observable_{a.stage}_registration.json']
  with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
   for path in files:
    name=str(path.relative_to(ROOT));z.write(path,name)
    entries.append(dict(path=name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
   z.writestr('MEMBER_HASHES.json',json.dumps(entries,indent=2));z.writestr('BATCH_CASES.json',json.dumps(chosen,indent=2))
   z.writestr('README.txt','Observable-control development experiment: selected-only UCB, bounded unconfirmed installation and local ordinary-report coalescing. Full native traces, controller observations, input streams, audit and pre-execution registration. Not held-out validation or deployment. No LLM runtime inference.\n')
  payload=buffer.getvalue()
  with building.open('wb')as handle:handle.write(payload);handle.flush();os.fsync(handle.fileno())
  assert building.read_bytes()==payload,'archive byte persistence mismatch'
  with zipfile.ZipFile(io.BytesIO(payload))as z:
   assert z.testzip()is None
   for e in entries:assert hashlib.sha256(z.read(e['path'])).hexdigest()==e['sha256']
  with building.open('rb')as handle:os.fsync(handle.fileno())
  saved=dict(archive=archive.name,stage=a.stage,cases=len(chosen),configuration_keys=keys,
             bytes=building.stat().st_size,sha256=hashlib.sha256(building.read_bytes()).hexdigest(),
             mac_jobs=sum(r['audit']['mac_jobs']for r in chosen),CRC_and_member_hashes_verified=True,
             atomic_archive_publication=True,formal_validation=False,LLM_runtime_calls=0)
  os.replace(building,archive);temporary=receipt.with_suffix('.partial');temporary.write_text(json.dumps(saved,indent=2)+'\n');os.replace(temporary,receipt)
  print(json.dumps(saved))


if __name__=='__main__':main()
