"""Selected-only UCB and explicitly bounded unconfirmed installations.

An installation budget exit is absence of confirmation, not proof of failure.
Late matching received reports may reconcile the route without retroactive reward.
"""
from wsn.installation import Installation
from wsn.transaction_controller import TransactionController


class BoundedInstallation(Installation):
    def __init__(self, decision, time_ns, paths, retry_limit=1, deadline_ns=10_000_000_000):
        super().__init__(decision, time_ns, paths, retry_limit)
        self.deadline_ns = time_ns + deadline_ns

    def observe(self, obs):
        t = obs['time_ns']
        if self.closed and self.outcome != 'abandoned_unconfirmed':
            return None
        was_closed = self.closed
        fresh = {r['node']: r for r in obs['reports'] if r['node'] < 2 and 0 <= t-r['stamp_ns'] <= 8_000_000_000}
        for f, r in fresh.items():
            if not r['stamp_ns'] <= r['received_ns'] <= t:
                raise ValueError('future installation confirmation')
            if r['version'] == self.decision and r['stamp_ns'] >= self.time_ns and f not in self.confirmations:
                self.confirmations[f] = dict(assessed_ns=t, stamp_ns=r['stamp_ns'], received_ns=r['received_ns'], version=r['version'])
        missing = [f for f in (0, 1) if f not in self.confirmations]
        targets = []
        if not missing:
            self.closed = True
            self.outcome = 'confirmed'
        elif not was_closed and t >= self.deadline_ns:
            self.closed = True
            self.outcome = 'abandoned_unconfirmed'
        elif not was_closed and t >= self.time_ns + 5_000_000_000:
            targets = [f for f in missing if self.attempts[f] < self.retry_limit and t >= self.time_ns+(self.attempts[f]+1)*5_000_000_000]
            for f in targets:
                self.attempts[f] += 1
        if was_closed and missing:
            return None
        row = dict(decision=self.decision, time_ns=t, missing_sources=missing, retry_sources=targets,
                   retry_counts=list(self.attempts), confirmations={str(k):v for k,v in sorted(self.confirmations.items())},
                   closed=self.closed, outcome=self.outcome, installation_deadline_ns=self.deadline_ns,
                   exit_scope='unconfirmed installation budget; no assertion of physical failure',
                   late_confirmation=was_closed and not missing)
        self.history.append(row)
        return row


class ObservableController(TransactionController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.score_only = '_scoreonly_' in self.policy
        self.bounded_install = '_installexit_' in self.policy
        if self.score_only:
            self.exploration_cap = 0
        if self.bounded_install:
            self.retry_limit = 1

    def exploration_candidates(self, allowed, attempts):
        if self.score_only:
            return []
        return super().exploration_candidates(allowed, attempts)

    def step(self, obs):
        reply, row = super().step(obs)
        d = row['decision']
        if d is not None:
            d['observable_admission'] = dict(explicit_exposure_cap=self.exploration_cap,
                selector='feasible UCB score' if self.score_only else 'single-attempt exposure',
                unconfirmed_install_deadline_ns=10_000_000_000 if self.bounded_install else 15_000_000_000,
                no_censored_reward_imputation=True)
            if d['paths'] and self.bounded_install:
                current = BoundedInstallation(d['decision'], d['time_ns'], d['paths'])
                self.installation = current
                self.installations[-1] = current
        fb = row['feedback']
        if fb is not None and fb.get('missing_reason') == 'installation_unconfirmed':
            fb['exit_kind'] = 'installation_budget_exit' if self.bounded_install else 'legacy_installation_timeout'
            fb['physical_failure_asserted'] = False
        return reply, row
