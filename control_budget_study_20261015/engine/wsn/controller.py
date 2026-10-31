from wsn.base_controller import Controller as BaseController,LinUCB,POINTS,INITIAL,CATALOG
from wsn.installation import Installation
from wsn.version_failures import assess_report

class Controller(BaseController):
    def hold_admission(self,obs,proposal):
        """Suppress identical-route installation only with fresh, confirmed evidence."""
        reports,fresh,active,x,event=self.view(obs)
        if any(f not in fresh for f in (0,1)):return False,'missing_fresh_source'
        if proposal!=self.current:return False,'route_changed'
        if any(n not in active for path in proposal for n in path):return False,'route_not_observably_feasible'
        if any(v.get('n') is None or v['n']<20 for v in event['source_failure_reports'].values()):return False,'insufficient_current_version_evidence'
        if any(v['eligible'] for v in event['source_failure_reports'].values()):return False,'current_version_failure'
        if self.installation is not None and (not self.installation.closed or self.installation.outcome!='confirmed'):
            return False,'installation_not_confirmed'
        for f in (0,1):
            version=fresh[f]['version']
            if version not in self.version_paths or self.version_paths[version][f]!=proposal[f]:return False,'unknown_installed_version'
        return True,'identical_confirmed_feasible_route'
    def __init__(self,policy,report_profile='full5',points=None,action_stop_ns=80_000_000_000,selection_seed=0):
        super().__init__(policy,report_profile,points=points,action_stop_ns=action_stop_ns,selection_seed=selection_seed)
        self.retry_limit=2 if '_retry_' in policy else 0;self.unknown_risk='_unknown_' in policy
        if '_risk4_' in policy:self.search_mode='riskfirst'
        self.installation=None;self.installations=[];self.retries=[]
        self.failure_mode='current' if '_current_' in policy else 'mixed'
        self.feedback_grace_ns=5_000_000_000 if '_grace5_' in policy else 0
        self.closed_buckets=None;self.feedback_waits=[]
        if self.feedback_grace_ns or '_cache20_' in policy:
            from wsn.feedback import ClosedBucketCache
            self.closed_buckets=ClosedBucketCache()
    def view(self,obs):
        reports,fresh,active,x,event=super().view(obs);details={}
        for f in (0,1):
            r=fresh.get(f)
            if r is None:details[str(f)]=dict(fresh=False,eligible=False);continue
            if self.failure_mode=='current':
                result=assess_report(r,obs['time_ns'])
                details[str(f)]=dict(fresh=True,n=result.n,failed=result.failed,fraction=result.fraction,
                    stamp_ns=r['stamp_ns'],sampled_version=result.sampled_version,
                    reason=result.reason,eligible=result.eligible,mode='current')
                continue
            n=r['n'];failed=r['failed']
            if not 0<=failed<=n:raise ValueError('inconsistent failure report')
            fraction=failed/max(1,n)
            details[str(f)]=dict(fresh=True,n=n,failed=failed,fraction=fraction,stamp_ns=r['stamp_ns'],eligible=n>=20 and fraction>=.2)
        high=any(r['eligible'] for r in details.values())
        event.update(source_failure_reports=details,transmission_failure=high,trigger_failure=high and '_failure_' in self.policy)
        return reports,fresh,active,x,event
    def feedback(self,obs,reports):
        if self.closed_buckets is not None:return self.cached_feedback(obs,reports)
        return self.latest_report_feedback(obs,reports)
    def cached_feedback(self,obs,reports):
        self.closed_buckets.observe(obs)
        p=self.pending;t=obs['time_ns']
        if p is None or t<p['time_ns']+20_000_000_000:return None
        due=p['time_ns']+20_000_000_000;deadline=due+self.feedback_grace_ns
        bs=[p['bucket']+i for i in range(3)]
        counts,evidence,missing=self.closed_buckets.cohort(bs)
        if any(missing) and t<deadline:
            row=dict(decision=p['decision'],time_ns=t,due_ns=due,deadline_ns=deadline,missing_closed_buckets=missing,
                     available_bucket_evidence=evidence,extra_packets_requested=0)
            if not self.feedback_waits or self.feedback_waits[-1]['decision']!=p['decision']:self.feedback_waits.append(row)
            return None
        reason='closed generation buckets not received before deadline' if any(missing) else None
        timely=[sum(obs['timely_buckets'].get(str(b),[0,0])[f] for b in bs) for f in (0,1)]
        reward=None;probs=None
        if reason is None and len(counts)==2 and all(counts):
            probs=[d/n for d,n in zip(timely,counts)]
            if any(v<0 or v>1 for v in probs):raise ValueError('inconsistent cached feedback')
            reward=.75*sum(probs)/2+.25*min(probs)-.05*min(p['fe']/64,1)-.05*min(p['install_budget_bytes']/5994,1)
            self.last_pdr=sum(probs)/2
            if self.is_bandit and self.train_bandit:self.bandit.update(p['action'],p['context'],reward)
        elif reason is None:reason='empty offered cohort'
        waited=any(w['decision']==p['decision'] for w in self.feedback_waits)
        row=dict(decision=p['decision'],action=p['action'],time_ns=t,cohort_start_ns=p['time_ns'],cohort_end_ns=p['time_ns']+15_000_000_000,
                 offered=counts,timely=timely,probabilities=probs,reward=reward,missing_reason=reason,
                 updated_action=p['action'] if reward is not None and self.is_bandit and self.train_bandit else None,
                 inputs=[r for f in (0,1) if (r:=reports.get(f)) is not None],charged_install_budget_bytes=p['install_budget_bytes'],
                 feedback_protocol='closed_cache_grace5' if self.feedback_grace_ns else 'closed_cache20',
                 bucket_evidence=evidence,missing_closed_buckets=missing,extra_wait_ns=max(0,t-due),
                 grace_budget_ns=self.feedback_grace_ns,recovered_after_wait=waited and reward is not None)
        self.feedbacks.append(row);self.pending=None;return row
    def latest_report_feedback(self,obs,reports):
        p=self.pending
        if p is None or obs['time_ns']<p['time_ns']+20_000_000_000:return None
        counts=[];reason=None;bs=[p['bucket']+i for i in range(3)]
        for f in (0,1):
            r=reports.get(f)
            if r is None or r['stamp_ns']<p['time_ns']+15_000_000_000:reason='source report missing or sampled before cohort end';break
            buckets=dict(r['buckets'])
            if any(b not in buckets for b in bs):reason='feedback cohort absent from report';break
            counts.append(sum(buckets[b] for b in bs))
        timely=[sum(obs['timely_buckets'].get(str(b),[0,0])[f] for b in bs) for f in (0,1)]
        reward=None;probs=None
        if reason is None and len(counts)==2 and all(counts):
            probs=[d/n for d,n in zip(timely,counts)]
            if any(v<0 or v>1 for v in probs):raise ValueError('inconsistent received feedback')
            reward=.75*sum(probs)/2+.25*min(probs)-.05*min(p['fe']/64,1)-.05*min(p['install_budget_bytes']/5994,1)
            self.last_pdr=sum(probs)/2
            if self.is_bandit and self.train_bandit:self.bandit.update(p['action'],p['context'],reward)
        elif reason is None:reason='empty offered cohort'
        row=dict(decision=p['decision'],action=p['action'],time_ns=obs['time_ns'],cohort_start_ns=p['time_ns'],cohort_end_ns=p['time_ns']+15_000_000_000,
            offered=counts,timely=timely,probabilities=probs,reward=reward,missing_reason=reason,updated_action=p['action'] if reward is not None and self.is_bandit and self.train_bandit else None,
            inputs=[r for f in (0,1) if (r:=reports.get(f)) is not None],charged_install_budget_bytes=p['install_budget_bytes'])
        self.feedbacks.append(row);self.pending=None;return row
    def step(self,obs):
        self.view(obs) # Validate visibility before any confirmation processing.
        if self.closed_buckets is not None:self.closed_buckets.observe(obs)
        install=self.installation.observe(obs) if self.installation else None
        if install and install['retry_sources']:
            if self.pending is None:raise ValueError('retry outside original feedback transaction')
            sources=install['retry_sources'];p=self.pending;p['install_budget_bytes']+=999*len(sources)
            retry=dict(decision=p['decision'],time_ns=obs['time_ns'],sources=sources,fe=0,declared_install_budget_bytes=999*len(sources),
                ordinal_by_source=[self.installation.attempts[f] for f in sources])
            self.retries.append(retry)
            reports,fresh,active,x,event=self.view(obs)
            chunks=['-2',str(p['decision']),'0',str(sum(1<<f for f in sources)),str(p['action'])]
            for path in p['paths']:chunks+=[str(len(path))]+list(map(str,path))
            return ' '.join(chunks),dict(kind='step',observation=obs,event=event,context=x,decision=None,feedback=None,constraints=None,installation=install,retry=retry)
        reply,row=super().step(obs);row['installation']=install;row['retry']=None
        if self.closed_buckets is not None:
            waiting=next((w for w in reversed(self.feedback_waits) if w['time_ns']==obs['time_ns']),None)
            if waiting is not None:
                event=row['event'];waiting['observed_event_blocked']=(obs['time_ns']<self.action_stop_ns and
                    (event['missing']>0 or event['busy']>.35 or event['source_queue']>2 or event.get('trigger_failure',False)))
            row['feedback_wait']=waiting
        if row['decision'] and row['decision']['paths'] and '_noop_' in self.policy:
            p=row['decision'];proposal=p['paths'];allowed,reason=self.hold_admission(obs,proposal)
            p['admission']={'suppressed':allowed,'reason':reason,'proposed_paths':proposal}
            if allowed:
                del self.version_paths[p['decision']]
                p['paths']=None;p['install_budget_bytes']=0;p['admitted_hold']=True
                reply=f"-3 {p['decision']} {p['fe']} {p['action']}"
        if row['decision'] and row['decision']['paths']:
            p=row['decision'];self.installation=Installation(p['decision'],p['time_ns'],p['paths'],self.retry_limit);self.installations.append(self.installation)
        return reply,row


OriginalController=Controller
from wsn.revision_controller import RevisionController
from wsn.aligned_controller import AlignedController
from wsn.safety_controller import SafetyController
from wsn.transaction_controller import TransactionController
def Controller(policy,*args,**kwargs):
    if '_reviewmechanism_' in policy:
        from wsn.mechanism_controller import MechanismController
        return MechanismController(policy,*args,**kwargs)
    if '_candidate2_' in policy:
        from wsn.candidate_controller import CandidateController
        return CandidateController(policy,*args,**kwargs)
    if '_learnstudy_' in policy:
        from wsn.learning_controller import LearningController
        return LearningController(policy,*args,**kwargs)
    if '_observable_' in policy:
        from wsn.observable_controller import ObservableController
        return ObservableController(policy,*args,**kwargs)
    return (TransactionController if '_transaction_' in policy else SafetyController if '_safe_' in policy else AlignedController if '_aligned_' in policy else RevisionController if "_ops_" in policy else OriginalController)(policy,*args,**kwargs)
