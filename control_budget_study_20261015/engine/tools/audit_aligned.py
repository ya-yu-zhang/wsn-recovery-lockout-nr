"""Independent received-provenance, route attribution and reservation audit."""
import collections,csv,gzip,json
from pathlib import Path

def audit_aligned(row,folder):
 prefix=folder/row['id'];messages=[json.loads(s)for s in gzip.open(str(prefix)+'.protocol.jsonl.gz','rt')]
 c=json.loads(Path(str(prefix)+'.controller.json').read_text());decisions={d['decision']:d for d in row['decisions']};visible={};valid=0;censored=0
 generated=[x for x in messages if x['kind']=='generated'];delivered=[x for x in messages if x['kind']=='delivered']
 for step in c['steps']:
  obs=step['observation'];t=obs['time_ns'];visible={k:p for k,p in visible.items()if(k[2]+1)*5_000_000_000>=t-60_000_000_000}
  for rr in obs['reports']:
   if rr['node']not in(0,1):continue
   anchor=rr['epoch_first_bucket']
   for bucket,n in rr['buckets']:
    if bucket==2**32-1 or bucket<anchor or(bucket+1)*5_000_000_000>rr['stamp_ns']or(bucket+1)*5_000_000_000<t-60_000_000_000:continue
    key=rr['node'],rr['version'],bucket
    if key not in visible:visible[key]=dict(source=rr['node'],version=rr['version'],epoch_first_bucket=anchor,bucket=bucket,count=n,stamp_ns=rr['stamp_ns'],received_ns=rr['received_ns'],visible_ns=t)
  fb=step['feedback']
  if fb is None or fb.get('feedback_protocol')!='version_aligned_one_bucket':continue
  d=decisions[fb['decision']];assert fb['deadline_ns']==d['time_ns']+30_000_000_000
  if fb['reward']is None:
   censored+=1;assert fb['censored']and fb['offered']==[]and fb['updated_action']is None
   assert fb['missing_reason'];continue
  valid+=1;assert not fb['censored'];start=fb['cohort_start_ns'];end=fb['cohort_end_ns'];b=start//5_000_000_000
  assert start>=d['time_ns']and end-start==5_000_000_000 and end+200_000_000<=t
  confirmations=fb['source_version_confirmation'];expected=fb['expected_versions'];assert len(confirmations)==2
  for f,proof in enumerate(confirmations):
   assert proof['source']==f and proof['version']==expected[f]
   assert proof['stamp_ns']<=proof['received_ns']<=proof['visible_ns']<=t and proof['visible_ns']-proof['stamp_ns']<=8_000_000_000
   assert start>=proof['epoch_first_bucket']*5_000_000_000
   # Confirm that this precise received snapshot was exposed at its claimed step.
   snapshot=next(s['observation']for s in c['steps']if s['observation']['time_ns']==proof['visible_ns'])
   assert any(r['node']==f and r['version']==proof['version']and r['stamp_ns']==proof['stamp_ns']and r['received_ns']==proof['received_ns']and r['epoch_first_bucket']==proof['epoch_first_bucket']for r in snapshot['reports'])
  expected_proofs=[visible[f,expected[f],b]for f in(0,1)];assert expected_proofs==fb['version_bucket_evidence']
  target=d['paths']or d['admission']['proposed_paths']
  cohort=[g for g in generated if start<=g['time_ns']<end]
  for f in(0,1):
   gs=[g for g in cohort if g['flow']==f];assert len(gs)==fb['offered'][f]>=20
   assert all(g['version']==expected[f]and g['path']==list(target[f])for g in gs),'mixed-route/version reward'
   n=sum(x['flow']==f and start<=x['generated_ns']<end and x['time_ns']<=t and x['time_ns']-x['generated_ns']<=200_000_000 for x in delivered)
   assert n==fb['timely'][f]
  probabilities=[n/d for n,d in zip(fb['timely'],fb['offered'])]
  reward=.75*sum(probabilities)/2+.25*min(probabilities)-.05*min(d['fe']/64,1)-.05*min(d['install_budget_bytes']/5994,1)
  assert fb['reward']==reward
 with gzip.open(str(prefix)+'.jobs.csv.gz','rt')as f:jobs={(int(j['node']),int(j['flow']),int(j['sequence'])):j for j in csv.DictReader(f)}
 packets={x['sequence']:x for x in messages if x['kind']=='report_packet'};logical=collections.Counter();reservations=collections.Counter();admitted=0;rejected=0
 for i,x in enumerate(messages):
  if x['kind']=='queue_terminal'and x['flow']==65000 and row['report_retry']and row['report_budget']:
   j=jobs[x['node'],65000,x['sequence']];meta=packets[x['sequence']];stamp=meta.get('stamp_ns',meta['time_ns']);key=meta['source'],stamp,x['node']
   delay=20_000_000+((x['sequence']*2654435761+x['node'])%40)*1_000_000
   eligible=int(j['status'])!=0 and meta['source']<2 and x['time_ns']+delay<=stamp+3_000_000_000 and logical[key]<1
   if eligible:
    offset=1
    if 'report_retry_mode'in row:
     classification=messages[i+1]
     assert classification['kind']=='report_retry_classified'and classification['parent_sequence']==x['sequence']and classification['node']==x['node']
     assert classification['time_ns']==x['time_ns']and classification['source']==meta['source']and classification['stamp_ns']==stamp
     if not classification['admitted']:continue
     offset=2
    nxt=messages[i+offset];assert nxt['kind']=='report_budget_admission'and nxt['parent_sequence']==x['sequence']and nxt['node']==x['node']
  elif x['kind']=='report_budget_admission':
   assert row['report_budget']and x['window']==x['time_ns']//20_000_000_000 and x['reservation_bytes']==1143
   key=x['node'],x['window'];assert x['used_before']==reservations[key]
   assert x['admitted']==(reservations[key]<1)
   if x['admitted']:
    reservations[key]+=1;admitted+=1;nxt=messages[i+1];assert nxt['kind']=='report_retry_scheduled'and nxt['parent_sequence']==x['parent_sequence']and nxt['node']==x['node']
   else:rejected+=1
  elif x['kind']=='report_retry_scheduled':logical[x['source'],x['stamp_ns'],x['node']]+=1
 if row['report_budget']:
  assert admitted==sum(x['kind']=='report_retry_scheduled'for x in messages)
  assert row['audit']['report_recovery']['extra_report_data_bytes']<=admitted*1143
 return dict(status='passed',valid_aligned_rewards=valid,censored_aligned_rewards=censored,mixed_route_reward_packets=0 if '_aligned_'in row['policy']else None,reservations_admitted=admitted,reservations_rejected=rejected,reserved_extra_data_bound_bytes=admitted*1143,scope='DATA reservation only; excludes ACK, energy and service guarantees')
