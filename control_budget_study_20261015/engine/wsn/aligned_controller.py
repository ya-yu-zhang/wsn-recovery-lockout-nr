"""Isolated aligned short-cohort feedback revision, with explicit censoring."""
from wsn.revision_controller import RevisionController
from wsn.aligned_feedback import VersionBucketCache
from wsn.feedback import BUCKET_NS

class AlignedController(RevisionController):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.reward_cache=VersionBucketCache();self.reward_waits=[]
 def cached_feedback(self,obs,reports):
  self.reward_cache.observe(obs);p=self.pending;t=obs['time_ns']
  if p is None:return None
  expected=p['reward_expected_versions'];target=p['paths']or p.get('admission',{}).get('proposed_paths');deadline=p['time_ns']+30_000_000_000
  reason=None;counts=[];proof=[];missing=[];timely=[];probs=None;reward=None
  if target is None:reason='no_proposal'
  elif not p.get('admitted_hold')and self.installation is not None and self.installation.closed and self.installation.outcome!='confirmed':reason='installation_unconfirmed'
  fresh={f:r for f in(0,1)if(r:=reports.get(f))is not None and 0<=t-r['stamp_ns']<=8_000_000_000 and r['version']==expected[f]}
  if reason is None and 'reward_bucket'not in p:
   if len(fresh)==2:
    anchors=[fresh[f]['epoch_first_bucket']for f in(0,1)]
    p['reward_bucket']=max((p['time_ns']+BUCKET_NS-1)//BUCKET_NS,*anchors)
    p['reward_confirmation']=[dict(source=f,version=expected[f],stamp_ns=fresh[f]['stamp_ns'],received_ns=fresh[f]['received_ns'],visible_ns=t,epoch_first_bucket=anchors[f])for f in(0,1)]
   else:reason='await_expected_source_versions'
  bucket=p.get('reward_bucket')
  if reason is None and bucket is not None:
   if t<(bucket+1)*BUCKET_NS+200_000_000:reason='await_closed_reward_bucket'
   else:
    counts,proof,missing=self.reward_cache.cohort(expected,bucket)
    if missing:reason='await_received_version_bucket'
    elif min(counts)<20:reason='insufficient_generation'
    else:
     timely=list(obs['timely_buckets'].get(str(bucket),[0,0]));probs=[n/d for n,d in zip(timely,counts)]
     if any(not 0<=v<=1 for v in probs):raise ValueError('inconsistent aligned feedback')
     reward=.75*sum(probs)/2+.25*min(probs)-.05*min(p['fe']/64,1)-.05*min(p['install_budget_bytes']/5994,1)
  terminal=reward is not None or reason in('no_proposal','installation_unconfirmed','insufficient_generation')or t>=deadline
  if not terminal:
   self.reward_waits.append(dict(decision=p['decision'],time_ns=t,reason=reason,expected_versions=list(expected),bucket=bucket,deadline_ns=deadline))
   return None
  start=bucket*BUCKET_NS if bucket is not None else p['time_ns'];end=start+BUCKET_NS if bucket is not None else start
  # Censored records never expose partial counts as a valid scored cohort.
  if reward is None:counts=[];timely=[];probs=None;start=p['time_ns'];end=start
  if reward is not None:
   self.last_pdr=sum(probs)/2
   if self.is_bandit and self.train_bandit:self.bandit.update(p['action'],p['context'],reward)
  row=dict(decision=p['decision'],action=p['action'],time_ns=t,cohort_start_ns=start,cohort_end_ns=end,planned_reward_bucket=bucket,offered=counts,timely=timely,probabilities=probs,reward=reward,missing_reason=reason if reward is None else None,updated_action=p['action']if reward is not None and self.is_bandit and self.train_bandit else None,inputs=[r for f in(0,1)if(r:=reports.get(f))is not None],charged_install_budget_bytes=p['install_budget_bytes'],feedback_protocol='version_aligned_one_bucket',expected_versions=list(expected),version_bucket_evidence=proof,missing_sources=missing,source_version_confirmation=p.get('reward_confirmation',[]),deadline_ns=deadline,minimum_offered_per_source=20,window_buckets=1,censored=reward is None)
  self.feedbacks.append(row);self.pending=None;return row
 def step(self,obs):
  reply,row=super().step(obs)
  if row['decision']is not None:
   p=row['decision'];reports={r['node']:r for r in obs['reports']}
   p['reward_expected_versions']=[reports[f]['version']for f in(0,1)]if p.get('admitted_hold')else[p['decision']]*2
  wait=next((w for w in reversed(self.reward_waits)if w['time_ns']==obs['time_ns']),None)
  row['reward_wait']=wait
  return reply,row
