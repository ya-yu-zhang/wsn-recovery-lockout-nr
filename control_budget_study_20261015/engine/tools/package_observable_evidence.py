import json,subprocess,time
from pathlib import Path
root=Path('wsn_paper/observable_control_study_20261012');out=Path('WSN_observable_evidence_20261012')
def package(stage,first,last):
 p=subprocess.run(['python3',str(root/'tools/checkpoint_observable.py'),'--stage',stage,'--first',str(first),'--last',str(last)],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr)
 return json.loads(p.stdout)
for stage,total in [('functional',18),('development',112)]:
 reg=json.loads((root/'docs'/f'observable_{stage}_registration.json').read_text())
 for first in range(0,total,2):
  keys=['_'.join(str(c[k])for k in('topology','scenario','model','profile','seed'))for c in reg['configs'][first:first+2]]
  while True:
   manifest=root/'results'/f'observable_{stage}_manifest.json';rows=json.loads(manifest.read_text())if manifest.exists()else[]
   if set(keys)<={r['configuration_key']for r in rows}:break
   time.sleep(2)
  receipt=package(stage,first,first+2)
  if receipt['bytes']>=48*1024**2:
   oversized=out/'oversized_not_for_delivery';oversized.mkdir(exist_ok=True)
   (out/receipt['archive']).replace(oversized/receipt['archive']);rp=(out/receipt['archive']).with_suffix('.receipt.json');rp.replace(oversized/rp.name)
   for k in(first,first+1):
    r=package(stage,k,k+1);assert r['bytes']<48*1024**2,'individual case needs split-member packaging'
    print(json.dumps(dict(archive=r['archive'],cases=r['cases'],bytes=r['bytes'])),flush=True)
  else:print(json.dumps(dict(archive=receipt['archive'],cases=receipt['cases'],bytes=receipt['bytes'])),flush=True)
print('PACKAGING_COMPLETE',flush=True)
