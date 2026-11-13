"""Confirmation-contract ablation (registered 2026-11-03 before any ablation run).

Only premise T of Proposition 1 is changed. Joint (baseline) keeps the
implemented global contract: after an unconfirmed installation exit the
transaction stays open for every admission predicate. PostExit releases the
transaction once the bounded installation wait has ended unconfirmed and no
feedback transaction is pending; the controller then reasons from the
per-source state it already reconciles from received report versions
(base_controller.view). No threshold, failure-eligibility rule (F_s),
wire format, native code, byte budget or report schedule is changed.
"""
from budget_controller import BudgetController
from horizon_controller import HorizonController,HorizonCohortController,HorizonClosingController

class PostExitMixin:
    def __init__(self,*a,contract='joint',**k):
        self.contract=contract;self.contract_events=[]
        super().__init__(*a,**k)
    def step(self,obs):
        inst=self.installation
        if(self.contract=='post_exit'and inst is not None and inst.closed
           and inst.outcome=='abandoned_unconfirmed'and self.pending is None):
            self.contract_events.append(dict(time_ns=obs['time_ns'],released_decision=inst.decision,
                exit_outcome=inst.outcome,missing_sources=[f for f in(0,1)if f not in inst.confirmations],
                observed_current=[list(p)for p in self.current],rule='post-exit release; per-source observed state'))
            self.installation=None
        return super().step(obs)

def make(base):
    return type('PostExit'+base.__name__,(PostExitMixin,base),{})
FACTORIES={'full_v2':make(BudgetController),'horizon':make(HorizonController),
           'cohort':make(HorizonCohortController),'closing':make(HorizonClosingController)}
