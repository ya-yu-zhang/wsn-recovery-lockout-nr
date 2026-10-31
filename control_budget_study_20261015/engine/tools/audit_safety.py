"""Independent reconstruction of legal safety triggers and control accounts."""
import collections,gzip,json
from pathlib import Path

def audit_safety(row,folder):
 p=folder/row['id'];messages=[json.loads(x)for x in gzip.open(str(p)+'.protocol.jsonl.gz','rt')]
 c=json.loads(Path(str(p)+'.controller.json').read_text());streak={};meters={};reservations=collections.Counter();allocations=[];interrupts=[];costs=[]
 phy=[x for x in messages if x['kind']=='phy_data'and x['flow']>=65000];packets={x['sequence']:x for x in messages if x['kind']=='install_packet'}
 installbytes=collections.Counter()
 for x in phy:
  if x['flow']==65001:installbytes[packets[x['sequence']]['decision']]+=x['bytes']
 for step in c['steps']:
  obs=step['observation'];t=obs['time_ns'];reports={r['node']:r for r in obs['reports']}
  assert set(obs)=={'time_ns','reports','sink_control_bytes','timely_buckets'},'unregistered online truth'
  for n,r in reports.items():meters[n]=max(meters.get(n,0),r['ctrl_bytes'])
  meters[9]=sum(x['bytes']for x in phy if x['node']==9 and x['time_ns']<=t)
  cost=step.get('cost_observation')
  if cost is not None:
   assert cost['meter_by_node']=={str(n):v for n,v in sorted(meters.items())}
   assert cost['observed_control_data_lower_bound']==sum(meters.values())<=sum(x['bytes']for x in phy if x['time_ns']<=t)
   costs.append(cost)
  safety=step.get('safety_assessment')
  if safety is not None:
   used={n for path in safety['current_paths']for n in path[1:-1]}
   active={n for n,r in reports.items()if t-r['stamp_ns']<=(8_000_000_000 if n<2 else 16_000_000_000)}|{9}
   missing=sorted(used-active)
   streak={n:streak.get(n,0)+1 for n in missing}
   sustained=[n for n in missing if streak[n]>=2]
   failed=[f for f in(0,1)if f in active and reports[f]['current_n']>=20 and reports[f]['current_failed']/reports[f]['current_n']>=.2]
   reason='sustained_missing_current_relay'if sustained else'current_version_source_failure'if failed else None
   assert safety['missing_relays']==missing and safety['sustained_missing_relays']==sustained
   assert safety['missing_streak']=={str(n):v for n,v in sorted(streak.items())}and safety['failure_sources']==failed and safety['reason']==reason
  fb=step['feedback']
  if fb is not None and str(fb.get('missing_reason','')).startswith('safety_interrupt:'):
   d=next(d for d in row['decisions']if d['decision']==fb['decision'])
   assert '_interrupt_'in row['policy']and fb['reward']is None and fb['updated_action']is None and fb['offered']==[]
   assert t>=d['time_ns']+5_000_000_000 and t<row['action_stop_ns']
   assert all(f in active for f in(0,1))and safety['reason']is not None and fb['safety_evidence']==safety
   if safety['reason']=='current_version_source_failure':assert any(reports[f]['version']==fb['expected_versions'][f]and reports[f]['stamp_ns']>=d['time_ns']for f in failed)
   interrupts.append(dict(time_ns=t,decision=fb['decision'],reason=fb['missing_reason'],evidence=safety))
  d=step['decision']
  if d is not None and d.get('install_reservation'):
   allocation=d['install_reservation'];w=t//20_000_000_000
   assert allocation==dict(decision=d['decision'],time_ns=t,window=w,used_before=reservations[w],reservation_bytes=5994,budget_enabled='_installbudget_'in row['policy'])
   if allocation['budget_enabled']:assert reservations[w]<1
   reservations[w]+=1;allocations.append(allocation)
   assert installbytes[d['decision']]<=5994
 assert costs==row['cost_observations']==c['cost_observations']
 assert interrupts==json.loads(json.dumps(row['safety_events']))==c['safety_events']
 assert allocations==row['install_reservations']==c['install_reservations']
 return dict(status='passed',safety_interrupts=len(interrupts),install_allocations=len(allocations),reserved_install_DATA_bound_bytes=5994*len(allocations),actual_install_DATA_bytes=sum(installbytes.values()),observable_cost_snapshots=len(costs),online_truth_leakage=False,scope='prepaid install DATA and separately metered received-control lower bound; no total traffic savings guarantee')
