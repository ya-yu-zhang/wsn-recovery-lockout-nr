"""Bounded exploration under received evidence; relay congestion stays unknown."""
from wsn.learning_controller import LearningController,exposure_gate,NS
from wsn.rng import uniform

def candidate_gate(c,allowed,plain=False):
    o=c.current_observation;t=o['time_ns'];reasons=[]
    fresh={r['node']:r for r in o['reports'] if 0<=t-r['stamp_ns']<=c.fresh_limit(r['node'],r)}
    valid=[f for f in c.feedbacks if f['reward'] is not None]
    if c.pending is not None:reasons.append('pending_transaction')
    if not valid:reasons.append('no_prior_qualified_feedback')
    if not all(f in fresh for f in (0,1)):reasons.append('missing_fresh_source')
    if c.installation is not None and (not c.installation.closed or c.installation.outcome!='confirmed'):
        reasons.append('installation_not_confirmed')
    matched=all(f in fresh and fresh[f]['version'] in c.version_paths and c.version_paths[fresh[f]['version']][f]==c.current[f] for f in (0,1))
    if not matched:reasons.append('unmatched_observed_paths')
    failures=[f for f in (0,1) if f in fresh and fresh[f].get('current_n',0)>=20 and fresh[f].get('current_failed',0)/fresh[f]['current_n']>=.2]
    service=c.service_evidence
    poor=bool(service.get('known',False) and service['worst_timely']<.8)
    source_known=all(f in fresh and fresh[f]['cca']>0 for f in (0,1))
    busy=max((fresh[f]['busy']/fresh[f]['cca'] for f in (0,1) if f in fresh and fresh[f]['cca']>0),default=None)
    queue=max((fresh[f]['depth'] for f in (0,1) if f in fresh),default=None)
    if not plain:
        if not failures and not poor:reasons.append('no_received_failure_or_service_deficit')
        if not source_known:reasons.append('source_congestion_unknown')
        elif busy>.25:reasons.append('source_busy_above_quarter')
        if queue is not None and queue>2:reasons.append('source_queue_above_two')
    exposure_ids={d['decision'] for d in c.logs if d['selection_phase']=='event_exploration'}
    closed=max((f['time_ns'] for f in c.feedbacks if f.get('decision') in exposure_ids),default=None)
    if closed is not None and t-closed<20*NS:reasons.append('exposure_transaction_cooldown')
    if c.reservations.get(t//(20*NS),0)>=1:reasons.append('installation_budget_used')
    credited={f['action'] for f in valid};witnesses={};unmeasured={}
    eligible=[]
    for a in allowed:
        if a==0 or a in credited or a in c.event_attempts:continue
        witness=c.candidate_witnesses.get(str(a))
        if witness is None or any(n not in fresh and n!=9 for p in witness for n in p):continue
        eligible.append(a);witnesses[str(a)]=witness
        unmeasured[str(a)]=sorted({n for p in witness for n in p[1:-1] if fresh[n]['cca']==0})
    if not eligible:reasons.append('no_fresh_feasible_uncredited_candidate')
    if len(c.event_attempts)>=3:reasons.append('exposure_cap')
    eligible.sort(key=lambda a:(uniform(c.selection_seed,'gated-single-exposure',a),a))
    return dict(mode='plain3' if plain else 'candidate2',time_ns=t,admitted=not reasons,reasons=reasons,
                eligible=eligible,cap=3,attempts_before=list(c.event_attempts),credited_actions=sorted(credited),
                failure_sources=failures,poor_received_service=poor,received_service=service,
                source_congestion_known=source_known,source_busy_max=busy,source_queue_max=queue,
                candidate_witnesses=witnesses,unmeasured_candidate_relays=unmeasured,
                previous_exposure_closed_ns=closed,prior_qualified_feedback=len(valid),
                uncertainty_scope='source-local admission only; unmeasured relay congestion is not low congestion and no service guarantee is implied')

class CandidateController(LearningController):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.candidate_witnesses={}
        if '_gated_' in self.policy:self.exploration_cap=3
    def constraint_view(self,active,t):
        domains,row=super().constraint_view(active,t)
        self.candidate_witnesses=row['witnesses']
        return domains,row
    def exploration_candidates(self,allowed,attempts):
        if attempts is None or '_scoreonly_' in self.policy:return []
        if '_legacygate_' in self.policy:
            self._admission=exposure_gate(self,allowed);self._admission['mode']='legacy'
        else:self._admission=candidate_gate(self,allowed,plain='_plain3_' in self.policy)
        self.admission_checks.append(self._admission)
        return self._admission['eligible'] if self._admission['admitted'] else []
