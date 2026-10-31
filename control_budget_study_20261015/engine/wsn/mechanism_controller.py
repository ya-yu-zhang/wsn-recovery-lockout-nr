"""Non-learning mechanism controls; only visible snapshots guide recovery."""
from wsn.candidate_controller import CandidateController

def hop_reference(candidates,current,service):
    rows=[dict(paths=p,score=sum(len(v)-1 for v in p),objectives=None) for p in candidates]
    poor=service.get('known',False) and service['worst_timely']<.8
    alt=[r for r in rows if r['paths']!=current]
    choice=alt if poor and alt else rows
    best=min(choice,key=lambda r:(r['score'],r['paths'])) if choice else None
    return (best['paths'] if best else None),rows,dict(mode='geometry_hop_reference',
        selected_objectives=None,poor_settled_service=poor,
        scope='minimum total hop count within the common admitted pool; not ETX, Dijkstra or a standardized routing protocol')

class MechanismController(CandidateController):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.install_exit_ns=15_000_000_000 if '_install15_' in self.policy else 10_000_000_000
        if self.is_bandit:raise ValueError('mechanism validation uses non-learning controls')
        assert self.bounded_install and self.score_only
    def search_candidates(self,action,candidates,fresh,active):
        if '_hopref_' not in self.policy:return super().search_candidates(action,candidates,fresh,active)
        if self.enable_interrupt and self.safety_evidence and self.safety_evidence['reason']:
            alt=[p for p in candidates if p!=self.current]
            if alt:candidates=alt
        return hop_reference(candidates,self.current,self.service_evidence)
    def step(self,obs):
        reply,row=super().step(obs);d=row['decision']
        if d is not None:
            d['observable_admission']['unconfirmed_install_deadline_ns']=self.install_exit_ns
            d['mechanism_treatment']=dict(installation_deadline_ns=self.install_exit_ns,
                 installation_retry_limit=self.retry_limit,learning_enabled=False,explicit_exposure=False,
                 search='hop_reference' if '_hopref_' in self.policy else 'fixed_operator')
            if d['paths']:self.installation.deadline_ns=d['time_ns']+self.install_exit_ns
        return reply,row
