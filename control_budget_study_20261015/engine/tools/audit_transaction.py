"""Independent two-source guard and selected-only exploration ledger audit."""
import collections,json
from pathlib import Path

def audit_transaction(row,folder):
 steps=json.loads((folder/(row['id']+'.controller.json')).read_text())['steps']
 decisions={d['decision']:d for d in row['decisions']};attempts=[];credited=set();checks=0;blocked=collections.Counter()
 for s in steps:
  o=s['observation'];t=o['time_ns'];reports={r['node']:r for r in o['reports']};check=s.get('transaction_interruption_check');fb=s['feedback']
  if check is not None:
   checks+=1;d=decisions[check['decision']];fresh={f:r for f in (0,1)if(r:=reports.get(f))is not None and 0<=t-r['stamp_ns']<=8_000_000_000}
   proofs=[dict(source=f,version=r['version'],stamp_ns=r['stamp_ns'],received_ns=r['received_ns'])for f,r in sorted(fresh.items())]
   matched=len(fresh)==2 and all(fresh[f]['version']==d['reward_expected_versions'][f]and fresh[f]['stamp_ns']>=d['time_ns']for f in (0,1))
   assert check['source_proofs']==proofs and check['two_sources_match']==matched
   target=d['paths']or d.get('admission',{}).get('proposed_paths')
   missing={n for p in target or ()for n in p[1:-1]}&set(s['safety_assessment']['sustained_missing_relays'])
   assert check['target_missing_relays']==sorted(missing)
   if check['blocked_reason']:blocked[check['blocked_reason']]+=1
   if fb is not None and str(fb.get('missing_reason','')).startswith('safety_interrupt:'):
    assert matched and check['allowed']
    if check['reason']=='sustained_missing_current_relay':assert missing
    bucket=d.get('reward_bucket');earliest=(bucket+1)*5_000_000_000+5_200_000_000 if bucket is not None else d['time_ns']+15_200_000_000
    assert t>=earliest and check['reward_not_before_ns']==earliest
  if fb is not None and fb['reward']is not None:credited.add(fb['action'])
  d=s['decision']
  if d is not None and '_creditexplore_'in row['policy']:
   state=d['credit_exploration']
   if d['selection_phase']=='event_exploration':
    counts=collections.Counter(attempts);allowed=[a for a,v in enumerate(d['constraints']['available'])if v]
    eligible=[a for a in allowed if a not in credited and counts[a]<2]
    assert eligible;minimum=min(counts[a]for a in eligible)
    assert d['action']==min(a for a in eligible if counts[a]==minimum)
    attempts.append(d['action'])
   assert state==dict(cap=8,max_attempts_per_arm=2,attempts=attempts,qualified_actions=sorted(credited),scope='selected feedback only; censoring is not zero reward')
 assert len(attempts)<=8 and max(collections.Counter(attempts).values(),default=0)<=2
 return dict(status='passed',two_source_guard_checks=checks,guard_blocks=dict(blocked),event_exploration_attempts=len(attempts),selected_reward_actions=sorted(credited),censor_imputations=0,scope='received evidence and bounded exposure ledger; no end-to-end benefit guarantee')
