"""Independent reconstruction of queued packets, bounded overtaking and age."""
import collections,json
from pathlib import Path
from audit_closed_loop import read
def audit_epoch(row,folder):
 messages=[json.loads(x)for x in read(folder/(row['id']+'.protocol.jsonl.gz')).decode().splitlines()]
 queues=collections.defaultdict(list);credit=collections.defaultdict(lambda:4);active={};accepted=0;requests=0;bypasses=0
 generated={};ages=[];source_ages=[];drops=0
 for x in messages:
  kind=x['kind'];n=x.get('node');t=x['time_ns']
  if kind=='report_packet':generated[x['sequence']]=x
  elif kind=='queue_arrival':
   if x['accepted']:
    assert len(queues[n])+int(n in active)<16
    queues[n].append(x);accepted+=1
   else:drops+=1
  elif kind=='queue_choice':
   q=queues[n];assert n not in active and len(q)==x['queued_before']
   expected=0
   if row['queue_discipline']=='bounded_age' and credit[n]>=4:
    for i,p in enumerate(q):
     if p['flow']==65000:
      if t-p['generated_ns']>=1_000_000_000:expected=i
      break
   assert x['selected_index']==expected,'queue policy mismatch'
   p=q.pop(expected);assert (p['flow'],p['sequence'])==(x['flow'],x['sequence'])
   credit[n]=0 if p['flow']==65000 else credit[n]+1
   assert credit[n]==x['nonreports_after'];active[n]=(p['flow'],p['sequence']);requests+=1;bypasses+=expected>0
  elif kind=='queue_terminal':
   assert active[n]==(x['flow'],x['sequence']);del active[n]
  elif kind=='queue_purge':
   p=queues[n].pop(0);assert (p['flow'],p['sequence'])==(x['flow'],x['sequence'])
  elif kind=='report_received':
   age=t-x['report']['stamp_ns'];assert age>=0;ages.append(age)
   if x['report']['node']<2:source_ages.append(age)
 assert requests==row['native']['finalized_jobs'] and not active
 return dict(status='passed',queue_requests=requests,accepted=accepted,drops=drops,bypasses=bypasses,
             report_receipts=len(ages),source_report_receipts=len(source_ages),
             fresh_source_report_receipts=sum(a<=8_000_000_000 for a in source_ages),
             maximum_source_receipt_age_ns=max(source_ages,default=None),
             mean_source_receipt_age_ns=sum(source_ages)/len(source_ages)if source_ages else None,
             independent_queue_policy_verified=True)
