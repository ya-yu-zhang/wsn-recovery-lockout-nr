"""Transaction-qualified interruption and bounded feedback-aware exploration.

Neither missing reports nor censored feedback are imputed as route outcomes.
The old SafetyController is retained as an explicitly matched ablation.
"""
from collections import Counter
from wsn.safety_controller import SafetyController
from wsn.feedback import BUCKET_NS

class TransactionController(SafetyController):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  self.transaction_guard='_txguard_'in self.policy
  self.credit_exploration='_creditexplore_'in self.policy
  if self.credit_exploration:self.exploration_cap=8
  self.interruption_checks=[];self.last_interruption_check=None

 def exploration_candidates(self,allowed,attempts):
  if not self.credit_exploration or attempts is None:
   return super().exploration_candidates(allowed,attempts)
  counts=Counter(attempts)
  credited={f['action']for f in self.feedbacks if f['reward']is not None}
  eligible=[a for a in allowed if a not in credited and counts[a]<2]
  if not eligible:return []
  minimum=min(counts[a]for a in eligible)
  return [a for a in eligible if counts[a]==minimum]

 def interrupt_feedback(self,obs,evidence):
  if not self.transaction_guard:return super().interrupt_feedback(obs,evidence)
  self.last_interruption_check=None
  p=self.pending;t=obs['time_ns']
  if not self.enable_interrupt or p is None or evidence['reason']is None:
   return None
  reports={r['node']:r for r in obs['reports']}
  fresh={f:r for f in (0,1)if(r:=reports.get(f))is not None and 0<=t-r['stamp_ns']<=8_000_000_000}
  proofs=[dict(source=f,version=r['version'],stamp_ns=r['stamp_ns'],received_ns=r['received_ns'])for f,r in sorted(fresh.items())]
  matched=len(fresh)==2 and all(fresh[f]['version']==p['reward_expected_versions'][f]and fresh[f]['stamp_ns']>=p['time_ns']for f in (0,1))
  target=p['paths']or p.get('admission',{}).get('proposed_paths')
  target_missing={n for path in target or ()for n in path[1:-1]}&set(evidence['sustained_missing_relays'])
  check=dict(decision=p['decision'],time_ns=t,expected_versions=list(p['reward_expected_versions']),source_proofs=proofs,two_sources_match=matched,target_missing_relays=sorted(target_missing),reason=evidence['reason'],allowed=False,blocked_reason=None,reward_not_before_ns=None)
  self.last_interruption_check=check;self.interruption_checks.append(check)
  if not matched:check['blocked_reason']='await_two_matching_sources';return None
  if evidence['reason']=='sustained_missing_current_relay'and not target_missing:
   check['blocked_reason']='missing_relay_not_in_target';return None
  # Let qualified credit settle and travel through one further source report
  # period. The grace does not assert that a report will actually arrive.
  fb=self.cached_feedback(obs,reports)
  if fb is not None:check['blocked_reason']='qualified_feedback_closed';return fb
  bucket=p.get('reward_bucket')
  earliest=(bucket+1)*BUCKET_NS+5_200_000_000 if bucket is not None else p['time_ns']+15_200_000_000
  check['reward_not_before_ns']=earliest
  if t<earliest:check['blocked_reason']='settled_credit_delivery_grace';return None
  check['allowed']=True
  return super().interrupt_feedback(obs,evidence)

 def step(self,obs):
  reply,row=super().step(obs)
  row['transaction_interruption_check']=self.last_interruption_check
  d=row['decision']
  if d is not None and self.credit_exploration:
   d['credit_exploration']=dict(cap=8,max_attempts_per_arm=2,attempts=list(self.event_attempts),qualified_actions=sorted({f['action']for f in self.feedbacks if f['reward']is not None}),scope='selected feedback only; censoring is not zero reward')
  return reply,row
