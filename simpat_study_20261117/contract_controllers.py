"""Confirmation-contract arms for the SIMPAT simulation study (registered 2026-11-17).

Only one premise of Proposition 1 is changed.  Under the implemented joint
contract an installation transaction that closed as ``abandoned_unconfirmed``
keeps every admission predicate in the "installation not confirmed" state.
Under ``post_exit`` that transaction is released once the bounded wait has
ended and no feedback transaction is pending.  The controller then reasons from
the per-source observed configuration that ``base_controller.view`` already
rebuilds from received report versions.  Thresholds, eligibility rules,
reporting, budgets, wire formats and route scoring are unchanged.

``install_exit_s`` overrides the bounded installation wait (sensitivity stage).
"""
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent
BASE = STUDY.parent / 'control_budget_study_20261015'
for p in (BASE, BASE / 'engine'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import wsn.controller  # noqa: E402,F401  (fixes the engine's import order, as fast_native_run does)
from budget_controller import BudgetController  # noqa: E402
from horizon_controller import (HorizonController, HorizonCohortController,  # noqa: E402
                                HorizonClosingController)

CONTRACTS = ('joint', 'post_exit')


class ContractMixin:
    def __init__(self, *args, contract='joint', install_exit_s=None, **kwargs):
        if contract not in CONTRACTS:
            raise ValueError(contract)
        self.contract = contract
        super().__init__(*args, **kwargs)
        if install_exit_s is not None:
            if not 1 <= install_exit_s <= 60:
                raise ValueError('installation wait outside registered range')
            self.install_exit_ns = int(install_exit_s * 1_000_000_000)
        self.contract_releases = []

    def step(self, obs):
        release = None
        i = self.installation
        if (self.contract == 'post_exit' and i is not None and i.closed
                and i.outcome == 'abandoned_unconfirmed' and self.pending is None):
            release = dict(time_ns=obs['time_ns'], decision=i.decision,
                           desired_paths=[list(p) for p in i.paths] if getattr(i, 'paths', None) else None,
                           observed_paths=[list(p) for p in self.current],
                           scope='bounded wait ended without confirmation; joint target released, '
                                 'observed per-source versions retained')
            self.contract_releases.append(release)
            self.installation = None
        reply, row = super().step(obs)
        row['contract'] = self.contract
        row['contract_release'] = release
        return reply, row


class JointBudget(ContractMixin, BudgetController):
    pass


class JointHorizon(ContractMixin, HorizonController):
    pass


class JointCohort(ContractMixin, HorizonCohortController):
    pass


class JointClosing(ContractMixin, HorizonClosingController):
    pass


FACTORIES = {'full_v2': JointBudget, 'horizon': JointHorizon,
             'cohort': JointCohort, 'closing': JointClosing, 'legacy': JointBudget}
