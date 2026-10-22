"""Existing deterministic routing and transactions with advertised source pacing."""
from wsn.mechanism_controller import MechanismController
class BudgetController(MechanismController):
    def __init__(self,*args,pacing=False,evidence_gate=False,**kwargs):
        self.pacing=pacing
        self.evidence_gate=evidence_gate
        super().__init__(*args,**kwargs)
    def fresh_limit(self,node,report):
        if self.pacing and node<2 and report.get('period_s')==15:return 16_000_000_000
        return super().fresh_limit(node,report)
    def positive_recovery_evidence(self):
        bad=self.service_evidence.get('known',False)and self.service_evidence['worst_timely']<.8
        failed=bool(self.safety_evidence and self.safety_evidence['failure_sources'])
        return bool(bad or failed)
    def assess_safety(self,obs):
        evidence=super().assess_safety(obs)
        if self.evidence_gate and evidence['reason']=='sustained_missing_current_relay':
            bad=self.service_evidence.get('known',False)and self.service_evidence['worst_timely']<.8
            if not bad and not evidence['failure_sources']:
                evidence['unconfirmed_missing_only']=True;evidence['reason']=None
        return evidence
    def constraint_view(self,active,t):
        domains,row=super().constraint_view(active,t)
        if self.evidence_gate and self.sequence>0:
            allowed=self.positive_recovery_evidence()
            row['evidence_qualified_admission']={'allowed':allowed,'geometry_available':list(row['available']),'unknown_is_not_failure':True}
            if not allowed:
                row['available']=[False]*4;row['witnesses']={str(a):None for a in range(4)}
                domains={a:[]for a in range(4)}
        return domains,row
    def step(self,obs):
        reply,row=super().step(obs)
        if self.evidence_gate and row.get('rejection')=='all_arms_infeasible'and row.get('constraints',{}).get('evidence_qualified_admission',{}).get('allowed')is False:
            row['rejection']='no_positive_recovery_evidence'
        return reply,row
