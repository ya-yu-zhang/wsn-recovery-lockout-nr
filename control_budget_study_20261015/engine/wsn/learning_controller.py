"""Registered selected-feedback diagnosis; no new observations or rewards."""
import math
import numpy as np
from wsn.observable_controller import ObservableController
from wsn.rng import uniform

NS=1_000_000_000

def exposure_gate(c, allowed):
    o=c.current_observation;t=o['time_ns']
    fresh={r['node']:r for r in o['reports'] if 0<=t-r['stamp_ns']<=c.fresh_limit(r['node'],r)}
    used={n for p in c.current for n in p[:-1]}
    reasons=[]
    if c.pending is not None:reasons.append('pending_transaction')
    valid=[f for f in c.feedbacks if f['reward'] is not None]
    if not valid:reasons.append('no_prior_qualified_feedback')
    if not all(f in fresh for f in (0,1)):reasons.append('missing_fresh_source')
    confirmed=c.installation is None or (c.installation.closed and c.installation.outcome=='confirmed')
    if not confirmed:reasons.append('installation_not_confirmed')
    matched=all(f in fresh and fresh[f]['version'] in c.version_paths and c.version_paths[fresh[f]['version']][f]==c.current[f] for f in (0,1))
    if not matched:reasons.append('unmatched_observed_paths')
    failure=[]
    for f in (0,1):
        r=fresh.get(f)
        if r is not None and r.get('current_n',0)>=20 and r.get('current_failed',0)/r['current_n']>=.2:failure.append(f)
    if not failure:reasons.append('no_received_current_failure')
    known=used<=set(fresh) and all(fresh[n]['cca']>0 for n in used)
    if not known:reasons.append('congestion_unknown')
    busy=max((fresh[n]['busy']/fresh[n]['cca'] for n in used if n in fresh and fresh[n]['cca']>0),default=None)
    queue=max((fresh[n]['depth'] for n in used if n in fresh),default=None)
    if known and busy>.25:reasons.append('busy_above_quarter')
    if known and queue>2:reasons.append('queue_above_two')
    closed=max((f['time_ns'] for f in c.feedbacks),default=None)
    if closed is not None and t-closed<20*NS:reasons.append('transaction_cooldown')
    if c.reservations.get(t//(20*NS),0)>=1:reasons.append('installation_budget_used')
    credited={f['action'] for f in valid}
    eligible=[a for a in allowed if a!=0 and a not in credited and a not in c.event_attempts]
    if not eligible:reasons.append('no_uncredited_nonresource_arm')
    if len(c.event_attempts)>=3:reasons.append('exposure_cap')
    eligible.sort(key=lambda a:(uniform(c.selection_seed,'gated-single-exposure',a),a))
    return dict(time_ns=t,admitted=not reasons,reasons=reasons,eligible=eligible,used_nodes=sorted(used),
                fresh_nodes=sorted(fresh),failure_sources=failure,congestion_known=known,max_busy=busy,max_queue=queue,
                previous_transaction_closed_ns=closed,prior_qualified_feedback=len(valid),
                attempts_before=list(c.event_attempts),credited_actions=sorted(credited),cap=3)

class LearningController(ObservableController):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.gated='_gated_' in self.policy
        self.freeze_after_four='_freeze4_' in self.policy
        if self.gated:self.exploration_cap=3
        self.admission_checks=[];self._admission=None;self.freeze_time_ns=None
    def exploration_candidates(self,allowed,attempts):
        if not self.gated:return super().exploration_candidates(allowed,attempts)
        if attempts is None:return []
        self._admission=exposure_gate(self,allowed);self.admission_checks.append(self._admission)
        return self._admission['eligible'] if self._admission['admitted'] else []
    def step(self,obs):
        if self.freeze_after_four and sum(self.bandit.updates)>=4:
            self.train_bandit=False
            if self.freeze_time_ns is None:self.freeze_time_ns=obs['time_ns']
        self._admission=None
        reply,row=super().step(obs)
        row['learning_admission']=self._admission
        row['learning_freeze']=dict(enabled=self.freeze_after_four,updates=sum(self.bandit.updates),
                                    training_enabled=self.train_bandit,freeze_time_ns=self.freeze_time_ns)
        d=row['decision']
        if d is not None:
            x=np.asarray(d['context'],dtype=float)
            if self.selection_mode=='intercept':x=np.array([x[0]]+[0.]*(len(x)-1))
            means=[];bonuses=[]
            for a in range(4):
                v=np.linalg.solve(self.bandit.A[a],x)
                means.append(float(self.bandit.b[a]@v))
                bonuses.append(float(self.bandit.alpha*math.sqrt(max(0.,x@v))))
            d['score_decomposition']=dict(mean=means,bonus=bonuses,model_context=x.tolist(),
                                          A_condition_numbers=[float(np.linalg.cond(A)) for A in self.bandit.A],
                                          scores=[m+b for m,b in zip(means,bonuses)])
            d['learning_admission']=self._admission
            d['learning_freeze']=dict(row['learning_freeze'])
        return reply,row
