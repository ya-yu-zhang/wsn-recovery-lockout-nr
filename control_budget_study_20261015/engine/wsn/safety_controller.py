"""Received-evidence safety interruptions and prepaid install transactions.

All safety inputs are received snapshots; the meter is a delayed lower bound.
No refund or release is made for a failed/partly applied install transaction.
"""
from wsn.aligned_controller import AlignedController
from wsn.feedback import BUCKET_NS

WINDOW=20_000_000_000
INSTALL_RESERVATION=5994

class SafetyController(AlignedController):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  self.enable_interrupt='_interrupt_'in self.policy
  self.enable_install_budget='_installbudget_'in self.policy
  self.reservations={};self.install_reservations=[];self.safety_events=[]
  self.meters={};self.cost_observations=[];self.missing_streak={};self.safety_evidence=None

 def observe_cost(self,obs):
  t=obs['time_ns']
  for r in obs['reports']:
   if not r['stamp_ns']<=r['received_ns']<=t:raise ValueError('future cost report')
   n=r['node'];v=r['ctrl_bytes']
   if v<0:raise ValueError('negative reported meter')
   self.meters[n]=max(v,self.meters.get(n,0))
  sink=obs.get('sink_control_bytes',0)
  if sink<self.meters.get(9,0):raise ValueError('sink meter moved backwards')
  self.meters[9]=sink
  row=dict(time_ns=t,observed_control_data_lower_bound=sum(self.meters.values()),meter_by_node={str(n):v for n,v in sorted(self.meters.items())},scope='received cumulative control DATA plus sink-local control DATA; stale nodes remain lower bounds; excludes ACK and energy')
  self.cost_observations.append(row);return row

 def assess_safety(self,obs):
  reports,fresh,active,x,event=self.view(obs);t=obs['time_ns']
  used={n for path in self.current for n in path[1:-1]};missing=sorted(used-active)
  for n in list(self.missing_streak):
   if n not in missing:self.missing_streak.pop(n)
  for n in missing:self.missing_streak[n]=self.missing_streak.get(n,0)+1
  sustained=[n for n in missing if self.missing_streak[n]>=2]
  failed=[int(f)for f,d in event['source_failure_reports'].items()if d.get('eligible')and d['sampled_version']==fresh[int(f)]['version']]
  reason='sustained_missing_current_relay'if sustained else'current_version_source_failure'if failed else None
  return dict(time_ns=t,reason=reason,missing_relays=missing,sustained_missing_relays=sustained,missing_streak={str(n):v for n,v in sorted(self.missing_streak.items())},failure_sources=failed,fresh_sources=[f for f in(0,1)if f in fresh],current_paths=self.current,source_failure_reports=event['source_failure_reports'],report_provenance=[dict(node=r['node'],version=r['version'],stamp_ns=r['stamp_ns'],received_ns=r['received_ns'])for r in obs['reports']])

 def constraint_view(self,active,t):
  domains,row=super().constraint_view(active,t)
  exhausted=self.enable_install_budget and self.reservations.get(t//WINDOW,0)>=1
  if exhausted:
   # An identical confirmed route can still be evaluated without installation.
   hold_ok,_=self.hold_admission(self.current_observation,self.current)
   domains={a:[p for p in ps if p==self.current and hold_ok]for a,ps in domains.items()}
   row['available']=[bool(domains[a])for a in range(4)]
   row['witnesses']={str(a):domains[a][0]if domains[a]else None for a in range(4)}
   row['pool_size']=len(domains[0])
  row['install_budget_exhausted']=exhausted
  row['install_reservation_window']=t//WINDOW
  return domains,row

 def search_candidates(self,action,candidates,fresh,active):
  # Current-version source failures motivate alternatives without pretending
  # that unknown end-to-end service was measured or predicting their outcome.
  if self.enable_interrupt and self.safety_evidence and self.safety_evidence['reason']:
   alternatives=[p for p in candidates if p!=self.current]
   if alternatives:candidates=alternatives
  return super().search_candidates(action,candidates,fresh,active)

 def interrupt_feedback(self,obs,evidence):
  p=self.pending;t=obs['time_ns']
  if not self.enable_interrupt or p is None or evidence['reason']is None or len(evidence['fresh_sources'])!=2 or t>=self.action_stop_ns or t<p['time_ns']+5_000_000_000:return None
  # A received failure must concern the expected version of this transaction.
  # A missing relay is path-specific and may concern the observed installed
  # path while a newer installation is still unconfirmed.
  reports={r['node']:r for r in obs['reports']}
  if evidence['reason']=='current_version_source_failure' and not any(reports[f]['version']==p['reward_expected_versions'][f]and reports[f]['stamp_ns']>=p['time_ns']for f in evidence['failure_sources']):return None
  # Already available qualified credit takes precedence over censoring.
  fb=self.cached_feedback(obs,reports)
  if fb is not None:return fb
  reason='safety_interrupt:'+evidence['reason']
  row=dict(decision=p['decision'],action=p['action'],time_ns=t,cohort_start_ns=p['time_ns'],cohort_end_ns=p['time_ns'],planned_reward_bucket=p.get('reward_bucket'),offered=[],timely=[],probabilities=None,reward=None,missing_reason=reason,updated_action=None,inputs=[r for f in(0,1)if(r:=reports.get(f))is not None],charged_install_budget_bytes=p['install_budget_bytes'],feedback_protocol='version_aligned_one_bucket',expected_versions=list(p['reward_expected_versions']),version_bucket_evidence=[],missing_sources=[],source_version_confirmation=p.get('reward_confirmation',[]),deadline_ns=p['time_ns']+30_000_000_000,minimum_offered_per_source=20,window_buckets=1,censored=True,safety_evidence=evidence)
  self.feedbacks.append(row);self.pending=None
  if self.installation and not self.installation.closed:
   self.installation.closed=True;self.installation.outcome='safety_interrupted'
  self.safety_events.append(dict(time_ns=t,decision=p['decision'],reason=reason,evidence=evidence))
  return row

 def step(self,obs):
  self.current_observation=obs;cost=self.observe_cost(obs)
  self.safety_evidence=self.assess_safety(obs)
  early=self.interrupt_feedback(obs,self.safety_evidence)
  reply,row=super().step(obs)
  if early is not None:
   if row['feedback']is not None:raise ValueError('two feedback records in one step')
   row['feedback']=early
  d=row['decision']
  if d is not None and d['paths']:
   window=d['time_ns']//WINDOW;before=self.reservations.get(window,0)
   if self.enable_install_budget and before>=1:raise ValueError('unfunded installation')
   self.reservations[window]=before+1
   allocation=dict(decision=d['decision'],time_ns=d['time_ns'],window=window,used_before=before,reservation_bytes=INSTALL_RESERVATION,budget_enabled=self.enable_install_budget)
   self.install_reservations.append(allocation);d['install_reservation']=allocation
  row['safety_assessment']=self.safety_evidence;row['cost_observation']=cost
  return reply,row
