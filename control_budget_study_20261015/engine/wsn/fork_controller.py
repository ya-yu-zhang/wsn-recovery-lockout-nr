"""Deterministic same-observation branches; no future labels or state restore."""
import copy,hashlib,json
from wsn.mechanism_controller import MechanismController
NS=1_000_000_000
def clean(x):
    if isinstance(x,dict):return{k:clean(v)for k,v in x.items()if k not in ('compute_wall_ns','constraint_wall_ns')}
    if isinstance(x,(tuple,list)):return[clean(v)for v in x]
    return x
def digest(x):return hashlib.sha256(json.dumps(clean(x),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def eligibility(available,pending,installation_closed,budget_exhausted,shared):
    reasons=[]
    if pending:reasons.append('pending_transaction')
    if not installation_closed:reasons.append('installation_open')
    if budget_exhausted:reasons.append('install_budget_used')
    if not all(available):reasons.append('not_all_arms_feasible')
    if not shared:reasons.append('candidate_pools_differ')
    return reasons
class ForkController(MechanismController):
    def __init__(self,*args,fork_time_ns=None,fork_arm=None,**kwargs):
        super().__init__(*args,**kwargs)
        if (fork_time_ns is None)!=(fork_arm is None):raise ValueError('Both fork time and arm are required')
        if fork_arm is not None and fork_arm not in range(4):raise ValueError('invalid fork arm')
        self.requested_fork_time=fork_time_ns;self.requested_fork_arm=fork_arm
        self.initial_action_stop_ns=self.action_stop_ns;self.state_candidates=[];self.fork_info=None;self._candidate=None
    def constraint_view(self,active,t):
        domains,row=super().constraint_view(active,t)
        shared=all(domains[a]==domains[0]for a in range(4))
        reasons=eligibility(row['available'],self.pending is not None,self.installation is None or self.installation.closed,row['install_budget_exhausted'],shared)
        snapshot=dict(time_ns=t,observation=copy.deepcopy(self.current_observation),current_paths=self.current,memory=copy.deepcopy(self.memory),
            visible_versions=copy.deepcopy(self.visible_versions),version_paths=copy.deepcopy(self.version_paths),last_pdr=self.last_pdr,sequence=self.sequence,
            service_evidence=copy.deepcopy(self.service_evidence),safety_evidence=copy.deepcopy(self.safety_evidence),
            reservations=copy.deepcopy(self.reservations),constraint=clean(row),common_candidate_pool=copy.deepcopy(domains[0]),
            policy_before_selection=self.policy,initial_action_stop_ns=self.action_stop_ns,
            installation_state=None if self.installation is None else dict(decision=self.installation.decision,closed=self.installation.closed,outcome=self.installation.outcome))
        self._candidate=dict(time_ns=t,eligible=not reasons,reasons=reasons,snapshot=clean(snapshot))
        if t==self.requested_fork_time:
            if reasons:raise ValueError('Selected reference state became ineligible: '+str(reasons))
            if self.fork_info is not None:raise ValueError('Duplicate fork')
            self.policy=self.policy.replace('force0_','force'+str(self.requested_fork_arm)+'_',1)
        return domains,row
    def step(self,obs):
        self._candidate=None
        if self.requested_fork_time is not None and obs['time_ns']>self.requested_fork_time and self.fork_info is None:
            raise ValueError('Reference fork time not reached as a decision')
        reply,row=super().step(obs);d=row['decision'];c=self._candidate
        if c is not None:
            c['decision_emitted']=d is not None
            if d is not None:
                c['snapshot']['context']=d['context'];c['snapshot_sha256']=digest(c['snapshot']);c['decision']=d['decision']
            self.state_candidates.append(copy.deepcopy(c));row['fork_candidate']=copy.deepcopy(c)
        else:row['fork_candidate']=None
        if d is not None and obs['time_ns']==self.requested_fork_time:
            assert c['eligible']and d['action']==self.requested_fork_arm
            self.fork_info=dict(time_ns=obs['time_ns'],decision=d['decision'],arm=d['action'],snapshot_sha256=c['snapshot_sha256'],snapshot=c['snapshot'],
                post_fork_new_decisions_disabled=True,installation_retries_and_received_feedback_preserved=True,online_learning=False)
            self.action_stop_ns=obs['time_ns']+1
        row['fork_control']=dict(requested_time_ns=self.requested_fork_time,requested_arm=self.requested_fork_arm,
            forked=self.fork_info is not None,effective_action_stop_ns=self.action_stop_ns)
        return reply,row
