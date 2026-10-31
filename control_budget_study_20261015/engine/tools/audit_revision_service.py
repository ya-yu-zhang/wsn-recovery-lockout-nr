"""Independent offline check of controller service evidence; no policy feedback."""
import json
from pathlib import Path
from audit_closed_loop import read

def audit_service(row,folder):
 p=folder/row['id'];messages=[json.loads(x) for x in read(Path(str(p)+'.protocol.jsonl.gz')).decode().splitlines()]
 gen=[x for x in messages if x['kind']=='generated'];deliver=[x for x in messages if x['kind']=='delivered']
 steps=json.loads(Path(str(p)+'.controller.json').read_text())['steps'];known=0
 for step in steps:
  service=step['event'].get('settled_service',{})
  if not service.get('known'):continue
  known+=1;obs=step['observation'];t=obs['time_ns'];bs=service['buckets'];earliest=service['earliest_current_version_ns']
  assert all(b*5_000_000_000>=earliest and (b+1)*5_000_000_000+200_000_000<=t for b in bs)
  offered=[sum(x['flow']==f and x['time_ns']//5_000_000_000 in bs for x in gen) for f in (0,1)]
  timely=[sum(x['flow']==f and x['generated_ns']//5_000_000_000 in bs and x['time_ns']<=t and x['time_ns']-x['generated_ns']<=200_000_000 for x in deliver) for f in (0,1)]
  assert offered==service['offered'] and timely==service['timely'] and min(offered)>=20
  for f in (0,1):
   assert all(x['version']==service['version_by_source'][str(f)] for x in gen if x['flow']==f and x['time_ns']//5_000_000_000 in bs),'mixed-version service evidence'
  assert service['worst_timely']==min(n/d for n,d in zip(timely,offered))
  for proof in service['bucket_evidence']:
   assert (proof['bucket']+1)*5_000_000_000<=proof['stamp_ns']<=proof['received_ns']<=proof['visible_ns']<=t
 return {'status':'passed','known_service_snapshots':known,'service_evidence_independently_reconstructed':True}
