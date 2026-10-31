import collections,gzip,json,csv
from pathlib import Path
def audit_report_recovery(row,folder):
 p=folder/row['id'];messages=[json.loads(s)for s in gzip.open(str(p)+'.protocol.jsonl.gz','rt')]
 with gzip.open(str(p)+'.jobs.csv.gz','rt')as f:jobs={(int(j['node']),int(j['flow']),int(j['sequence'])):j for j in csv.DictReader(f)}
 reports={(x['report']['node'],x['report']['stamp_ns']):x['report']for x in messages if x['kind']=='report_generated'}
 schedules=[x for x in messages if x['kind']=='report_retry_scheduled'];packets={x['sequence']:x for x in messages if x['kind']=='report_packet'}
 budgets=collections.Counter();extra=0
 for s in schedules:
  assert row['report_retry']and s['source']<2
  key=(s['source'],s['stamp_ns'],s['node']);budgets[key]+=1;assert budgets[key]<=1
  parent=jobs[s['node'],65000,s['parent_sequence']]
  assert int(parent['status'])==s['status']!=0 and int(parent['request_ns'])+int(parent['J_ns'])==s['time_ns']
  delay=20_000_000+((s['parent_sequence']*2654435761+s['node'])%40)*1_000_000
  assert s['dispatch_ns']==s['time_ns']+delay<=s['deadline_ns']==s['stamp_ns']+3_000_000_000
  original=reports[s['source'],s['stamp_ns']];assert original['version']==s['version']
  packet=packets[s['sequence']];assert packet['retry']and packet['source']==s['source']and packet['stamp_ns']==s['stamp_ns']and packet['time_ns']==s['dispatch_ns']and packet['body_bytes']==80
  extra+=sum(x['bytes']for x in messages if x['kind']=='phy_data'and x['flow']==65000 and x['sequence']==s['sequence'])
 # Retries may be forwarded across remaining hops, each with up to three PHY
 # attempts. Bound each allocated retry packet by its actual possible suffix.
 assert extra<=len(schedules)*3*3*127
 assert sum(bool(x.get('retry'))for x in packets.values())==len(schedules)
 return dict(status='passed',report_retry_schedules=len(schedules),extra_report_data_bytes=extra,
             conservative_extra_data_bound_bytes=len(schedules)*3*3*127,
             dispatch_deadline_and_local_failure_independently_verified=True)
