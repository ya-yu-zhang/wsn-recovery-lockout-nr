"""Pacing-aware received-observation horizons, with no extra wire traffic."""
from budget_controller import BudgetController
from cadence_controller import CohortController,ClosingController

class HorizonController(BudgetController):
    def fresh_limit(self,node,report):
        if self.pacing and node<2:return 16_000_000_000
        return super().fresh_limit(node,report)

class HorizonCohortController(CohortController):
    def fresh_limit(self,node,report):
        if self.pacing and node<2:return 16_000_000_000
        return super().fresh_limit(node,report)

class HorizonClosingController(ClosingController):
    def fresh_limit(self,node,report):
        if self.pacing and node<2:return 16_000_000_000
        return super().fresh_limit(node,report)
